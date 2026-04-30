"""矢量模式分解核心算法"""
import numpy as np
from scipy.special import jv, kv
from numpy.typing import NDArray


def cal_F(R: NDArray[np.float64], l: int, U: float, V: float) -> NDArray[np.float64]:
    """计算径向场分布 F(r)"""
    W = np.sqrt(V**2 - U**2)
    F_r = jv(l, U * R) / jv(l, U)
    rows, cols = np.where(R >= 1)
    F_r[rows, cols] = kv(l, W * R[rows, cols]) / kv(l, W)
    return F_r


def cal_intensity(R: NDArray[np.float64], l: int, U: float, V: float) -> NDArray[np.float64]:
    """计算模式强度 |F(r)|^2"""
    return np.abs(cal_F(R, l, U, V)) ** 2


def get_vector_modes(l: int, m: int, U: float, V: float,
                     arrow_n: int = 23,
                     intensity_n: int = 200,
                     extent: float = 2.0,
                     mask_threshold: float = 0.15):
    """
    按参考算法：低分辨率网格计算箭头，mask = |F| > threshold，
    高分辨率网格计算强度背景。
    """
    # 低分辨率网格用于箭头（与参考代码一致）
    x0 = np.linspace(-extent, extent, arrow_n)
    y0 = np.linspace(-extent, extent, arrow_n)
    X0, Y0 = np.meshgrid(x0, y0)
    R0 = np.sqrt(X0**2 + Y0**2)
    Phi0 = np.arctan2(Y0, X0)

    # 高分辨率网格用于强度背景
    x1 = np.linspace(-extent, extent, intensity_n)
    y1 = np.linspace(-extent, extent, intensity_n)
    X1, Y1 = np.meshgrid(x1, y1)
    R1 = np.sqrt(X1**2 + Y1**2)

    F = cal_F(R0, l, U, V)
    intensity = cal_intensity(R1, l, U, V)

    F_max = np.max(np.abs(F))
    mask = np.abs(F) > (0.9 * F_max if F_max > 0 else 1.0)

    E1 = F[mask] * np.cos(l * Phi0[mask])
    E2 = F[mask] * np.sin(l * Phi0[mask])

    if l == 1:
        modes = [(E1, -E2), (E1, E2), (E2, E1), (E2, -E1)]
        titles = [f"HE{l+1}{m} even", f"TM0{m}", f"HE{l+1}{m} odd", f"TE0{m}"]
    elif l > 1:
        modes = [(E1, -E2), (E1, E2), (E2, E1), (E2, -E1)]
        titles = [f"HE{l+1}{m} even", f"EH{l-1}{m} even", f"HE{l+1}{m} odd", f"EH{l-1}{m} odd"]
    else:
        modes = [(E1, -E2), (E1, E2), (E2, E1), (E2, -E1)]
        titles = ["Mode 1", "Mode 2", "Mode 3", "Mode 4"]

    return {
        "intensity": intensity,
        "modes": modes,
        "titles": titles,
        "X_arrow": X0[mask],
        "Y_arrow": Y0[mask],
        "extent": extent,
    }


def format_decomposition(l: int, m: int) -> list[str]:
    """生成 LP→矢量模式叠加公式文本，E1/E2 展开为具体表达式"""
    c = f"F(r)cos({l}φ)"
    s = f"F(r)sin({l}φ)"
    lines = [
        f"── Vector Mode Decomposition ──",
        f"F(r) = J{l}(Ur)/J{l}(U)  [r≤1]",
        f"     = K{l}(Wr)/K{l}(W)  [r>1]",
        f"",
    ]
    if l == 1:
        w = max(len(f"HE{l+1}{m} even"), len(f"TM0{m}"), len(f"HE{l+1}{m} odd"), len(f"TE0{m}"),
                len(f"LP{l}{m} even"), len(f"LP{l}{m} odd"))
        lines += [
            f"{'HE'+str(l+1)+str(m)+' even':<{w}} = {c}·ex - {s}·ey",
            f"{'TM0'+str(m):<{w}} = {c}·ex + {s}·ey",
            f"{'HE'+str(l+1)+str(m)+' odd':<{w}} = {s}·ex + {c}·ey",
            f"{'TE0'+str(m):<{w}} = {s}·ex - {c}·ey",
            f"",
            f"{'LP'+str(l)+str(m)+' even':<{w}} = HE{l+1}{m}(even) + TM0{m}",
            f"{'LP'+str(l)+str(m)+' odd':<{w}} = HE{l+1}{m}(odd)  + TE0{m}",
        ]
    elif l > 1:
        w = max(len(f"HE{l+1}{m} even"), len(f"EH{l-1}{m} even"), len(f"HE{l+1}{m} odd"), len(f"EH{l-1}{m} odd"),
                len(f"LP{l}{m} even"), len(f"LP{l}{m} odd"))
        lines += [
            f"{'HE'+str(l+1)+str(m)+' even':<{w}} = {c}·ex - {s}·ey",
            f"{'EH'+str(l-1)+str(m)+' even':<{w}} = {c}·ex + {s}·ey",
            f"{'HE'+str(l+1)+str(m)+' odd':<{w}} = {s}·ex + {c}·ey",
            f"{'EH'+str(l-1)+str(m)+' odd':<{w}} = {s}·ex - {c}·ey",
            f"",
            f"{'LP'+str(l)+str(m)+' even':<{w}} = HE{l+1}{m}(even) + EH{l-1}{m}(even)",
            f"{'LP'+str(l)+str(m)+' odd':<{w}} = HE{l+1}{m}(odd)  + EH{l-1}{m}(odd)",
        ]
    return lines
