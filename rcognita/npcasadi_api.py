import numpy as np
import casadi as csd
import rcognita.utilities as utilities


class SymbolicHandler:
    def __init__(self, is_symbolic=False):
        self.is_symbolic = is_symbolic

    def cos(self, x):
        return csd.cos(x) if self.is_symbolic else np.cos(x)

    def sin(self, x):
        return csd.sin(x) if self.is_symbolic else np.sin(x)

    def hstack(self, tup):
        return csd.horzcat(tup) if self.is_symbolic else np.hstack(tup)

    def push_vec(self, matrix, vec):
        return self.vstack([matrix[1:, :], vec.T])

    def vstack(self, tup):
        if not isinstance(tup, tuple):
            tup = tuple(tup)
        return csd.vertcat(*tup) if self.is_symbolic else np.vstack(tup)

    def reshape_casadi_as_np(self, array, dim_params):
        result = csd.SX(*dim_params)
        n_rows = dim_params[0]
        n_cols = dim_params[1]
        for i in range(n_rows):
            result[i, :] = array[i * n_cols : (i + 1) * n_cols]

        return result

    def reshape(self, array, dim_params):
        if self.is_symbolic:
            if isinstance(dim_params, list):
                if len(dim_params) > 1:
                    return self.reshape_casadi_as_np(array, dim_params)
                else:
                    return csd.reshape(array, dim_params[0], 1)
            elif isinstance(dim_params, int):
                return csd.reshape(array, dim_params, 1)
            else:
                raise TypeError(
                    "Wrong type of dimension parameter was passed.\
                         Possible cases are: int, [int], [int, int, ...]"
                )
        else:
            return np.reshape(array, dim_params)

    def array(self, array, ignore=False, array_type="DM"):
        if self.is_symbolic and not ignore:
            if array_type == "DM":
                return csd.DM(array)
            elif array_type == "SX":
                return csd.SX(array)
            else:
                ValueError(f"Invalid array type:{array_type}")

        else:
            return np.array(array)

    def symbolic_array_creation(self, *args):
        return tuple(self.array(arg) for arg in args)

    def ones(self, tup):
        if isinstance(tup, int):
            return csd.DM.ones(tup) if self.is_symbolic else np.ones(tup)
        else:
            return csd.DM.ones(*tup) if self.is_symbolic else np.ones(tup)

    def zeros(self, tup, array_type="DM"):
        if isinstance(tup, int):
            if self.is_symbolic:
                if array_type == "DM":
                    return csd.DM.zeros(tup)
                elif array_type == "SX":
                    return csd.SX.zeros(tup)
                else:
                    ValueError(f"Invalid array type:{array_type}")
            else:
                return np.zeros(tup)
        else:
            if self.is_symbolic:
                if array_type == "DM":
                    return csd.DM.zeros(*tup)
                elif array_type == "SX":
                    return csd.SX.zeros(*tup)
                else:
                    ValueError(f"Invalid array type:{array_type}")
            else:
                return np.zeros(tup)

    def concatenate(self, tup):
        if len(tup) > 1:
            if self.is_symbolic:
                all_symbolic = all(
                    [type(x) == csd.DM or type(x) == csd.SX for x in tup]
                )
                if not all_symbolic:
                    raise TypeError(
                        f"""
                        Cannot perform symbolic array concatenation due to presence of numerical data. Check type-casting in your algorithm.
                        Types are: {[type(x) for x in tup]}
                        """
                    )
                else:
                    return csd.vertcat(*tup)
            else:
                return np.concatenate(tup)

    def rep_mat(self, array, n, m):
        return (
            csd.repmat(array, n, m)
            if self.is_symbolic
            else utilities.rep_mat(array, n, m)
        )

    def matmul(self, A, B):
        return csd.mtimes(A, B) if self.is_symbolic else np.matmul(A, B)

    def inner_product(self, A, B):
        return csd.dot(A, B) if self.is_symbolic else np.inner(A, B)

    def rc_array(self, A):
        return csd.DM.sym(A) if self.is_symbolic else np.array(A)

    def sign(self, x):
        return csd.sign(x) if self.is_symbolic else np.sign(x)

    def abs(self, x):
        return csd.fabs(x) if self.is_symbolic else np.abs(x)

    def min(self, array):
        return csd.fmin(*array) if self.is_symbolic else np.min(array)

    def max(self, array):
        return csd.fmax(array) if self.is_symbolic else np.max(array)

    def dot(self, A, B):
        return csd.dot(A, B) if self.is_symbolic else A @ B

    def shape(self, array):
        return array.size() if self.is_symbolic else np.shape(array)

    def create_cost_function(self, cost_function, *args, x0=None):
        if not self.is_symbolic:
            return (
                lambda my_action_sqn: cost_function(
                    my_action_sqn, *args, self.is_symbolic
                ),
                csd.SX.sym("x", *self.shape(x0)),
            )
        else:
            action_sqn_symb = csd.SX.sym("x", self.shape(x0))
            args = self.symbolic_array_creation(*args)
            return (
                cost_function(action_sqn_symb, *args, self.is_symbolic),
                action_sqn_symb,
            )

    def kron(self, A, B):
        return csd.kron(A, B) if self.is_symbolic else np.kron(A, B)

