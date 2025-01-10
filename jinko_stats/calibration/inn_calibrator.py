from jinko_stats.dependencies.dependency_checker import check_dependencies

check_dependencies(["matplotlib", "torch"])

from jinko_stats.calibration.inn import INN
from jinko_stats.calibration.utils.data import (
    normalize_df,
    remove_outliers,
    denormalize_input_df,
)
from jinko_helpers.types import asDict as jinko_types
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import torch
from scipy.stats import uniform, norm


class INNCalibrator:
    def __init__(
        self,
        vpop_design: jinko_types.VpopDesignWithModel,
        objectives: List[jinko_types.MarginalDistribution],
        inn: INN,
    ):
        """
        Initialize the INNCalibrator object.

        :param vpop_design: VpopDesign containing the input and output definitions
        :param objectives: List of MarginalDistribution objects of the objectives to be calibrated
        :param inn: INN to be used for calibration
        """
        self.input = []
        self.input_bounds = {}
        self.output = [o["id"] for o in objectives]
        self.objectives = objectives

        for marginal_distribution in vpop_design["marginalDistributions"]:
            distribution = marginal_distribution["distribution"]
            if isinstance(distribution, dict) and "tag" in distribution:
                if distribution["tag"] == "Uniform":
                    self.input.append(marginal_distribution["id"])
                    # Collect (min, max) tuple for inputs
                    self.input_bounds[marginal_distribution["id"]] = (
                        distribution["lowBound"],
                        distribution["highBound"],
                    )
                else:
                    # Raise an error, we only support Uniform for now
                    raise NotImplementedError(
                        f"Unsupported distribution type: {distribution['tag']}"
                    )
            else:
                raise TypeError(
                    f"Expected a dictionary-like distribution, got: {type(distribution)}"
                )

        self.N_DIM = len(self.input_bounds)
        self.N_OUT = len(self.output)

        self.training_df = None

        self.calib_with_output_df = None
        self.calib_with_output_csv = None

        self.last_id = None
        self.vpops = {}
        self.inn = inn

    def create_db_from_output_law(
        self,
        objectives: List[jinko_types.MarginalDistribution],
        filesave: str,
        n_samples: int = 5000,
        reuse: bool = False,
    ):
        """
        Create a pandas DataFrame from a list of output laws (marginal distributions).

        Parameters
        ----------
        objectives : List[jinko_types.MarginalDistribution]
            A list of marginal distributions.
        filesave : str
            The name of the file to save the DataFrame to. If None, the DataFrame
            will not be saved.
        n_samples : int, optional
            The number of samples to generate from each distribution. Defaults to 5000.
        reuse : bool, optional
            If True, do not re-generate the database if it already exists. Defaults to False.

        Returns
        -------
        pd.DataFrame
            The generated DataFrame.
        """
        # Check if replacement is not allowed and file exists
        if reuse and os.path.exists(filesave):
            existing_df = pd.read_csv(filesave)
            if len(existing_df) == n_samples:
                print(
                    f"File '{filesave}' already exists with {n_samples} samples. Loading the existing database."
                )
                self.calib_with_output_df = existing_df
                self.calib_with_output_csv = filesave
                return existing_df
            else:
                print(
                    f"File '{filesave}' exists but has {len(existing_df)} samples. Generating a new database."
                )

        samples = {}

        for obj in objectives:
            dist = obj["distribution"]

            if isinstance(dist, dict) and "tag" in dist:
                if dist["tag"] == "Uniform":
                    # Generate samples from a uniform distribution
                    low = dist["lowBound"]
                    high = dist["highBound"]
                    samples[obj["id"]] = np.random.uniform(low, high, n_samples)

                elif dist["tag"] == "Normal":
                    # Generate samples from a normal distribution
                    mean = dist["mean"]
                    stdev = dist["stdev"]
                    samples[obj["id"]] = np.random.normal(mean, stdev, n_samples)
                else:
                    raise NotImplementedError(
                        f"Unsupported distribution type: {dist['tag']}"
                    )
            else:
                raise TypeError(
                    f"Expected a dictionary-like distribution, got: {type(dist)}"
                )

        # Create DataFrame
        df = pd.DataFrame(samples)

        # Save to CSV if filename is provided
        df.to_csv(filesave, index=False)
        print(f"DataFrame saved to {filesave}")

        # Update class attributes
        self.calib_with_output_df = df
        self.calib_with_output_csv = filesave

    def calibrate_from_output(
        self,
        innObj: INN,
        n_samples: int,
        filesave: Optional[str] = None,
        viz: bool = True,
        filter_interval: bool = True,
        sigma: Optional[float] = None,
        id=None,
        dropna: bool = False,
        denormalize_input: bool = False,
        ratio: int = 2,
        set_to_zero: bool = False,
    ):
        """
        Calculate and save parameters based on the invertible neural network and visualize results.

        Parameters:
            inn (INN): An instance of the invertible neural network.
            n_samples (int): Number of samples to generate.
            filesave (str, optional): Path to the file where the results will be saved. Defaults to None.
            viz (bool, optional): Whether to visualize the results. Defaults to True.
            filter_interval (bool, optional): Whether to filter the generated samples to be within the interval. Defaults to True.
            sigma (float, optional): Sigma value for removing outliers. Defaults to None.
            id (int, optional): ID for the vpop. Defaults to None.
            dropna (bool, optional): Whether to drop NA values. Defaults to False.
            denormalize_input (bool, optional): Whether to denormalize the input. Defaults to False.
            ratio (int, optional): Ratio of samples to generate. Defaults to 2.
            set_to_zero (bool, optional): Whether to set the additional variables to zero. Defaults to False.
        """
        inn = innObj.inn
        normalization = innObj.normalization

        augmented_samples = ratio * n_samples

        df = normalize_df(self.calib_with_output_df, normalization)

        output_samples = []
        for param in self.output:
            if param in df.columns:
                values = df[param].values
                # Convert to tensor and append
                output_samples.append(torch.Tensor(values))
            else:
                raise ValueError(
                    f"Column '{param}' not found in the calibration DataFrame."
                )

        for i in range(self.N_DIM - self.N_OUT):
            additional_var_samples = (
                np.random.randn(augmented_samples)
                if not set_to_zero
                else np.zeros(augmented_samples)
            )
            output_samples.append(
                torch.Tensor(additional_var_samples)
            )  # Additional variable

        y_samples = torch.stack(output_samples, dim=1)

        with torch.no_grad():
            params_samples, _ = inn(y_samples, rev=True)
            params_pred = [
                params_samples[:, i].numpy() for i in range(len(self.input_bounds))
            ]

        vpop = {name: params_pred[i] for i, name in enumerate(self.input)}
        vpop_df = pd.DataFrame(vpop)

        if denormalize_input:
            vpop_df = denormalize_input_df(vpop_df, self.input_bounds)

        if filter_interval:
            total_rows_removed = 0
            mask = pd.Series([True] * len(vpop_df))  # Start with all True mask
            for col, (min_bound, max_bound) in self.input_bounds.items():
                initial_row_count = mask.sum()
                mask &= (vpop_df[col] >= min_bound) & (vpop_df[col] <= max_bound)
                rows_removed = initial_row_count - mask.sum()
                total_rows_removed += rows_removed
                print(
                    f"Filtered column '{col}' with interval ({min_bound}, {max_bound}): {rows_removed} rows removed"
                )
            print(f"Total rows removed: {total_rows_removed}")

        # Convert DataFrame to tensor
        input_tensor = torch.tensor(vpop_df.values, dtype=torch.float32)

        inn.eval()

        with torch.no_grad():
            # Pass tensor through the neural network
            output_tensor, _ = inn(input_tensor)

        # Extract the first n_out outputs
        n_out = len(self.output)
        first_n_out = output_tensor[:, :n_out]

        # Convert tensor to NumPy array
        first_n_out_np = first_n_out.detach().numpy()

        # Create DataFrame from first_n_out_np with new column names
        out_df = pd.DataFrame(first_n_out_np, columns=self.output)

        # Reset indices if they don't match
        vpop_df = vpop_df.reset_index(drop=True)
        out_df = out_df.reset_index(drop=True)

        vpop_df = pd.concat([vpop_df, out_df], axis=1)

        if sigma is not None:
            vpop_df = remove_outliers(vpop_df, self.output, sigma)

        ids = set(self.vpops.keys())
        if id is None:
            inside = True
            while inside:
                id = np.random.randint(0, 10000)
                inside = id in ids
        elif id in ids:
            raise Warning(f"Erasing vpop {id}")

        if dropna:
            vpop_df.dropna()

        try:
            vpop_df = vpop_df.sample(n_samples)
        except:
            raise Warning(f"Filtering leaves only {len(vpop_df)} samples")

        self.vpops[id] = vpop_df
        self.last_id = id

        # add a column patientIndex to vpop_df
        vpop_df["patientIndex"] = [f"patient{i+1}" for i in range(len(vpop_df))]

        vpop_df_for_export = vpop_df.copy(deep=True)
        # removes the output columns
        for col in self.output:
            vpop_df_for_export = vpop_df_for_export.drop(col, axis=1)
        if filesave is not None:
            # Save to CSV if filename is provided
            vpop_df_for_export.to_csv(filesave, index=False)
            print(f"DataFrame saved to {filesave}")

        if viz:

            num_cols = len(self.input_bounds)
            # Determine the number of rows and columns for subplots
            num_rows = (num_cols + 2) // 3  # Ensure at least one row for each 3 columns
            num_cols_subplot = min(num_cols, 3)  # At most 3 columns per row

            # Create a figure and set of subplots
            fig, axs = plt.subplots(
                num_rows, num_cols_subplot, figsize=(15, num_rows * 5)
            )

            # Flatten the axs array for easy indexing
            axs = axs.flatten() if num_cols > 1 else [axs]

            # Plot histograms for each column
            for i, column in enumerate(self.input):
                ax = axs[i]
                ax.hist(vpop_df[column], bins=30, color="b", alpha=0.7, density=True)
                ax.set_title(f"Histogram of {column}")
                ax.set_xlabel(column)
                ax.set_ylabel("Frequency")

                (a, b) = self.input_bounds[column]
                law = uniform(a, b - a)
                # Plot prior distribution
                x = np.linspace(law.ppf(0.001), law.ppf(0.999), 100)
                ax.plot(
                    x,
                    law.pdf(x),
                    "r-",
                    label=f"Prior: {column}",
                    linewidth=2,
                )

            # Hide any remaining subplots if there are fewer columns than subplots
            for j in range(i + 1, len(axs)):
                axs[j].axis("off")

            # Adjust layout and show plot
            plt.tight_layout()
            plt.show()
            # Initialize lists to collect computed values

    def visualize_generated_vpop_fit(
        self,
        vpop_file_path: str,
        scalar_results_file_path: str,
        scalar_results_train_path: str,
        percentile: Tuple[float, float] = (1, 99),
    ):
        """
        Visualize the generated virtual population fit to the computed values.

        :param vpop_file_path: Path to the CSV file containing the virtual population.
        :param scalar_results_file_path: Path to the CSV file containing the computed values.
        :param scalar_results_train_path: Path to the CSV file containing the training population.
        :param percentile: Tuple (1, 99) specifying the percentile range to filter the data.

        This function loads the virtual population and computed values into DataFrames. It then
        pivots the scalar data to make each scalarId a column, merges the DataFrames, and drops
        the 'patientId' column. The function then plots histograms for each computed value
        vs. the theoretical distribution.

        The histograms are filtered to include only values between the 1st and 99th percentiles
        of the training population. The x-axis range for the histograms is set to the range of
        the filtered data. The function then plots the distribution curve for each computed
        value. The function finally shows the plot.

        The function is useful for visualizing the generated virtual population fit to the
        computed values.
        """
        # Load CSVs into DataFrames
        df_vpop = pd.read_csv(vpop_file_path)
        df_scalar_results = pd.read_csv(scalar_results_file_path)

        # Pivot the scalar data to make each scalarId a column
        df_pivot = df_scalar_results.pivot(
            index="patientId", columns="scalarId", values="value"
        ).reset_index()
        # Merge the pivoted scalar data with the vpop data
        df_merged = pd.merge(
            df_vpop, df_pivot, left_on="patientIndex", right_on="patientId", how="left"
        )
        # Drop the 'patientId' column from the merge
        df_merged.drop(columns=["patientIndex", "patientId"], inplace=True)

        scalar_results_train_df = pd.read_csv(scalar_results_train_path)
        # Pivot the scalar data to make each scalarId a column
        training_df = scalar_results_train_df.pivot(
            index="patientId", columns="scalarId", values="value"
        ).reset_index()

        vpop_df = df_merged

        # Plot histograms for computed values vs. theoretical distributions
        num_outputs = len(self.output)
        num_rows = (num_outputs + 2) // 3

        if num_rows > 1:
            _, axs = plt.subplots(num_rows, 3, figsize=(15, num_rows * 5))
        else:
            _, axs = plt.subplots(1, num_outputs, figsize=(15, num_rows * 5))

        for i, name in enumerate(self.output):
            ax = axs[i // 3, i % 3] if num_rows > 1 else axs[i % 3]

            # Calculate the 1st and 99th percentiles
            p1_vpop = float(np.percentile(vpop_df[name], percentile[0]))
            p99_vpop = float(np.percentile(vpop_df[name], percentile[1]))
            p1_train = float(np.percentile(training_df[name], percentile[0]))
            p99_train = float(np.percentile(training_df[name], percentile[1]))

            p1 = min(p1_train, p1_vpop)
            p99 = max(p99_train, p99_vpop)

            # Filter the data to include only values between the 1st and 99th percentiles
            filtered_data = vpop_df[name][
                (vpop_df[name] >= p1) & (vpop_df[name] <= p99)
            ]
            filtered_training_data = training_df[name][
                (training_df[name] >= p1) & (training_df[name] <= p99)
            ]

            # Plot histogram of the filtered data
            ax.hist(
                filtered_data,
                bins=30,
                density=True,
                alpha=0.6,
                color="#e69e66",
                label=f"Histogram of {name} for virtual population",
            )
            ax.hist(
                filtered_training_data,
                bins=30,
                density=True,
                alpha=0.6,
                color="#56b4e9",
                label=f"Histogram of {name} for training population",
            )

            # Create the x values for the PDF plot, based on the filtered data range
            x_min = min(filtered_data.min(), filtered_training_data.min())
            x_max = max(filtered_data.max(), filtered_training_data.max())
            x = np.linspace(x_min, x_max, 100)

            # Plot the distribution curve
            dist = next(
                obj["distribution"] for obj in self.objectives if obj["id"] == name
            )

            if isinstance(dist, dict) and "tag" in dist:
                if dist["tag"] == "Uniform":
                    law = uniform(
                        loc=dist["lowBound"], scale=dist["highBound"] - dist["lowBound"]
                    )
                elif dist["tag"] == "Normal":
                    law = norm(loc=dist["mean"], scale=dist["stdev"])
                else:
                    raise NotImplementedError(
                        f"Unsupported distribution type: {dist['tag']}"
                    )
            else:
                raise TypeError(
                    f"Expected a dictionary-like distribution, got: {type(dist)}"
                )

            ax.plot(
                x,
                law.pdf(x),
                color="#e7a106",
                label=f"Objective of : {name}",
                linewidth=2,
            )

            # Set the title and legend
            ax.set_title(
                f"Histogram of {name} displaying at least ({percentile[0]} to {percentile[1]} percentile)"
            )
            ax.legend()

            # Hide any remaining subplots if there are fewer columns than subplots
        for j in range(i + 1, len(axs)):
            axs[j].axis("off")

        plt.tight_layout()
        plt.show()
