
import streamlit as st
import pandas as pd

from invoice_extractor import extract_invoice
from data_validator import validate_invoice
from po_matcher import match_invoice_to_po
from decision_engine import decide_invoice
from audit_logger import check_duplicate, record_run, get_history


st.set_page_config(
    page_title="AI Invoice Processing System",
    page_icon="🧾",
    layout="wide",
)

st.title("AI Invoice Processing System")
st.caption(
    "Invoice extraction, validation, purchase-order matching and audit history"
)


def display_table(dataframe, **kwargs):
    """Display mixed-type data safely without changing source data."""
    safe_df = dataframe.copy().astype(str)
    st.dataframe(safe_df, width="stretch", **kwargs)


# Load audit history
try:
    history = get_history() or []
except Exception as exc:
    history = []
    st.error(f"Could not load processing history: {exc}")


# Dashboard
approved_count = sum(
    row.get("decision") == "Approved" for row in history
)
rejected_count = sum(
    row.get("decision") == "Rejected" for row in history
)
review_count = sum(
    row.get("decision") == "Needs Review" for row in history
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Processed", len(history))
col2.metric("Approved", approved_count)
col3.metric("Rejected", rejected_count)
col4.metric("Needs Review", review_count)

overview_tab, process_tab, history_tab = st.tabs(
    ["Overview", "Process Invoice", "History"]
)


# Overview
with overview_tab:
    st.subheader("Recent Processing Activity")

    if history:
        recent = pd.DataFrame(history)
        columns = [
            col for col in [
                "timestamp",
                "file_name",
                "vendor_name",
                "invoice_number",
                "po_number",
                "invoice_total",
                "decision",
            ]
            if col in recent.columns
        ]

        if columns:
            display_table(
                recent[columns].head(10),
                hide_index=True,
            )
        else:
            st.info("No displayable history columns were found.")
    else:
        st.info("No invoices have been processed yet.")


# Process Invoice
with process_tab:
    st.subheader("Process a Vendor Invoice")

    uploaded_file = st.file_uploader(
        "Upload an invoice PDF",
        type=["pdf"],
        key="invoice_upload",
    )

    if uploaded_file is not None:
        st.write("Selected file:", uploaded_file.name)

        if st.button("Process Invoice", type="primary"):
            try:
                with st.status(
                    "Processing invoice...",
                    expanded=True,
                ) as status_box:

                    st.write("1. Extracting invoice details...")
                    extraction = extract_invoice(uploaded_file)

                    if not extraction.get("success"):
                        st.error(
                            extraction.get(
                                "error",
                                "Invoice extraction failed.",
                            )
                        )
                        status_box.update(
                            label="Extraction failed",
                            state="error",
                        )
                        st.stop()

                    fields = extraction.get("fields", {})

                    st.write("2. Validating extracted information...")
                    validation = validate_invoice(fields)

                    st.write("3. Matching purchase order...")
                    matching = match_invoice_to_po(fields)

                    st.write("4. Checking for duplicate invoices...")
                    duplicate = check_duplicate(
                        fields.get("vendor_name"),
                        fields.get("invoice_number"),
                    )

                    st.write("5. Applying decision rules...")
                    decision_result = decide_invoice(
                        validation,
                        matching,
                        is_duplicate=duplicate,
                    )

                    decision = decision_result.get(
                        "decision", "Needs Review"
                    )
                    reasons = decision_result.get("reasons", [])

                    st.write("6. Saving audit record...")
                    run_id = record_run(
                        file_name=uploaded_file.name,
                        invoice=fields,
                        decision=decision,
                        reasons=reasons,
                    )

                    status_box.update(
                        label="Processing completed",
                        state="complete",
                    )

                # Final decision
                st.subheader("Final Decision")

                if decision == "Approved":
                    st.success("Approved")
                elif decision == "Rejected":
                    st.error("Rejected")
                else:
                    st.warning("Needs Review")

                st.write("**Run ID:**", run_id)

                # Extracted fields
                st.subheader("Extracted Invoice Details")
                st.json(fields)

                st.write(
                    "**Extraction method:**",
                    extraction.get("extraction_method", "Unknown"),
                )
                st.write(
                    "**Extraction completeness:**",
                    f'{extraction.get("completeness_score", 0):.0%}',
                )

                # Validation report
                st.subheader("Validation Report")
                st.write(
                    "**Validation status:**",
                    validation.get("status", "Unknown"),
                )

                with st.expander("Debug: Decision Inputs", expanded=True):
                    st.write("**Duplicate detected:**", duplicate)

                    st.write("**Validation report**")
                    st.json(validation)

                    st.write("**PO matching report**")
                    st.json(matching)

                with st.expander("Passed checks"):
                    passed_checks = validation.get("passed_checks", [])
                    if passed_checks:
                        for item in passed_checks:
                            st.write(f"✅ {item}")
                    else:
                        st.write("No checks passed.")

                with st.expander("Failed checks"):
                    failed_checks = validation.get("failed_checks", [])
                    if failed_checks:
                        for item in failed_checks:
                            st.write(f"❌ {item}")
                    else:
                        st.write("No failed checks.")

                with st.expander("Missing information and warnings"):
                    missing = validation.get("missing_information", [])
                    warnings = validation.get("warnings", [])
                    extraction_warnings = extraction.get("warnings", [])

                    for item in missing:
                        st.write(f"⚠️ Missing: {item}")

                    for item in warnings:
                        st.write(f"⚠️ Validation: {item}")

                    for item in extraction_warnings:
                        st.write(f"⚠️ Extraction: {item}")

                    if not missing and not warnings and not extraction_warnings:
                        st.write("No missing information or warnings.")

                # PO matching
                st.subheader("PO Matching Report")
                st.write("PO found:", matching.get("po_found", False))
                st.write(
                    "Vendor verified:",
                    matching.get("vendor_verified", False),
                )
                st.write(
                    "Matching status:",
                    matching.get("decision", "Unknown"),
                )

                comparison = matching.get("comparison", {})
                if comparison:
                    comparison_table = pd.DataFrame([
                        {"Field": key, "Value": value}
                        for key, value in comparison.items()
                    ])
                    display_table(comparison_table, hide_index=True)

                # Decision reasons
                st.subheader("Decision Explanation")
                if reasons:
                    for reason in reasons:
                        st.write(f"- {reason}")
                else:
                    st.write("No decision reasons were returned.")

                st.caption(
                    "Invoices are approved only when the configured "
                    "validation and matching checks pass."
                )

            except Exception as exc:
                st.error(f"Processing error: {exc}")
                st.exception(exc)


# Processing History
with history_tab:
    st.subheader("Processing History")

    try:
        history = get_history() or []
    except Exception as exc:
        st.error(f"Could not retrieve history: {exc}")
        history = []

    if history:
        history_df = pd.DataFrame(history)

        columns = [
            col for col in [
                "run_id",
                "timestamp",
                "file_name",
                "vendor_name",
                "invoice_number",
                "po_number",
                "invoice_total",
                "decision",
                "reasons",
            ]
            if col in history_df.columns
        ]

        if columns:
            display_table(history_df[columns], hide_index=True)

            csv_data = history_df[columns].to_csv(index=False)
            st.download_button(
                "Download History as CSV",
                data=csv_data,
                file_name="invoice_processing_history.csv",
                mime="text/csv",
            )
        else:
            st.info("No displayable history columns were found.")
    else:
        st.info("Your processing history will appear here.")
