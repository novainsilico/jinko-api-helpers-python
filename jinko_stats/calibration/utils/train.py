from jinko_stats.dependencies.dependency_checker import check_dependencies

check_dependencies(["torch"])

import torch
from tqdm import tqdm
from torch.nn import KLDivLoss
import torch.nn.functional as F
from enum import Enum


class Subloss(Enum):
    OUTPUT_MSE = "w"
    MSE = "m"
    INVERSE_MSE = "i"
    KULLBACK = "l"
    KOLMOGOROV = "k"
    MMD = "d"
    OUTPUT_MAE = "n"
    JACOBIAN = "j"
    UNIT = "u"
    QUANTILE = "q"
    INVERSE_UNIT = "r"
    ZERO = "z"


def interpolate_ecdf(grid, sorted_values, ecdf_values):
    """
    Custom function to interpolate ECDF values to a uniform grid.

    Args:
    - grid (torch.Tensor): The uniform grid to interpolate.
    - sorted_values (torch.Tensor): The sorted values for which ECDF is computed.
    - ecdf_values (torch.Tensor): The ECDF values corresponding to the sorted values.

    Returns:
    - interp_values (torch.Tensor): Interpolated ECDF values on the grid.
    """
    interp_values = torch.zeros_like(grid)
    n = sorted_values.size(0)

    # Interpolate within the range of the sorted values
    for i in range(n):
        if i == 0:
            interp_values[grid <= sorted_values[i]] = ecdf_values[i]
        else:
            mask = (grid > sorted_values[i - 1]) & (grid <= sorted_values[i])
            interp_values[mask] = ecdf_values[i - 1] + (
                ecdf_values[i] - ecdf_values[i - 1]
            ) * (grid[mask] - sorted_values[i - 1]) / (
                sorted_values[i] - sorted_values[i - 1]
            )

    # Handle values greater than the maximum sorted value
    interp_values[grid > sorted_values[-1]] = ecdf_values[-1]

    return interp_values


def ks_distance(y_hat, y):
    """
    Computes the sum of squared Kolmogorov-Smirnov distances between predicted and true values for each output dimension.

    Args:
    - y_hat (torch.Tensor): Predictions from the model of shape (batch_size, N_OUT).
    - y (torch.Tensor): True values of shape (batch_size, N_OUT).

    Returns:
    - ks_loss (torch.Tensor): The sum of squared Kolmogorov-Smirnov distances.
    """
    batch_size, n_out = y_hat.size()
    ks_losses = torch.zeros(n_out, device=y.device)

    for i in range(n_out):
        # Extract the i-th column for predictions and true values
        y_hat_i = y_hat[:, i]
        y_i = y[:, i]

        mini = min(min(y_hat_i), min(y_i))
        maxi = max(max(y_hat_i), max(y_i))

        # Sort both tensors
        y_hat_i_sorted, _ = torch.sort(y_hat_i)
        y_i_sorted, _ = torch.sort(y_i)

        # Compute ECDFs
        ecdf_y_hat_i = (
            torch.arange(1, batch_size + 1, dtype=torch.float32, device=y.device)
            / batch_size
        )
        ecdf_y_i = (
            torch.arange(1, batch_size + 1, dtype=torch.float32, device=y.device)
            / batch_size
        )

        # Interpolate ECDFs to create a uniform grid
        grid = torch.linspace(mini, maxi, steps=100, device=y.device)

        # Interpolating ECDFs
        ecdf_y_hat_i_interp = interpolate_ecdf(grid, y_hat_i_sorted, ecdf_y_hat_i)
        ecdf_y_i_interp = interpolate_ecdf(grid, y_i_sorted, ecdf_y_i)

        # Compute KS distance for the i-th dimension
        ks_dist_i = torch.max(torch.abs(ecdf_y_hat_i_interp - ecdf_y_i_interp))
        ks_losses[i] = ks_dist_i  # Squared KS distance

    # Return the sum of squared KS distances
    ks_loss = torch.sum(ks_losses)
    return ks_loss


