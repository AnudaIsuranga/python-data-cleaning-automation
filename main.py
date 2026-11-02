
from pathlib import Path
import re
import numbers
import pandas as pd


# =============================================================
# PROJECT CONFIGURATION
# =============================================================

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

SUPPORTED_FORMATS = {".csv", ".xlsx"}

COLUMN_TYPES = [
    "Auto",
    "Text",
    "Email",
    "Phone",
    "Number",
    "Date",
    "Ignore"
]

MISSING_MARKERS = {
    "",
    "n/a",
    "na",
    "null",
    "none",
    "-",
    "not available"
}

EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

PHONE_PATTERN = re.compile(
    r"^\+?[\d\s().-]+$"
)

PHONE_KEYWORDS = {
    "phone",
    "mobile",
    "telephone",
    "tel",
    "whatsapp"
}

DATE_KEYWORDS = {
    "date",
    "dob",
    "timestamp"
}

NUMERIC_KEYWORDS = {
    "amount",
    "price",
    "cost",
    "quantity",
    "qty",
    "total",
    "revenue",
    "salary",
    "stock",
    "fee",
    "tax",
    "count",
    "age",
    "year"
}

ISSUE_COLUMNS = [
    "source_row",
    "column",
    "issue",
    "value",
    "details"
]

CHANGE_COLUMNS = [
    "source_row",
    "column",
    "original_value",
    "new_value",
    "action",
    "details"
]

DEFAULT_OPTIONS = {
    "trim_whitespace": True,
    "standardize_missing": True,
    "remove_empty_rows": True,
    "remove_empty_columns": True,
    "remove_duplicates": True,
    "lowercase_emails": False,
    "convert_numeric_columns": False,
    "standardize_date_columns": False,
    "invalid_numeric_action": "report_only",
    "invalid_date_action": "report_only"
}


# =============================================================
# GENERAL HELPERS
# =============================================================

def is_missing(value):
    """Safely identify scalar missing values."""

    try:
        result = pd.isna(value)
        return bool(result)

    except (TypeError, ValueError):
        return False


def display_value(value):
    """Convert values into readable report text."""

    return "<MISSING>" if is_missing(value) else str(value)


def values_equal(old_value, new_value):
    """Recognise both value changes and data-type changes."""

    old_missing = is_missing(old_value)
    new_missing = is_missing(new_value)

    if old_missing and new_missing:
        return True

    if old_missing != new_missing:
        return False

    if type(old_value) is not type(new_value):
        return False

    try:
        return bool(old_value == new_value)

    except (TypeError, ValueError):
        return False


def add_change(
    changes,
    source_row,
    column,
    original_value,
    new_value,
    action,
    details
):
    """Record an actual data transformation."""

    changes.append({
        "source_row": source_row,
        "column": column,
        "original_value": display_value(original_value),
        "new_value": display_value(new_value),
        "action": action,
        "details": details
    })


def add_issue(
    issues,
    source_row,
    column,
    issue,
    value="",
    details=""
):
    """Record an identified data-quality issue."""

    issues.append({
        "source_row": source_row,
        "column": column,
        "issue": issue,
        "value": value,
        "details": details
    })


def capture_cell_changes(
    before_df,
    after_df,
    source_row_numbers,
    changes,
    action,
    details
):
    """Compare matching cells and record actual changes."""

    common_indices = before_df.index.intersection(
        after_df.index
    )

    common_columns = before_df.columns.intersection(
        after_df.columns
    )

    for index in common_indices:

        for column in common_columns:

            old_value = before_df.at[index, column]
            new_value = after_df.at[index, column]

            if not values_equal(old_value, new_value):

                add_change(
                    changes,
                    source_row_numbers.get(index, ""),
                    column,
                    old_value,
                    new_value,
                    action,
                    details
                )


def format_row(row):
    """Convert a complete row into readable text."""

    return "; ".join(
        f"{column}={display_value(value)}"
        for column, value in row.items()
    )


# =============================================================
# LOAD INPUT FILES
# =============================================================

def load_file(file_path):
    """Load CSV or Excel files."""

    file_path = Path(file_path)
    extension = file_path.suffix.lower()

    if extension == ".csv":

        try:
            return pd.read_csv(
                file_path,
                encoding="utf-8-sig",
                low_memory=False,
                dtype="string"
            )

        except UnicodeDecodeError:

            return pd.read_csv(
                file_path,
                encoding="cp1252",
                low_memory=False,
                dtype="string"
            )

    if extension == ".xlsx":

        return pd.read_excel(
            file_path,
            engine="openpyxl"
        )

    raise ValueError(
        f"Unsupported file format: {extension}"
    )


