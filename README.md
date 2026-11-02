# Python Data Cleaning Automation

A Python-based data cleaning and quality analysis application with an interactive Streamlit interface. Upload CSV or Excel datasets, configure validation rules, clean inconsistent data, inspect detected issues, and download detailed reports.

## Project Overview

Data preparation is an important part of data analysis, but real-world datasets frequently contain missing values, duplicate records, inconsistent formatting, and invalid entries.

This project provides an interactive tool to help automate common data cleaning operations and make data quality issues easier to identify and review.

Users can upload datasets, configure column-specific validation and missing-value handling, apply cleaning operations, inspect before-and-after results, and export cleaned data with supporting reports.

## Key Features

### 1. Dataset Upload
- Upload CSV and Excel (`.xlsx`) files.
- Preview uploaded datasets before processing.
- Upload multiple datasets through the application interface.

### 2. Configurable Column Validation
Configure data types for individual columns:

- Auto
- Text
- Email
- Phone
- Number
- Date
- Ignore

### 3. Data Cleaning
- Remove unnecessary leading and trailing whitespace.
- Standardise common missing-value markers.
- Remove completely empty rows.
- Remove completely empty columns.
- Detect and remove exact duplicate records.
- Convert email addresses to lowercase.
- Convert valid numeric values.
- Standardise valid dates to `YYYY-MM-DD`.

### 4. Data Quality Validation
- Identify missing values.
- Validate email addresses.
- Validate phone number formats.
- Identify invalid numeric values.
- Identify invalid date values.
- Optionally flag negative numeric values.
- Review detected issues before and after correction.

### 5. Missing-Value Management
Configure missing-value handling for individual columns, including retaining missing values or replacing them with specified values.

### 6. Invalid Data Correction
Choose how invalid numeric and date values should be handled:
- Keep and report.
- Replace invalid values with missing values.

### 7. Interactive Data Quality Dashboard
The Streamlit interface provides:
- Data quality indicators.
- Before-and-after dataset previews.
- Issue summaries.
- Missing-value analysis.
- Issue exploration by row and column.
- Transformation history.
- Visual summaries of detected issues and applied changes.

### 8. Transformation Change Log
Record data modifications with details such as:
- Source row.
- Column name.
- Original value.
- New value.
- Transformation performed.
- Explanation of the change.

### 9. Exportable Reports

The application provides five downloadable outputs:

1. Cleaned dataset.
2. Data quality report.
3. Detailed issue report.
4. Transformation change log.
5. Complete Excel quality report.

The complete Excel report contains seven worksheets:

- Cleaned Data
- Issue Log
- Change Log
- Summary
- Column Settings
- Missing Settings
- Cleaning Settings

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| Pandas | Data manipulation and cleaning |
| Streamlit | Interactive web application |
| Plotly | Data visualisation |
| OpenPyXL | Excel file processing and reporting |
| Unittest | Automated testing |

Additional dependencies are listed in `requirements.txt`.

## Project Structure

```text
Python_Data_Cleaning_Automation/
│
├── input/
│   ├── sample_customers.csv
│   ├── sample_customers_excel.xlsx
│   ├── advanced_sample_customers.csv
│   └── manual_test.csv
│
├── output/
│   └── .gitkeep
│
├── app.py
├── main.py
├── test_main.py
├── requirements.txt
├── README.md
└── .gitignore
```

The `input` folder contains demonstration datasets. The `output` folder is used for generated files by the core cleaning engine.

The virtual environment and generated output files are excluded from the Git repository.

## Installation and Setup

### Prerequisites

- Python
- pip
- Git
- Visual Studio Code (recommended)

### 1. Clone the Repository

```bash
git clone <YOUR-GITHUB-REPOSITORY-URL>
```

Navigate into the project directory:

```bash
cd Python_Data_Cleaning_Automation
```

### 2. Create a Virtual Environment

Windows:

```powershell
py -m venv venv
```

### 3. Activate the Virtual Environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python -m streamlit run app.py
```

Open the local application in your browser:

```text
http://localhost:8501
```

## Running Automated Tests

The project includes an automated test suite covering core data-cleaning functionality.

Run:

```bash
python -m unittest -v test_main.py
```

The current test suite contains 11 tests covering:

- Numeric, date and email transformations.
- Missing-value replacement.
- Duplicate removal and preservation.
- Ignored column validation.
- Invalid numeric value correction.
- Invalid date correction.
- Excel report generation.
- Excel input processing.
- Empty-row removal.
- Entirely missing column handling.

All 11 automated tests passed in the development environment.

## How to Use

1. Launch the Streamlit application.
2. Upload a CSV or Excel dataset.
3. Preview the original dataset.
4. Configure data types and missing-value handling for individual columns.
5. Select the cleaning and validation operations.
6. Choose how invalid numeric and date values should be handled.
7. Click **Clean and Analyse Data**.
8. Review the data quality indicators, issue explorer and transformation history.
9. Download the cleaned dataset and generated reports.

## Data Quality Score

The application displays a demonstration data quality score based on identified issues relative to the original dataset size.

This is a project-specific indicator for comparing results. It is not an industry-certified data quality measurement.

Detected issues are retained in the issue report even when corresponding values are corrected, preserving an audit trail of the original problems.

## Testing and Development Status

The following have been verified during development:

- 11 automated unit tests passed.
- CSV processing and cleaning.
- Excel input processing through the core engine.
- Streamlit CSV processing.
- Data validation and transformation logging.
- Generation and opening of downloadable reports.

Additional testing is required before treating the application as a production-ready service.

## Limitations and Future Improvements

Potential future enhancements include:

- More advanced data validation rules.
- Customisable validation patterns.
- Additional file format support.
- Larger dataset performance improvements.
- More advanced data quality metrics.
- Cloud deployment.
- User authentication and access control.
- Automated data profiling and cleaning recommendations.

## Disclaimer

This project is a data cleaning and quality analysis portfolio application. Users should review the cleaning configuration and generated outputs before using cleaned data in business-critical workflows.

## Author

Developed as a Python data automation and data quality portfolio project.