def quantile_loss(predicted, target, quantile=0.5):
    """
    Compute the quantile loss between predicted and target values.

    Parameters:
    - predicted (torch.Tensor): Predicted values (e.g., the model output).
    - target (torch.Tensor): True target values.
    - quantile (float): The quantile to be estimated (between 0 and 1).

    Returns:
    - torch.Tensor: The quantile loss.
    """
    errors = target - predicted
    loss = torch.max(
        (quantile - (errors < 0).float()) * errors, (quantile - 1) * errors
    )
    return loss.mean()


def unit_loss(x):
    """
    Computes and normalizes a custom loss function.

    Parameters:
    x (torch.Tensor): Input tensor of shape (N,).

    Returns:
    torch.Tensor: The computed normalized loss.
    """

    # Ensure x is of float type for numerical stability
    x = x.float()

    # Create a mask for elements not in the range [0, 1]
    mask = (x < -1) | (x > 1)

    # Compute the term ln(abs(2*x - 1)) for masked elements
    loss_terms = torch.where(
        mask, torch.log(torch.abs(x)), torch.tensor(0.0, device=x.device)
    )

    # Sum over all elements
    loss = loss_terms.mean()

    return loss


def inverse_unit_loss(x):
    """
    Computes a loss that penalizes all values not in the range [0, 1].

    Parameters:
    x (torch.Tensor): Input tensor of shape (N,).

    Returns:
    torch.Tensor: The computed loss penalizing values not in the range [0, 1].
    """

    # Ensure x is of float type for numerical stability
    x = x.float()

    # Create a mask for elements outside the range [0, 1]
    mask = (x < 0) | (x > 1)

    # Compute the penalty for elements outside the range
    penalty = torch.where(
        mask, torch.log(torch.abs(x - 0.5) + 0.5), torch.tensor(0.0, device=x.device)
    )

    # Sum over all elements
    loss = penalty.mean()

    return loss


def accuracy(real, predicted):
    inbound = [
        (
            1
            if ((predicted[i] - real[i]) / predicted[i]) > -0.05
            and ((predicted[i] - real[i]) / predicted[i]) < 0.05
            else 0
        )
        for i in range(len(real))
    ]
    return sum(inbound) / len(inbound)


def MMD(x, y, device, kernel="multiscale"):
    """Emprical maximum mean discrepancy. The lower the result
       the more evidence that distributions are the same.

    Args:
        x: first sample, distribution P
        y: second sample, distribution Q
        kernel: kernel type such as "multiscale" or "rbf"
    """
    xx, yy, zz = torch.mm(x, x.t()), torch.mm(y, y.t()), torch.mm(x, y.t())
    rx = xx.diag().unsqueeze(0).expand_as(xx)
    ry = yy.diag().unsqueeze(0).expand_as(yy)

    dxx = rx.t() + rx - 2.0 * xx  # Used for A in (1)
    dyy = ry.t() + ry - 2.0 * yy  # Used for B in (1)
    dxy = rx.t() + ry - 2.0 * zz  # Used for C in (1)

    XX, YY, XY = (
        torch.zeros(xx.shape).to(device),
        torch.zeros(xx.shape).to(device),
        torch.zeros(xx.shape).to(device),
    )

    if kernel == "multiscale":

        bandwidth_range = [0.2, 0.5, 0.9, 1.3]
        for a in bandwidth_range:
            XX += a**2 * (a**2 + dxx) ** -1
            YY += a**2 * (a**2 + dyy) ** -1
            XY += a**2 * (a**2 + dxy) ** -1

    if kernel == "rbf":

        bandwidth_range = [10, 15, 20, 50]
        for a in bandwidth_range:
            XX += torch.exp(-0.5 * dxx / a)
            YY += torch.exp(-0.5 * dyy / a)
            XY += torch.exp(-0.5 * dxy / a)

    return torch.mean(XX + YY - 2.0 * XY)


