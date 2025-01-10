from jinko_stats.dependencies.dependency_checker import check_dependencies

check_dependencies(["FrEIA", "torch"])

import jinko_stats.calibration.utils.layers as l
import FrEIA.framework as Ff
import FrEIA.modules as Fm
import torch
from torch import nn
from torch.optim.lr_scheduler import ExponentialLR


## NEURAL NETWORK DEFINITION


def invertible_nn(
    type,
    N_DIM,
    N_NODES=512,
    N_LAYERS=4,
    s=[None, None],
    init=None,
    dropout=None,
    lr=0.001,
    inn_resource_dir=None,
):
    """
    Constructs an invertible neural network (NN) model with customizable parameters.

    Parameters:
    - type (str): The type of invertible neural network to create, "linear_batchnorm", "linear_batchnorm_leaky", "linear_basic", "graph_simple", graph_revnet".
    - N_DIM (int): The dimensionality of the input features for the neural network.
    - N_NODES (int, optional): The number of nodes (units) in each hidden layer of the subnetworks. Default is 512.
    - N_LAYERS (int, optional): The number of layers in the neural network. Default is 4.
    - s (list of str, int or None, optional): Specifies the scheduler. Defaults to [None, None], best performances with ["lr-exp", 0.985].
    - init (str, optional): The initialization method for the network weights. Can be "Xav", "He" or None. Default is None.
    - dropout (float or None, optional): The dropout rate to apply between layers. If None, dropout is not applied. Default is None.
    - lr (float, optional): The learning rate for training the model. Default is 0.001.

    Returns:
    - model: An instance of the invertible neural network model with the specified configuration. Ff.SequenceINN or Ff.ReversibleGraphNet

    Notes:
    - Proper initialization and dropout settings can improve model performance and training stability.
    - The learning rate (`lr`) affects the optimization process and should be adjusted according to the specific training needs.
    """

    # MODEL
    if type == "linear_batchnorm":
        inn = create_nn_batchnorm(N_DIM=N_DIM, N_NODES=N_NODES, N_LAYERS=N_LAYERS)
    elif type == "linear_basic":
        inn = create_nn(N_DIM=N_DIM, N_NODES=N_NODES, N_LAYERS=N_LAYERS)
    elif type == "graph_simple":
        inn = create_nn_graph(N_DIM=N_DIM, N_NODES=N_NODES, N_LAYERS=N_LAYERS)
    elif type == "graph_revnet":
        inn = create_nn_graph_expnodes(N_DIM=N_DIM, N_NODES=N_NODES, N_LAYERS=N_LAYERS)
    elif type == "linear_batchnorm_leaky":
        inn = create_nn_batchnorm_leaky(
            N_DIM=N_DIM, N_NODES=N_NODES, N_LAYERS=N_LAYERS, dropout=dropout
        )
    else:
        return None

    # OPTIMIZER
    if "graph" in type:
        params_trainable = list(filter(lambda p: p.requires_grad, inn.parameters()))
        optimizer = torch.optim.Adam(params_trainable, lr=lr)
    else:
        optimizer = torch.optim.Adam(inn.parameters(), lr=lr)

    # SCHEDULER
    if s[0] == "exp-lr":
        scheduler = ExponentialLR(
            optimizer, gamma=s[1]
        )  # Decays learning rate by a factor of 0.9 every epoch
        sched_name = s[0] + str(s[1])
    else:
        scheduler = None
        sched_name = "no_sched"

    if init == "He":
        inn.apply(he_init_weights)
        init_name = init
    elif init == "Xav":
        inn.apply(xavier_init_weights)
        init_name = init
    else:
        init_name = "no_init"

    # NAME

    f_nn = f"{inn_resource_dir}/inn-{sched_name}-{init_name}-{N_LAYERS}layers-{N_NODES}nodes"

    return inn, optimizer, scheduler, f_nn


def he_init_weights(m):
    """INITIALIZE WEIGHTS WITH HE : DOES NOT WORK WELL"""
    if isinstance(m, nn.Linear):
        # Initialize weights with He initialization
        nn.init.kaiming_normal_(m.weight, nonlinearity="relu")
        if m.bias is not None:
            nn.init.constant_(m.bias, 0)


def xavier_init_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.xavier_uniform_(m.weight)
        if m.bias is not None:
            nn.init.zeros_(m.bias)


def create_nn(N_DIM, N_NODES=512, N_LAYERS=40):
    """
    Create an invertible neural network (INN) model using FrEIA framework.

    Parameters:
    N_DIM (int): Number of input dimensions.
    N_NODES (int, optional): Number of nodes in each hidden layer of the subnet. Default is 512.
    N_LAYERS (int, optional): Number of layers in the invertible neural network. Default is 40.

    Returns:
    Ff.SequenceINN
    """

    def subnet_fc(dims_in, dims_out):
        return nn.Sequential(
            nn.Linear(dims_in, N_NODES), nn.ReLU(), nn.Linear(N_NODES, dims_out)
        )

    # Create a SequenceINN model with N_DIM input dimensions
    cinn = Ff.SequenceINN(N_DIM)

    # Append N_LAYERS AllInOneBlock layers to the INN model
    for _ in range(N_LAYERS):
        cinn.append(Fm.AllInOneBlock, subnet_constructor=subnet_fc)

    return cinn


