"""LP模式计算核心模块"""
import numpy as np
from scipy.optimize import brentq
from scipy.special import jv, kv


class LPMode:

    def __init__(self, l: int, m: int, wavelength: float, n_core: float,
                 n_clad: float, a: float, is_odd: bool = False):
        self.l = l
        self.m = m
        if self.m <= 0:
            raise ValueError("m must be greater than 0")
        self.wavelength = wavelength
        self.n_core = n_core
        self.n_clad = n_clad
        self.a = a
        self.is_odd = is_odd
        self._v: float | None = None

    def calculate_v(self) -> float:
        k0 = 2 * np.pi / self.wavelength
        self._v = k0 * self.a * np.sqrt(self.n_core**2 - self.n_clad**2)
        return self._v

    def find_roots(self, v: float, N: int = 300) -> list:
        eps = np.finfo(float).eps
        u_try = np.linspace(eps, v, N, endpoint=False)
        roots = []

        def char_eq(u: float, v: float) -> float:
            w = np.sqrt(v**2 - u**2)
            return (jv(self.l, u) / (u * jv(self.l + 1, u))
                    - kv(self.l, w) / (w * kv(self.l + 1, w)))

        for i in range(N - 1):
            try:
                f1 = char_eq(u_try[i], v)
                f2 = char_eq(u_try[i + 1], v)
                if f1 * f2 < 0:
                    root = brentq(char_eq, u_try[i], u_try[i + 1], args=(v,))
                    if abs(char_eq(root, v)) < 1e-6:
                        roots.append(root)
            except (ValueError, ZeroDivisionError):
                pass

        return roots

    def E_x(self, R: np.ndarray, phi: np.ndarray, U: float) -> np.ndarray:
        v = self._v if self._v is not None else self.calculate_v()
        W = np.sqrt(v**2 - U**2)
        angle = np.sin(self.l * phi) if self.is_odd else np.cos(self.l * phi)

        e_x = jv(self.l, U * R) / jv(self.l, U) * angle
        rows, cols = np.where(R > 1)
        e_x[rows, cols] = kv(self.l, W * R[rows, cols]) / kv(self.l, W) * angle[rows, cols]
        return e_x

    @staticmethod
    def generate_mesh(N: int, extent: float = 2.0):
        x = np.linspace(-extent, extent, N)
        y = np.linspace(-extent, extent, N)
        X, Y = np.meshgrid(x, y)
        R = np.sqrt(X**2 + Y**2)
        Phi = np.arctan2(Y, X)
        return X, Y, R, Phi
