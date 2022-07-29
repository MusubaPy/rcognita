#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains auxiliary functions.

Remarks: 

- All vectors are treated as of type [n,]
- All buffers are treated as of type [L, n] where each row is a vector
- Buffers are updated from bottom to top

"""

import numpy as np
import os, sys

PARENT_DIR = os.path.abspath(__file__ + "/../../")
sys.path.insert(0, PARENT_DIR)
CUR_DIR = os.path.abspath(__file__ + "/..")
sys.path.insert(0, CUR_DIR)
from numpy.random import rand
from numpy.matlib import repmat
import scipy.stats as st
from scipy import signal
import matplotlib.pyplot as plt
from npcasadi_api import typeInferenceDecorator
import casadi


class SymbolicHandler(metaclass=typeInferenceDecorator):
    def is_any_CasADi(self, *args):
        return any([isinstance(arg, (casadi.SX, casadi.DM, casadi.MX)) for arg in args])

    def is_any_symbolic(self, *args):
        return any([isinstance(arg, (casadi.SX, casadi.MX)) for arg in args])

    def cos(cls, x, is_symbolic=False, force=None):
        return casadi.cos(x) if is_symbolic else np.cos(x)

    def sin(self, x, is_symbolic=False, force=None):
        return casadi.sin(x) if is_symbolic else np.sin(x)

    def hstack(self, tup, is_symbolic=False, force=None):
        if not isinstance(tup, tuple):
            tup = tuple(tup)
        return casadi.horzcat(*tup) if is_symbolic else np.hstack(tup)

    def push_vec(self, matrix, vec, is_symbolic=False, force=None):
        return self.vstack([matrix[1:, :], vec.T])

    def vstack(self, tup, is_symbolic=False, force=None):
        if not isinstance(tup, tuple):
            tup = tuple(tup)
        return casadi.vertcat(*tup) if is_symbolic else np.vstack(tup)

    def reshape_CasADi_as_np(self, array, dim_params, is_symbolic=False, force=None):
        result = casadi.SX(*dim_params)
        n_rows = dim_params[0]
        n_cols = dim_params[1]
        for i in range(n_rows):
            result[i, :] = array[i * n_cols : (i + 1) * n_cols]

        return result

    def reshape(self, array, dim_params, is_symbolic=False, force=None):
        if is_symbolic:
            if isinstance(dim_params, list) or isinstance(dim_params, tuple):
                if len(dim_params) > 1:
                    return self.reshape_CasADi_as_np(array, dim_params)
                else:
                    return casadi.reshape(array, dim_params[0], 1)
            elif isinstance(dim_params, int):
                return casadi.reshape(array, dim_params, 1)
            else:
                raise TypeError(
                    "Wrong type of dimension parameter was passed.\
                         Possible cases are: int, [int], [int, int, ...]"
                )
        else:
            return np.reshape(array, dim_params)

    def array(
        self, array, ignore=False, array_type="DM", is_symbolic=False, force=None
    ):
        if is_symbolic and not ignore:
            if array_type == "DM":
                return casadi.DM(array)
            elif array_type == "SX":
                return casadi.SX(array)
            else:
                ValueError(f"Invalid array type:{array_type}")

        else:
            return np.array(array)

    def symbolic_array_creation(
        self, *args, array_type="DM", is_symbolic=False, force=None
    ):
        return tuple(self.array(arg, array_type=array_type) for arg in args)

    def ones(self, tup, is_symbolic=False):
        if isinstance(tup, int):
            return casadi.DM.ones(tup) if is_symbolic else np.ones(tup)
        else:
            return casadi.DM.ones(*tup) if is_symbolic else np.ones(tup)

    def zeros(self, tup, array_type="DM", is_symbolic=False):
        if isinstance(tup, int):
            if is_symbolic:
                if array_type == "DM":
                    return casadi.DM.zeros(tup)
                elif array_type == "SX":
                    return casadi.SX.zeros(tup)
                else:
                    ValueError(f"Invalid array type:{array_type}")
            else:
                return np.zeros(tup)
        else:
            if is_symbolic:
                if array_type == "DM":
                    return casadi.DM.zeros(*tup)
                elif array_type == "SX":
                    return casadi.SX.zeros(*tup)
                else:
                    ValueError(f"Invalid array type:{array_type}")
            else:
                return np.zeros(tup)

    def concatenate(self, tup, is_symbolic=False, force=None):
        if len(tup) > 1:
            if is_symbolic:
                all_symbolic = all(
                    [type(x) == casadi.DM or type(x) == casadi.SX for x in tup]
                )
                if not all_symbolic:
                    raise TypeError(
                        f"""
                        Cannot perform symbolic array concatenation due to presence of numerical data. Check type-casting in your algorithm.
                        Types are: {[type(x) for x in tup]}
                        """
                    )
                else:
                    return casadi.vertcat(*tup)
            else:
                return np.concatenate(tup)

    def rep_mat(self, array, n, m, is_symbolic=False, force=None):
        return casadi.repmat(array, n, m) if is_symbolic else rep_mat(array, n, m)

    def matmul(self, A, B, is_symbolic=False, force=None):
        return casadi.mtimes(A, B) if is_symbolic else np.matmul(A, B)

    def inner_product(self, A, B, is_symbolic=False, force=None):
        return casadi.dot(A, B) if is_symbolic else np.inner(A, B)

    def rc_array(self, A, is_symbolic=False, force=None):
        return casadi.DM.sym(A) if is_symbolic else np.array(A)

    def sign(self, x, is_symbolic=False, force=None):
        return casadi.sign(x) if is_symbolic else np.sign(x)

    def abs(self, x, is_symbolic=False, force=None):
        return casadi.fabs(x) if is_symbolic else np.abs(x)

    def min(self, array, is_symbolic=False, force=None):
        return casadi.fmin(*array) if is_symbolic else np.min(array)

    def max(self, array, is_symbolic=False, force=None):
        return casadi.fmax(array) if is_symbolic else np.max(array)

    def to_col(self, argin, is_symbolic=False, force=None):
        if is_symbolic:
            if self.shape(argin)[0] < self.shape(argin)[1]:
                return argin.T
            else:
                return argin
        else:
            return to_col_vec(argin)

    def dot(self, A, B, is_symbolic=False, force=None):
        return (
            casadi.dot(*self.symbolic_array_creation(A, B, array_type="SX"))
            if is_symbolic
            else A @ B
        )

    def shape(self, array, is_symbolic=False, force=None):
        return (
            array.size()
            if isinstance(array, (casadi.SX, casadi.DM, casadi.MX))
            else np.shape(array)
        )

    def function2SX(self, func, *args, x0=None, is_symbolic=False, force=None):
        if not is_symbolic:
            return (
                lambda x: func(x, *args),
                casadi.SX.sym("x", *self.shape(x0)),
            )
        else:
            try:
                x_symb = casadi.SX.sym("x", self.shape(x0))
            except NotImplementedError as e:
                x_symb = casadi.SX.sym("x", *self.shape(x0), 1)
            args = self.symbolic_array_creation(*args)
            if len(args) > 0:
                return func(x_symb, *args), x_symb
            else:
                return func(x_symb), x_symb

    def kron(self, A, B, is_symbolic=False, force=None):
        return casadi.kron(A, B) if is_symbolic else np.kron(A, B)

    @staticmethod
    def autograd(func, x, *args, is_symbolic=False, force=None):
        return casadi.Function("f", [x, *args], [casadi.gradient(func(x, *args), x)])

    def array_symb(self, tup, literal="x", is_symbolic=False, force=None):
        if isinstance(tup, tuple):
            if len(tup) > 2:
                raise ValueError(
                    f"Not implemented for number of dimensions grreater than 2. Passed: {len(tup)}"
                )
            else:
                return casadi.SX.sym(literal, *tup)

        elif isinstance(tup, int):
            return casadi.SX.sym(literal, tup)

        else:
            raise TypeError(
                f"Passed an invalide argument of type {type(tup)}. Takes either int or tuple data types"
            )

    def norm_1(self, v, is_symbolic=False, force=None):
        return casadi.norm_1(v) if is_symbolic else np.linalg.norm(v, 1)

    def norm_2(self, v, is_symbolic=False, force=None):
        return casadi.norm_2(v) if is_symbolic else np.linalg.norm(v, 2)


nc = SymbolicHandler()


def rej_sampling_rvs(dim, pdf, M):
    """
    Random variable (pseudo)-realizations via rejection sampling.
    
    Parameters
    ----------
    dim : : integer
        dimension of the random variable
    pdf : : function
        desired probability density function
    M : : number greater than 1
        it must hold that :math:`\\text{pdf}_{\\text{desired}} \le M \\text{pdf}_{\\text{proposal}}`.
        This function uses a normal pdf with zero mean and identity covariance matrix as a proposal distribution.
        The smaller `M` is, the fewer iterations to produce a sample are expected.

    Returns
    -------
    A single realization (in general, as a vector) of the random variable with the desired probability density.

    """

    # Use normal pdf with zero mean and identity covariance matrix as a proposal distribution
    normal_RV = st.multivariate_normal(cov=np.eye(dim))

    # Bound the number of iterations to avoid too long loops
    max_iters = 1e3

    curr_iter = 0

    while curr_iter <= max_iters:
        proposal_sample = normal_RV.rvs()

        unif_sample = rand()

        if unif_sample < pdf(proposal_sample) / M / normal_RV.pdf(proposal_sample):
            return proposal_sample


def to_col_vec(argin):
    """
    Convert input to a column vector.

    """
    if argin.ndim < 2:
        return np.reshape(argin, (argin.size, 1))
    elif argin.ndim == 2:
        if argin.shape[0] < argin.shape[1]:
            return argin.T
        else:
            return argin


def rep_mat(argin, n, m):
    """
    Ensures 1D result.
    
    """
    return np.squeeze(repmat(argin, n, m))


def push_vec(matrix, vec):
    return nc.vstack([matrix[1:, :], vec.T])


def uptria2vec(mat):
    """
    Convert upper triangular square sub-matrix to column vector.
    
    """
    n = mat.shape[0]

    vec = np.zeros((int(n * (n + 1) / 2)))

    k = 0
    for i in range(n):
        for j in range(i, n):
            vec[k] = mat[i, j]
            k += 1

    return vec


class ZOH:
    """
    Zero-order hold.
    
    """

    def __init__(self, init_time=0, init_val=0, sample_time=1):
        self.time_step = init_time
        self.sample_time = sample_time
        self.currVal = init_val

    def hold(self, signal_val, t):
        timeInSample = t - self.time_step
        if timeInSample >= self.sample_time:  # New sample
            self.time_step = t
            self.currVal = signal_val

        return self.currVal


class DFilter:
    """
    Real-time digital filter.
    
    """

    def __init__(
        self,
        filter_num,
        filter_den,
        buffer_size=16,
        init_time=0,
        init_val=0,
        sample_time=1,
    ):
        self.Num = filter_num
        self.Den = filter_den
        self.zi = rep_mat(signal.lfilter_zi(filter_num, filter_den), 1, init_val.size)

        self.time_step = init_time
        self.sample_time = sample_time
        self.buffer = rep_mat(init_val, 1, buffer_size)

    def filt(self, signal_val, t=None):
        # Sample only if time is specified
        if t is not None:
            timeInSample = t - self.time_step
            if timeInSample >= self.sample_time:  # New sample
                self.time_step = t
                self.buffer = push_vec(self.buffer, signal_val)
        else:
            self.buffer = push_vec(self.buffer, signal_val)

        bufferFiltered = np.zeros(self.buffer.shape)

        for k in range(0, signal_val.size):
            bufferFiltered[k, :], self.zi[k] = signal.lfilter(
                self.Num, self.Den, self.buffer[k, :], zi=self.zi[k, :]
            )
        return bufferFiltered[-1, :]


def dss_sim(A, B, C, D, uSqn, x0, y0):
    """
    Simulate output response of a discrete-time state-space model.
    """
    if uSqn.ndim == 1:
        return y0, x0
    else:
        ySqn = np.zeros([uSqn.shape[0], C.shape[0]])
        xSqn = np.zeros([uSqn.shape[0], A.shape[0]])
        x = x0
        ySqn[0, :] = y0
        xSqn[0, :] = x0
        for k in range(1, uSqn.shape[0]):
            x = A @ x + B @ uSqn[k - 1, :]
            xSqn[k, :] = x
            ySqn[k, :] = C @ x + D @ uSqn[k - 1, :]

        return ySqn, xSqn


def upd_line(line, newX, newY):
    line.set_xdata(np.append(line.get_xdata(), newX))
    line.set_ydata(np.append(line.get_ydata(), newY))


def reset_line(line):
    line.set_data([], [])


def upd_scatter(scatter, newX, newY):
    scatter.set_offsets(np.vstack([scatter.get_offsets().data, np.c_[newX, newY]]))


def upd_text(textHandle, newText):
    textHandle.set_text(newText)


def on_key_press(event, anm):
    """
    Key press event handler for a ``FuncAnimation`` animation object.

    """
    if event.key == " ":
        if anm.running:
            anm.event_source.stop()

        else:
            anm.event_source.start()
        anm.running ^= True
    elif event.key == "q":
        plt.close("all")
        raise Exception("exit")
