"""Tkinter GUI for Fiber Mode Visualization."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
import threading
from core.lpmode import LPMode
from core.renderer import ImageRenderer
from core.vector_mode import get_vector_modes, format_decomposition
from core.phase_map import vortex_phase, blazed_grating, lp_phase_distribution

# ── palette ───────────────────────────────────────────────────────────────────
BG       = "#F5F7FA"  # window / panel background
CARD_BG  = "#FFFFFF"  # card interior (white)
CARD_BD  = "#E6EAF0"  # card border
TEXT     = "#2C3E50"  # primary text
TEXT2    = "#7F8C8D"  # secondary / label text
BLUE     = "#4A90E2"  # accent blue
BLUE_DK  = "#357ABD"  # darker blue for hover
GREEN    = "#27AE60"
RED      = "#E74C3C"
ORANGE   = "#F39C12"
SEP      = "#E6EAF0"  # separator line
ENTRY_BD = "#DCDCDC"  # entry border
MONO_BG  = "#FAFAFA"  # image / results area background

TAB_ACT_BG = BLUE
TAB_ACT_FG = "#FFFFFF"
TAB_INACT  = TEXT2
TAB_HOVER  = "#F0F4FA"

# ── typography ────────────────────────────────────────────────────────────────
F_TITLE   = ("Helvetica", 14, "bold")
F_SECTION = ("Helvetica", 10, "bold")
F_LABEL   = ("Helvetica", 10)
F_LABEL2  = ("Helvetica", 9)
F_MONO    = ("Menlo", 9)

# ── layout constants ──────────────────────────────────────────────────────────
PAD    = 8    # inner card padding
GAP    = 5    # vertical gap between cards
ROW    = 3    # row spacing inside a card body
LPAD   = 10   # outer left/right panel padding
LEFT_W = 280  # fixed width of the left control panel


# ── widget helpers ────────────────────────────────────────────────────────────

def _bordered_card(parent, title="", fill_bg=CARD_BG):
    """1px-border card. Returns (outer_frame, body_frame).
    White header + separator when title is given; plain body otherwise."""
    outer = tk.Frame(parent, bg=CARD_BD, bd=0, highlightthickness=0)
    inner = tk.Frame(outer, bg=fill_bg, bd=0, highlightthickness=0)
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    if title:
        tk.Label(inner, text=title, bg=fill_bg, fg=TEXT,
                 font=F_SECTION, anchor=tk.W).pack(
            fill=tk.X, padx=PAD, pady=(PAD, 4))
        tk.Frame(inner, height=1, bg=SEP).pack(fill=tk.X, padx=PAD)
        body = tk.Frame(inner, bg=fill_bg)
        body.pack(fill=tk.BOTH, expand=True, padx=PAD, pady=(6, PAD))
    else:
        body = tk.Frame(inner, bg=fill_bg)
        body.pack(fill=tk.BOTH, expand=True, padx=PAD, pady=PAD)
    return outer, body


def _sec_card(parent, title, bg_inner=CARD_BG):
    """Scrollable-panel section card with title + separator. Returns body frame."""
    outer = tk.Frame(parent, bg=CARD_BD, bd=0, highlightthickness=0)
    outer.pack(fill=tk.X, padx=PAD, pady=(0, GAP + 3))
    inner = tk.Frame(outer, bg=bg_inner, bd=0, highlightthickness=0)
    inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    hdr = tk.Frame(inner, bg=bg_inner)
    hdr.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))
    tk.Label(hdr, text=title, bg=bg_inner, fg=TEXT,
             font=F_SECTION, anchor=tk.W).pack(side=tk.LEFT)
    tk.Frame(inner, height=1, bg=SEP).pack(fill=tk.X, padx=PAD)
    body = tk.Frame(inner, bg=bg_inner)
    body.pack(fill=tk.X, padx=PAD, pady=(8, PAD + 2))
    return body


def _label_entry(parent, label_text, width=10, label_width=15, bg=CARD_BG):
    """Label + Entry row. Entry border turns blue on focus. Returns Entry."""
    row = tk.Frame(parent, bg=bg)
    row.pack(fill=tk.X, pady=(0, ROW))
    tk.Label(row, text=label_text, bg=bg, fg=TEXT2,
             font=F_LABEL, width=label_width, anchor=tk.W).pack(side=tk.LEFT)
    ef = tk.Frame(row, bg=ENTRY_BD, bd=0, highlightthickness=0)
    ef.pack(side=tk.LEFT)
    e = tk.Entry(ef, width=width, bg=CARD_BG, fg=TEXT,
                 relief=tk.FLAT, bd=3, font=F_LABEL,
                 insertbackground=TEXT, highlightthickness=0)
    e.pack(padx=1, pady=1)
    e.bind("<FocusIn>",  lambda _: ef.config(bg=BLUE))
    e.bind("<FocusOut>", lambda _: ef.config(bg=ENTRY_BD))
    return e


def _spinbox_row(parent, label_text, var, from_=0, to=20, label_width=15, bg=CARD_BG):
    """Label + Spinbox row. Returns Spinbox."""
    row = tk.Frame(parent, bg=bg)
    row.pack(fill=tk.X, pady=(0, ROW))
    tk.Label(row, text=label_text, bg=bg, fg=TEXT2,
             font=F_LABEL, width=label_width, anchor=tk.W).pack(side=tk.LEFT)
    sb = tk.Spinbox(row, textvariable=var, from_=from_, to=to, width=6,
                    bg=CARD_BG, fg=TEXT, relief=tk.FLAT, bd=1,
                    highlightthickness=1, highlightbackground=ENTRY_BD,
                    highlightcolor=BLUE, font=F_LABEL,
                    buttonbackground=BG, insertbackground=TEXT,
                    disabledbackground=CARD_BG)
    sb.pack(side=tk.LEFT)
    return sb


def _radio_row(parent, label_text, var, choices, label_width=15, bg=CARD_BG,
               use_default_color=False, btn_width=0, grid_parent=None, grid_row=0):
    """Horizontal radio-button row. If grid_parent is given, uses grid layout for column alignment."""
    if grid_parent is not None:
        selectcolor = "systemButtonFace" if use_default_color else BLUE
        tk.Label(grid_parent, text=label_text, bg=bg, fg=TEXT2,
                 font=F_LABEL, anchor=tk.W).grid(row=grid_row, column=0, sticky=tk.W, padx=(0, 4), pady=(0, ROW))
        btns = []
        for col, (val, txt) in enumerate(choices):
            b = tk.Radiobutton(grid_parent, text=txt, variable=var, value=val,
                               bg=bg, fg=TEXT, activebackground=bg,
                               selectcolor=selectcolor, relief=tk.FLAT, bd=0,
                               highlightthickness=0, font=F_LABEL)
            b.grid(row=grid_row, column=col + 1, sticky=tk.W, padx=(15
            , 8), pady=(0, ROW))
            btns.append(b)
        return btns
    row = tk.Frame(parent, bg=bg)
    row.pack(fill=tk.X, pady=(0, ROW))
    tk.Label(row, text=label_text, bg=bg, fg=TEXT2,
             font=F_LABEL, width=label_width, anchor=tk.W).pack(side=tk.LEFT)
    btns = []
    selectcolor = "systemButtonFace" if use_default_color else BLUE
    for val, txt in choices:
        kw = dict(width=btn_width) if btn_width else {}
        b = tk.Radiobutton(row, text=txt, variable=var, value=val,
                           bg=bg, fg=TEXT, activebackground=bg,
                           selectcolor=selectcolor, relief=tk.FLAT, bd=0,
                           highlightthickness=0, font=F_LABEL, **kw)
        b.pack(side=tk.LEFT, padx=(0, 8))
        btns.append(b)
    return btns


def _img_btn(parent, text, command, bg=MONO_BG):
    """Flat label-button for image card headers.
    Uses tk.Label instead of tk.Button to avoid macOS system chrome."""
    lbl = tk.Label(parent, text=text, bg=bg, fg=BLUE, font=F_LABEL2, padx=6)
    lbl.pack(side=tk.RIGHT)
    lbl.bind("<Button-1>", lambda _: command())
    lbl.bind("<Enter>", lambda _: lbl.config(fg=BLUE_DK))
    lbl.bind("<Leave>", lambda _: lbl.config(fg=BLUE))


def _scrollable_frame(parent):
    """Canvas + Scrollbar inside parent. Returns the inner scrollable Frame."""
    cvs = tk.Canvas(parent, bg=BG, highlightthickness=0, bd=0)
    sb  = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=cvs.yview,
                        style='TScrollbar')
    sf  = tk.Frame(cvs, bg=BG)
    win_id = cvs.create_window((0, 0), window=sf, anchor="nw")
    sf.bind("<Configure>", lambda _: cvs.configure(scrollregion=cvs.bbox("all")))
    cvs.bind("<Configure>", lambda e: cvs.itemconfigure(win_id, width=e.width))
    cvs.configure(yscrollcommand=sb.set)
    cvs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    return sf


class TabBar(tk.Frame):
    """Custom tab bar. Active tab: blue background + white text.
    Inactive tabs: gray text, hover highlight."""

    def __init__(self, parent, tabs, on_switch, **kw):
        super().__init__(parent, bg=CARD_BG, highlightthickness=1,
                         highlightbackground=CARD_BD, bd=0, **kw)
        self._on_switch = on_switch
        self._btns: dict[str, tk.Label] = {}
        self._active: str | None = None

        for name in tabs:
            btn = tk.Label(self, text=f"  {name}  ", bg=CARD_BG, fg=TAB_INACT,
                           font=F_LABEL, pady=10)
            btn.bind("<Button-1>", lambda e, n=name: self.select(n))
            btn.bind("<Enter>",    lambda e, b=btn: self._on_hover(b, True))
            btn.bind("<Leave>",    lambda e, b=btn: self._on_hover(b, False))
            btn.pack(side=tk.LEFT)
            self._btns[name] = btn

        # set initial active state without firing the callback
        self._active = tabs[0]
        self._btns[tabs[0]].config(bg=TAB_ACT_BG, fg=TAB_ACT_FG)

    def _on_hover(self, btn, entering):
        if btn is self._btns.get(self._active):
            return
        btn.config(bg=TAB_HOVER if entering else CARD_BG)

    def select(self, name):
        if self._active and self._active != name:
            self._btns[self._active].config(bg=CARD_BG, fg=TAB_INACT)
        self._active = name
        self._btns[name].config(bg=TAB_ACT_BG, fg=TAB_ACT_FG)
        self._on_switch(name)


class FiberModeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fiber Mode Visualization")
        self.root.geometry("1200x780")
        self.root.minsize(800, 560)
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Set custom icon
        try:
            import os
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self._setup_ttk_style()

        self.params = {
            "l": 0, "m": 1,
            "wavelength": 638e-9,
            "n_core": 1.4633, "n_clad": 1.4569,
            "a": 4.5e-6, "is_odd": False, "mesh_size": 300,
        }
        self.mode = None
        self.current_pil_image  = None
        self.current_phase_image = None
        self.is_computing = False
        self.entries:       dict[str, tk.Entry] = {}
        self.phase_entries: dict[str, tk.Entry] = {}

        self._build_ui()

    def _setup_ttk_style(self):
        """Configure ttk theme and button styles."""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TScrollbar', background=BG, troughcolor=BG,
                        borderwidth=0, arrowsize=12)
        style.configure('P.TButton', font=("Helvetica", 10, "bold"),
                        background=BLUE, foreground="#FFFFFF",
                        borderwidth=0, relief='flat', padding=(14, 10))
        style.map('P.TButton',
                  background=[('active', BLUE_DK), ('pressed', '#2A6099')])

    def _build_ui(self):
        # ── tab bar ──────────────────────────────────────────────────────────
        tab_row = tk.Frame(self.root, bg=BG)
        tab_row.pack(fill=tk.X, padx=LPAD, pady=(14, 0))

        self._tab_bar = TabBar(tab_row, ["Intensity", "Phase Map"],
                               self._switch_tab)
        self._tab_bar.pack(side=tk.LEFT)

        # ── content ──────────────────────────────────────────────────────────
        self._content = tk.Frame(self.root, bg=BG)
        self._content.pack(fill=tk.BOTH, expand=True)

        self._current_page = None
        self._pages: dict[str, tk.Frame] = {}
        for name, builder in [("Intensity",  self._build_intensity_tab),
                               ("Phase Map",  self._build_phase_tab)]:
            page = tk.Frame(self._content, bg=BG)
            builder(page)
            self._pages[name] = page

        self._switch_tab("Intensity")

    def _switch_tab(self, name):
        if self._current_page:
            self._current_page.pack_forget()
        self._current_page = self._pages[name]
        self._current_page.pack(fill=tk.BOTH, expand=True)

    # ============================================================ INTENSITY TAB
    def _build_intensity_tab(self, parent):
        left = tk.Frame(parent, width=LEFT_W, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(LPAD, 4), pady=LPAD)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                   padx=(4, LPAD), pady=LPAD)

        self._build_intensity_left(left)
        self._build_intensity_right(right)

    def _build_intensity_left(self, parent):
        card_outer = tk.Frame(parent, bg=CARD_BD, bd=0, highlightthickness=0)
        card_outer.pack(fill=tk.BOTH, expand=True)
        card = tk.Frame(card_outer, bg=BG, bd=0, highlightthickness=0)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # title
        title_row = tk.Frame(card, bg=BG)
        title_row.pack(fill=tk.X, padx=PAD, pady=(PAD + 2, 4))
        tk.Label(title_row, text="Mode Visualization",
                 bg=BG, fg=TEXT, font=F_TITLE).pack(side=tk.LEFT)
        tk.Frame(card, height=1, bg=SEP).pack(fill=tk.X, padx=PAD)

        scroll_wrap = tk.Frame(card, bg=BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, PAD))
        sf = _scrollable_frame(scroll_wrap)
        body = _sec_card(sf, "Mode Parameters")
        self.l_var = tk.IntVar(value=self.params["l"])
        self.m_var = tk.IntVar(value=self.params["m"])
        _spinbox_row(body, "l  (azimuthal)", self.l_var, from_=0, to=20, bg=CARD_BG)
        _spinbox_row(body, "m  (radial)",    self.m_var, from_=1, to=20, bg=CARD_BG)

        # ── Fiber Properties ─────────────────────────────────────────────────
        body = _sec_card(sf, "Fiber Properties")
        for lbl, key, val in [
            ("wavelength (nm)", "wavelength_nm", str(self.params["wavelength"] * 1e9)),
            ("n_core",          "n_core",        str(self.params["n_core"])),
            ("n_clad",          "n_clad",        str(self.params["n_clad"])),
            ("a  (μm)",         "a_um",          str(self.params["a"] * 1e6)),
        ]:
            e = _label_entry(body, lbl)
            self.entries[key] = e
            e.insert(0, val)

        # ── Computation ──────────────────────────────────────────────────────
        body = _sec_card(sf, "Computation")
        e = _label_entry(body, "mesh size")
        self.entries["mesh_size"] = e
        e.insert(0, str(self.params["mesh_size"]))

        # ── Display Options ──────────────────────────────────────────────────
        body = _sec_card(sf, "Display Options")

        grid = tk.Frame(body, bg=CARD_BG)
        grid.pack(fill=tk.X)

        self.colormap_var = tk.StringVar(value="jet")
        _radio_row(body, "Colormap", self.colormap_var,
                   [("jet", "jet"), ("gray", "gray")], use_default_color=True,
                   grid_parent=grid, grid_row=0)

        self.overlay_var = tk.StringVar(value="lp")
        self.overlay_var.trace_add("write", self._on_overlay_change)
        _radio_row(body, "Mode", self.overlay_var,
                   [("lp", "LP"), ("vector", "Vector")], use_default_color=True,
                   grid_parent=grid, grid_row=1)

        self.parity_var = tk.StringVar(value="even")
        self._parity_btns = _radio_row(body, "Parity", self.parity_var,
                                        [("even", "even"), ("odd", "odd")], use_default_color=True,
                                        grid_parent=grid, grid_row=2)

        self.pol_dir_var = tk.StringVar(value="x")
        self._pol_dir_btns = _radio_row(body, "Pol dir", self.pol_dir_var,
                                         [("x", "x-pol"), ("y", "y-pol")], use_default_color=True,
                                         grid_parent=grid, grid_row=3)

        chk_row = tk.Frame(body, bg=CARD_BG)
        chk_row.pack(fill=tk.X, pady=(0, 4))
        self.show_pol_var = tk.BooleanVar(value=False)
        tk.Checkbutton(chk_row, text="Polarization Arrows",
                       variable=self.show_pol_var,
                       bg=CARD_BG, fg=TEXT, activebackground=CARD_BG,
                       selectcolor=CARD_BG, relief=tk.FLAT, bd=0,
                       highlightthickness=0, font=F_LABEL).pack(anchor=tk.W)

        # ── Generate button ───────────────────────────────────────────────────
        btn_f = tk.Frame(sf, bg=BG)
        btn_f.pack(fill=tk.X, padx=PAD, pady=(4, 0))
        ttk.Button(btn_f, text="Generate", command=self._on_calculate,
                   style='P.TButton').pack(fill=tk.X)

        # ── Status ───────────────────────────────────────────────────────────
        self.status_label = tk.Label(sf, text="● Ready",
                                     bg=BG, fg=GREEN,
                                     font=("Helvetica", 9, "bold"))
        self.status_label.pack(anchor=tk.CENTER, pady=(8, 0))

    def _build_intensity_right(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # image card with action buttons in header
        outer_v = tk.Frame(parent, bg=CARD_BD, bd=0, highlightthickness=0)
        outer_v.grid(row=0, column=0, sticky="nsew", pady=(0, GAP))
        inner_v = tk.Frame(outer_v, bg=CARD_BG, bd=0, highlightthickness=0)
        inner_v.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        hdr_v = tk.Frame(inner_v, bg=CARD_BG)
        hdr_v.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))
        tk.Label(hdr_v, text="Field Intensity Distribution",
                 bg=CARD_BG, fg=TEXT, font=F_SECTION, anchor=tk.W).pack(side=tk.LEFT)
        _img_btn(hdr_v, "Zoom",     self._on_zoom_image,  bg=CARD_BG)
        _img_btn(hdr_v, "Download", self._on_export,      bg=CARD_BG)
        tk.Frame(inner_v, height=1, bg=SEP).pack(fill=tk.X, padx=PAD)

        img_container = tk.Frame(inner_v, bg=MONO_BG)
        img_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.image_label = tk.Label(img_container, bg=MONO_BG, anchor=tk.CENTER)
        self.image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER,
                               relwidth=1, relheight=1)

        outer_r, body_r = _bordered_card(parent, "Calculation Results")
        outer_r.grid(row=1, column=0, sticky="nsew")
        self.info_text = tk.Text(body_r, height=7, font=("Menlo", 10),
                                 relief=tk.FLAT, bd=0, state=tk.DISABLED,
                                 bg=MONO_BG, fg=TEXT,
                                 highlightthickness=0,
                                 padx=8, pady=8, spacing1=3, spacing3=3)
        self.info_text.pack(fill=tk.BOTH, expand=True)

    # ============================================================ PHASE TAB
    def _build_phase_tab(self, parent):
        left = tk.Frame(parent, width=LEFT_W, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(LPAD, 4), pady=LPAD)
        left.pack_propagate(False)

        right = tk.Frame(parent, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                   padx=(4, LPAD), pady=LPAD)

        self._build_phase_left(left)
        self._build_phase_right(right)

    def _build_phase_left(self, parent):
        # outer bordered card — BG interior, no inner sub-card borders
        card_outer = tk.Frame(parent, bg=CARD_BD, bd=0, highlightthickness=0)
        card_outer.pack(fill=tk.BOTH, expand=True)
        card = tk.Frame(card_outer, bg=BG, bd=0, highlightthickness=0)
        card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # title
        title_row = tk.Frame(card, bg=BG)
        title_row.pack(fill=tk.X, padx=PAD, pady=(PAD + 2, 4))
        tk.Label(title_row, text="Phase Map Generator",
                 bg=BG, fg=TEXT, font=F_TITLE).pack(side=tk.LEFT)
        tk.Frame(card, height=1, bg=SEP).pack(fill=tk.X, padx=PAD)
        scroll_wrap = tk.Frame(card, bg=BG)
        scroll_wrap.pack(fill=tk.BOTH, expand=True, pady=(4, PAD))
        sf = _scrollable_frame(scroll_wrap)

        # Phase Type
        body = _sec_card(sf, "Phase Type")
        self.phase_type_var = tk.StringVar(value="lp")
        _radio_row(body, "Type", self.phase_type_var,
                   [("lp", "LP Mode"), ("vortex", "Vortex")], label_width=10, use_default_color=True)

        # Parameters
        body = _sec_card(sf, "Parameters")
        for lbl, key, default in [
            ("Topological",   "vortex_l",    "1"),
            ("Phase rot (°)", "phase_angle", "0"),
            ("Grating fx",    "fx",          "0"),
            ("Grating fy",    "fy",          "0"),
        ]:
            e = _label_entry(body, lbl, label_width=12)
            e.insert(0, default)
            self.phase_entries[key] = e

        # Output Size
        body = _sec_card(sf, "Output Size")
        self.lp_size_var = tk.StringVar(value="square")
        self._lp_size_btns = []
        for val, txt in [("square", "1024×1024"), ("wide", "1920×1080")]:
            b = tk.Radiobutton(body, text=txt, variable=self.lp_size_var, value=val,
                               bg=CARD_BG, fg=TEXT, activebackground=CARD_BG,
                               selectcolor=CARD_BG, relief=tk.FLAT, bd=0,
                               highlightthickness=0, font=F_LABEL, anchor=tk.W)
            b.pack(fill=tk.X, pady=(0, 2))
            self._lp_size_btns.append(b)

        # Generate button
        btn_f = tk.Frame(sf, bg=BG)
        btn_f.pack(fill=tk.X, padx=PAD, pady=(4, 0))
        ttk.Button(btn_f, text="Generate", command=self._on_generate_phase,
                   style='P.TButton').pack(fill=tk.X)

        # Status
        self.phase_status_label = tk.Label(sf, text="● Ready",
                                           bg=BG, fg=GREEN,
                                           font=("Helvetica", 9, "bold"))
        self.phase_status_label.pack(anchor=tk.CENTER, pady=(8, 0))

    def _build_phase_right(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        outer_v = tk.Frame(parent, bg=CARD_BD, bd=0, highlightthickness=0)
        outer_v.grid(row=0, column=0, sticky="nsew", pady=(0, GAP))
        inner_v = tk.Frame(outer_v, bg=CARD_BG, bd=0, highlightthickness=0)
        inner_v.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        hdr_v = tk.Frame(inner_v, bg=CARD_BG)
        hdr_v.pack(fill=tk.X, padx=PAD, pady=(PAD, 4))
        tk.Label(hdr_v, text="Phase Distribution",
                 bg=CARD_BG, fg=TEXT, font=F_SECTION, anchor=tk.W).pack(side=tk.LEFT)
        _img_btn(hdr_v, "Zoom",     self._on_zoom_phase,    bg=CARD_BG)
        _img_btn(hdr_v, "Download", self._on_export_phase,  bg=CARD_BG)
        tk.Frame(inner_v, height=1, bg=SEP).pack(fill=tk.X, padx=PAD)

        phase_container = tk.Frame(inner_v, bg=MONO_BG)
        phase_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.phase_image_label = tk.Label(phase_container, bg=MONO_BG, anchor=tk.CENTER)
        self.phase_image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER,
                                     relwidth=1, relheight=1)

        outer_r, body_r = _bordered_card(parent, "Generation Results")
        outer_r.grid(row=1, column=0, sticky="nsew")
        self.phase_info_text = tk.Text(body_r, height=7, font=("Menlo", 10),
                                       relief=tk.FLAT, bd=0, state=tk.DISABLED,
                                       bg=MONO_BG, fg=TEXT,
                                       highlightthickness=0,
                                       padx=8, pady=8, spacing1=3, spacing3=3)
        self.phase_info_text.pack(fill=tk.BOTH, expand=True)

    # ============================================================ LOGIC
    def _on_overlay_change(self, *_):
        """Disable parity/pol-dir controls when Vector mode is selected."""
        state = tk.DISABLED if self.overlay_var.get() == "vector" else tk.NORMAL
        for btn in self._parity_btns + self._pol_dir_btns:
            btn.config(state=state)

    def _on_calculate(self):
        if self.is_computing:
            messagebox.showwarning("Warning", "Already computing...")
            return
        try:
            self.params["l"] = int(self.l_var.get())
            self.params["m"] = int(self.m_var.get())
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
        self._update_status("● Computing...", ORANGE)
        try:
            self.mode = LPMode(
                l=self.params["l"], m=self.params["m"],
                wavelength=self.params["wavelength"],
                n_core=self.params["n_core"], n_clad=self.params["n_clad"],
                a=self.params["a"], is_odd=self.params["is_odd"],
            )
            v = self.mode.calculate_v()
            roots = self.mode.find_roots(v, 300)
            if len(roots) < self.params["m"]:
                raise ValueError(
                    f"Cannot find root {self.params['m']} "
                    f"(V={v:.4f} has {len(roots)} solutions)")
            _, _, R, Phi = LPMode.generate_mesh(self.params["mesh_size"])
            U = roots[self.params["m"] - 1]
            intensity = np.abs(self.mode.E_x(R, Phi, U)) ** 2
            self._last_R, self._last_Phi, self._last_U = R, Phi, U
            self.root.after(0, self._display_result, intensity, v, roots, U, R, Phi)
        except Exception as e:
            self.root.after(0, self._display_error, str(e))
        finally:
            self.is_computing = False
            self._update_status("● Ready", GREEN)

    def _display_error(self, msg):
        self.image_label.config(image='')
        self.image_label.image = None
        self.current_pil_image = None
        self._set_info_text(f"Error:\n{msg}")
        self._update_status("● Error", RED)

    def _display_result(self, intensity, v, roots, U, R, Phi):
        colormap = self.colormap_var.get()
        l, m = self.params["l"], self.params["m"]
        show_pol = self.show_pol_var.get()

        if self.overlay_var.get() == "vector":
            assert self.mode is not None
            v_val = self.mode._v if self.mode._v is not None else self.mode.calculate_v()
            vec_data = get_vector_modes(l=l, m=m, U=U, V=v_val)
            pil_image = ImageRenderer.draw_vector_mode(
                vec_data["intensity"], vec_data["modes"], vec_data["titles"],
                vec_data["X_arrow"], vec_data["Y_arrow"],
                colormap=colormap, size=(900, 240),
                extent=vec_data["extent"], show_pol=show_pol,
                gap_color=(250, 250, 250),
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

        w = self.image_label.winfo_width()
        h = self.image_label.winfo_height()
        if w > 1 and h > 1:
            pil_image.thumbnail((w - 10, h - 10), Image.Resampling.LANCZOS)

        self.current_pil_image = pil_image
        photo = ImageTk.PhotoImage(pil_image)
        self.image_label.config(image=photo)
        self.image_label.image = photo

        is_vector = self.overlay_var.get() == "vector"
        lines = [] if is_vector else [f"LP Mode: LP{l}{m} ({self.parity_var.get()})", ""]
        lines += [
            f"V-number:    {v:.4f}",
            f"Roots found: {len(roots)}",
            f"Selected U:  {U:.4f}",
            f"Wavelength:  {self.params['wavelength']*1e9:.1f} nm",
            f"Core radius: {self.params['a']*1e6:.2f} um",
        ]
        if is_vector and l >= 1:
            lines += [""] + format_decomposition(l, m)
        self._set_info_text("\n".join(lines))

    # ── display helpers ───────────────────────────────────────────────────────

    def _set_info_text(self, text):
        """Replace content of the intensity results text widget."""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, text)
        self.info_text.config(state=tk.DISABLED)

    def _set_phase_info(self, text):
        """Replace content of the phase results text widget."""
        self.phase_info_text.config(state=tk.NORMAL)
        self.phase_info_text.delete(1.0, tk.END)
        self.phase_info_text.insert(1.0, text)
        self.phase_info_text.config(state=tk.DISABLED)

    def _update_status(self, text, color):
        self.status_label.config(text=text, fg=color)
        self.root.update_idletasks()

    def _show_zoom_window(self, pil_image, title):
        """Open a non-resizable Toplevel showing pil_image at up to 85% screen size."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=MONO_BG)
        max_w = int(self.root.winfo_screenwidth()  * 0.85)
        max_h = int(self.root.winfo_screenheight() * 0.85)
        img = pil_image.copy()
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl = tk.Label(win, image=photo, bg=MONO_BG)
        lbl.image = photo
        lbl.pack(padx=10, pady=10)
        win.resizable(False, False)

    def _on_export(self):
        if self.current_pil_image is None:
            messagebox.showwarning("Warning", "No image to export")
            return
        fn = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if fn:
            try:
                self.current_pil_image.save(fn)
                messagebox.showinfo("Success", f"Saved to {fn}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _on_zoom_image(self):
        if self.current_pil_image is None:
            messagebox.showwarning("Warning", "No image to display")
            return
        self._show_zoom_window(self.current_pil_image, "Field Intensity")

    def _on_zoom_phase(self):
        if self.current_phase_image is None:
            messagebox.showwarning("Warning", "No phase image to display")
            return
        self._show_zoom_window(self.current_phase_image, "Phase Distribution")

    def _on_generate_phase(self):
        ptype = self.phase_type_var.get()
        try:
            phase_angle = float(self.phase_entries["phase_angle"].get())
            fx = float(self.phase_entries["fx"].get())
            fy = float(self.phase_entries["fy"].get())
        except ValueError:
            self._set_phase_info("Error: invalid numeric input")
            return
        try:
            l_val = int(self.phase_entries["vortex_l"].get())
            size = self.lp_size_var.get()
            if ptype == "lp":
                phase = lp_phase_distribution(
                    size, l_val,
                    n_x=int(fx) if fx != 0 else 0,
                    n_y=int(fy) if fy != 0 else 0,
                    phase_angle=phase_angle)
                info_lines = [
                    "Phase type:  LP Phase Distribution",
                    f"Topological: l = {l_val}",
                    f"Size:        {'1024×1024' if size=='square' else '1920×1080'}",
                    f"Grating:     fx={int(fx)}, fy={int(fy)}",
                    f"Phase rot:   {phase_angle}°",
                ]
                colormap = "phase_gray"
            else:
                phase = vortex_phase(size, l_val, phase_angle=phase_angle)
                if fx != 0 or fy != 0:
                    phase = phase + blazed_grating(phase.shape, fx, fy)
                info_lines = [
                    "Phase type:  Vortex",
                    f"Topological: l = {l_val}",
                    f"Grating:     fx={int(fx)}, fy={int(fy)}",
                    f"Phase rot:   {phase_angle}°",
                ]
                colormap = "gray"
        except Exception as e:
            self._set_phase_info(f"Error: {e}")
            return

        pil_image = ImageRenderer.phase_to_image(
            phase, colormap=colormap, size=phase.shape[::-1])

        w = self.phase_image_label.winfo_width()
        h = self.phase_image_label.winfo_height()
        if w > 1 and h > 1:
            pil_image.thumbnail((w - 10, h - 10), Image.Resampling.LANCZOS)

        self.current_phase_image = pil_image
        photo = ImageTk.PhotoImage(pil_image)
        self.phase_image_label.config(image=photo)
        self.phase_image_label.image = photo

        info_lines.append("")
        info_lines.append("Status:      Generated successfully")
        self._set_phase_info("\n".join(info_lines))

    def _on_export_phase(self):
        if self.current_phase_image is None:
            messagebox.showwarning("Warning", "No phase image to export")
            return
        fn = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if fn:
            try:
                self.current_phase_image.save(fn)
                messagebox.showinfo("Success", f"Saved to {fn}")
            except Exception as e:
                messagebox.showerror("Error", str(e))


def main():
    root = tk.Tk()
    FiberModeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
