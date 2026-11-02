
from pathlib import Path
from tempfile import TemporaryDirectory
from io import BytesIO, StringIO
from contextlib import redirect_stdout
import hashlib

import pandas as pd
import streamlit as st

import main as cleaner


# =============================================================
# PAGE CONFIGURATION
# =============================================================

st.set_page_config(
    page_title="Data Cleaning Automation",
    page_icon="🧹",
    layout="wide"
)


# =============================================================
# CUSTOM STYLING
# =============================================================

st.markdown(
    """
    <style>

    .main-header {
        font-size: 2.3rem;
        font-weight: 750;
        margin-bottom: 0.2rem;
    }

    .sub-header {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    .section-header {
        font-size: 1.35rem;
        font-weight: 700;
        margin-top: 1.2rem;
        margin-bottom: 0.8rem;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =============================================================
# HELPER FUNCTIONS
# =============================================================

def read_uploaded_file(uploaded_file):
    """Read an uploaded CSV or XLSX file."""

    extension = Path(uploaded_file.name).suffix.lower()

    file_data = BytesIO(
        uploaded_file.getvalue()
    )

    if extension == ".csv":

        try:

            return pd.read_csv(
                file_data,
                encoding="utf-8-sig",
                dtype="string",
                low_memory=False
            )

        except UnicodeDecodeError:

            file_data.seek(0)

            return pd.read_csv(
                file_data,
                encoding="cp1252",
                dtype="string",
                low_memory=False
            )

    if extension == ".xlsx":

        return pd.read_excel(
            file_data,
            engine="openpyxl"
        )

    raise ValueError(
        "Unsupported file format."
    )


def calculate_quality_score(stats):
    """Calculate a demonstration data quality score."""

    original_cells = stats.get(
        "original_cells",
        0
    )

    total_issues = stats.get(
        "total_issues",
        0
    )

    if original_cells <= 0:
        return 0.0

    score = 100 * (
        1 - total_issues / original_cells
    )

    return round(
        max(0, score),
        1
    )


def create_file_signature(files):
    """Detect uploaded file content changes."""

    return tuple(
        (
            file.name,
            hashlib.sha256(
                file.getvalue()
            ).hexdigest()
        )
        for file in files
    )


# =============================================================
# SESSION STATE
# =============================================================

if "cleaning_results" not in st.session_state:

    st.session_state.cleaning_results = []

if "upload_signature" not in st.session_state:

    st.session_state.upload_signature = None


# =============================================================
# HEADER
# =============================================================

st.markdown(
    '<div class="main-header">'
    '🧹 Data Cleaning Automation'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-header">'
    'Upload datasets, configure validation rules, '
    'review corrections, clean data and analyse data quality.'
    '</div>',
    unsafe_allow_html=True
)

st.divider()


# =============================================================
# STEP 1: FILE UPLOAD
# =============================================================

st.markdown(
    '<div class="section-header">'
    '1. Upload your datasets'
    '</div>',
    unsafe_allow_html=True
)

uploaded_files = st.file_uploader(
    "Choose CSV or Excel files",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
    help="Upload one or multiple CSV and XLSX files."
)


# =============================================================
# RESET RESULTS WHEN UPLOADS CHANGE
# =============================================================

if uploaded_files:

    current_signature = create_file_signature(
        uploaded_files
    )

    if current_signature != st.session_state.upload_signature:

        st.session_state.cleaning_results = []

        st.session_state.upload_signature = current_signature

else:

    st.session_state.upload_signature = None

    st.session_state.cleaning_results = []


if uploaded_files:

    st.success(
        f"{len(uploaded_files)} file(s) selected."
    )

    for uploaded_file in uploaded_files:

        st.write(
            f"📄 {uploaded_file.name} "
            f"({uploaded_file.size / 1024:.2f} KB)"
        )

else:

    st.info(
        "Upload a CSV or Excel file to begin. "
        "No dataset is processed until you click the processing button."
    )


# =============================================================
# STEP 2: COLUMN CONFIGURATION AND DUPLICATE REVIEW
# =============================================================

column_configurations = {}

if uploaded_files:

    st.divider()

    st.markdown(
        '<div class="section-header">'
        '2. Configure your column types'
        '</div>',
        unsafe_allow_html=True
    )

    st.info(
        "Suggested types are based on column names. "
        "Review each suggestion and select the correct type."
    )

    for file_index, uploaded_file in enumerate(uploaded_files):

        file_token = (
            f"{file_index}_"
            + hashlib.sha256(
                uploaded_file.getvalue()
            ).hexdigest()[:12]
        )

        try:

            original_preview = read_uploaded_file(
                uploaded_file
            )

            normalised_preview = cleaner.normalise_columns(
                original_preview.copy()
            )

        except Exception as error:

            st.error(
                f"Cannot read {uploaded_file.name}: "
                f"{type(error).__name__}: {error}"
            )

            continue

        with st.expander(
            f"⚙️ Configure: {uploaded_file.name}",
            expanded=True
        ):

            # -----------------------------------------
            # ORIGINAL DATA PREVIEW
            # -----------------------------------------

            st.markdown("**Original dataset preview**")

            st.dataframe(
                normalised_preview.head(10),
                use_container_width=True,
                hide_index=True
            )

            # -----------------------------------------
            # DUPLICATE PREVIEW
            # -----------------------------------------

            st.markdown("**Duplicate record preview**")

            try:

                duplicate_mask = normalised_preview.duplicated(
                    keep=False
                )

                duplicate_preview = normalised_preview.loc[
                    duplicate_mask
                ].copy()

            except TypeError:

                duplicate_preview = pd.DataFrame()

                st.warning(
                    "The duplicate preview could not compare "
                    "some complex cell values. Duplicate checking "
                    "will still be attempted during processing."
                )

            if duplicate_preview.empty:

                st.success(
                    "No exact duplicate records found in the uploaded dataset preview."
                )

            else:

                duplicate_preview.insert(
                    0,
                    "source_row",
                    [
                        index + 2
                        for index in duplicate_preview.index
                    ]
                )

                st.warning(
                    f"{len(duplicate_preview)} rows belong to "
                    "exact duplicate groups."
                )

                st.dataframe(
                    duplicate_preview.head(200),
                    use_container_width=True,
                    hide_index=True
                )

                if len(duplicate_preview) > 200:

                    st.caption(
                        "Only the first 200 duplicate rows are displayed."
                    )

            st.caption(
                "This preview checks exact duplicates in the uploaded "
                "data. Additional duplicates may appear after enabled "
                "standardisation or correction operations."
            )

            st.divider()

            # -----------------------------------------
            # COLUMN TYPE AND MISSING-VALUE SETTINGS
            # -----------------------------------------

            st.markdown(
                "**Column validation and missing-value settings**"
            )

            file_column_settings = {}

            left_column, right_column = st.columns(2)

            for column_index, column in enumerate(
                normalised_preview.columns
            ):

                detected_type = cleaner.infer_column_type(
                    column,
                    normalised_preview[column]
                )

                current_column = (
                    left_column
                    if column_index % 2 == 0
                    else right_column
                )

                with current_column:

                    st.markdown(f"**{column}**")

                    selected_type = st.selectbox(
                        "Data type",
                        options=cleaner.COLUMN_TYPES,
                        index=0,
                        key=f"type_{file_token}_{column}"
                    )

                    effective_type = (
                        detected_type
                        if selected_type == "Auto"
                        else selected_type
                    )

                    st.caption(
                        f"Suggested: {detected_type} | "
                        f"Selected: {effective_type}"
                    )

                    # ---------------------------------
                    # NEGATIVE NUMBER VALIDATION
                    # ---------------------------------

                    flag_negative = False

                    if effective_type == "Number":

                        flag_negative = st.checkbox(
                            "Flag negative values",
                            value=False,
                            key=f"negative_{file_token}_{column}"
                        )

                    # ---------------------------------
                    # MISSING-VALUE SETTINGS
                    # ---------------------------------

                    missing_strategy_label = st.selectbox(
                        "Missing-value handling",
                        options=[
                            "Keep missing values",
                            "Fill with a value"
                        ],
                        index=0,
                        key=f"missing_strategy_{file_token}_{column}",
                        disabled=(effective_type == "Ignore")
                    )

                    missing_value = ""

                    if missing_strategy_label == "Fill with a value":

                        missing_value = st.text_input(
                            "Replacement value",
                            placeholder="Enter replacement value",
                            key=f"missing_value_{file_token}_{column}",
                            help=(
                                "The replacement is validated against "
                                "the selected column type if missing "
                                "values are present."
                            )
                        )

                    file_column_settings[column] = {

                        "type": selected_type,

                        "flag_negative": flag_negative,

                        "missing_strategy": (
                            "fill"
                            if missing_strategy_label == "Fill with a value"
                            else "keep"
                        ),

                        "missing_value": missing_value

                    }

                    st.divider()

            column_configurations[file_index] = (
                file_column_settings
            )


# =============================================================
# STEP 3: CLEANING AND CORRECTION OPTIONS
# =============================================================

cleaning_options = {}

if uploaded_files:

    st.divider()

    st.markdown(
        '<div class="section-header">'
        '3. Choose cleaning and correction operations'
        '</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Choose which transformations should be applied. "
        "Your original uploaded files are not modified."
    )

    with st.expander(
        "Cleaning and correction settings",
        expanded=True
    ):

        option_col1, option_col2 = st.columns(2)

        with option_col1:

            trim_whitespace = st.checkbox(
                "Trim unnecessary spaces",
                value=True
            )

            standardize_missing = st.checkbox(
                "Standardise missing-value markers",
                value=True
            )

            remove_empty_rows = st.checkbox(
                "Remove completely empty rows",
                value=True
            )

            remove_duplicates = st.checkbox(
                "Remove exact duplicate records",
                value=True
            )

            lowercase_emails = st.checkbox(
                "Convert email addresses to lowercase",
                value=False
            )

        with option_col2:

            remove_empty_columns = st.checkbox(
                "Remove completely empty columns",
                value=True
            )

            convert_numeric = st.checkbox(
                "Convert valid numeric values to numbers",
                value=False
            )

            standardize_dates = st.checkbox(
                "Standardise valid dates to YYYY-MM-DD",
                value=False
            )

        st.divider()

        # ---------------------------------------------
        # INVALID NUMERIC VALUE POLICY
        # ---------------------------------------------

        st.markdown("**Invalid numeric values**")

        numeric_policy_label = st.selectbox(
            "How should invalid numeric values be handled?",
            options=[
                "Keep original value and report",
                "Replace invalid value with missing"
            ],
            index=0,
            disabled=not convert_numeric,
            help=(
                "Available when numeric conversion is enabled. "
                "Original validation findings remain in the issue report."
            )
        )

        # ---------------------------------------------
        # INVALID DATE POLICY
        # ---------------------------------------------

        st.markdown("**Invalid dates**")

        date_policy_label = st.selectbox(
            "How should invalid dates be handled?",
            options=[
                "Keep original value and report",
                "Replace invalid date with missing"
            ],
            index=0,
            disabled=not standardize_dates,
            help=(
                "Available when date standardisation is enabled. "
                "Original validation findings remain in the issue report."
            )
        )

    cleaning_options = {

        "trim_whitespace": trim_whitespace,

        "standardize_missing": standardize_missing,

        "remove_empty_rows": remove_empty_rows,

        "remove_empty_columns": remove_empty_columns,

        "remove_duplicates": remove_duplicates,

        "lowercase_emails": lowercase_emails,

        "convert_numeric_columns": convert_numeric,

        "standardize_date_columns": standardize_dates,

        "invalid_numeric_action": (
            "set_missing"
            if numeric_policy_label.startswith("Replace")
            else "report_only"
        ),

        "invalid_date_action": (
            "set_missing"
            if date_policy_label.startswith("Replace")
            else "report_only"
        )

    }


# =============================================================
# STEP 4: PROCESS DATA
# =============================================================

st.divider()

process_button = st.button(
    "🚀 Clean and Analyse Data",
    type="primary",
    disabled=not uploaded_files,
    use_container_width=True
)


if process_button:

    results = []

    progress = st.progress(0)

    status = st.empty()

    previous_output_dir = cleaner.OUTPUT_DIR

    try:

        with TemporaryDirectory() as temporary_directory:

            temp_root = Path(temporary_directory)

            for index, uploaded_file in enumerate(uploaded_files):

                status.write(
                    f"Processing {uploaded_file.name}..."
                )

                try:

                    # ---------------------------------
                    # CREATE TEMPORARY DIRECTORIES
                    # ---------------------------------

                    file_input_dir = (
                        temp_root / f"input_{index + 1}"
                    )

                    file_output_dir = (
                        temp_root / f"output_{index + 1}"
                    )

                    file_input_dir.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    file_output_dir.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    # ---------------------------------
                    # SAVE UPLOADED FILE
                    # ---------------------------------

                    safe_filename = Path(
                        uploaded_file.name
                    ).name

                    input_path = (
                        file_input_dir / safe_filename
                    )

                    input_path.write_bytes(
                        uploaded_file.getvalue()
                    )

                    # ---------------------------------
                    # SET TEMPORARY OUTPUT DIRECTORY
                    # ---------------------------------

                    cleaner.OUTPUT_DIR = file_output_dir

                    # ---------------------------------
                    # GET COLUMN CONFIGURATION
                    # ---------------------------------

                    selected_columns = column_configurations.get(
                        index,
                        {}
                    )

                    # ---------------------------------
                    # RUN CLEANING ENGINE
                    # ---------------------------------

                    log_buffer = StringIO()

                    with redirect_stdout(log_buffer):

                        processing_result = cleaner.process_file(
                            input_path,
                            options=cleaning_options,
                            column_types=selected_columns
                        )

                    stats = processing_result["stats"]

                    issue_df = processing_result["issue_df"]

                    change_df = processing_result["change_df"]

                    cleaned_df = processing_result["cleaned_df"]

                    score = calculate_quality_score(
                        stats
                    )

                    # ---------------------------------
                    # DEFINE OUTPUT ARTIFACTS
                    # ---------------------------------

                    extension = input_path.suffix.lower()

                    cleaned_mime = (
                        "text/csv"
                        if extension == ".csv"
                        else (
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        )
                    )

                    excel_mime = (
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    )

                    artifact_paths = [

                        (
                            "Cleaned dataset",
                            processing_result["cleaned_file"],
                            cleaned_mime
                        ),

                        (
                            "Quality report",
                            processing_result["report_file"],
                            "text/plain"
                        ),

                        (
                            "Detailed issue report",
                            processing_result["issue_file"],
                            "text/csv"
                        ),

                        (
                            "Transformation change log",
                            processing_result["change_file"],
                            "text/csv"
                        ),

                        (
                            "Complete Excel report",
                            processing_result["excel_report_file"],
                            excel_mime
                        )

                    ]

                    # ---------------------------------
                    # READ GENERATED DOWNLOAD FILES
                    # ---------------------------------

                    artifacts = []

                    for label, artifact_path, mime in artifact_paths:

                        if not artifact_path.exists():

                            raise FileNotFoundError(
                                f"Expected output not found: "
                                f"{artifact_path.name}"
                            )

                        artifacts.append({

                            "label": label,

                            "filename": artifact_path.name,

                            "mime": mime,

                            "data": artifact_path.read_bytes()

                        })

                    # ---------------------------------
                    # STORE PROCESSING RESULTS
                    # ---------------------------------

                    results.append({

                        "filename": uploaded_file.name,

                        "success": True,

                        "stats": stats,

                        "score": score,

                        "original_preview": (
                            processing_result["original_df"].head(10)
                        ),

                        "cleaned_preview": cleaned_df.head(10),

                        "issue_df": issue_df,

                        "change_df": change_df,

                        "column_settings": (
                            processing_result["column_settings"]
                        ),

                        "missing_settings": (
                            processing_result["missing_settings"]
                        ),

                        "options": processing_result["options"],

                        "artifacts": artifacts,

                        "log": log_buffer.getvalue()

                    })

                except Exception as error:

                    results.append({

                        "filename": uploaded_file.name,

                        "success": False,

                        "error": (
                            f"{type(error).__name__}: {error}"
                        )

                    })

                progress.progress(
                    (index + 1) / len(uploaded_files)
                )

    finally:

        cleaner.OUTPUT_DIR = previous_output_dir

    # ---------------------------------------------
    # SAVE RESULTS IN SESSION
    # ---------------------------------------------

    st.session_state.cleaning_results = results

    progress.empty()

    status.empty()

    if any(
        result["success"]
        for result in results
    ):

        st.success(
            "Data processing and analysis completed!"
        )

    if any(
        not result["success"]
        for result in results
    ):

        st.warning(
            "Some files could not be processed. "
            "Review the error information below."
        )


# =============================================================
# STEP 5: DISPLAY PROCESSING RESULTS
# =============================================================

results = st.session_state.cleaning_results

if results:

    st.divider()

    # ---------------------------------------------------------
    # PROCESSING OVERVIEW
    # ---------------------------------------------------------

    st.markdown(
        '<div class="section-header">'
        '4. Processing overview'
        '</div>',
        unsafe_allow_html=True
    )

    successful = sum(
        result["success"]
        for result in results
    )

    failed = len(results) - successful

    total_cleaned_records = sum(

        result["stats"]["cleaned_rows"]

        for result in results

        if result["success"]

    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total files",
        len(results)
    )

    c2.metric(
        "Successful",
        successful
    )

    c3.metric(
        "Failed",
        failed
    )

    c4.metric(
        "Cleaned records",
        total_cleaned_records
    )

    # ---------------------------------------------------------
    # INDIVIDUAL FILE RESULTS
    # ---------------------------------------------------------

    st.markdown(
        '<div class="section-header">'
        '5. File analysis results'
        '</div>',
        unsafe_allow_html=True
    )

    for result_index, result in enumerate(results):

        with st.expander(
            result["filename"],
            expanded=True
        ):

            if not result["success"]:

                st.error(
                    result["error"]
                )

                continue

            stats = result["stats"]

            issue_df = result["issue_df"]

            change_df = result["change_df"]

            options = result["options"]

            st.success(
                "File processed successfully."
            )

            # ---------------------------------------------
            # DATA QUALITY METRICS
            # ---------------------------------------------

            st.markdown("#### Data quality indicators")

            score_col, issue_col, original_col, cleaned_col = (
                st.columns(4)
            )

            score_col.metric(
                "Quality score",
                f"{result['score']}/100"
            )

            issue_col.metric(
                "Issues identified",
                stats["total_issues"]
            )

            original_col.metric(
                "Original records",
                stats["original_rows"]
            )

            cleaned_col.metric(
                "Cleaned records",
                stats["cleaned_rows"]
            )

            st.caption(
                "Prototype score: 100 × (1 − issues identified "
                "÷ original data cells). This is a demonstration "
                "indicator, not an industry-certified score. "
                "Issue findings are retained from validation before "
                "value corrections."
            )

            # ---------------------------------------------
            # BEFORE AND AFTER COMPARISON
            # ---------------------------------------------

            st.markdown("#### Before and after comparison")

            before_col, after_col, removed_col = st.columns(3)

            before_col.metric(
                "Original rows",
                stats["original_rows"]
            )

            after_col.metric(
                "Final rows",
                stats["cleaned_rows"]
            )

            removed_col.metric(
                "Rows removed",
                stats["original_rows"] - stats["cleaned_rows"]
            )

            before_tab, after_tab = st.tabs(
                ["Original dataset", "Cleaned dataset"]
            )

            with before_tab:

                st.dataframe(
                    result["original_preview"],
                    use_container_width=True,
                    hide_index=True
                )

            with after_tab:

                st.dataframe(
                    result["cleaned_preview"],
                    use_container_width=True,
                    hide_index=True
                )

            # ---------------------------------------------
            # COLUMN VALIDATION SETTINGS
            # ---------------------------------------------

            st.markdown("#### Column validation settings")

            type_table = pd.DataFrame([

                {
                    "Column": column,
                    "Selected type": selected_type
                }

                for column, selected_type
                in result["column_settings"].items()

            ])

            st.dataframe(
                type_table,
                use_container_width=True,
                hide_index=True
            )

            # ---------------------------------------------
            # MISSING-VALUE SETTINGS
            # ---------------------------------------------

            st.markdown("#### Missing-value settings")

            missing_table = pd.DataFrame([

                {
                    "Column": column,

                    "Strategy": (
                        "Fill with configured value"
                        if config["strategy"] == "fill"
                        else "Keep missing values"
                    ),

                    "Replacement value": (
                        config["value"]
                        if config["strategy"] == "fill"
                        else ""
                    )

                }

                for column, config
                in result["missing_settings"].items()

            ])

            st.dataframe(
                missing_table,
                use_container_width=True,
                hide_index=True
            )

            # ---------------------------------------------
            # APPLIED CLEANING AND CORRECTION SETTINGS
            # ---------------------------------------------

            st.markdown(
                "#### Applied cleaning and correction settings"
            )

            boolean_options = [

                name.replace("_", " ").title()

                for name, enabled in options.items()

                if isinstance(enabled, bool) and enabled

            ]

            if boolean_options:

                st.write(
                    " • ".join(boolean_options)
                )

            else:

                st.info(
                    "No optional cleaning operations were selected."
                )

            st.write(
                "**Invalid numeric values:** "
                + (
                    "Replace with missing"
                    if options["invalid_numeric_action"] == "set_missing"
                    else "Keep and report"
                )
            )

            st.write(
                "**Invalid dates:** "
                + (
                    "Replace with missing"
                    if options["invalid_date_action"] == "set_missing"
                    else "Keep and report"
                )
            )

            # ---------------------------------------------
            # DATA QUALITY ANALYSIS
            # ---------------------------------------------

            st.markdown("#### Data quality analysis")

            if issue_df.empty:

                st.success(
                    "No data quality issues were detected."
                )

            else:

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:

                    st.markdown("**Issues by type**")

                    st.bar_chart(
                        issue_df["issue"].value_counts()
                    )

                with chart_col2:

                    st.markdown("**Missing values by column**")

                    missing_counts = (

                        issue_df.loc[
                            issue_df["issue"] == "Missing value"
                        ]

                        .groupby("column")
                        .size()
                        .sort_values(ascending=False)

                    )

                    if missing_counts.empty:

                        st.info(
                            "No missing values were identified before correction."
                        )

                    else:

                        st.bar_chart(
                            missing_counts
                        )

                # -----------------------------------------
                # ISSUE EXPLORER
                # -----------------------------------------

                st.markdown("**Detected issues explorer**")

                st.dataframe(
                    issue_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("**Issue summary**")

                issue_summary = (

                    issue_df["issue"]
                    .value_counts()
                    .rename_axis("Issue")
                    .reset_index(name="Count")

                )

                st.dataframe(
                    issue_summary,
                    use_container_width=True,
                    hide_index=True
                )

            # ---------------------------------------------
            # TRANSFORMATION CHANGE LOG
            # ---------------------------------------------

            st.divider()

            st.markdown(
                "#### 📝 Transformation change log"
            )

            st.caption(
                "The change log records actual modifications "
                "with the source row, original value, new value "
                "and action. Validation findings are listed "
                "separately in the issue report."
            )

            if change_df.empty:

                st.info(
                    "No data transformations were required."
                )

            else:

                change_col1, change_col2 = st.columns(2)

                change_col1.metric(
                    "Transformations recorded",
                    len(change_df)
                )

                change_col2.metric(
                    "Transformation types",
                    change_df["action"].nunique()
                )

                st.dataframe(
                    change_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("**Transformations by action**")

                st.bar_chart(
                    change_df["action"].value_counts()
                )

            # ---------------------------------------------
            # DOWNLOAD RESULTS
            # ---------------------------------------------

            st.divider()

            st.markdown("#### Download results")

            for artifact in result["artifacts"]:

                st.download_button(

                    label=f"⬇️ {artifact['label']}",

                    data=artifact["data"],

                    file_name=artifact["filename"],

                    mime=artifact["mime"],

                    key=(
                        f"download_{result_index}_"
                        f"{artifact['filename']}"
                    ),

                    use_container_width=True

                )

            # ---------------------------------------------
            # PROCESSING LOG
            # ---------------------------------------------

            with st.expander("View processing log"):

                st.code(
                    result["log"],
                    language="text"
                )


# =============================================================
# FOOTER
# =============================================================

st.divider()

st.caption(
    "Data Cleaning Automation | "
    "Python • Pandas • OpenPyXL • Streamlit"
)
