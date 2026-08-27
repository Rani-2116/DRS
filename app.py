import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime

# ---------------------------------------
# PAGE CONFIG
# ---------------------------------------

st.set_page_config(
    page_title="Derivative Reconciliation System",
    layout="wide"
)

st.title("Derivative Reconciliation System")

# ---------------------------------------
# SESSION STATE
# ---------------------------------------

if "result" not in st.session_state:
    st.session_state.result = None

# ---------------------------------------
# RESET
# ---------------------------------------

if st.button("Reset"):
    st.session_state.result = None
    st.rerun()

# ---------------------------------------
# FILE UPLOAD
# ---------------------------------------

source_file = st.file_uploader(
    "Upload Source File",
    type=["xlsx"]
)

target_file = st.file_uploader(
    "Upload Target File",
    type=["xlsx"]
)

tolerance = st.number_input(
    "Tolerance Amount",
    min_value=0,
    value=1000
)

# ---------------------------------------
# RUN RECON
# ---------------------------------------

if st.button("Run Reconciliation"):

    if source_file is None or target_file is None:
        st.error("Please upload both files.")
    else:

        source = pd.read_excel(source_file)
        target = pd.read_excel(target_file)

        source["Deal_ID"] = (
            source["Deal_ID"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        target["Deal_ID"] = (
            target["Deal_ID"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

        result = source.merge(
            target,
            on="Deal_ID",
            how="outer",
            suffixes=("_Source", "_Target"),
            indicator=True
        )

        result["Variance"] = (
            result["Amount_Source"].fillna(0)
            - result["Amount_Target"].fillna(0)
        )

        # Ageing

        if "Trade_Date" in result.columns:

            result["Trade_Date"] = pd.to_datetime(
                result["Trade_Date"],
                errors="coerce"
            )

            result["Age_Days"] = (
                datetime.today()
                - result["Trade_Date"]
            ).dt.days

        else:

            result["Age_Days"] = None

        # Status

        def get_status(row):

            if row["_merge"] == "left_only":
                return "Missing in Target"

            if row["_merge"] == "right_only":
                return "Missing in Source"

            if abs(row["Variance"]) <= tolerance:
                return "Matched"

            return "Break"

        result["Status"] = result.apply(
            get_status,
            axis=1
        )

        # Priority

        def get_priority(row):

            if row["Status"] == "Matched":
                return "NA"

            if pd.isna(row["Age_Days"]):
                return "High"

            if row["Age_Days"] >= 90:
                return "High"

            return "Medium"

        result["Priority"] = result.apply(
            get_priority,
            axis=1
        )

        # Escalate

        result["Escalate"] = result["Priority"].apply(
            lambda x: "Yes"
            if x == "High"
            else "No"
        )

        st.session_state.result = result

# ---------------------------------------
# DISPLAY RESULTS
# ---------------------------------------

if st.session_state.result is not None:

    result = st.session_state.result

    exceptions = result[
        result["Status"] != "Matched"
    ]

    escalated = result[
        result["Escalate"] == "Yes"
    ]

    total = len(result)

    matched = len(
        result[result["Status"] == "Matched"]
    )

    exception_count = len(exceptions)

    match_pct = round(
        matched / total * 100,
        2
    )

    high_priority = len(
        result[
            result["Priority"] == "High"
        ]
    )

    escalations = len(escalated)

    st.success(
        "Reconciliation completed successfully"
    )

    # KPI Cards

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric("Total", total)
    c2.metric("Matched", matched)
    c3.metric("Exceptions", exception_count)
    c4.metric("Match %", f"{match_pct}%")
    c5.metric("High Priority", high_priority)
    c6.metric("Escalations", escalations)

    # Results

    st.subheader("Reconciliation Results")

    st.dataframe(
        result,
        use_container_width=True
    )

    # Exceptions

    st.subheader("Exceptions")

    st.dataframe(
        exceptions,
        use_container_width=True
    )

    # Escalated

    st.subheader("Escalated Items")

    st.dataframe(
        escalated,
        use_container_width=True
    )

    # Pie Chart at End

    st.subheader("Status Distribution")

    chart_df = (
        result["Status"]
        .value_counts()
        .reset_index()
    )

    chart_df.columns = [
        "Status",
        "Count"
    ]

    fig = px.pie(
        chart_df,
        names="Status",
        values="Count",
        hole=0.4
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # Downloads

    recon_buffer = BytesIO()

    result.to_excel(
        recon_buffer,
        index=False
    )

    recon_buffer.seek(0)

    exception_buffer = BytesIO()

    exceptions.to_excel(
        exception_buffer,
        index=False
    )

    exception_buffer.seek(0)

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            "Download Recon Output",
            recon_buffer,
            file_name="Recon_Output.xlsx"
        )

    with col2:

        st.download_button(
            "Download Exception Report",
            exception_buffer,
            file_name="Exception_Report.xlsx"
        )