from jinko_stats.dependencies.dependency_checker import check_dependencies

check_dependencies(["torch"])

import numpy as np
from torch.utils.data import Dataset
import pandas as pd
import torch

## DATASET - DATALOADER


def create_normalization_df(df, colnames, outliers):
    """
    Filter out outliers (values beyond 'outlier' standard deviations from the mean) and normalize specified columns
    in a CSV file to be between 0 and 10 using affine transformation, and save the normalized DataFrame back
    to the same file.

    Parameters:
    - file_path: Path to the CSV file to be normalized.
    - colnames: List of column names to be normalized.

    Returns:
    - dict: A dictionary with column names as keys and tuples (a, b) as values,
            where the transformation for each column is f(x) = ax + b.
    """
    # Check if all specified columns are in the DataFrame
    missing_cols = [col for col in colnames if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Columns {missing_cols} are not present in the DataFrame.")

    # Initialize a dictionary to store the transformation parameters
    transformations = {}

    # Normalize specified columns
    df_normalized = df.copy()  # Make a copy to keep original data intact
    for col in colnames:
        if df[col].dtype in [float, int]:  # Only normalize numeric columns
            # Filter out outliers beyond 5 standard deviations from the mean
            mean = df[col].mean()
            std_dev = df[col].std()
            lower_bound = mean - outliers * std_dev
            upper_bound = mean + outliers * std_dev

            df_filtered = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

            if df_filtered[
                col
            ].empty:  # Check if filtering resulted in an empty DataFrame
                print(f"No data left after filtering outliers for column '{col}'")
                continue

            min_val = df_filtered[col].min()
            max_val = df_filtered[col].max()

            if min_val != max_val:  # Avoid division by zero
                # Calculate transformation parameters for normalization to [1, 10]
                a = (10 - 1) / (max_val - min_val)
                b = 1 - a * min_val
                df_normalized[col] = a * df_filtered[col] + b
                transformations[col] = (a, b)
            else:
                # If min_val == max_val, all values are the same, so we can't scale them to the desired range
                print(f"Constant column '{col}' after outlier removal")
                df_normalized[col] = df_filtered[col]  # Keep the column unchanged

                transformations[col] = (1, 0)  # Default to no change for such cases
        else:
            raise ValueError(f"Column '{col}' is not numeric and cannot be normalized.")

    df_normalized.dropna(inplace=True)

    return df_normalized, transformations


def remove_outliers(df, col, outliers):
    """
    Removes rows from the DataFrame where the values in the specified columns
    are farther away from the mean than `outliers * std`.

    Parameters:
    df (pd.DataFrame): The DataFrame to remove outliers from.
    col (list): A list of column names to check for outliers.
    outliers (float): The number of standard deviations away from the mean to define an outlier.

    Returns:
    pd.DataFrame: The DataFrame with outliers removed.
    """
    # Create a copy of the DataFrame to avoid modifying the original
    df_filtered = df.copy()

    for c in col:
        mean = df_filtered[c].mean()
        std = df_filtered[c].std()

        # Calculate the lower and upper bounds for non-outliers
        lower_bound = mean - outliers * std
        upper_bound = mean + outliers * std

        # Filter out rows where the values are outside the bounds
        df_filtered = df_filtered[
            (df_filtered[c] >= lower_bound) & (df_filtered[c] <= upper_bound)
        ]

    return df_filtered


def normalize_tensor(tensor, a, b):
    """Linearly normalize the tensor using provided a and b."""
    return a * tensor + b


def normalize_df(df: pd.DataFrame, normalization: dict) -> pd.DataFrame:
    """
    Normalize the columns of the DataFrame based on the provided normalization parameters.

    Parameters:
    df (pd.DataFrame): The DataFrame to be normalized.
    normalization (dict): A dictionary where keys are column names and values are tuples (a, b)
                           for the normalization formula: normalized_value = a * value + b.

    Returns:
    pd.DataFrame: A new DataFrame with normalized columns.
    """
    # Copy the DataFrame to avoid modifying the original
    normalized_df = df.copy()

    # Iterate over the normalization dictionary
    for col_name, (a, b) in normalization.items():
        if col_name in normalized_df.columns:
            # Apply the normalization formula
            normalized_df[col_name] = a * normalized_df[col_name] + b
        else:
            raise KeyError(f"Column '{col_name}' not found in DataFrame.")

    return normalized_df


def normalize_input_df(df, prior_bounds_dict):
    """
    Normalize specified columns of a DataFrame to the [-1, 1] interval.

    Parameters:
    df (pd.DataFrame): The input DataFrame.
    cols (list of str): The list of column names to normalize.
    intervals (list of tuple): A list of (a, b) tuples corresponding to the range of values
                               to normalize for each column.

    Returns:
    pd.DataFrame: A DataFrame with the specified columns normalized to the [-1, 1] range.
    """
    df_normalized = df.copy()  # Make a copy to avoid modifying the original DataFrame

    for col, (a, b) in prior_bounds_dict.items():
        df_normalized[col] = 2 * (df_normalized[col] - a) / (b - a) - 1

    return df_normalized


def denormalize_input_df(df, prior_bounds_dict):
    """
    Denormalize specified columns of a DataFrame from the [-1, 1] interval back to the original intervals.

    Parameters:
    df (pd.DataFrame): The input DataFrame with normalized data.
    prior_bounds_dict: dict: A dictionary mapping column names to their prior bounds. bounds are tuple (a, b)

    Returns:
    pd.DataFrame: A DataFrame with the specified columns denormalized to their original intervals.
    """
    df_denormalized = df.copy()  # Make a copy to avoid modifying the original DataFrame

    for col, (a, b) in prior_bounds_dict.items():
        df_denormalized[col] = (df_denormalized[col] + 1) * (b - a) / 2 + a

    return df_denormalized


def denormalize(df, norm):
    """
    Denormalizes a DataFrame using the given normalization dictionary.

    Parameters:
    df (pd.DataFrame): The DataFrame with normalized data.
    norm (dict): A dictionary where the keys are column names and values are tuples (a, b),
                 representing the normalization parameters.

    Returns:
    pd.DataFrame: A DataFrame with denormalized data.
    """
    # Create a copy of the DataFrame to avoid modifying the original
    df_denormalized = df.copy()

    # Apply the denormalization formula for each column in the norm dictionary
    for col, (a, b) in norm.items():
        df_denormalized[col] = (df_denormalized[col] - b) / a

    return df_denormalized


class TrajectoriesDataset(Dataset):
    def __init__(self, dataframe, cols_in, cols_out, N_DIM):
        """
        Initialize the dataset.

        Parameters:
        - dataframe: Pandas DataFrame containing all the data.
        - cols_in: List of column names to be used as input variables.
        - cols_out: List of column names to be used as output variables.
        - N_DIM: Total number of dimensions (including input variables and random variables).
        """
        self.df = dataframe
        self.cols_in = cols_in
        self.cols_out = cols_out
        self.N_DIM = N_DIM
        self.N_OUT = len(cols_out)
        self.N_RANDOM = N_DIM - self.N_OUT

        if self.N_RANDOM < 0:
            raise ValueError("N_DIM is too small for the number of output columns.")

        # Check if all specified columns exist in the DataFrame
        missing_cols_in = [col for col in self.cols_in if col not in self.df.columns]
        missing_cols_out = [col for col in self.cols_out if col not in self.df.columns]
        if missing_cols_in or missing_cols_out:
            raise ValueError(
                f"Columns {missing_cols_in + missing_cols_out} are not present in the DataFrame."
            )

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        # Extract input columns
        in_vars = [self.df[col].iloc[idx] for col in self.cols_in]

        # Extract output columns
        out_vars = [self.df[col].iloc[idx] for col in self.cols_out]

        # Generate random variables
        rand_vars = np.random.randn(self.N_RANDOM)

        # Combine input variables, output variables, and random variables
        all_vars = in_vars + out_vars + list(rand_vars)

        return [torch.tensor(all_vars, dtype=torch.float32)]