# =============================================================
# NORMALISE COLUMN NAMES
# =============================================================

def normalise_columns(df):
    """Convert column names into unique snake_case names."""

    new_columns = []
    used_names = set()

    for column in df.columns:

        name = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            str(column).strip().lower()
        )

        name = name.strip("_") or "column"

        base_name = name
        counter = 2

        while name in used_names:

            name = f"{base_name}_{counter}"
            counter += 1

        used_names.add(name)
        new_columns.append(name)

    df.columns = new_columns

    return df


# =============================================================
# COLUMN TYPE DETECTION
# =============================================================

def infer_column_type(column, series=None):
    """Suggest a data type from the column name."""

    name = str(column).lower()
    tokens = set(name.split("_"))

    if "email" in name or "e_mail" in name:
        return "Email"

    if (
        tokens.intersection(PHONE_KEYWORDS)
        or "contact_number" in name
    ):
        return "Phone"

    if (
        tokens.intersection(DATE_KEYWORDS)
        or name.endswith("_date")
    ):
        return "Date"

    if tokens.intersection(NUMERIC_KEYWORDS):
        return "Number"

    return "Text"


def resolve_column_settings(df, column_types=None):
    """Resolve user selections and column-level settings."""

    supplied = column_types or {}

    resolved_types = {}
    negative_flags = {}
    missing_settings = {}

    for column in df.columns:

        config = supplied.get(
            column,
            {"type": "Auto"}
        )

        if not isinstance(config, dict):
            config = {"type": config}

        selected_type = config.get("type", "Auto")

        if selected_type == "Auto":

            selected_type = infer_column_type(
                column,
                df[column]
            )

        if selected_type not in COLUMN_TYPES:
            selected_type = "Text"

        strategy = config.get(
            "missing_strategy",
            "keep"
        )

        if strategy not in {"keep", "fill"}:
            strategy = "keep"

        resolved_types[column] = selected_type

        negative_flags[column] = bool(
            config.get("flag_negative", False)
        )

        missing_settings[column] = {
            "strategy": strategy,
            "value": config.get(
                "missing_value",
                ""
            )
        }

    return (
        resolved_types,
        negative_flags,
        missing_settings
    )


# =============================================================
# CLEAN TEXT VALUES
# =============================================================

def clean_text(
    df,
    source_row_numbers,
    changes,
    trim_whitespace=True,
    standardize_missing=True
):
    """Trim whitespace and standardise missing-value markers."""

    if trim_whitespace:

        before = df.copy(deep=True)

        for column in df.columns:

            if (
                pd.api.types.is_object_dtype(df[column])
                or pd.api.types.is_string_dtype(df[column])
            ):

                values = df[column].astype("string").str.strip()

                values = values.str.replace(
                    r"\s+",
                    " ",
                    regex=True
                )

                df[column] = values

        capture_cell_changes(
            before,
            df,
            source_row_numbers,
            changes,
            "Whitespace trimming",
            "Removed leading/trailing spaces and collapsed repeated whitespace."
        )

    if standardize_missing:

        before = df.copy(deep=True)

        for column in df.columns:

            if (
                pd.api.types.is_object_dtype(df[column])
                or pd.api.types.is_string_dtype(df[column])
            ):

                values = df[column].astype("string")

                missing_mask = values.str.strip().str.lower().isin(
                    MISSING_MARKERS
                )

                df[column] = values.mask(
                    missing_mask,
                    pd.NA
                )

        capture_cell_changes(
            before,
            df,
            source_row_numbers,
            changes,
            "Missing-value standardisation",
            "Converted a recognised missing marker to a missing value."
        )

    return df


# =============================================================
# VALIDATION HELPERS
# =============================================================

def validate_email(value):

    return bool(
        EMAIL_PATTERN.fullmatch(
            str(value).strip()
        )
    )


def validate_phone(value):
    """Basic phone formatting and digit-count validation."""

    text = str(value).strip()

    if not PHONE_PATTERN.fullmatch(text):
        return False

    digits = re.sub(r"\D", "", text)

    return 7 <= len(digits) <= 15