def create_nn_batchnorm(N_DIM, N_NODES=512, N_LAYERS=40):
    """
    DIFFERENT RETURN : cinn, optimizer, scheduler. Create an invertible neural network (INN) model using FrEIA framework with batch normalization.

    Parameters:
    N_DIM (int): Number of input dimensions.
    N_NODES (int, optional): Number of nodes in each hidden layer of the subnet. Default is 512.
    N_LAYERS (int, optional): Number of layers in the invertible neural network. Default is 40.

    Returns:
    Ff.SequenceINN
    """

    def subnet_fc(dims_in, dims_out):
        return nn.Sequential(
            nn.Linear(dims_in, N_NODES),
            nn.BatchNorm1d(
                N_NODES
            ),  # Add batch normalization after the first linear layer
            nn.ReLU(),
            nn.Linear(N_NODES, dims_out),
            nn.BatchNorm1d(
                dims_out
            ),  # Add batch normalization after the second linear layer
        )

    # Create a SequenceINN model with N_DIM input dimensions
    cinn = Ff.SequenceINN(N_DIM)

    # Append N_LAYERS AllInOneBlock layers to the INN model
    for k in range(N_LAYERS):
        cinn.append(Fm.AllInOneBlock, subnet_constructor=subnet_fc)

    return cinn


# Define the invertible model using the FrEIA library
def create_nn_graph(N_DIM, N_NODES=512, N_LAYERS=40):
    """
    Creates an invertible neural network model using the FrEIA library.

    Parameters:
    N_DIM (int): Number of input dimensions.
    N_NODES (int): Number of nodes per hidden layer.
    N_LAYERS (int): Number of layers in the model.

    Returns:
    Ff.ReversibleGraphNet: Created invertible neural network model.
    torch.optim.Adam: Optimizer for training the model.
    """

    def subnet_fc(dims_in, dims_out):
        return nn.Sequential(
            nn.Linear(dims_in, N_NODES), nn.ReLU(), nn.Linear(N_NODES, dims_out)
        )

    nodes = [Ff.InputNode(N_DIM, name="input")]

    for i in range(N_LAYERS):
        nodes.append(
            Ff.Node(
                nodes[-1],
                Fm.AllInOneBlock,
                {"subnet_constructor": subnet_fc},
                name=f"block_{i}",
            )
        )

    nodes.append(Ff.OutputNode(nodes[-1], name="output"))

    model = Ff.ReversibleGraphNet(nodes, verbose=False)

    return model


def create_nn_graph_expnodes(N_DIM, N_NODES=512, N_LAYERS=40):
    """
    Creates an invertible neural network model using the FrEIA library.

    Parameters:
    N_DIM (int): Number of input dimensions.
    N_NODES (int): Number of nodes per hidden layer.
    N_LAYERS (int): Number of layers in the model.

    Returns:
    Ff.ReversibleGraphNet: Created invertible neural network model.
    torch.optim.Adam: Optimizer for training the model.
    """
    exponent_clamping = 4.0

    nodes = [Ff.InputNode(N_DIM, name="input")]

    for i in range(N_LAYERS):
        nodes.append(
            Ff.Node(
                [nodes[-1].out0],
                l.rev_multiplicative_layer,
                {
                    "F_class": l.F_fully_connected,
                    "F_args": {"internal_size": N_NODES},
                    "clamp": exponent_clamping,
                },
                name="coupling_{}".format(i),
            )
        )

    nodes.append(Ff.OutputNode(nodes[-1], name="output"))

    model = Ff.ReversibleGraphNet(nodes, verbose=False)

    return model


def create_nn_batchnorm_leaky(N_DIM, N_NODES=512, N_LAYERS=40, dropout=None):
    """
    Create an invertible neural network (INN) model using the FrEIA framework with batch normalization,
    element-wise learned scaling, and optional dropout.

    Parameters:
    N_DIM (int): Number of input dimensions.
    N_NODES (int, optional): Number of nodes in each hidden layer of the subnet. Default is 512.
    N_LAYERS (int, optional): Number of layers in the invertible neural network. Default is 40.
    dropout (float or None): Dropout probability. If None, dropout is not used. Default is None.

    Returns:
    Ff.SequenceINN: The invertible neural network model.
    """

    def subnet_fc(dims_in, dims_out):
        layers = [nn.Linear(dims_in, N_NODES), nn.BatchNorm1d(N_NODES), nn.LeakyReLU()]

        if dropout is not None:
            layers.append(nn.Dropout(p=dropout))

        layers.extend([nn.Linear(N_NODES, dims_out), nn.BatchNorm1d(dims_out)])

        return nn.Sequential(*layers)

    # Create a SequenceINN model with N_DIM input dimensions
    cinn = Ff.SequenceINN(N_DIM)

    # Add the LearnedElementwiseScaling layer as the first layer
    cinn.append(Fm.LearnedElementwiseScaling)

    # Append N_LAYERS AllInOneBlock layers to the INN model
    for k in range(N_LAYERS):
        cinn.append(Fm.AllInOneBlock, subnet_constructor=subnet_fc)

    return cinn
