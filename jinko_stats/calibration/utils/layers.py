from jinko_stats.dependencies.dependency_checker import check_dependencies

check_dependencies(["torch"])

from math import exp
import torch
import torch.nn as nn
import torch.nn.functional as F
import warnings


class F_conv(nn.Module):
    """ResNet transformation, not itself reversible, just used below"""

    def __init__(
        self,
        in_channels,
        channels,
        channels_hidden=None,
        stride=None,
        kernel_size=3,
        leaky_slope=0.1,
        batch_norm=False,
    ):
        super(F_conv, self).__init__()

        if stride:
            warnings.warn(
                "Stride doesn't do anything, the argument should be " "removed",
                DeprecationWarning,
            )
        if not channels_hidden:
            channels_hidden = channels

        pad = kernel_size // 2
        self.leaky_slope = leaky_slope
        self.conv1 = nn.Conv2d(
            in_channels,
            channels_hidden,
            kernel_size=kernel_size,
            padding=pad,
            bias=not batch_norm,
        )
        self.conv2 = nn.Conv2d(
            channels_hidden,
            channels_hidden,
            kernel_size=kernel_size,
            padding=pad,
            bias=not batch_norm,
        )
        self.conv3 = nn.Conv2d(
            channels_hidden,
            channels,
            kernel_size=kernel_size,
            padding=pad,
            bias=not batch_norm,
        )

        if batch_norm:
            self.bn1 = nn.BatchNorm2d(channels_hidden)
            self.bn1.weight.data.fill_(1)
            self.bn2 = nn.BatchNorm2d(channels_hidden)
            self.bn2.weight.data.fill_(1)
            self.bn3 = nn.BatchNorm2d(channels)
            self.bn3.weight.data.fill_(1)
        self.batch_norm = batch_norm

    def forward(self, x):
        out = self.conv1(x)
        if self.batch_norm:
            out = self.bn1(out)
        out = F.leaky_relu(out, self.leaky_slope)

        out = self.conv2(out)
        if self.batch_norm:
            out = self.bn2(out)
        out = F.leaky_relu(out, self.leaky_slope)

        out = self.conv3(out)
        if self.batch_norm:
            out = self.bn3(out)

        return out


class F_fully_connected(nn.Module):
    """Fully connected tranformation, not reversible, but used below."""

    def __init__(
        self, size_in, size, internal_size=None, dropout=0.0, batch_norm=False
    ):
        super(F_fully_connected, self).__init__()
        if not internal_size:
            internal_size = 2 * size

        self.d1 = nn.Dropout(p=dropout)
        self.d2 = nn.Dropout(p=dropout)
        self.d2b = nn.Dropout(p=dropout)

        self.fc1 = nn.Linear(size_in, internal_size)
        self.fc2 = nn.Linear(internal_size, internal_size)
        self.fc2b = nn.Linear(internal_size, internal_size)
        self.fc3 = nn.Linear(internal_size, size)

        self.nl1 = nn.ReLU()
        self.nl2 = nn.ReLU()
        self.nl2b = nn.ReLU()

        if batch_norm:
            self.bn1 = nn.BatchNorm1d(internal_size)
            self.bn1.weight.data.fill_(1)
            self.bn2 = nn.BatchNorm1d(internal_size)
            self.bn2.weight.data.fill_(1)
            self.bn2b = nn.BatchNorm1d(internal_size)
            self.bn2b.weight.data.fill_(1)
        self.batch_norm = batch_norm

    def forward(self, x):
        out = self.fc1(x)
        if self.batch_norm:
            out = self.bn1(out)
        out = self.nl1(self.d1(out))

        out = self.fc2(out)
        if self.batch_norm:
            out = self.bn2(out)
        out = self.nl2(self.d2(out))

        out = self.fc2b(out)
        if self.batch_norm:
            out = self.bn2b(out)
        out = self.nl2b(self.d2b(out))

        out = self.fc3(out)
        return out


class rev_layer(nn.Module):
    """General reversible layer modeled after the lifting scheme. Uses some
    non-reversible transformation F, but splits the channels up to make it
    revesible (see lifting scheme). F itself does not have to be revesible. See
    F_* classes above for examples."""

    def __init__(self, dims_in, F_class=F_conv, F_args={}):
        super(rev_layer, self).__init__()
        channels = dims_in[0][0]
        self.split_len1 = channels // 2
        self.split_len2 = channels - channels // 2

        self.F = F_class(self.split_len2, self.split_len1, **F_args)
        self.G = F_class(self.split_len1, self.split_len2, **F_args)

    def forward(self, x, rev=False):
        x1, x2 = (
            x[0].narrow(1, 0, self.split_len1),
            x[0].narrow(1, self.split_len1, self.split_len2),
        )

        if not rev:
            y1 = x1 + self.F(x2)
            y2 = x2 + self.G(y1)
        else:
            y2 = x2 - self.G(x1)
            y1 = x1 - self.F(y2)

        return [torch.cat((y1, y2), 1)]

    def jacobian(self, x, rev=False):
        return torch.zeros(x.shape[0])

    def output_dims(self, input_dims):
        assert len(input_dims) == 1, "Can only use 1 input"
        return input_dims