def parse_numeric(value):
    """Parse numbers and common thousands-separated numeric strings."""

    if isinstance(value, bool):
        return None

    if isinstance(value, numbers.Number):

        try:
            return float(value) if pd.notna(value) else None

        except (TypeError, ValueError, OverflowError):
            return None

    text = str(value).strip().replace(",", "")

    try:

        number = pd.to_numeric(
            text,
            errors="coerce"
        )

        if pd.isna(number):
            return None

        return float(number)

    except (TypeError, ValueError, OverflowError):
        return None


def parse_date(value):
    """Parse a date or return None."""

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce"
        )

        if pd.isna(parsed):
            return None

        return parsed

    except (TypeError, ValueError, OverflowError):
        return None


def validate_date(value):

    return parse_date(value) is not None


# =============================================================
# MISSING-VALUE REPLACEMENT VALIDATION
# =============================================================

def prepare_fill_value(
    value,
    selected_type,
    lowercase_emails=False
):
    """Validate a replacement value against its column type."""

    text = str(value).strip()

    if not text:

        raise ValueError(
            "Enter a replacement value for the selected column."
        )

    if selected_type == "Email":

        if not validate_email(text):

            raise ValueError(
                f"Replacement for email column is invalid: {text}"
            )

        return (
            text.lower()
            if lowercase_emails
            else text
        )

    if selected_type == "Phone":

        if not validate_phone(text):

            raise ValueError(
                f"Replacement for phone column is invalid: {text}"
            )

        return text

    if selected_type == "Number":

        number = parse_numeric(text)

        if number is None:

            raise ValueError(
                f"Replacement for numeric column is invalid: {text}"
            )

        return (
            int(number)
            if number.is_integer()
            else number
        )

    if selected_type == "Date":

        parsed = parse_date(text)

        if parsed is None:

            raise ValueError(
                f"Replacement for date column is invalid: {text}"
            )

        return parsed.strftime("%Y-%m-%d")

    return text


# =============================================================
# APPLY MISSING-VALUE HANDLING
# =============================================================

def apply_missing_value_handling(
    df,
    column_settings,
    missing_settings,
    options,
    source_row_numbers,
    changes
):
    """Fill missing values only where the user explicitly requested it."""

    for column in df.columns:

        if column_settings.get(column) == "Ignore":
            continue

        config = missing_settings.get(
            column,
            {"strategy": "keep", "value": ""}
        )

        if config.get("strategy") != "fill":
            continue

        missing_indices = df.index[
            df[column].isna()
        ].tolist()

        if not missing_indices:
            continue

        fill_value = prepare_fill_value(
            config.get("value", ""),
            column_settings[column],
            options.get("lowercase_emails", False)
        )

        df[column] = df[column].astype(object)

        for index in missing_indices:

            df.at[index, column] = fill_value

            add_change(
                changes,
                source_row_numbers.get(index, ""),
                column,
                pd.NA,
                fill_value,
                "Missing-value replacement",
                "Filled a missing value using the user-configured replacement."
            )

    return df


# =============================================================
# EMAIL STANDARDISATION
# =============================================================

def standardize_emails(
    df,
    column_settings,
    source_row_numbers,
    changes
):
    """Convert configured email columns to lowercase."""

    for column in df.columns:

        if column_settings.get(column) != "Email":
            continue

        df[column] = df[column].astype(object)

        for index in df.index:

            old_value = df.at[index, column]

            if is_missing(old_value):
                continue

            new_value = str(old_value).strip().lower()

            if new_value != str(old_value):

                df.at[index, column] = new_value

                add_change(
                    changes,
                    source_row_numbers.get(index, ""),
                    column,
                    old_value,
                    new_value,
                    "Email standardisation",
                    "Converted the email address to lowercase."
                )

    return df


# =============================================================
# GENERATE DATA QUALITY ISSUES
# =============================================================

