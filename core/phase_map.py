"""Phase map generation for optical fiber modes and vortex beams."""
import numpy as np


def lp_phase(R: np.ndarray, Phi: np.ndarray, U: float, V: float,
             l: int, is_odd: bool) -> np.ndarray:
    """Calculate LP mode phase from field components.

    Args:
        R: Radial coordinate grid
        Phi: Azimuthal coordinate grid
        U: Normalized frequency parameter (core)
        V: Fiber V-number
        l: Azimuthal order
        is_odd: Parity flag (True for odd, False for even)

    Returns:
        Phase array in radians
    """
    from scipy.special import jv, kv
    W = np.sqrt(max(V**2 - U**2, 0.0))
    angle = np.sin(l * Phi) if is_odd else np.cos(l * Phi)
    e_x = jv(l, U * R) / jv(l, U) * angle
    rows, cols = np.where(R > 1)
    if W > 0 and abs(kv(l, W)) > 1e-12:
        e_x[rows, cols] = kv(l, W * R[rows, cols]) / kv(l, W) * angle[rows, cols]
    else:
        e_x[rows, cols] = 0.0
    return np.angle(e_x)


def vortex_phase(size: str, l: int, phase_angle: float = 0.0) -> np.ndarray:
    """Generate optical vortex phase distribution.

    Args:
        size: "square" for 1024×1024, "wide" for 1920×1080
        l: Topological charge (winding number)
        phase_angle: Additional phase rotation in degrees

    Returns:
        Phase array in radians (0 to 2π)
    """
    if size == "square":
        H, V = 1024, 1024
    else:
        H, V = 1920, 1080

    x = np.linspace(-1, 1, H)
    y = np.linspace(-1, 1, V)
    X, Y = np.meshgrid(x, y)
    angle_rad = np.deg2rad(phase_angle)
    return l * np.arctan2(Y, X) + angle_rad


def blazed_grating(shape: tuple, fx: float, fy: float = 0.0) -> np.ndarray:
    """Generate blazed grating phase for beam steering.

    Args:
        shape: (height, width) tuple
        fx: Grating order in x direction
        fy: Grating order in y direction

    Returns:
        Grating phase array in radians
    """
    h, w = shape
    x = np.linspace(0, 1, w)
    y = np.linspace(0, 1, h)
    X, Y = np.meshgrid(x, y)
    return 2 * np.pi * (fx * X + fy * Y)


def lp_phase_distribution(size: str, l: int, n_x: int = 100, n_y: int = 0,
                          phase_angle: float = 0.0) -> np.ndarray:
    """Generate LP mode phase distribution with optional grating modulation.

    Args:
        size: "square" for 1024×1024, "wide" for 1920×1080
        l: Topological charge
        n_x: Grating order in x direction
        n_y: Grating order in y direction
        phase_angle: Phase rotation in degrees

    Returns:
        Phase distribution array (0 to 2π)
    """
    if size == "square":
        H, V = 1024, 1024
    else:
        H, V = 1920, 1080

    xs = np.linspace(-H/2, H/2, H)
    ys = np.linspace(-V/2, V/2, V)
    Xs, Ys = np.meshgrid(xs, ys)
    Phis = np.arctan2(Ys, Xs)

    gx = n_x / H
    gy = n_y / V
    angle_rad = np.deg2rad(phase_angle)

    #映射到[-pi,pi]
    phase_dis = np.mod(
        np.angle(np.cos(l * Phis + np.pi/2 + angle_rad)) + np.pi * 2 * (gx * Xs + gy * Ys),
        2 * np.pi
    )-np.pi
    return phase_dis
