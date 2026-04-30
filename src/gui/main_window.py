"""Tkinter GUI 主窗口"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
import threading
from src.core.lpmode import LPMode
from src.core.renderer import ImageRenderer
from src.core.vector_mode import get_vector_modes, format_decomposition
from src.core.phase_map import vortex_phase, blazed_grating, lp_phase_distribution


class FiberModeApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Fiber Mode Visualization")
        self.root.geometry("1400x800")
        self.root.resizable(True, True)

        self._setup_style()

        self.params = {
            "l": 0,
            "m": 1,
            "wavelength": 638e-9,
            "n_core": 1.4633,
            "n_clad": 1.4569,
            "a": 4.5e-6,
            "is_odd": False,
            "mesh_size": 300,
        }

        self.mode: LPMode | None = None
        self.current_pil_image: Image.Image | None = None
        self.current_phase_image: Image.Image | None = None
        self.is_computing = False
        self._last_R: np.ndarray | None = None
        self._last_Phi: np.ndarray | None = None
        self._last_U: float | None = None
        self._create_widgets()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        bg = "#f0f0f0"
        fg = "#333333"
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg, foreground=fg)
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'), background=bg)
        style.configure('Section.TLabel', font=('Arial', 11, 'bold'), background=bg)
        style.configure('TEntry', fieldbackground='white', foreground=fg, insertcolor=fg)
        style.configure('TButton', font=('Arial', 10))
        style.map('TButton', background=[])
        style.configure('TLabelframe', background=bg)
        style.configure('TLabelframe.Label', background=bg, foreground=fg)
        self._bg = bg

    def _create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        intensity_tab = ttk.Frame(self.notebook)
        self.notebook.add(intensity_tab, text="Intensity")
        self._create_intensity_tab(intensity_tab)

        phase_tab = ttk.Frame(self.notebook)
        self.notebook.add(phase_tab, text="Phase Map")
        self._create_phase_tab(phase_tab)

    # ── Tab 1: Intensity ──────────────────────────────────────────────────────

    def _create_intensity_tab(self, parent):
        left_frame = ttk.Frame(parent, width=350)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=15, pady=15)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Fiber Mode Visualization", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 15))

        self.entries = {}
        self._create_param_group(left_frame, "Mode Parameters", [
            ("l (azimuthal)", "l"),
            ("m (radial)", "m"),
        ])
        self._create_param_group(left_frame, "Fiber Properties", [
            ("wavelength (nm)", "wavelength_nm"),
            ("n_core", "n_core"),
            ("n_clad", "n_clad"),
            ("a (μm)", "a_um"),
        ])
        self._create_param_group(left_frame, "Computation", [
            ("mesh size", "mesh_size"),
        ])

        options_frame = ttk.LabelFrame(left_frame, text="Display Options", padding=(8, 6))
        options_frame.pack(fill=tk.X, pady=6)

        cmap_row = ttk.Frame(options_frame)
        cmap_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(cmap_row, text="Colormap:", width=10).pack(side=tk.LEFT)
        self.colormap_var = tk.StringVar(value="jet")
        for val in ["jet", "gray"]:
            tk.Radiobutton(cmap_row, text=val, variable=self.colormap_var, value=val,
                           bg=self._bg, fg="#333333", relief=tk.FLAT, bd=0).pack(side=tk.LEFT, padx=(6, 0))

        mode_row = ttk.Frame(options_frame)
        mode_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(mode_row, text="Mode:", width=10).pack(side=tk.LEFT)
        self.overlay_var = tk.StringVar(value="lp")
        self.overlay_var.trace_add("write", self._on_overlay_change)
        for val, label in [("lp", "LP"), ("vector", "Vector (1×4)")]:
            tk.Radiobutton(mode_row, text=label, variable=self.overlay_var, value=val,
                           bg=self._bg, fg="#333333", relief=tk.FLAT, bd=0).pack(side=tk.LEFT, padx=(6, 0))

        parity_row = ttk.Frame(options_frame)
        parity_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(parity_row, text="Parity:", width=10).pack(side=tk.LEFT)
        self.parity_var = tk.StringVar(value="even")
        self._parity_btns = []
        for val in ["even", "odd"]:
            btn = tk.Radiobutton(parity_row, text=val, variable=self.parity_var, value=val,
                                 bg=self._bg, fg="#333333", relief=tk.FLAT, bd=0)
            btn.pack(side=tk.LEFT, padx=(6, 0))
            self._parity_btns.append(btn)

        pol_dir_row = ttk.Frame(options_frame)
        pol_dir_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(pol_dir_row, text="Pol dir:", width=10).pack(side=tk.LEFT)
        self.pol_dir_var = tk.StringVar(value="x")
        self._pol_dir_btns = []
        for val in ["x", "y"]:
            btn = tk.Radiobutton(pol_dir_row, text=f"{val}-pol", variable=self.pol_dir_var, value=val,
                                 bg=self._bg, fg="#333333", relief=tk.FLAT, bd=0)
            btn.pack(side=tk.LEFT, padx=(6, 0))
            self._pol_dir_btns.append(btn)

        pol_row = ttk.Frame(options_frame)
        pol_row.pack(fill=tk.X)
        self.show_pol_var = tk.BooleanVar(value=False)
        tk.Checkbutton(pol_row, text="Polarization Arrows",
                       variable=self.show_pol_var,
                       bg=self._bg, fg="#333333", relief=tk.FLAT, bd=0).pack(anchor=tk.W)

        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Generate", command=self._on_calculate).pack(fill=tk.X, pady=3)
        ttk.Button(button_frame, text="Export Image", command=self._on_export).pack(fill=tk.X, pady=3)

        self.status_label = ttk.Label(left_frame, text="Ready", foreground="green",
                                      font=('Arial', 10, 'bold'), anchor=tk.CENTER)
        self.status_label.pack(fill=tk.X, pady=10)

        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=15, pady=15)

        paned = tk.PanedWindow(right_frame, orient=tk.VERTICAL, sashwidth=5, bg="#e0e0e0")
        paned.pack(fill=tk.BOTH, expand=True)

        image_frame = ttk.LabelFrame(paned, text="Field Intensity Distribution", padding=10)
        paned.add(image_frame, height=400)

        self.image_label = tk.Label(image_frame, background="#e0e0e0", relief=tk.SUNKEN,
                                    width=60, height=15)
        self.image_label.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.LabelFrame(paned, text="Calculation Results", padding=10)
        paned.add(info_frame, height=300)

        self.info_text = tk.Text(info_frame, height=8, width=60, font=('Courier', 9),
                                 relief=tk.FLAT, bd=0, state=tk.DISABLED,
                                 bg="white", fg="#333333",
                                 highlightthickness=1, highlightbackground="#cccccc",
                                 highlightcolor="#cccccc",
                                 selectbackground="#0078d4", selectforeground="white")
        self.info_text.pack(fill=tk.BOTH, expand=True)

    # ── Tab 2: Phase Map ──────────────────────────────────────────────────────

    def _create_phase_tab(self, parent):
        left_frame = ttk.Frame(parent, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=15, pady=15)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Phase Map Generator", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 15))

        # Phase type selection
        type_frame = ttk.Frame(left_frame)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="Phase Type", style='Section.TLabel').pack(anchor=tk.W, pady=(0, 4))
        self.phase_type_var = tk.StringVar(value="lp")
        self.phase_type_var.trace_add("write", self._on_phase_type_change)
        radio_frame = ttk.Frame(type_frame)
        radio_frame.pack(anchor=tk.W, padx=(4, 0))
        for val, label in [("lp", "LP Mode"), ("vortex", "Vortex Mode")]:
            tk.Radiobutton(radio_frame, text=label, variable=self.phase_type_var, value=val,
                           bg=self._bg, fg="#000000", relief=tk.FLAT, bd=0).pack(side=tk.LEFT, padx=(6, 0))

        phase_params_frame = ttk.Frame(left_frame)
        phase_params_frame.pack(fill=tk.X, pady=5)
        ttk.Label(phase_params_frame, text="Parameters", style='Section.TLabel').pack(anchor=tk.W, pady=(0, 4))

        self.phase_entries = {}

        def add_param(label_text, key, default):
            row = ttk.Frame(phase_params_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label_text, width=20).pack(side=tk.LEFT)
            e = ttk.Entry(row, width=15)
            e.insert(0, default)
            e.pack(side=tk.LEFT, padx=(5, 0))
            self.phase_entries[key] = e

        add_param("Topological:", "vortex_l", "1")
        add_param("Phase rotation (°):", "phase_angle", "0")
        add_param("Grating order (fx):", "fx", "0")
        add_param("Grating order (fy):", "fy", "0")

        size_row = ttk.Frame(phase_params_frame)
        size_row.pack(fill=tk.X, pady=4)
        ttk.Label(size_row, text="Size (LP mode):", width=20).pack(side=tk.LEFT)
        self.lp_size_var = tk.StringVar(value="square")
        self._lp_size_btns = []
        for val, label in [("square", "1024×1024"), ("wide", "1920×1080")]:
            btn = tk.Radiobutton(size_row, text=label, variable=self.lp_size_var, value=val,
                           bg=self._bg, fg="#000000", relief=tk.FLAT, bd=0)
            btn.pack(side=tk.LEFT, padx=(6, 0))
            self._lp_size_btns.append(btn)

        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Generate", command=self._on_generate_phase).pack(fill=tk.X, pady=3)
        ttk.Button(button_frame, text="Export Image", command=self._on_export_phase).pack(fill=tk.X, pady=3)

        self.phase_status_label = ttk.Label(left_frame, text="Ready", foreground="green",
                                            font=('Arial', 10, 'bold'), anchor=tk.CENTER)
        self.phase_status_label.pack(fill=tk.X, pady=10)

        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=15, pady=15)

        paned = tk.PanedWindow(right_frame, orient=tk.VERTICAL, sashwidth=5, bg="#e0e0e0")
        paned.pack(fill=tk.BOTH, expand=True)

        image_frame = ttk.LabelFrame(paned, text="Phase Distribution", padding=10)
        paned.add(image_frame, height=400)

        self.phase_image_label = tk.Label(image_frame, background="#e0e0e0", relief=tk.SUNKEN,
                                          width=60, height=15)
        self.phase_image_label.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.LabelFrame(paned, text="Generation Results", padding=10)
        paned.add(info_frame, height=300)

        self.phase_info_text = tk.Text(info_frame, height=8, width=60, font=('Courier', 9),
                                       relief=tk.FLAT, bd=0, state=tk.DISABLED,
                                       bg="white", fg="#333333",
                                       highlightthickness=1, highlightbackground="#cccccc",
                                       highlightcolor="#cccccc",
                                       selectbackground="#0078d4", selectforeground="white")
        self.phase_info_text.pack(fill=tk.BOTH, expand=True)

    # ── Phase generation ──────────────────────────────────────────────────────

    def _on_phase_type_change(self, *_):
        for widget in self._lp_size_btns:
            widget.config(state=tk.NORMAL)

    def _set_phase_info(self, text: str):
        self.phase_info_text.config(state=tk.NORMAL)
        self.phase_info_text.delete(1.0, tk.END)
        self.phase_info_text.insert(1.0, text)
        self.phase_info_text.config(state=tk.DISABLED)

    def _on_generate_phase(self):
        """Generate and display phase map based on current parameters."""
        ptype = self.phase_type_var.get()
        try:
            phase_angle = float(self.phase_entries["phase_angle"].get())
            fx = float(self.phase_entries["fx"].get())
            fy = float(self.phase_entries["fy"].get())
        except ValueError:
            self._set_phase_info("Error: invalid numeric input")
            return

        try:
            if ptype == "lp":
                l_val = int(self.phase_entries["vortex_l"].get())
                size = self.lp_size_var.get()
                size_map = {"square": "1024×1024", "wide": "1920×1080"}
                size_label = size_map[size]

                phase = lp_phase_distribution(size, l_val, n_x=int(fx) if fx != 0 else 0,
                                             n_y=int(fy) if fy != 0 else 0, phase_angle=phase_angle)

                info_lines = [
                    f"Phase type:  LP Phase Distribution",
                    f"Topological: l = {l_val}",
                    f"Size:        {size_label}",
                    f"Grating:     fx={int(fx)}, fy={int(fy)}",
                    f"Phase rot:   {phase_angle}°",
                ]
                colormap = "phase_gray"
            else:
                l_val = int(self.phase_entries["vortex_l"].get())
                size = self.lp_size_var.get()
                phase = vortex_phase(size, l_val, phase_angle=phase_angle)
                info_lines = [
                    f"Phase type:  Vortex",
                    f"Topological: l = {l_val}",
                    f"Grating:     fx={int(fx)}, fy={int(fy)}",
                    f"Phase rot:   {phase_angle}°",
                ]
                colormap = "gray"

                if fx != 0 or fy != 0:
                    phase = phase + blazed_grating(phase.shape, fx, fy)

        except Exception as e:
            self._set_phase_info(f"Error: {e}")
            return

        pil_image = ImageRenderer.phase_to_image(phase, colormap=colormap, size=phase.shape[::-1])

        display_w = self.phase_image_label.winfo_width()
        display_h = self.phase_image_label.winfo_height()
        if display_w > 1 and display_h > 1:
            pil_image.thumbnail((display_w - 10, display_h - 10), Image.Resampling.LANCZOS)

        self.current_phase_image = pil_image
        photo = ImageTk.PhotoImage(pil_image)
        self.phase_image_label.config(image=photo)
        self.phase_image_label.image = photo  # type: ignore[attr-defined]

        info_lines.append("")
        info_lines.append("Status:      Generated successfully")
        self._set_phase_info("\n".join(info_lines))

    def _on_export_phase(self):
        if self.current_phase_image is None:
            messagebox.showwarning("Warning", "No phase image to export")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.current_phase_image.save(filename)
                messagebox.showinfo("Success", f"Saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _create_param_group(self, parent, title, params):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=title, style='Section.TLabel').pack(anchor=tk.W, pady=(0, 4))
        for label, key in params:
            row_frame = ttk.Frame(frame)
            row_frame.pack(fill=tk.X, pady=2)
            ttk.Label(row_frame, text=label, width=18).pack(side=tk.LEFT)
            entry = ttk.Entry(row_frame, width=15)
            entry.pack(side=tk.LEFT, padx=(5, 0))
            self.entries[key] = entry
            if key == "wavelength_nm":
                entry.insert(0, str(self.params["wavelength"] * 1e9))
            elif key == "a_um":
                entry.insert(0, str(self.params["a"] * 1e6))
            else:
                entry.insert(0, str(self.params[key]))

    def _on_overlay_change(self, *_):
        state = tk.DISABLED if self.overlay_var.get() == "vector" else tk.NORMAL
        for btn in self._parity_btns + self._pol_dir_btns:
            btn.config(state=state)

    def _on_calculate(self):
        if self.is_computing:
            messagebox.showwarning("Warning", "Already computing...")
            return
        try:
            self.params["l"] = int(self.entries["l"].get())
            self.params["m"] = int(self.entries["m"].get())
            self.params["wavelength"] = float(self.entries["wavelength_nm"].get()) * 1e-9
            self.params["n_core"] = float(self.entries["n_core"].get())
            self.params["n_clad"] = float(self.entries["n_clad"].get())
            self.params["a"] = float(self.entries["a_um"].get()) * 1e-6
            self.params["mesh_size"] = int(self.entries["mesh_size"].get())
            self.params["is_odd"] = self.parity_var.get() == "odd"
            threading.Thread(target=self._compute, daemon=True).start()
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid parameter: {e}")

    def _compute(self):
        self.is_computing = True
        self._update_status("Computing...", "orange")
        try:
            self.mode = LPMode(
                l=self.params["l"],
                m=self.params["m"],
                wavelength=self.params["wavelength"],
                n_core=self.params["n_core"],
                n_clad=self.params["n_clad"],
                a=self.params["a"],
                is_odd=self.params["is_odd"],
            )
            v = self.mode.calculate_v()
            roots = self.mode.find_roots(v, 300)
            if len(roots) < self.params["m"]:
                raise ValueError(f"找不到第 {self.params['m']} 个根（V={v:.4f} 下只有 {len(roots)} 个解）")

            _, _, R, Phi = LPMode.generate_mesh(self.params["mesh_size"])
            U = roots[self.params["m"] - 1]
            intensity = np.abs(self.mode.E_x(R, Phi, U)) ** 2
            self._last_R = R
            self._last_Phi = Phi
            self._last_U = U

            self.root.after(0, self._display_result, intensity, v, roots, U, R, Phi)
        except Exception as e:
            self.root.after(0, self._display_error, str(e))
        finally:
            self.is_computing = False
            self._update_status("Ready", "green")

    def _display_error(self, msg: str):
        self.image_label.config(image='')
        self.image_label.image = None  # type: ignore[attr-defined]
        self.current_pil_image = None
        self._set_info_text(f"Error:\n{msg}")
        self._update_status("Error", "red")

    def _display_result(self, intensity: np.ndarray, v: float, roots: list,
                        U: float, R: np.ndarray, Phi: np.ndarray):
        colormap = self.colormap_var.get()
        l = self.params["l"]
        m = self.params["m"]
        show_pol = self.show_pol_var.get()

        if self.overlay_var.get() == "vector":
            assert self.mode is not None
            v_val = self.mode._v if self.mode._v is not None else self.mode.calculate_v()
            vec_data = get_vector_modes(l=l, m=m, U=U, V=v_val)
            pil_image = ImageRenderer.draw_vector_mode(
                vec_data["intensity"],
                vec_data["modes"],
                vec_data["titles"],
                vec_data["X_arrow"],
                vec_data["Y_arrow"],
                colormap=colormap,
                size=(900, 240),
                extent=vec_data["extent"],
                show_pol=show_pol,
            )
        else:
            if show_pol:
                assert self.mode is not None
                E_field = self.mode.E_x(R, Phi, U)
                pol_dir = self.pol_dir_var.get()
                Ex = E_field if pol_dir == "x" else np.zeros_like(E_field)
                Ey = E_field if pol_dir == "y" else None
                pil_image = ImageRenderer.draw_polarization(intensity, Ex, Ey, colormap=colormap)
            else:
                pil_image = ImageRenderer.array_to_image(intensity, colormap, size=(400, 400))

        display_w = self.image_label.winfo_width()
        display_h = self.image_label.winfo_height()
        if display_w > 1 and display_h > 1:
            pil_image.thumbnail((display_w - 10, display_h - 10), Image.Resampling.LANCZOS)

        self.current_pil_image = pil_image
        photo = ImageTk.PhotoImage(pil_image)
        self.image_label.config(image=photo)
        self.image_label.image = photo  # type: ignore[attr-defined]

        info_lines = [
            f"LP Mode: LP{l}{m} ({self.parity_var.get()})",
            f"",
            f"V-number:    {v:.4f}",
            f"Roots found: {len(roots)}",
            f"Selected U:  {U:.4f}",
            f"Wavelength:  {self.params['wavelength']*1e9:.1f} nm",
            f"Core radius: {self.params['a']*1e6:.2f} μm",
        ]
        if self.overlay_var.get() == "vector" and l >= 1:
            info_lines += [""] + format_decomposition(l, m)

        self._set_info_text("\n".join(info_lines))

    def _set_info_text(self, text: str):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, text)
        self.info_text.config(state=tk.DISABLED)

    def _on_export(self):
        if self.current_pil_image is None:
            messagebox.showwarning("Warning", "No image to export")
            return
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.current_pil_image.save(filename)
                messagebox.showinfo("Success", f"Saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _update_status(self, text, color):
        self.status_label.config(text=text, foreground=color)
        self.root.update()


def main():
    root = tk.Tk()
    FiberModeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