def create_issue_log(
    df,
    source_row_numbers,
    row_events,
    column_settings,
    negative_flags
):
    """Identify missing and invalid values before corrections."""

    issues = list(row_events)

    for index, row in df.iterrows():

        source_row = source_row_numbers.get(
            index,
            index + 2
        )

        if row.isna().all():
            continue

        for column in df.columns:

            selected_type = column_settings.get(
                column,
                "Text"
            )

            if selected_type == "Ignore":
                continue

            value = row[column]

            if is_missing(value):

                add_issue(
                    issues,
                    source_row,
                    column,
                    "Missing value",
                    "",
                    "Value was missing before correction."
                )

                continue

            if selected_type == "Email":

                if not validate_email(value):

                    add_issue(
                        issues,
                        source_row,
                        column,
                        "Invalid email",
                        str(value),
                        "Email format does not match the basic validation pattern."
                    )

            elif selected_type == "Phone":

                if not validate_phone(value):

                    add_issue(
                        issues,
                        source_row,
                        column,
                        "Invalid phone number",
                        str(value),
                        "Phone number format is invalid or has an unexpected digit count."
                    )

            elif selected_type == "Number":

                number = parse_numeric(value)

                if number is None:

                    add_issue(
                        issues,
                        source_row,
                        column,
                        "Invalid numeric value",
                        str(value),
                        "Expected a valid numeric value."
                    )

                elif (
                    number < 0
                    and negative_flags.get(column, False)
                ):

                    add_issue(
                        issues,
                        source_row,
                        column,
                        "Negative value not allowed",
                        str(value),
                        "Column is configured to flag negative values."
                    )

            elif selected_type == "Date":

                if not validate_date(value):

                    add_issue(
                        issues,
                        source_row,
                        column,
                        "Invalid date",
                        str(value),
                        "Value could not be parsed as a date."
                    )

    return pd.DataFrame(
        issues,
        columns=ISSUE_COLUMNS
    )


# =============================================================
# NUMERIC AND DATE CONVERSIONS
# =============================================================

def apply_type_conversions(
    df,
    column_settings,
    options,
    source_row_numbers,
    changes
):
    """Convert valid numeric/date values and apply correction policies."""

    # ---------------------------------------------------------
    # NUMERIC CONVERSION
    # ---------------------------------------------------------

    if options.get("convert_numeric_columns", False):

        for column in df.columns:

            if column_settings.get(column) != "Number":
                continue

            df[column] = df[column].astype(object)

            for index in df.index:

                old_value = df.at[index, column]

                if is_missing(old_value):
                    continue

                if (
                    isinstance(old_value, numbers.Number)
                    and not isinstance(old_value, bool)
                ):
                    continue

                number = parse_numeric(old_value)

                if number is None:

                    if options.get("invalid_numeric_action") == "set_missing":

                        df.at[index, column] = pd.NA

                        add_change(
                            changes,
                            source_row_numbers.get(index, ""),
                            column,
                            old_value,
                            pd.NA,
                            "Invalid numeric value correction",
                            "Replaced an invalid numeric value with a missing value."
                        )

                    continue

                new_value = (
                    int(number)
                    if number.is_integer()
                    else number
                )

                df.at[index, column] = new_value

                add_change(
                    changes,
                    source_row_numbers.get(index, ""),
                    column,
                    old_value,
                    new_value,
                    "Numeric conversion",
                    "Converted a valid value into numeric data."
                )

    # ---------------------------------------------------------
    # DATE STANDARDISATION
    # ---------------------------------------------------------

    if options.get("standardize_date_columns", False):

        for column in df.columns:

            if column_settings.get(column) != "Date":
                continue

            df[column] = df[column].astype(object)

            for index in df.index:

                old_value = df.at[index, column]

                if is_missing(old_value):
                    continue

                parsed = parse_date(old_value)

                if parsed is None:

                    if options.get("invalid_date_action") == "set_missing":

                        df.at[index, column] = pd.NA

                        add_change(
                            changes,
                            source_row_numbers.get(index, ""),
                            column,
                            old_value,
                            pd.NA,
                            "Invalid date correction",
                            "Replaced an unparseable date with a missing value."
                        )

                    continue

                new_value = parsed.strftime("%Y-%m-%d")

                if new_value != str(old_value):

                    df.at[index, column] = new_value

                    add_change(
                        changes,
                        source_row_numbers.get(index, ""),
                        column,
                        old_value,
                        new_value,
                        "Date standardisation",
                        "Standardised the date to YYYY-MM-DD."
                    )

    return df


# =============================================================
# CREATE TRANSFORMATION CHANGE LOG
# =============================================================

def create_change_log(changes):

    return pd.DataFrame(
        changes,
        columns=CHANGE_COLUMNS
    )


# =============================================================
# GENERATE QUALITY REPORT
# =============================================================

