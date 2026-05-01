"""图像处理和可视化模块 - 纯 Pillow 实现"""
import numpy as np
from PIL import Image, ImageDraw


class ColorMap:
    @staticmethod
    def apply(data: np.ndarray, colormap: str = "jet") -> np.ndarray:
        d = np.clip(data, 0, 1)
        h, w = d.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)
        if colormap == "jet":
            cpts = np.array([
                [0.000, 0.0, 0.0, 0.5],
                [0.125, 0.0, 0.0, 1.0],
                [0.375, 0.0, 1.0, 1.0],
                [0.625, 1.0, 1.0, 0.0],
                [0.875, 1.0, 0.0, 0.0],
                [1.000, 0.5, 0.0, 0.0],
            ])
            rgb[..., 0] = (np.interp(d, cpts[:, 0], cpts[:, 1]) * 255).astype(np.uint8)
            rgb[..., 1] = (np.interp(d, cpts[:, 0], cpts[:, 2]) * 255).astype(np.uint8)
            rgb[..., 2] = (np.interp(d, cpts[:, 0], cpts[:, 3]) * 255).astype(np.uint8)
        else:
            v = (d * 255).astype(np.uint8)
            rgb[..., 0] = v
            rgb[..., 1] = v
            rgb[..., 2] = v
        return rgb


class ImageRenderer:

    @staticmethod
    def _normalize(data: np.ndarray) -> np.ndarray:
        lo, hi = np.min(data), np.max(data)
        if hi > lo:
            return (data - lo) / (hi - lo)
        return np.zeros_like(data)

    @staticmethod
    def array_to_image(data: np.ndarray, colormap: str = "jet", size: tuple = (400, 400)) -> Image.Image:
        norm = ImageRenderer._normalize(data)
        img = Image.fromarray(ColorMap.apply(norm, colormap), mode='RGB')
        return img.resize(size, Image.Resampling.BILINEAR)

    @staticmethod
    def _draw_arrow(draw: ImageDraw.ImageDraw,
                    cx: float, cy: float,
                    ex: float, ey: float,
                    length: float = 14,
                    head: float = 5,
                    width: int = 2,
                    color: tuple = (255, 255, 255, 220)):
        mag = np.sqrt(ex**2 + ey**2)
        if mag < 1e-6:
            return
        ux, uy = ex / mag, ey / mag
        tail_x = cx - ux * length / 2
        tail_y = cy - uy * length / 2
        tip_x  = cx + ux * length / 2
        tip_y  = cy + uy * length / 2
        shaft_x = tip_x - ux * head
        shaft_y = tip_y - uy * head
        draw.line([(tail_x, tail_y), (shaft_x, shaft_y)], fill=color, width=width)
        perp_x, perp_y = -uy, ux
        half_w = head * 0.5
        draw.polygon([
            (tip_x, tip_y),
            (shaft_x + perp_x * half_w, shaft_y + perp_y * half_w),
            (shaft_x - perp_x * half_w, shaft_y - perp_y * half_w),
        ], fill=color)

    @staticmethod
    def draw_polarization(intensity: np.ndarray,
                          Ex: np.ndarray,
                          Ey,
                          colormap: str = "jet",
                          size: tuple = (400, 400)) -> Image.Image:
        """LP 偏振态：x-pol 水平箭头，y-pol 垂直箭头，2× 超采样"""
        scale = 2
        sw, sh = size[0] * scale, size[1] * scale
        img = ImageRenderer.array_to_image(intensity, colormap, (sw, sh))
        h, w = intensity.shape
        norm = ImageRenderer._normalize(intensity)
        draw = ImageDraw.Draw(img, 'RGBA')

        arrow_n = 30
        step_y = max(1, h // arrow_n)
        step_x = max(1, w // arrow_n)

        for iy in range(step_y // 2, h, step_y):
            for ix in range(step_x // 2, w, step_x):
                if norm[iy, ix] <= 0.15:
                    continue
                cx = (ix + 0.5) / w * sw
                cy = (iy + 0.5) / h * sh
                if Ey is not None:
                    ImageRenderer._draw_arrow(draw, cx, cy, 0, -Ey[iy, ix],
                                              length=16, head=7, width=3)
                else:
                    ImageRenderer._draw_arrow(draw, cx, cy, Ex[iy, ix], 0,
                                              length=16, head=7, width=3)
        return img.resize(size, Image.Resampling.LANCZOS)

    @staticmethod
    def draw_vector_mode(intensity: np.ndarray,
                         modes: list,
                         titles: list,
                         X_arrow: np.ndarray,
                         Y_arrow: np.ndarray,
                         colormap: str = "jet",
                         size: tuple = (900, 240),
                         extent: float = 2.0,
                         show_pol: bool = False,
                         gap_color: tuple = (30, 30, 30)) -> Image.Image:
        """矢量模式 1×4 横排拼图，2× 超采样"""
        scale = 2
        n = len(modes)
        cell_w = size[0] // n
        cell_h = size[1]
        scw, sch = cell_w * scale, cell_h * scale

        font = None
        for font_path in [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            try:
                from PIL import ImageFont
                font = ImageFont.truetype(font_path, 26)
                break
            except Exception:
                continue

        gap = 4  # pixels between cells
        canvas_w = cell_w * n + gap * (n - 1)
        canvas = Image.new('RGB', (canvas_w, cell_h), color=gap_color)

        def phys_to_px(x: float, y: float) -> tuple:
            px = (x + extent) / (2 * extent) * scw
            py = (extent - y) / (2 * extent) * sch
            return px, py

        for idx, ((Ex, Ey), title) in enumerate(zip(modes, titles)):
            cell_img = ImageRenderer.array_to_image(intensity[::-1], colormap, size=(scw, sch))
            draw = ImageDraw.Draw(cell_img, 'RGBA')

            if show_pol:
                for i in range(len(X_arrow)):
                    cx, cy = phys_to_px(X_arrow[i], Y_arrow[i])
                    ImageRenderer._draw_arrow(draw, cx, cy, Ex[i], -Ey[i],
                                              length=18, head=7, width=3,
                                              color=(255, 255, 255, 220))

            draw2 = ImageDraw.Draw(cell_img)
            if font:
                draw2.text((12, 10), title, fill=(255, 255, 255), font=font)
            else:
                draw2.text((12, 10), title, fill=(255, 255, 255))

            cell_img = cell_img.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            canvas.paste(cell_img, (idx * (cell_w + gap), 0))

        return canvas

    @staticmethod
    def phase_to_image(phase: np.ndarray, colormap: str = "phase_gray", size: tuple = (400, 400)) -> Image.Image:
        h, w = phase.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        if colormap == "gray":
            wrapped = (phase + np.pi) / (2 * np.pi)
            wrapped = np.mod(wrapped, 1.0)
            v = (wrapped * 255).astype(np.uint8)
            rgb[..., 0] = v
            rgb[..., 1] = v
            rgb[..., 2] = v
        else:  # phase_gray: linear mapping 0-2π to 0-255
            v = (phase / (2 * np.pi) * 255).astype(np.uint8)
            rgb[..., 0] = v
            rgb[..., 1] = v
            rgb[..., 2] = v

        img = Image.fromarray(rgb, mode='RGB')
        return img.resize(size, Image.Resampling.BILINEAR)