def train_model_display(
    cinn,
    optimizer,
    dataloader,
    n_epochs,
    N_DIM,
    N_OUT,
    df_test,
    file_save=None,
    sublosses_dict={Subloss.OUTPUT_MSE: 1},
    clip=None,
    scheduler=None,
    verbose=False,
    batch_size=None,
    num_points=None,
):
    """
    Trains the given invertible neural network model and optionally saves it.

    Parameters:
    - cinn (Ff.SequenceINN or Ff.ReversibleGraphNet): The invertible neural network model to be trained. Ensure it has not already been trained before. Else, reset the weights.
    - optimizer (torch.optim.Optimizer): The optimizer to use for training the model (e.g., Adam).
    - dataloader (torch.utils.data.DataLoader): DataLoader providing the training data.
    - n_epochs (int): The number of epochs to train the model.
    - N_DIM (int): Number of input dimensions.
    - N_OUT (int): Number of output dimensions of interest. The model will also fit `N_DIM - N_OUT` Gaussian distributions.
    - df_test (pd.DataFrame): A DataFrame used for evaluating the model's performance on a test dataset.
    - file_save (str or None, optional): File path to save the trained model. If None, the model is not saved. Default is None.
    - sublosses_dict (dict, optional): Dictionary specifying additional partial losses to include in the loss function. The keys are:
      - `i`: Inverse loss
      - `w`: Weighted loss
      - `m`: Mean squared error (MSE) loss
      - `j`: Jacobian loss
      - `k`: Kullback-Leibler divergence (KL) loss
      - `n`: Negative log-likelihood or other custom loss
      - `q`: Quantile loss
      - `l`: Additional loss types
      The values are the corresponding weight factors for each loss. Default is `{Subloss.OUTPUT_MSE: 1}`.
      Corresponding enumeration from Sublosses can be used.
    - clip (float or None, optional): Gradient clipping value to prevent exploding gradients. If None, no gradient clipping is applied. Default is None.
    - scheduler (torch.optim.lr_scheduler._LRScheduler or None, optional): Learning rate scheduler to adjust the learning rate during training. If None, no scheduler is used. Default is None.
    - verbose (bool, optional): If True, prints detailed training progress. Default is False.
    - batch_size (int or None, optional): Batch size for training. If None, uses the batch size from the DataLoader. Default is None.
    - num_points (int or None, optional): Number of training points for correct INN naming.

    Returns:
    Ff.ReversibleGraphNet or Ff.SequenceINN
    """
    accuracy_list = [[] for _ in range(N_OUT)]
    losses = {loss: [] for loss in sublosses_dict.keys()}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    kl_loss = KLDivLoss(reduction="batchmean")

    for epoch in tqdm(range(n_epochs), desc="Training Model"):
        epoch_loss = 0
        num_batches = 0

        for batch in dataloader:
            optimizer.zero_grad()

            x_list = []
            y_list = []
            for i in range(N_DIM):
                x_list.append(batch[0][:, i])
                y_list.append(batch[0][:, N_DIM + i])
            x = torch.stack(tuple(x_list), dim=1)
            y = torch.stack(tuple(y_list), dim=1)

            y_hat, log_jac_det = cinn(x)

            loss_dict = {}

            if Subloss.JACOBIAN in sublosses_dict:
                loss_dict[Subloss.JACOBIAN] = (
                    -log_jac_det * sublosses_dict[Subloss.JACOBIAN]
                )
            if Subloss.OUTPUT_MSE in sublosses_dict:
                weights = torch.zeros(N_DIM)
                weights[:N_OUT] = torch.ones(N_OUT)
                squared_errors = (y_hat - y) ** 2
                weighted_squared_errors = squared_errors * weights
                loss_dict[Subloss.OUTPUT_MSE] = (
                    0.5
                    * torch.sum(weighted_squared_errors, dim=1)
                    * sublosses_dict[Subloss.OUTPUT_MSE]
                )
            if Subloss.MSE in sublosses_dict:
                loss_dict[Subloss.MSE] = (
                    0.5
                    * torch.sum((y_hat - y) ** 2, dim=1)
                    * sublosses_dict[Subloss.MSE]
                )
            if (
                Subloss.INVERSE_MSE in sublosses_dict
                or Subloss.INVERSE_UNIT in sublosses_dict
            ):
                x_hat, _ = cinn(y, rev=True)
            if Subloss.INVERSE_MSE in sublosses_dict:
                loss_dict[Subloss.INVERSE_MSE] = (
                    0.5
                    * torch.sum((x_hat - x) ** 2, dim=1)
                    * sublosses_dict[Subloss.INVERSE_MSE]
                )
            if Subloss.MMD in sublosses_dict:
                y_normal_hat = y_hat[:, N_OUT:]
                y_normal = y[:, N_OUT:]
                loss_dict[Subloss.MMD] = (
                    MMD(y_normal_hat, y_normal, device) * sublosses_dict[Subloss.MMD]
                )
            if Subloss.UNIT in sublosses_dict:
                y_normal_hat = y_hat[:, N_OUT:]
                loss_dict[Subloss.UNIT] = (
                    unit_loss(y_normal_hat) * sublosses_dict[Subloss.UNIT]
                )

            if Subloss.ZERO in sublosses_dict:
                y_normal_hat = y_hat[:, N_OUT:]
                loss_dict[Subloss.ZERO] = (
                    torch.sum((y_normal_hat) ** 2, dim=1) * sublosses_dict[Subloss.ZERO]
                )

            if Subloss.KOLMOGOROV in sublosses_dict:
                y_real = y[:, N_OUT:]
                loss_dict[Subloss.KOLMOGOROV] = (
                    ks_distance(y_hat[:, N_OUT:], y_real)
                    * sublosses_dict[Subloss.KOLMOGOROV]
                )
            if Subloss.OUTPUT_MAE in sublosses_dict:
                abs_errors = torch.abs(y_hat[:, :N_OUT] - y[:, :N_OUT])
                # Compute the maximum absolute error across the entire dataset
                loss_dict[Subloss.OUTPUT_MAE] = (
                    torch.max(abs_errors) * sublosses_dict[Subloss.OUTPUT_MAE]
                )

            if Subloss.QUANTILE in sublosses_dict:
                quantile = 0.8  # Adjust as needed for the specific quantile
                loss_dict[Subloss.QUANTILE] = (
                    quantile_loss(y_hat[:, :N_OUT], y[:, :N_OUT], quantile=quantile)
                    * sublosses_dict[Subloss.QUANTILE]
                )
            if Subloss.KULLBACK in sublosses_dict:
                # Compute KL divergence loss
                y_pred = F.log_softmax(y_hat[:, N_OUT:], dim=0)
                y_true = F.softmax(y[:, N_OUT:], dim=0)
                loss_dict[Subloss.KULLBACK] = (
                    kl_loss(y_pred, y_true) * sublosses_dict[Subloss.KULLBACK]
                )

            if Subloss.INVERSE_UNIT in sublosses_dict:
                loss_dict[Subloss.INVERSE_UNIT] = (
                    inverse_unit_loss(x_hat[N_OUT:])
                    * sublosses_dict[Subloss.INVERSE_UNIT]
                )

            # Aggregate losses
            total_loss = sum(loss_dict.values())
            total_loss = total_loss.mean()
            total_loss.backward()
            optimizer.step()
            if clip is not None:
                torch.nn.utils.clip_grad_norm_(cinn.parameters(), max_norm=clip)

            epoch_loss += total_loss.item()
            num_batches += 1

        if scheduler is not None:
            # Check if the scheduler is an instance of ReduceLROnPlateau
            if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                if total_loss is None:
                    raise ValueError(
                        "Loss must be provided for ReduceLROnPlateau scheduler."
                    )
                scheduler.step(total_loss)
            else:
                scheduler.step()

        cinn.eval()  # Set the model to evaluation mode

        if not df_test is None:
            x_list = []
            y_real_list = []
            for i in range(N_DIM):
                x_list.append(
                    torch.tensor(df_test.iloc[:, i].values, dtype=torch.float32)
                )
            for i in range(N_OUT):
                y_real_list.append(
                    torch.tensor(df_test.iloc[:, N_DIM + i].values, dtype=torch.float32)
                )

            x = torch.stack(x_list, dim=1)
            y_real = torch.stack(y_real_list, dim=1)

            with torch.no_grad():
                y_hat, _ = cinn(x)

            for i in range(N_OUT):
                real = y_real[:, i].numpy()
                predicted = y_hat[:, i].numpy()
                acc = accuracy(real, predicted)
                accuracy_list[i].append(acc)

        if verbose:
            verbose_loss_info = []
            if Subloss.OUTPUT_MSE in sublosses_dict:
                verbose_loss_info.append(
                    f"Weighted Loss: {loss_dict[Subloss.OUTPUT_MSE].mean().item():.4f}"
                )
            if Subloss.MSE in sublosses_dict:
                verbose_loss_info.append(
                    f"MSE Loss: {loss_dict[Subloss.MSE].mean().item():.4f}"
                )
            if Subloss.INVERSE_MSE in sublosses_dict:
                verbose_loss_info.append(
                    f"Inverse Loss: {loss_dict[Subloss.INVERSE_MSE].mean().item():.4f}"
                )
            if Subloss.JACOBIAN in sublosses_dict:
                verbose_loss_info.append(
                    f"Jacobian Loss: {loss_dict[Subloss.JACOBIAN].mean().item():.4f}"
                )
            if Subloss.ZERO in sublosses_dict:
                verbose_loss_info.append(
                    f"Zero Loss: {loss_dict[Subloss.ZERO].mean().item():.4f}"
                )
            if Subloss.MMD in sublosses_dict:
                verbose_loss_info.append(
                    f"MMD Loss: {loss_dict[Subloss.MMD].mean().item():.4f}"
                )
            if Subloss.UNIT in sublosses_dict:
                verbose_loss_info.append(
                    f"Uniform/unit Loss: {loss_dict[Subloss.UNIT].mean().item():.4f}"
                )
            if Subloss.KOLMOGOROV in sublosses_dict:
                verbose_loss_info.append(
                    f"KS Loss: {loss_dict[Subloss.KOLMOGOROV].mean().item():.4f}"
                )
            if Subloss.MAE in sublosses_dict:
                verbose_loss_info.append(
                    f"MAE Loss: {loss_dict[Subloss.MAE].mean().item():.4f}"
                )
            if Subloss.QUANTILE in sublosses_dict:
                verbose_loss_info.append(
                    f"Quantile Loss: {loss_dict[Subloss.QUANTILE].mean().item():.4f}"
                )
            if Subloss.KULLBACK in sublosses_dict:
                verbose_loss_info.append(
                    f"KL Divergence Loss: {loss_dict[Subloss.KULLBACK].mean().item():.4f}"
                )
            if Subloss.INVERSE_UNIT in sublosses_dict:
                verbose_loss_info.append(
                    f"Inverse Unit Loss: {loss_dict[Subloss.INVERSE_UNIT].mean().item():.4f}"
                )

            tqdm.write(
                f"Epoch {epoch + 1}/{n_epochs} - Loss: {epoch_loss/num_batches:.4f}, "
                + ", ".join(verbose_loss_info)
            )

        # Append loss values to the dictionary
        for key in losses.keys():
            if key in sublosses_dict:
                losses[key].append(loss_dict[key].mean().item())

    if file_save:
        print("file save", file_save)
        file_save += f"-{n_epochs}epochs-{str(clip)}clip-{sublosses_dict}-{batch_size}batch-{num_points}points.pth"
        torch.save(cinn.state_dict(), file_save)

    return cinn, accuracy_list, losses