def create_report(
    file_name,
    original_rows,
    original_columns,
    empty_rows_removed,
    empty_columns_removed,
    duplicates_removed,
    final_df,
    issue_log,
    column_settings,
    missing_settings,
    options,
    change_log
):
    """Generate a detailed text-based data quality report."""

    missing_counts = final_df.isna().sum()

    report = [
        "DATA CLEANING AND QUALITY REPORT",
        "=" * 60,
        f"Source file: {file_name}",
        "",
        "RECORD SUMMARY",
        "-" * 60,
        f"Original rows: {original_rows}",
        f"Original columns: {original_columns}",
        f"Empty rows removed: {empty_rows_removed}",
        f"Empty columns removed: {empty_columns_removed}",
        f"Duplicate rows removed: {duplicates_removed}",
        f"Final rows: {len(final_df)}",
        f"Final columns: {len(final_df.columns)}",
        "",
        "DATA QUALITY SUMMARY",
        "-" * 60,
        f"Issues identified before correction: {len(issue_log)}",
        f"Transformations recorded: {len(change_log)}",
        "",
        "COLUMN TYPES",
        "-" * 60
    ]

    for column, selected_type in column_settings.items():
        report.append(f"{column}: {selected_type}")

    report.extend([
        "",
        "MISSING-VALUE SETTINGS",
        "-" * 60
    ])

    for column, config in missing_settings.items():

        strategy = config.get("strategy", "keep")
        value = config.get("value", "")

        suffix = (
            f" (replacement: {value})"
            if strategy == "fill"
            else ""
        )

        report.append(
            f"{column}: {strategy}{suffix}"
        )

    report.extend([
        "",
        "CLEANING AND CORRECTION SETTINGS",
        "-" * 60
    ])

    for option, value in options.items():
        report.append(f"{option}: {value}")

    report.extend([
        "",
        "REMAINING MISSING VALUES",
        "-" * 60
    ])

    nonzero_missing = missing_counts[missing_counts > 0]

    if nonzero_missing.empty:
        report.append("No remaining missing values.")

    else:
        for column, count in nonzero_missing.items():
            report.append(f"{column}: {count}")

    report.extend([
        "",
        "ISSUES BY TYPE",
        "-" * 60
    ])

    if issue_log.empty:
        report.append("No issues detected.")

    else:
        for issue, count in issue_log["issue"].value_counts().items():
            report.append(f"{issue}: {count}")

    report.extend([
        "",
        "TRANSFORMATIONS BY ACTION",
        "-" * 60
    ])

    if change_log.empty:
        report.append("No transformations were required.")

    else:
        for action, count in change_log["action"].value_counts().items():
            report.append(f"{action}: {count}")

    report.extend([
        "",
        "=" * 60,
        "END OF REPORT"
    ])

    return "\n".join(report)


# =============================================================
# CREATE COMPLETE EXCEL REPORT
# =============================================================

def create_excel_report(
    output_path,
    cleaned_df,
    issue_df,
    change_df,
    stats,
    column_settings,
    missing_settings,
    options
):
    """Create a complete Excel workbook with seven worksheets."""

    summary_df = pd.DataFrame(
        [
            ("Original records", stats["original_rows"]),
            ("Original columns", stats["original_columns"]),
            ("Cleaned records", stats["cleaned_rows"]),
            ("Cleaned columns", stats["cleaned_columns"]),
            (
                "Rows removed",
                stats["original_rows"] - stats["cleaned_rows"]
            ),
            ("Empty rows removed", stats["empty_rows"]),
            ("Empty columns removed", stats["empty_columns"]),
            ("Duplicate rows detected", stats["duplicates_detected"]),
            ("Duplicate rows removed", stats["duplicates_removed"]),
            (
                "Issues identified before correction",
                stats["total_issues"]
            ),
            ("Transformations recorded", stats["total_changes"])
        ],
        columns=["Metric", "Value"]
    )

    column_df = pd.DataFrame(
        [
            {"Column": column, "Selected type": selected_type}
            for column, selected_type in column_settings.items()
        ]
    )

    missing_df = pd.DataFrame(
        [
            {
                "Column": column,
                "Strategy": config.get("strategy", "keep"),
                "Replacement value": (
                    config.get("value", "")
                    if config.get("strategy") == "fill"
                    else ""
                )
            }
            for column, config in missing_settings.items()
        ]
    )

    options_df = pd.DataFrame(
        [
            {"Setting": key, "Value": value}
            for key, value in options.items()
        ]
    )

    with pd.ExcelWriter(
        output_path,
        engine="openpyxl"
    ) as writer:

        cleaned_df.to_excel(
            writer,
            sheet_name="Cleaned Data",
            index=False
        )

        issue_df.to_excel(
            writer,
            sheet_name="Issue Log",
            index=False
        )

        change_df.to_excel(
            writer,
            sheet_name="Change Log",
            index=False
        )

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        column_df.to_excel(
            writer,
            sheet_name="Column Settings",
            index=False
        )

        missing_df.to_excel(
            writer,
            sheet_name="Missing Settings",
            index=False
        )

        options_df.to_excel(
            writer,
            sheet_name="Cleaning Settings",
            index=False
        )

        # Basic workbook formatting
        for worksheet in writer.book.worksheets:

            worksheet.freeze_panes = "A2"

            if (
                worksheet.max_row >= 1
                and worksheet.max_column >= 1
            ):
                worksheet.auto_filter.ref = worksheet.dimensions

            for cells in worksheet.columns:

                max_length = max(
                    (
                        len(str(cell.value or ""))
                        for cell in cells
                    ),
                    default=10
                )

                worksheet.column_dimensions[
                    cells[0].column_letter
                ].width = min(
                    max(max_length + 2, 12),
                    50
                )


