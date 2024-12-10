import base64 as _base64
import os as _os
import pandas as _pandas
import sqlite3 as _sqlite3


def df_to_sqlite(
    df: _pandas.DataFrame,
) -> str:
    """
    Convert a pandas DataFrame into a base64-encoded SQLite database.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to be converted.

    Returns
    -------
    str
        A base64-encoded SQLite database.

    Notes
    -----
    The function first renames the columns of the DataFrame to "col_{i}" with {i} > 0.
    Then, it writes the DataFrame to a temporary SQLite database file.
    Finally, it encodes the SQLite database in base64 and returns it.
    """
    column_real_names = df.columns.tolist()

    # Rename columns to col_{i} with {i} > 0
    column_names = ["col_%s" % (i + 1) for i, _ in enumerate(column_real_names)]
    column_names_mapping = {}
    for i, name in enumerate(column_real_names):
        column_names_mapping[name] = column_names[i]
    df.rename(columns=column_names_mapping, inplace=True)

    # Connect to SQLite database (or create it)
    data_table_sqlite_file_path = "temp_db.sqlite"

    # Remove existing file
    try:
        _os.remove(data_table_sqlite_file_path)
    except:
        pass

    conn = _sqlite3.connect(data_table_sqlite_file_path)
    cursor = conn.cursor()

    # Write the DataFrame to the SQLite database
    df.to_sql(
        "data",
        conn,
        if_exists="replace",
        index=False,
        dtype="TEXT",
    )

    # Create the 'data_columns' table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS data_columns (
        name TEXT UNIQUE,
        realname TEXT UNIQUE
    )
    """
    )

    # Insert column data into 'data_columns' table
    for i, name in enumerate(column_names):
        cursor.execute(
            "INSERT OR IGNORE INTO data_columns (name, realname) VALUES (?, ?)",
            (name, column_real_names[i]),
        )

    # Commit changes and close the connection
    conn.commit()
    conn.close()

    # Step 2: Encode SQLite database in base64
    with open(data_table_sqlite_file_path, "rb") as f:
        encoded_data_table = _base64.b64encode(f.read()).decode("utf-8")
    _os.remove("temp_db.sqlite")

    return encoded_data_table


def data_table_to_sqlite(data_table_file_path: str) -> str:
    """
    Reads a CSV file at the given path and converts it to a base64-encoded SQLite database.

    Args:
        data_table_file_path: The path to the CSV file.

    Returns:
        A base64-encoded SQLite database containing the data from the CSV file.

    Raises:
        FileNotFoundError: If the file at `data_table_file_path` does not exist.
        ValueError: If the file at `data_table_file_path` cannot be parsed as a CSV file.
    """
    df = csv_to_df(data_table_file_path)
    return df_to_sqlite(df)


def csv_to_df(data_table_file_path: str) -> _pandas.DataFrame:
    """
    Converts a CSV file into a pandas DataFrame.

    Args:
        data_table_file_path: The path to the CSV file.

    Returns:
        A pandas DataFrame containing the data from the CSV file.

    Raises:
        FileNotFoundError: If the CSV file at the specified path does not exist.
        ValueError: If there is an error while parsing the CSV file.
    """
    if not _os.path.isfile(data_table_file_path):
        raise FileNotFoundError(f"CSV file '{data_table_file_path}' not found.")

    try:
        df = _pandas.read_csv(data_table_file_path)
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file '{data_table_file_path}': {e}")

    return df
