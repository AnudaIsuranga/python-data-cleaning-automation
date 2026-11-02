
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import main as cleaner


class DataCleaningTests(unittest.TestCase):

    def setUp(self):
        """Create an isolated temporary environment for each test."""

        self.temp = tempfile.TemporaryDirectory()

        self.root = Path(self.temp.name)

        self.input_dir = self.root / "input"
        self.output_dir = self.root / "output"

        self.input_dir.mkdir()
        self.output_dir.mkdir()

        self.output_patch = patch.object(
            cleaner,
            "OUTPUT_DIR",
            self.output_dir
        )

        self.output_patch.start()

    def tearDown(self):
        """Restore the original output directory and clean temporary files."""

        self.output_patch.stop()
        self.temp.cleanup()

    def create_csv(self, name, content):
        """Create a temporary CSV test file."""

        path = self.input_dir / name

        path.write_text(
            content,
            encoding="utf-8"
        )

        return path

    # ---------------------------------------------------------
    # TEST 1: NUMERIC, DATE AND EMAIL TRANSFORMATIONS
    # ---------------------------------------------------------

    def test_basic_transformations(self):

        path = self.create_csv(
            "transformation_test.csv",
            '''record_id,email,amount,order_date
1,ALICE@EXAMPLE.COM,"2,500",October 20 2026
2,bob@example.com,1800,October 21 2026
3,charlie@example.com,950,October 22 2026
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "lowercase_emails": True,
                "convert_numeric_columns": True,
                "standardize_date_columns": True
            }
        )

        cleaned = result["cleaned_df"]

        self.assertEqual(
            len(cleaned),
            3
        )

        self.assertEqual(
            cleaned.loc[0, "email"],
            "alice@example.com"
        )

        self.assertEqual(
            cleaned.loc[0, "amount"],
            2500
        )

        self.assertEqual(
            cleaned.loc[0, "order_date"],
            "2026-10-20"
        )

        self.assertEqual(
            len(result["change_df"]),
            7
        )

        self.assertTrue(
            result["issue_df"].empty
        )

        self.assertEqual(
            result["stats"]["total_changes"],
            7
        )

    # ---------------------------------------------------------
    # TEST 2: MISSING-VALUE REPLACEMENT
    # ---------------------------------------------------------

    def test_missing_value_replacement(self):

        path = self.create_csv(
            "missing_test.csv",
            '''customer_id,email
1,alice@example.com
2,
3,bob@example.com
'''
        )

        result = cleaner.process_file(
            path,
            column_types={
                "email": {
                    "type": "Email",
                    "missing_strategy": "fill",
                    "missing_value": "unknown@example.com"
                }
            }
        )

        cleaned = result["cleaned_df"]

        self.assertEqual(
            cleaned.loc[1, "email"],
            "unknown@example.com"
        )

        self.assertIn(
            "Missing value",
            result["issue_df"]["issue"].tolist()
        )

        self.assertIn(
            "Missing-value replacement",
            result["change_df"]["action"].tolist()
        )

    # ---------------------------------------------------------
    # TEST 3: DUPLICATE REMOVAL
    # ---------------------------------------------------------

    def test_duplicate_removal(self):

        path = self.create_csv(
            "duplicate_test.csv",
            '''customer_id,name
1,Amal
2,Nimali
2,Nimali
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "remove_duplicates": True
            }
        )

        self.assertEqual(
            len(result["cleaned_df"]),
            2
        )

        self.assertEqual(
            result["stats"]["duplicates_removed"],
            1
        )

        self.assertIn(
            "Duplicate row removed",
            result["issue_df"]["issue"].tolist()
        )

    # ---------------------------------------------------------
    # TEST 4: KEEP DUPLICATES WHEN DISABLED
    # ---------------------------------------------------------

    def test_duplicate_preservation(self):

        path = self.create_csv(
            "duplicate_keep_test.csv",
            '''customer_id,name
1,Amal
1,Amal
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "remove_duplicates": False
            }
        )

        self.assertEqual(
            len(result["cleaned_df"]),
            2
        )

        self.assertIn(
            "Duplicate row detected",
            result["issue_df"]["issue"].tolist()
        )

    # ---------------------------------------------------------
    # TEST 5: IGNORE COLUMN VALIDATION
    # ---------------------------------------------------------

    def test_ignore_column(self):

        path = self.create_csv(
            "ignore_test.csv",
            '''email
invalid-email
'''
        )

        result = cleaner.process_file(
            path,
            column_types={
                "email": {
                    "type": "Ignore"
                }
            }
        )

        self.assertNotIn(
            "Invalid email",
            result["issue_df"]["issue"].tolist()
        )

        self.assertEqual(
            len(result["cleaned_df"]),
            1
        )

    # ---------------------------------------------------------
    # TEST 6: INVALID NUMERIC VALUE CORRECTION
    # ---------------------------------------------------------

    def test_invalid_numeric_correction(self):

        path = self.create_csv(
            "invalid_numeric_test.csv",
            '''amount
100
not a number
250
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "convert_numeric_columns": True,
                "invalid_numeric_action": "set_missing"
            },
            column_types={
                "amount": {
                    "type": "Number"
                }
            }
        )

        cleaned = result["cleaned_df"]

        self.assertEqual(
            cleaned.loc[0, "amount"],
            100
        )

        self.assertTrue(
            pd.isna(cleaned.loc[1, "amount"])
        )

        self.assertIn(
            "Invalid numeric value",
            result["issue_df"]["issue"].tolist()
        )

        self.assertIn(
            "Invalid numeric value correction",
            result["change_df"]["action"].tolist()
        )

    # ---------------------------------------------------------
    # TEST 7: INVALID DATE VALUE CORRECTION
    # ---------------------------------------------------------

    def test_invalid_date_correction(self):

        path = self.create_csv(
            "invalid_date_test.csv",
            '''order_date
January 2 2026
not a date
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "standardize_date_columns": True,
                "invalid_date_action": "set_missing"
            },
            column_types={
                "order_date": {
                    "type": "Date"
                }
            }
        )

        cleaned = result["cleaned_df"]

        self.assertEqual(
            cleaned.loc[0, "order_date"],
            "2026-01-02"
        )

        self.assertTrue(
            pd.isna(cleaned.loc[1, "order_date"])
        )

        self.assertIn(
            "Invalid date",
            result["issue_df"]["issue"].tolist()
        )

        self.assertIn(
            "Invalid date correction",
            result["change_df"]["action"].tolist()
        )

    # ---------------------------------------------------------
    # TEST 8: COMPLETE EXCEL REPORT
    # ---------------------------------------------------------

    def test_excel_report_generation(self):

        path = self.create_csv(
            "excel_report_test.csv",
            '''customer_id,name
1,Amal
2,Nimali
'''
        )

        result = cleaner.process_file(path)

        report_path = result["excel_report_file"]

        self.assertTrue(
            report_path.exists()
        )

        expected_sheets = {
            "Cleaned Data",
            "Issue Log",
            "Change Log",
            "Summary",
            "Column Settings",
            "Missing Settings",
            "Cleaning Settings"
        }

        # Open the Excel report and automatically close it
        # after checking the worksheet names.
        with pd.ExcelFile(report_path) as excel_file:

            self.assertEqual(
                set(excel_file.sheet_names),
                expected_sheets
            )

    # ---------------------------------------------------------
    # TEST 9: XLSX INPUT PROCESSING
    # ---------------------------------------------------------

    def test_excel_input_processing(self):

        path = self.input_dir / "excel_input_test.xlsx"

        test_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "name": ["Amal", "Nimali", "Sahan"]
        })

        test_df.to_excel(
            path,
            index=False
        )

        result = cleaner.process_file(path)

        self.assertEqual(
            len(result["cleaned_df"]),
            3
        )

        self.assertTrue(
            result["cleaned_file"].exists()
        )

        self.assertTrue(
            result["excel_report_file"].exists()
        )

    # ---------------------------------------------------------
    # TEST 10: EMPTY ROW REMOVAL
    # ---------------------------------------------------------

    def test_empty_row_removal(self):

        path = self.create_csv(
            "empty_row_test.csv",
            '''id,name
1,Amal
,
2,Nimali
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "remove_empty_rows": True
            }
        )

        self.assertEqual(
            len(result["cleaned_df"]),
            2
        )

        self.assertEqual(
            result["stats"]["empty_rows"],
            1
        )

        self.assertIn(
            "Empty row removed",
            result["issue_df"]["issue"].tolist()
        )

    # ---------------------------------------------------------
    # TEST 11: MISSING VALUES IN AN ENTIRE COLUMN
    # ---------------------------------------------------------

    def test_empty_column_replacement(self):

        path = self.create_csv(
            "empty_column_test.csv",
            '''customer_id,reference
1,
2,
'''
        )

        result = cleaner.process_file(
            path,
            options={
                "remove_empty_columns": True
            },
            column_types={
                "reference": {
                    "type": "Text",
                    "missing_strategy": "fill",
                    "missing_value": "UNKNOWN"
                }
            }
        )

        cleaned = result["cleaned_df"]

        self.assertIn(
            "reference",
            cleaned.columns
        )

        self.assertTrue(
            (cleaned["reference"] == "UNKNOWN").all()
        )

        self.assertIn(
            "Missing-value replacement",
            result["change_df"]["action"].tolist()
        )


# =============================================================
# TEST RUNNER
# =============================================================

if __name__ == "__main__":

    print("\n")
    print("=" * 60)
    print("DATA CLEANING AUTOMATION - AUTOMATED TESTS")
    print("=" * 60)

    unittest.main(
        verbosity=2
    )
