import unittest
import pandas as pd
import sqlite3
import base64
from io import StringIO
import jinko_helpers

csv_example = """armScope,obsId,time,value
iv-0.1-10,tumorBurden,P0D,50.00
iv-0.1-10,tumorBurden,P7D,48.75
iv-1-10,tumorBurden,P0D,50.00
iv-1-10,tumorBurden,P7D,48.51
"""


class TestDataFrameToSQLite(unittest.TestCase):
    def test_data_frame_to_sqlite(self):
        # Load the CSV content into a pandas DataFrame
        df = pd.read_csv(StringIO(csv_example))

        # Convert DataFrame to base64-encoded SQLite database
        encoded_sqlite = jinko_helpers.df_to_sqlite(df)

        # Decode the base64 data back to a binary SQLite database
        sqlite_binary = base64.b64decode(encoded_sqlite)

        # Save the binary data to a temporary SQLite database file
        with open("test_temp_db.sqlite", "wb") as temp_db_file:
            temp_db_file.write(sqlite_binary)

        # Connect to the SQLite database
        conn = sqlite3.connect("test_temp_db.sqlite")
        cursor = conn.cursor()

        # Verify data table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='data';"
        )
        self.assertTrue(cursor.fetchone())

        # Verify columns were renamed correctly
        cursor.execute("PRAGMA table_info(data);")
        columns = [info[1] for info in cursor.fetchall()]
        expected_columns = ["col_1", "col_2", "col_3", "col_4"]
        self.assertEqual(columns, expected_columns)

        # Verify 'data_columns' table
        cursor.execute("SELECT * FROM data_columns;")
        data_columns = cursor.fetchall()
        expected_data_columns = [
            ("col_1", "armScope"),
            ("col_2", "obsId"),
            ("col_3", "time"),
            ("col_4", "value"),
        ]
        self.assertEqual(data_columns, expected_data_columns)

        # Verify the content of the data table
        cursor.execute("SELECT * FROM data;")
        data_rows = cursor.fetchall()
        expected_data_rows = [
            ("iv-0.1-10", "tumorBurden", "P0D", "50.0"),
            ("iv-0.1-10", "tumorBurden", "P7D", "48.75"),
            ("iv-1-10", "tumorBurden", "P0D", "50.0"),
            ("iv-1-10", "tumorBurden", "P7D", "48.51"),
        ]
        self.assertEqual(data_rows, expected_data_rows)

        conn.close()

        # Clean up temporary SQLite database file
        import os

        os.remove("test_temp_db.sqlite")


if __name__ == "__main__":
    unittest.main()