# =============================================================
# PROCESS ONE INPUT FILE
# =============================================================

def process_file(
    file_path,
    options=None,
    column_types=None
):
    """Clean, validate, transform and report one dataset."""

    file_path = Path(file_path)

    print(f"\nProcessing: {file_path.name}")

    # ---------------------------------------------------------
    # MERGE DEFAULT OPTIONS
    # ---------------------------------------------------------

    settings = DEFAULT_OPTIONS.copy()

    if options:
        settings.update(options)

    if settings["invalid_numeric_action"] not in {
        "report_only",
        "set_missing"
    }:
        raise ValueError("Invalid numeric correction setting.")

    if settings["invalid_date_action"] not in {
        "report_only",
        "set_missing"
    }:
        raise ValueError("Invalid date correction setting.")

    # ---------------------------------------------------------
    # LOAD ORIGINAL DATASET
    # ---------------------------------------------------------

    original_df = load_file(file_path)

    original_rows = len(original_df)
    original_columns = len(original_df.columns)

    df = original_df.copy(deep=True)

    changes = []
    row_events = []

    source_row_numbers = {
        index: position + 2
        for position, index in enumerate(df.index)
    }

    # ---------------------------------------------------------
    # NORMALISE COLUMN NAMES
    # ---------------------------------------------------------

    old_columns = list(df.columns)

    df = normalise_columns(df)

    for old_name, new_name in zip(old_columns, df.columns):

        if str(old_name) != str(new_name):

            add_change(
                changes,
                "",
                new_name,
                old_name,
                new_name,
                "Column name standardisation",
                "Standardised the column name to snake_case."
            )

    # ---------------------------------------------------------
    # RESOLVE COLUMN SETTINGS
    # ---------------------------------------------------------

    (
        column_settings,
        negative_flags,
        missing_settings
    ) = resolve_column_settings(
        df,
        column_types
    )

    # ---------------------------------------------------------
    # CLEAN TEXT
    # ---------------------------------------------------------

    df = clean_text(
        df,
        source_row_numbers,
        changes,
        trim_whitespace=settings["trim_whitespace"],
        standardize_missing=settings["standardize_missing"]
    )

    # ---------------------------------------------------------
    # DETECT AND REMOVE EMPTY ROWS
    # ---------------------------------------------------------

    empty_row_mask = df.isna().all(axis=1)

    empty_rows_detected = int(empty_row_mask.sum())
    empty_rows_removed = 0

    for index in df.index[empty_row_mask]:

        row_text = format_row(df.loc[index])

        if settings["remove_empty_rows"]:

            empty_rows_removed += 1

            add_issue(
                row_events,
                source_row_numbers[index],
                "",
                "Empty row removed",
                row_text,
                "Entire row contained no values."
            )

            add_change(
                changes,
                source_row_numbers[index],
                "",
                row_text,
                "<ROW REMOVED>",
                "Empty row removal",
                "Removed a completely empty record."
            )

        else:

            add_issue(
                row_events,
                source_row_numbers[index],
                "",
                "Empty row detected",
                row_text,
                "Entire row contained no values."
            )

    if settings["remove_empty_rows"]:

        df = df.loc[~empty_row_mask].copy()

    # ---------------------------------------------------------
    # DETECT AND REMOVE EMPTY COLUMNS
    # ---------------------------------------------------------

    empty_column_names = [
        column
        for column in df.columns
        if df[column].isna().all()
    ]

    empty_columns_removed = 0
    columns_to_remove = []

    for column in empty_column_names:

        config = missing_settings.get(
            column,
            {"strategy": "keep"}
        )

        should_fill = (
            config.get("strategy") == "fill"
            and column_settings.get(column) != "Ignore"
        )

        if (
            settings["remove_empty_columns"]
            and not should_fill
        ):

            columns_to_remove.append(column)
            empty_columns_removed += 1

            add_issue(
                row_events,
                "All",
                column,
                "Empty column removed",
                "",
                "Entire column contained no values."
            )

            add_change(
                changes,
                "All",
                column,
                "Entire column was empty",
                "<COLUMN REMOVED>",
                "Empty column removal",
                "Removed a column containing only missing values."
            )

        elif (
            not settings["remove_empty_columns"]
            and not should_fill
        ):

            add_issue(
                row_events,
                "All",
                column,
                "Empty column detected",
                "",
                "Entire column contained no values."
            )

    if columns_to_remove:

        df = df.drop(
            columns=columns_to_remove
        )

    # Keep settings aligned with remaining columns.

    column_settings = {
        column: column_settings[column]
        for column in df.columns
    }

    negative_flags = {
        column: negative_flags[column]
        for column in df.columns
    }

    missing_settings = {
        column: missing_settings[column]
        for column in df.columns
    }

    # ---------------------------------------------------------
    # GENERATE ORIGINAL VALIDATION FINDINGS
    # ---------------------------------------------------------

    issue_log = create_issue_log(
        df,
        source_row_numbers,
        row_events,
        column_settings,
        negative_flags
    )

    # ---------------------------------------------------------
    # APPLY MISSING-VALUE REPLACEMENTS
    # ---------------------------------------------------------

    df = apply_missing_value_handling(
        df,
        column_settings,
        missing_settings,
        settings,
        source_row_numbers,
        changes
    )

    # ---------------------------------------------------------
    # EMAIL STANDARDISATION
    # ---------------------------------------------------------

    if settings["lowercase_emails"]:

        df = standardize_emails(
            df,
            column_settings,
            source_row_numbers,
            changes
        )

    # ---------------------------------------------------------
    # NUMERIC AND DATE CONVERSIONS
    # ---------------------------------------------------------

    df = apply_type_conversions(
        df,
        column_settings,
        settings,
        source_row_numbers,
        changes
    )

    # ---------------------------------------------------------
    # DETECT DUPLICATES AFTER TRANSFORMATIONS
    # ---------------------------------------------------------

    duplicate_mask = df.duplicated(
        keep="first"
    )

    duplicates_detected = int(
        duplicate_mask.sum()
    )

    duplicates_removed = 0
    duplicate_events = []

    for index in df.index[duplicate_mask]:

        row_text = format_row(df.loc[index])

        if settings["remove_duplicates"]:

            duplicates_removed += 1

            add_issue(
                duplicate_events,
                source_row_numbers[index],
                "",
                "Duplicate row removed",
                row_text,
                "Record matched an earlier row after enabled cleaning operations."
            )

            add_change(
                changes,
                source_row_numbers[index],
                "",
                row_text,
                "<ROW REMOVED>",
                "Duplicate row removal",
                "Removed a duplicate while retaining the first occurrence."
            )

        else:

            add_issue(
                duplicate_events,
                source_row_numbers[index],
                "",
                "Duplicate row detected",
                row_text,
                "Record matches an earlier row after enabled cleaning operations."
            )

    if duplicate_events:

        issue_log = pd.concat(
            [
                issue_log,
                pd.DataFrame(
                    duplicate_events,
                    columns=ISSUE_COLUMNS
                )
            ],
            ignore_index=True
        )

    if settings["remove_duplicates"]:

        df = df.loc[~duplicate_mask].copy()

    # ---------------------------------------------------------
    # CREATE CHANGE LOG
    # ---------------------------------------------------------

    change_log = create_change_log(changes)

    # ---------------------------------------------------------
    # OUTPUT DIRECTORY
    # ---------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    extension = file_path.suffix.lower()

    # ---------------------------------------------------------
    # SAVE CLEANED DATASET
    # ---------------------------------------------------------

    cleaned_file = (
        OUTPUT_DIR
        / f"cleaned_{file_path.stem}{extension}"
    )

    if extension == ".csv":

        df.to_csv(
            cleaned_file,
            index=False,
            encoding="utf-8-sig"
        )

    else:

        df.to_excel(
            cleaned_file,
            index=False,
            engine="openpyxl"
        )

    # ---------------------------------------------------------
    # SAVE ISSUE REPORT
    # ---------------------------------------------------------

    issue_file = (
        OUTPUT_DIR
        / f"data_quality_issues_{file_path.stem}.csv"
    )

    issue_log.to_csv(
        issue_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ---------------------------------------------------------
    # SAVE TRANSFORMATION LOG
    # ---------------------------------------------------------

    change_file = (
        OUTPUT_DIR
        / f"transformation_log_{file_path.stem}.csv"
    )

    change_log.to_csv(
        change_file,
        index=False,
        encoding="utf-8-sig"
    )

    # ---------------------------------------------------------
    # CALCULATE STATISTICS
    # ---------------------------------------------------------

    stats = {

        "original_rows": original_rows,

        "original_columns": original_columns,

        "cleaned_rows": len(df),

        "cleaned_columns": len(df.columns),

        "empty_rows": empty_rows_removed,

        "empty_rows_detected": empty_rows_detected,

        "empty_columns": empty_columns_removed,

        "duplicates": duplicates_removed,

        "duplicates_detected": duplicates_detected,

        "duplicates_removed": duplicates_removed,

        "total_issues": len(issue_log),

        "total_changes": len(change_log),

        "original_cells": original_rows * original_columns

    }

    # ---------------------------------------------------------
    # GENERATE QUALITY REPORT
    # ---------------------------------------------------------

    report_content = create_report(
        file_path.name,
        original_rows,
        original_columns,
        empty_rows_removed,
        empty_columns_removed,
        duplicates_removed,
        df,
        issue_log,
        column_settings,
        missing_settings,
        settings,
        change_log
    )

    report_file = (
        OUTPUT_DIR
        / f"quality_report_{file_path.stem}.txt"
    )

    report_file.write_text(
        report_content,
        encoding="utf-8"
    )

    # ---------------------------------------------------------
    # GENERATE COMPLETE EXCEL REPORT
    # ---------------------------------------------------------

    excel_report_file = (
        OUTPUT_DIR
        / f"complete_data_quality_report_{file_path.stem}.xlsx"
    )

    create_excel_report(
        excel_report_file,
        df,
        issue_log,
        change_log,
        stats,
        column_settings,
        missing_settings,
        settings
    )

    # ---------------------------------------------------------
    # TERMINAL SUMMARY
    # ---------------------------------------------------------

    print("\nSuccessfully processed!")

    print(f"Cleaned dataset: {cleaned_file.name}")

    print(f"Quality report: {report_file.name}")

    print(f"Issue report: {issue_file.name}")

    print(f"Transformation log: {change_file.name}")

    print(f"Complete Excel report: {excel_report_file.name}")

    print(f"Original records: {original_rows}")

    print(f"Cleaned records: {len(df)}")

    print(f"Issues identified: {len(issue_log)}")

    print(f"Transformations recorded: {len(change_log)}")

    # ---------------------------------------------------------
    # RETURN PROCESSING RESULTS
    # ---------------------------------------------------------

    return {

        "original_df": original_df,

        "cleaned_df": df,

        "issue_df": issue_log,

        "change_df": change_log,

        "stats": stats,

        "column_settings": column_settings,

        "missing_settings": missing_settings,

        "options": settings,

        "report_content": report_content,

        "cleaned_file": cleaned_file,

        "report_file": report_file,

        "issue_file": issue_file,

        "change_file": change_file,

        "excel_report_file": excel_report_file

    }


# =============================================================
# MAIN APPLICATION
# =============================================================

def main():

    INPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        [
            file_path
            for file_path in INPUT_DIR.iterdir()
            if (
                file_path.is_file()
                and file_path.suffix.lower() in SUPPORTED_FORMATS
                and not file_path.name.startswith("~$")
            )
        ]
    )

    if not files:

        print(
            "No supported input files found. "
            "Add CSV or XLSX files to the input folder."
        )

        return

    print("\n" + "=" * 60)

    print("PYTHON DATA CLEANING AUTOMATION")

    print("=" * 60)

    successful = 0
    failed = 0

    for file_path in files:

        try:

            process_file(file_path)

            successful += 1

        except Exception as error:

            failed += 1

            print(
                f"\nError processing {file_path.name}: "
                f"{type(error).__name__}: {error}"
            )

    print("\n" + "=" * 60)

    print("PROCESSING COMPLETED")

    print("=" * 60)

    print(f"Successful files: {successful}")

    print(f"Failed files: {failed}")

    print(f"Output directory: {OUTPUT_DIR}")

    print("=" * 60)


# =============================================================
# APPLICATION ENTRY POINT
# =============================================================

if __name__ == "__main__":
    main()