class rev_multiplicative_layer(nn.Module):
    """The RevNet block is not a general function approximator. The reversible
    layer with a multiplicative term presented in the real-NVP paper is much
    more general. This class uses some non-reversible transformation F, but
    splits the channels up to make it revesible (see lifting scheme). F itself
    does not have to be revesible. See F_* classes above for examples."""

    def __init__(self, dims_in, F_class=F_fully_connected, F_args={}, clamp=5.0):
        super(rev_multiplicative_layer, self).__init__()
        channels = dims_in[0][0]

        self.split_len1 = channels // 2
        self.split_len2 = channels - channels // 2
        self.ndims = len(dims_in[0])

        self.clamp = clamp
        self.max_s = exp(clamp)
        self.min_s = exp(-clamp)

        self.s1 = F_class(self.split_len1, self.split_len2, **F_args)
        self.t1 = F_class(self.split_len1, self.split_len2, **F_args)
        self.s2 = F_class(self.split_len2, self.split_len1, **F_args)
        self.t2 = F_class(self.split_len2, self.split_len1, **F_args)

    def e(self, s):
        return torch.exp(self.clamp * 0.636 * torch.atan(s))

    def log_e(self, s):
        """log of the nonlinear function e"""
        return self.clamp * 0.636 * torch.atan(s)

    def forward(self, x, rev=False, jac=None):
        x1, x2 = (
            x[0].narrow(1, 0, self.split_len1),
            x[0].narrow(1, self.split_len1, self.split_len2),
        )

        if not rev:
            y1 = self.e(self.s2(x2)) * x1 + self.t2(x2)
            y2 = self.e(self.s1(y1)) * x2 + self.t1(y1)
        else:  # names of x and y are swapped!
            y2 = (x2 - self.t1(x1)) / self.e(self.s1(x1))
            y1 = (x1 - self.t2(y2)) / self.e(self.s2(y2))
        return [torch.cat((y1, y2), 1)], jac

    def jacobian(self, x, rev=False):
        x1, x2 = (
            x[0].narrow(1, 0, self.split_len1),
            x[0].narrow(1, self.split_len1, self.split_len2),
        )

        if not rev:
            s2 = self.s2(x2)
            y1 = self.e(s2) * x1 + self.t2(x2)
            jac = self.log_e(self.s1(y1)) + self.log_e(s2)
        else:
            s1 = self.s1(x1)
            y2 = (x2 - self.t1(x1)) / self.e(s1)
            jac = -self.log_e(s1) - self.log_e(self.s2(y2))

        return torch.sum(jac, dim=tuple(range(1, self.ndims + 1)))

    def output_dims(self, input_dims):
        assert len(input_dims) == 1, "Can only use 1 input"
        return input_dims


class glow_coupling_layer(nn.Module):
    def __init__(self, dims_in, F_class=F_fully_connected, F_args={}, clamp=5.0):
        super(glow_coupling_layer, self).__init__()
        channels = dims_in[0][0]
        self.ndims = len(dims_in[0])

        self.split_len1 = channels // 2
        self.split_len2 = channels - channels // 2

        self.clamp = clamp
        self.max_s = exp(clamp)
        self.min_s = exp(-clamp)

        self.s1 = F_class(self.split_len1, self.split_len2 * 2, **F_args)
        self.s2 = F_class(self.split_len2, self.split_len1 * 2, **F_args)

    def e(self, s):
        return torch.exp(self.clamp * 0.636 * torch.atan(s / self.clamp))

    def log_e(self, s):
        return self.clamp * 0.636 * torch.atan(s / self.clamp)

    def forward(self, x, rev=False, jac=None):
        x1, x2 = (
            x[0].narrow(1, 0, self.split_len1),
            x[0].narrow(1, self.split_len1, self.split_len2),
        )

        if not rev:
            r2 = self.s2(x2)
            s2, t2 = r2[:, : self.split_len1], r2[:, self.split_len1 :]
            y1 = self.e(s2) * x1 + t2

            r1 = self.s1(y1)
            s1, t1 = r1[:, : self.split_len2], r1[:, self.split_len2 :]
            y2 = self.e(s1) * x2 + t1

        else:  # names of x and y are swapped!
            r1 = self.s1(x1)
            s1, t1 = r1[:, : self.split_len2], r1[:, self.split_len2 :]
            y2 = (x2 - t1) / self.e(s1)

            r2 = self.s2(y2)
            s2, t2 = r2[:, : self.split_len1], r2[:, self.split_len1 :]
            y1 = (x1 - t2) / self.e(s2)

        return ([torch.cat((y1, y2), 1)], jac)

    def jacobian(self, x, rev=False):
        x1, x2 = (
            x[0].narrow(1, 0, self.split_len1),
            x[0].narrow(1, self.split_len1, self.split_len2),
        )

        if not rev:
            r2 = self.s2(x2)
            s2, t2 = r2[:, : self.split_len1], r2[:, self.split_len1 :]
            y1 = self.e(s2) * x1 + t2

            r1 = self.s1(y1)
            s1, t1 = r1[:, : self.split_len2], r1[:, self.split_len2 :]

        else:  # names of x and y are swapped!
            r1 = self.s1(x1)
            s1, t1 = r1[:, : self.split_len2], r1[:, self.split_len2 :]
            y2 = (x2 - t1) / self.e(s1)

            r2 = self.s2(y2)
            s2, t2 = r2[:, : self.split_len1], r2[:, self.split_len1 :]

        jac = torch.sum(self.log_e(s1), dim=1) + torch.sum(self.log_e(s2), dim=1)
        for i in range(self.ndims - 1):
            jac = torch.sum(jac, dim=1)

        return jac

    def output_dims(self, input_dims):
        assert len(input_dims) == 1, "Can only use 1 input"
        return input_dims
