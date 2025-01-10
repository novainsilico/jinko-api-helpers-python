from jinko_stats.dependencies.dependency_checker import check_dependencies

check_dependencies(["sklearn.model_selection", "seaborn", "matplotlib", "torch"])

from jinko_stats.calibration.utils.nn import invertible_nn
from jinko_stats.calibration.utils.data import (
    normalize_df,
    normalize_input_df,
    TrajectoriesDataset,
    denormalize,
    create_normalization_df,
)
from jinko_stats.calibration.utils.train import train_model_display
from jinko_helpers.types import asDict as jinko_types
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
import torch
import seaborn as sns
from typing import Optional, Union
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np


class INN:
    def __init__(
        self,
        type: str,
        N_DIM: int,
        N_NODES: int,
        N_LAYERS: int,
        lr: float,
        inn_resource_dir: str,
    ):
        self.N_DIM = N_DIM
        self.N_NODES = N_NODES
        self.N_LAYERS = N_LAYERS
        self.type = type
        self.lr = lr
        self.inn_resource_dir = inn_resource_dir
        self.inn, self.optimizer, self.scheduler, self.filesave = invertible_nn(
            type,
            N_DIM,
            N_NODES,
            N_LAYERS,
            s=["lr-exp", 0.985],
            lr=lr,
            inn_resource_dir=inn_resource_dir,
        )
        self.training_csv = None
        self.training_df = None
        self.output_columns = None
        self.input_columns = None
        self.df_test = None
        self.testing_csv = None
        self.testing_df = None
        self.acc = None
        self.N_OUT = None
        self.loss = None

    def create_train_validation_set(
        self,
        vpop_file_path: str,
        scalar_results_file_path: str,
        vpop_design: jinko_types.VpopDesignWithModel,
        train_file_path: str,
        validation_file_path: str,
        ratio: float = 0.2,
    ):
        """
        Process the CSV file to transform it into the desired DataFrame format.

        :param csv_file_path: Path to the CSV file to be processed
        :return: Transformed DataFrame
        """

        # Load CSVs into DataFrames
        df_vpop = pd.read_csv(vpop_file_path)
        df_scalar_results = pd.read_csv(scalar_results_file_path)

        self.output_columns = df_scalar_results.scalarId.unique().tolist()

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

        df_train, df_validation = train_test_split(df_merged, test_size=ratio)

        df_train.to_csv(train_file_path, index=False)
        print("successfully saved train set to " + train_file_path)
        df_validation.to_csv(validation_file_path, index=False)
        print("successfully saved validation set to " + validation_file_path)

        self.build_training_set(train_file_path, vpop_design, self.output_columns)
        self.build_validation_set(validation_file_path)

    # Function to load a trained model
    def load_model(self, file: str, parallel: bool = False):
        """
        Loads a trained model state dictionary from a file. Make sure INN was initialized with same parameters

        Parameters:
        file (str): File path to the trained model state dictionary.
        parallel (bool) : Indicates if bool has been trained with DataParallel.
        """
        state_dict = torch.load(file)

        new_state_dict = {}

        if parallel:
            for k, v in state_dict.items():
                if k.startswith("module."):
                    new_state_dict[k[7:]] = v
                else:
                    new_state_dict[k] = v
        else:
            new_state_dict = state_dict
        self.inn.load_state_dict(new_state_dict)

    def build_training_set(
        self,
        training_csv: str,
        vpop_design_content: jinko_types.VpopDesignWithModel,
        output_columns: list[str],
        outliers: int = 3,
    ):
        """
        Builds a normalized training set from a CSV file, filters out outliers and applies normalization.

        :param training_csv: Path to the CSV file containing the training data
        :param vpop_design_content: VpopDesignWithModel object containing the input and output definitions
        :param output_columns: List of strings of the output columns
        :param outliers: number of standard deviations to consider as outliers
        """
        self.training_csv = training_csv

        # Initialize the output lists
        self.input_columns = []
        self.output_columns = output_columns
        self.prior_list = []
        self.prior_bounds_dict = {}

        for marginal_distribution in vpop_design_content["marginalDistributions"]:
            distribution = marginal_distribution["distribution"]
            if distribution["tag"] == "Uniform":
                self.input_columns.append(marginal_distribution["id"])
                # Collect (min, max) tuple for inputs
                self.prior_list.append(
                    (distribution["lowBound"], distribution["highBound"])
                )
                self.prior_bounds_dict[marginal_distribution["id"]] = (
                    distribution["lowBound"],
                    distribution["highBound"],
                )
            else:
                # raise an error, we only support Uniform for now
                raise NotImplementedError

        self.N_DIM = len(self.prior_bounds_dict)
        self.N_OUT = len(self.output_columns)

        training_df = pd.read_csv(self.training_csv)
        self.training_df, self.normalization = create_normalization_df(
            training_df, self.output_columns, outliers
        )
        print("Normalized Training set is built")

    def build_validation_set(self, testing_csv: str):
        """
        Loads the validation CSV file, applies normalization using the provided normalization dictionary,
        and saves the normalized DataFrame with original columns duplicated with a '_real' suffix.

        Parameters:
        - testing_csv: Path to the CSV file containing the testing data.
        """
        self.testing_csv = testing_csv
        self.testing_df = pd.read_csv(testing_csv)

        self.testing_df = self.testing_df[self.input_columns + self.output_columns]

        # Check if self.normalization is defined
        if not hasattr(self, "normalization") or self.normalization is None:
            raise ValueError(
                "Normalization dictionary 'self.normalization' is not defined."
            )

        # Duplicate original columns with '_real' suffix
        for col in self.normalization.keys():
            if col in self.testing_df.columns:
                self.testing_df[f"{col}_real"] = self.testing_df[col]
            else:
                print(
                    f"Warning: Column '{col}' is not present in the testing DataFrame."
                )

        self.testing_df = normalize_df(self.testing_df, self.normalization)
        print("Normalized validation set is built")

    def visualize_set_2d(self, plot: Union[str, pd.DataFrame], normalized: bool = True):
        if len(self.output_columns) != 2:
            raise ValueError("There must be exactly 2 outputs for this plot")

        if isinstance(plot, str):
            if plot == "testing":
                plot_df = self.testing_df
            else:
                plot_df = self.training_df
        else:
            plot_df = plot

        if normalized:
            df = plot_df
        else:
            df = plot_df.copy()  # Make a copy to keep original data intact
            df = denormalize(df, self.normalization)

        # Create the scatter plot with marginal distributions
        g = sns.JointGrid(data=df, x=self.output_columns[0], y=self.output_columns[1])

        # Plot scatter
        g.plot(sns.scatterplot, sns.histplot)

        # Customize the plot
        g.set_axis_labels(self.output_columns[0], self.output_columns[1])
        g.fig.suptitle(
            f"Scatter Plot of training {self.output_columns[1]} vs {self.output_columns[0]} with Marginal Distributions"
        )

        # Adjust the plot layout
        plt.tight_layout()
        plt.show()
        return

    def train(
        self,
        n_epochs: int,
        batch_size: int = 32,
        sublosses_dict: dict = {"m": 1},
        clip: float = 10,
        verbose: bool = False,
    ):
        df_train = normalize_input_df(self.training_df, self.prior_bounds_dict)
        df_test = normalize_input_df(self.testing_df, self.prior_bounds_dict)
        dataset = TrajectoriesDataset(
            df_train, self.input_columns, self.output_columns, self.N_DIM
        )
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        self.inn, self.acc, self.loss = train_model_display(
            self.inn,
            self.optimizer,
            dataloader,
            n_epochs,
            self.N_DIM,
            self.N_OUT,
            df_test,
            self.filesave,
            sublosses_dict,
            clip,
            self.scheduler,
            verbose,
            batch_size,
            len(self.training_df),
        )

    def visualize_training_loss(self):
        """
        Visualizes training loss where each bar represents the total loss and is split into colors
        according to the different sub-losses.

        Parameters:
        - d (dict): A dictionary where the keys are loss names and the values are lists of loss values over epochs.
        """
        d = self.loss

        # Extract loss names and data
        loss_names = list(d.keys())
        loss_data = np.array([d[name] for name in loss_names])

        num_epochs = len(loss_data[0])

        # Set up the bar positions
        epoch_range = np.arange(num_epochs)

        # Plotting
        fig, ax = plt.subplots(figsize=(12, 8))

        # Create stacked bars for each epoch
        bottom_values = np.zeros(num_epochs)
        for i, loss_name in enumerate(loss_names):
            ax.bar(epoch_range, loss_data[i], bottom=bottom_values, label=loss_name)
            bottom_values += loss_data[i]

        # Add labels and title
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.set_title("Training Loss Visualization")
        ax.legend(loc="upper right")

        # Display the plot
        plt.tight_layout()
        plt.show()

    def reset_inn(
        self,
        type: Optional[str] = None,
        N_DIM: Optional[int] = None,
        N_NODES: Optional[int] = None,
        N_LAYERS: Optional[int] = None,
        lr: Optional[float] = None,
    ):
        if N_DIM is not None:
            self.N_DIM = N_DIM
        if N_NODES is not None:
            self.N_NODES = N_NODES
        if N_LAYERS is not None:
            self.N_LAYERS = N_LAYERS
        if type is not None:
            self.type = type
        if lr is not None:
            self.lr = lr
        self.inn, self.optimizer, self.scheduler, self.filesave = invertible_nn(
            self.type,
            self.N_DIM,
            self.N_NODES,
            self.N_LAYERS,
            s=["lr-exp", 0.985],
            lr=self.lr,
            inn_resource_dir=self.inn_resource_dir,
        )
        print("INN was reset")

    def plot_training_epochs(self):
        """
        Plots proportion of testing points with less than 5% error (against epoch).
        """
        epochs = range(len(self.acc[0]))
        plt.figure(figsize=(12, 6))

        for i in range(self.N_OUT):

            plt.subplot(1, self.N_OUT, i + 1)
            plt.plot(epochs, self.acc[i], marker="o", linestyle="-", color="b")
            plt.xlabel("Training Epoch")
            plt.ylabel(
                f"Proportion of {self.output_columns[i]} within 5% of the True Value"
            )
            plt.title(f"Training effect on {self.output_columns[i]}")

        plt.tight_layout()
        plt.show()
        return
