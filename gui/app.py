"""
SymSolver — Tkinter GUI

A chat-style interface for solving linear equations step-by-step.
Dark theme, scrollable solution area, and collapsible explanations.
"""

import os
import re
import tkinter as tk
from tkinter import ttk, font as tkfont
import threading

from solver import solve_linear_equation
from gui.sidebar import Sidebar


# ── colour palette ─────────────────────────────────────────────────────────
_DARK_PALETTE = dict(
    BG           = "#0a0a0a",
    BG_DARKER    = "#050505",
    HEADER_BG    = "#111111",
    ACCENT       = "#1a8cff",
    ACCENT_HOVER = "#0a70d4",
    TEXT         = "#d0d0d0",
    TEXT_DIM     = "#ffffff",
    TEXT_BRIGHT  = "#f0f0f0",
    USER_BG      = "#1a1a1a",
    BOT_BG       = "#121212",
    STEP_BG      = "#181818",
    STEP_BORDER  = "#2a2a2a",
    SUCCESS      = "#4caf50",
    ERROR        = "#ff5555",
    INPUT_BG     = "#181818",
    INPUT_BORDER = "#2a2a2a",
    VERIFY_BG    = "#0f1a0f",
    SCROLLBAR_BG = "#2a2a2a",
    SCROLLBAR_ACT= "#444444",
    SCROLLBAR_ARR= "#555555",
)
# ── Case-badge colour tables (graph analysis card) ────────────────────────
_DARK_CASE_COLORS = {
    "one_solution":             {"bg": "#0d1f0d", "border": "#4caf50", "fg": "#4caf50"},
    "infinite":                 {"bg": "#1a1500", "border": "#f0c040", "fg": "#f0c040"},
    "no_solution":              {"bg": "#1f0d0d", "border": "#ff5555", "fg": "#ff5555"},
    "degenerate_identity":      {"bg": "#1a1500", "border": "#f0c040", "fg": "#f0c040"},
    "degenerate_contradiction":  {"bg": "#1f0d0d", "border": "#ff5555", "fg": "#ff5555"},
}
_LIGHT_CASE_COLORS = {
    "one_solution":             {"bg": "#e8f5e9", "border": "#2e7d32", "fg": "#1b5e20"},
    "infinite":                 {"bg": "#fff8e1", "border": "#f57f17", "fg": "#e65100"},
    "no_solution":              {"bg": "#ffebee", "border": "#c62828", "fg": "#b71c1c"},
    "degenerate_identity":      {"bg": "#fff8e1", "border": "#f57f17", "fg": "#e65100"},
    "degenerate_contradiction":  {"bg": "#ffebee", "border": "#c62828", "fg": "#b71c1c"},
}

_LIGHT_PALETTE = dict(
    BG           = "#f2f4f7",
    BG_DARKER    = "#e4e8ee",
    HEADER_BG    = "#ffffff",
    ACCENT       = "#0F4C75",
    ACCENT_HOVER = "#0a3a5c",
    TEXT         = "#444444",
    TEXT_DIM     = "#000000",
    TEXT_BRIGHT  = "#111111",
    USER_BG      = "#e6eaf0",
    BOT_BG       = "#ffffff",
    STEP_BG      = "#f7f9fc",
    STEP_BORDER  = "#dde2ea",
    SUCCESS      = "#2e7d32",
    ERROR        = "#c62828",
    INPUT_BG     = "#ffffff",
    INPUT_BORDER = "#c5ccd6",
    VERIFY_BG    = "#e8f5e9",
    SCROLLBAR_BG = "#c5ccd6",
    SCROLLBAR_ACT= "#9baabb",
    SCROLLBAR_ARR= "#888888",
)

# Active palette (mutable globals — updated by _apply_theme)
BG           = _DARK_PALETTE["BG"]
BG_DARKER    = _DARK_PALETTE["BG_DARKER"]
HEADER_BG    = _DARK_PALETTE["HEADER_BG"]
ACCENT       = _DARK_PALETTE["ACCENT"]
ACCENT_HOVER = _DARK_PALETTE["ACCENT_HOVER"]
TEXT         = _DARK_PALETTE["TEXT"]
TEXT_DIM     = _DARK_PALETTE["TEXT_DIM"]
TEXT_BRIGHT  = _DARK_PALETTE["TEXT_BRIGHT"]
USER_BG      = _DARK_PALETTE["USER_BG"]
BOT_BG       = _DARK_PALETTE["BOT_BG"]
STEP_BG      = _DARK_PALETTE["STEP_BG"]
STEP_BORDER  = _DARK_PALETTE["STEP_BORDER"]
SUCCESS      = _DARK_PALETTE["SUCCESS"]
ERROR        = _DARK_PALETTE["ERROR"]
INPUT_BG     = _DARK_PALETTE["INPUT_BG"]
INPUT_BORDER = _DARK_PALETTE["INPUT_BORDER"]
VERIFY_BG    = _DARK_PALETTE["VERIFY_BG"]


class SymSolverApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("SymSolver — Linear Equation Solver")
        self.geometry("1000x850")
        self.minsize(680, 600)
        self.configure(bg=BG)

        # ── Fonts ────────────────────────────────────────────────────────
        self._default = tkfont.Font(family="Segoe UI", size=14)
        self._bold    = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self._title   = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self._mono    = tkfont.Font(family="Consolas", size=15)
        self._small   = tkfont.Font(family="Segoe UI", size=12)
        self._frac    = tkfont.Font(family="Consolas", size=13)
        self._frac_sm = tkfont.Font(family="Consolas", size=11)

        self._auto_scroll: bool = True  # False while user has scrolled away from bottom
        self._theme: str = "dark"        # current theme
        self._graph_panels: list = []    # [(fig, FigureCanvasTkAgg)] for live re-theme
        self._logo_photo = None          # Hold reference to prevent GC
        self._show_verification: bool = False  # auto-expand verification
        self._show_graph: bool = True          # auto-expand graph & analysis
        self._settings_visible: bool = False   # full-page settings open?
        self._solve_gen: int = 0               # generation counter — incremented on clear

        self._build_ui()
        self._sidebar = Sidebar(self)
        # Apply saved guest settings on startup (animation speed, display toggles)
        self._sidebar._apply_user_settings()
        self._show_welcome()

        # bind Enter
        self.bind("<Return>", lambda _: self._on_send())
        # Escape closes settings page first, otherwise sidebar
        self.bind("<Escape>", lambda _: self.close_settings_page()
              if self._settings_visible else self._sidebar.close())

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Main content wrapper ─────────────────────────────────────
        self._content = tk.Frame(self, bg=BG)
        self._content.pack(fill=tk.BOTH, expand=True)

        # header
        self._header = tk.Frame(self._content, bg=HEADER_BG, height=72)
        self._header.pack(fill=tk.X)
        self._header.pack_propagate(False)
        # hamburger menu button
        self._hamburger_font = tkfont.Font(family="Segoe UI", size=20)
        self._hamburger_btn = tk.Button(
            self._header, text="☰", font=self._hamburger_font,
            bg=HEADER_BG, fg=TEXT_DIM, activebackground=HEADER_BG,
            activeforeground=TEXT_BRIGHT, bd=0, padx=10, pady=0,
            cursor="hand2", relief=tk.FLAT,
            command=self._toggle_sidebar,
        )
        self._hamburger_btn.pack(side=tk.LEFT, padx=(14, 0))

        self._header_logo = self._load_header_logo()
        self._header_logo.pack(side=tk.LEFT, padx=(8, 20))

        # new chat button
        self._small_bold = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self._new_btn = tk.Button(
            self._header, text="+ New Chat", font=self._small_bold,
            bg=ACCENT, fg=TEXT_BRIGHT, activebackground=ACCENT_HOVER,
            activeforeground=TEXT_BRIGHT, bd=0, padx=16, pady=6,
            cursor="hand2", command=self._clear_chat,
        )
        self._new_btn.pack(side=tk.RIGHT, padx=(0, 20))

        # theme toggle button
        self._theme_btn = tk.Button(
            self._header, text="☀ Light", font=self._small,
            bg=HEADER_BG, fg=TEXT_DIM, activebackground=HEADER_BG,
            activeforeground=TEXT_BRIGHT, bd=0, padx=12, pady=6,
            cursor="hand2", relief=tk.FLAT, highlightthickness=1,
            highlightbackground=STEP_BORDER,
            command=self._toggle_theme,
        )
        self._theme_btn.pack(side=tk.RIGHT, padx=(0, 8))

        # chat area (canvas + scrollbar for widget embedding)
        self._chat_wrapper = tk.Frame(self._content, bg=BG)
        self._chat_wrapper.pack(fill=tk.BOTH, expand=True)

        # Custom scrollbar style
        self._sb_style_name = "Themed.Vertical.TScrollbar"
        self._style = ttk.Style()
        self._style.theme_use("default")
        self._update_scrollbar_style()

        self._canvas = tk.Canvas(self._chat_wrapper, bg=BG, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(
            self._chat_wrapper, orient=tk.VERTICAL, command=self._canvas.yview,
            style=self._sb_style_name,
        )
        self._chat_frame = tk.Frame(self._canvas, bg=BG)

        self._chat_frame.bind(
            "<Configure>",
            lambda _: self._update_scroll_region(),
        )
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._chat_frame, anchor="nw",
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # make inner frame stretch to canvas width
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        # mouse-wheel scrolling
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # input bar
        self._input_bar = tk.Frame(self._content, bg=BG_DARKER, pady=14)
        self._input_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self._input_inner = tk.Frame(self._input_bar, bg=INPUT_BG,
                                     highlightbackground=INPUT_BORDER,
                                     highlightthickness=1)
        self._input_inner.pack(fill=tk.X, padx=20)

        self._entry = tk.Entry(
            self._input_inner, font=self._mono, bg=INPUT_BG, fg=TEXT_BRIGHT,
            insertbackground=TEXT_BRIGHT, bd=0, relief=tk.FLAT,
            disabledbackground=INPUT_BG, disabledforeground="#666666",
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 6), pady=10)
        self._entry.focus_set()

        # Solve button — packed first so it lands at the farthest right
        self._action_frame = tk.Frame(self._input_inner, bg=INPUT_BG)
        self._action_frame.pack(side=tk.RIGHT, padx=(0, 8), pady=6)
        self._action_frame.pack_propagate(False)
        # Set a fixed size after the Solve button renders
        self.after(50, self._lock_action_frame_size)

        self._send_btn = tk.Button(
            self._action_frame, text="Solve ➤", font=self._bold,
            bg=ACCENT, fg=TEXT_BRIGHT, activebackground=ACCENT_HOVER,
            activeforeground=TEXT_BRIGHT, bd=0, padx=18, pady=6,
            cursor="hand2", command=self._on_send,
        )
        self._send_btn.pack(fill=tk.BOTH, expand=True)

        # Stop button — shown only during solving/animation
        self._stop_btn = tk.Button(
            self._action_frame, text="⏹", font=self._bold,
            bg="#3a1a1a", fg="#ff6b6b", activebackground="#4a2020",
            activeforeground="#ff9999", bd=0, padx=18, pady=6,
            cursor="hand2", relief=tk.FLAT,
            command=self._stop_solving,
        )
        # not packed yet — shown on demand

        # ── Symbol-pad toggle button (keyboard icon) ────────────────
        self._sympad_font = tkfont.Font(family="Segoe UI", size=16)
        self._sympad_btn = tk.Button(
            self._input_inner, text="\u2328", font=self._sympad_font,
            bg=INPUT_BG, fg=TEXT_DIM, activebackground=INPUT_BG,
            activeforeground=TEXT_BRIGHT, bd=0, padx=8, pady=4,
            cursor="hand2", relief=tk.FLAT,
            command=self._toggle_symbol_pad,
        )
        self._sympad_btn.pack(side=tk.RIGHT, padx=(0, 2), pady=6)
        self._symbol_pad_win: tk.Toplevel | None = None

    def _lock_action_frame_size(self) -> None:
        """Freeze the action frame to the Solve button's rendered size."""
        self._action_frame.update_idletasks()
        w = self._send_btn.winfo_reqwidth()
        h = self._send_btn.winfo_reqheight()
        self._action_frame.configure(width=w, height=h)

    # ── Symbol pad ──────────────────────────────────────────────────────

    _SYMBOL_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
        ("Trig / Functions", [
            ("sin()",  "sin("),
            ("cos()",  "cos("),
            ("tan()",  "tan("),
            ("log()",  "log("),
            ("ln()",   "ln("),
            ("√",      "√("),
        ]),
        ("Constants / Ops", [
            ("π",      "π"),
            ("^",      "^"),
            ("/",      "/"),
            ("·",      "*"),
            ("+",      "+"),
            ("−",      "-"),
        ]),
        ("Brackets", [
            ("( )",    "("),
            ("[ ]",    "["),
            ("{ }",    "{"),
            (")",      ")"),
            ("]",      "]"),
            ("}",      "}"),
        ]),
        ("Symbols", [
            ("=",      "="),
        ]),
    ]

    def _toggle_symbol_pad(self) -> None:
        """Show or hide the floating symbol pad above the input bar."""
        if self._symbol_pad_win and self._symbol_pad_win.winfo_exists():
            self._symbol_pad_win.destroy()
            self._symbol_pad_win = None
            return
        self._show_symbol_pad()

    def _show_symbol_pad(self) -> None:
        p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE
        pad = tk.Toplevel(self)
        pad.overrideredirect(True)
        pad.configure(bg=p["STEP_BORDER"])
        pad.attributes("-topmost", True)
        self._symbol_pad_win = pad

        inner = tk.Frame(pad, bg=p["BG_DARKER"], padx=10, pady=8)
        inner.pack(padx=1, pady=1)  # 1px border via outer bg

        btn_font = tkfont.Font(family="Consolas", size=13)
        lbl_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        for group_name, symbols in self._SYMBOL_GROUPS:
            tk.Label(inner, text=group_name, font=lbl_font,
                     bg=p["BG_DARKER"], fg=p["TEXT_DIM"],
                     anchor="w").pack(fill=tk.X, pady=(6, 2))
            row = tk.Frame(inner, bg=p["BG_DARKER"])
            row.pack(fill=tk.X)
            for display, insert_text in symbols:
                b = tk.Button(
                    row, text=display, font=btn_font, width=5,
                    bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
                    activebackground=p["ACCENT"], activeforeground="#ffffff",
                    bd=0, padx=4, pady=4, cursor="hand2", relief=tk.FLAT,
                    command=lambda t=insert_text: self._insert_symbol(t),
                )
                b.pack(side=tk.LEFT, padx=2, pady=2)

        # Position above the keyboard button
        self.update_idletasks()
        bx = self._sympad_btn.winfo_rootx()
        by = self._sympad_btn.winfo_rooty()
        pw = pad.winfo_reqwidth()
        ph = pad.winfo_reqheight()
        # Align right edge with button right, above the button
        x = bx + self._sympad_btn.winfo_width() - pw
        y = by - ph - 4
        # Keep on-screen
        if x < 0:
            x = bx
        pad.geometry(f"+{x}+{y}")

        # Close when clicking elsewhere
        pad.bind("<FocusOut>", lambda _: self._close_symbol_pad())
        pad.focus_set()

    def _close_symbol_pad(self) -> None:
        if self._symbol_pad_win and self._symbol_pad_win.winfo_exists():
            self._symbol_pad_win.destroy()
        self._symbol_pad_win = None

    def _insert_symbol(self, text: str) -> None:
        """Insert *text* into the equation entry at the current cursor position."""
        pos = self._entry.index(tk.INSERT)
        self._entry.insert(pos, text)
        self._entry.focus_set()

    # ── Canvas helpers ──────────────────────────────────────────────────

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self._canvas.itemconfig(self._canvas_window, width=event.width)
        self._update_scroll_region()

    def _update_scroll_region(self) -> None:
        """Update scroll region and show/hide scrollbar based on content."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._canvas.update_idletasks()
        content_h = self._chat_frame.winfo_reqheight()
        canvas_h = self._canvas.winfo_height()
        if content_h <= canvas_h:
            # Content fits — hide scrollbar and lock scroll position
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0.0)
            self._scroll_enabled = False
        else:
            # Content overflows — show scrollbar
            if not self._scrollbar.winfo_ismapped():
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self._scroll_enabled = True

    def _on_mousewheel(self, event: tk.Event) -> None:
        if getattr(self, '_scroll_enabled', False):
            self._canvas.yview_scroll(int(-event.delta / 120), "units")
            # Update auto-scroll based on whether we're at the bottom
            try:
                _, bottom = self._canvas.yview()
                self._auto_scroll = bottom >= 0.99
            except Exception:
                pass

    def _scroll_to_bottom(self) -> None:
        if getattr(self, '_instant_rendering', False):
            return  # suppress during instant-mode batch render
        if not self._auto_scroll:
            return
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── Theme ────────────────────────────────────────────────────────────

    def _update_scrollbar_style(self) -> None:
        p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE
        bg  = p["BG"]
        sbg = p["SCROLLBAR_BG"]
        sac = p["SCROLLBAR_ACT"]
        sar = p["SCROLLBAR_ARR"]
        self._style.configure(self._sb_style_name,
                              background=sbg, troughcolor=bg,
                              bordercolor=bg, arrowcolor=sar,
                              relief=tk.FLAT, borderwidth=0)
        self._style.map(self._sb_style_name,
                        background=[("active", sac), ("!active", sbg)],
                        arrowcolor=[("active", "#cccccc"), ("!active", sar)])
        self._style.layout(self._sb_style_name, [
            ("Vertical.Scrollbar.trough", {
                "sticky": "ns",
                "children": [
                    ("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
                ]
            })
        ])

    def _load_header_logo(self):
        """Load the theme-appropriate PNG logo for the header."""
        try:
            from PIL import Image, ImageTk
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
            fname = "darkmode-logo.png" if self._theme == "dark" else "lightmode-logo.png"
            path = os.path.normpath(os.path.join(base, fname))
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            img = Image.open(path)
            h = 48
            w = int(h * img.width / img.height)
            img = img.resize((w, h), Image.Resampling.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(img)
            return tk.Label(self._header, image=self._logo_photo, bg=HEADER_BG)
        except Exception as e:
            print(f"Could not load logo: {e}")
            return tk.Label(self._header, text="SymSolver", font=self._title,
                            bg=HEADER_BG, fg=ACCENT)

    def _refresh_header_logo(self):
        """Swap header logo image when theme changes."""
        p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE
        try:
            self._header_logo.pack_forget()
            self._header_logo.destroy()
        except Exception:
            pass
        self._header_logo = self._load_header_logo()
        self._header_logo.configure(bg=p["HEADER_BG"])
        self._header_logo.pack(side=tk.LEFT, padx=(8, 20))

    def _toggle_sidebar(self) -> None:
        """Open / close the sidebar."""
        self._sidebar.toggle()

    def _toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        self._refresh_header_logo()
        self._apply_theme()
        self._sidebar.refresh_theme()

    def _apply_theme(self) -> None:
        """Update global colour variables and re-style all static widgets."""
        import sys
        p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE
        mod = sys.modules[__name__]
        for k, v in p.items():
            if k in ("SCROLLBAR_BG", "SCROLLBAR_ACT", "SCROLLBAR_ARR"):
                continue
            setattr(mod, k, v)

        # header
        self._header.configure(bg=p["HEADER_BG"])
        self._header_logo.configure(bg=p["HEADER_BG"])
        self._hamburger_btn.configure(bg=p["HEADER_BG"], fg=p["TEXT_DIM"],
                                      activebackground=p["HEADER_BG"],
                                      activeforeground=p["TEXT_BRIGHT"])
        self._new_btn.configure(bg=p["ACCENT"], fg="#ffffff",
                                activebackground=p["ACCENT_HOVER"],
                                activeforeground="#ffffff")
        self._theme_btn.configure(
            text="🌙 Dark" if self._theme == "light" else "☀ Light",
            bg=p["HEADER_BG"], fg=p["TEXT_DIM"],
            activebackground=p["HEADER_BG"], activeforeground=p["TEXT_BRIGHT"],
            highlightbackground=p["STEP_BORDER"],
        )
        # canvas / chat area
        self.configure(bg=p["BG"])
        self._content.configure(bg=p["BG"])
        self._chat_wrapper.configure(bg=p["BG"])
        self._canvas.configure(bg=p["BG"])
        self._chat_frame.configure(bg=p["BG"])
        # input bar
        self._input_bar.configure(bg=p["BG_DARKER"])
        self._input_inner.configure(bg=p["INPUT_BG"],
                                    highlightbackground=p["INPUT_BORDER"])
        self._action_frame.configure(bg=p["INPUT_BG"])
        self._entry.configure(bg=p["INPUT_BG"], fg=p["TEXT_BRIGHT"],
                              insertbackground=p["TEXT_BRIGHT"],
                              disabledbackground=p["INPUT_BG"])
        self._send_btn.configure(bg=p["ACCENT"], fg="#ffffff",
                                 activebackground=p["ACCENT_HOVER"],
                                 activeforeground="#ffffff")
        self._sympad_btn.configure(bg=p["INPUT_BG"], fg=p["TEXT_DIM"],
                                   activebackground=p["INPUT_BG"],
                                   activeforeground=p["TEXT_BRIGHT"])
        # Close & re-open symbol pad so it picks up new colours
        if self._symbol_pad_win and self._symbol_pad_win.winfo_exists():
            self._close_symbol_pad()
        # scrollbar
        self._update_scrollbar_style()
        # graph palette
        try:
            from solver.graph import set_theme as _graph_set_theme
            _graph_set_theme(self._theme)
        except Exception:
            pass

        # re-colour all existing chat widgets
        self._retheme_chat(p)
        # re-colour all embedded matplotlib graphs
        self._retheme_graphs()

    def _retheme_graphs(self) -> None:
        """Re-colour every embedded matplotlib figure and its tk canvas widget."""
        try:
            from solver.graph import restyle_figure
        except Exception:
            return
        p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE
        for entry in self._graph_panels:
            try:
                fig, mpl_canvas, tk_widget = entry
                restyle_figure(fig, self._theme)
                mpl_canvas.draw()
                # Also translate the tk widget background
                tk_widget.configure(bg=p["STEP_BG"])
            except Exception:
                pass

    def _retheme_chat(self, p: dict) -> None:
        """Translate palette colours on every widget already inside the chat frame."""
        # Build old-hex → new-hex mapping.
        # If we just switched TO light, the widgets were painted with dark colours.
        # If we just switched TO dark, the widgets were painted with light colours.
        from_palette = _DARK_PALETTE if self._theme == "light" else _LIGHT_PALETTE
        trans = {}
        for key, new_val in p.items():
            old_val = from_palette.get(key)
            if old_val:
                trans[old_val.lower()] = new_val

        # Also translate case-badge colours (hardcoded, not in global palette)
        from_cases = _DARK_CASE_COLORS if self._theme == "light" else _LIGHT_CASE_COLORS
        to_cases   = _LIGHT_CASE_COLORS if self._theme == "light" else _DARK_CASE_COLORS
        for case_key in from_cases:
            for slot in ("bg", "border", "fg"):
                old_c = from_cases[case_key][slot]
                new_c = to_cases[case_key][slot]
                trans[old_c.lower()] = new_c

        _ATTRS = (
            "bg", "fg",
            "activebackground",
            "highlightbackground", "highlightcolor",
            "insertbackground",
        )

        def _norm(widget, raw) -> str:
            """Normalize any Tkinter color value to lowercase 6-digit hex.

            Tkinter on Windows may return colors as 12-digit strings like
            '#00000a0a0a0a' instead of '#0a0a0a', so we normalise through
            winfo_rgb() which always gives the 0-65535 component triplet.
            """
            try:
                r, g, b = widget.winfo_rgb(raw)
                return "#{:02x}{:02x}{:02x}".format(r >> 8, g >> 8, b >> 8)
            except Exception:
                return str(raw).lower().strip()

        def _walk(widget):
            try:
                cfg = widget.configure()
                patches = {}
                for attr in _ATTRS:
                    if attr in cfg:
                        norm = _norm(widget, widget.cget(attr))
                        new_val = trans.get(norm)
                        if new_val:
                            patches[attr] = new_val
                if patches:
                    widget.configure(**patches)
            except Exception:
                pass
            for child in widget.winfo_children():
                _walk(child)

        _walk(self._chat_frame)


    def _show_welcome(self) -> None:
        self._welcome_frame = tk.Frame(self._chat_frame, bg=BG)
        self._welcome_frame.pack(fill=tk.BOTH, expand=True, pady=(100, 50))

        tk.Label(
            self._welcome_frame, text="Welcome to SymSolver",
            font=self._title, bg=BG, fg=TEXT_BRIGHT,
        ).pack(pady=(8, 2))
        tk.Label(
            self._welcome_frame,
            text="Type a linear equation or system below and press Solve.",
            font=self._default, bg=BG, fg=TEXT_DIM,
        ).pack(pady=(0, 4))
        tk.Label(
            self._welcome_frame,
            text="Supports one or more variables  •  Separate systems with commas",
            font=self._small, bg=BG, fg=TEXT_DIM,
        ).pack(pady=(0, 20))

        tk.Label(
            self._welcome_frame, text="Try an example:",
            font=self._bold, bg=BG, fg=TEXT_DIM,
        ).pack(pady=(0, 6))

        examples = ["2x + 3 = 7", "x + y = 10, x - y = 2"]
        for eq in examples:
            btn = tk.Button(
                self._welcome_frame, text=eq, font=self._mono,
                bg=STEP_BG, fg=ACCENT, activebackground=ACCENT,
                activeforeground="#ffffff", bd=0, padx=20, pady=8,
                cursor="hand2",
                command=lambda e=eq: self._use_example(e),
            )
            btn.pack(pady=3)

    def _use_example(self, equation: str) -> None:
        self._entry.delete(0, tk.END)
        self._entry.insert(0, equation)
        self._on_send()

    # ── Clear / reset ───────────────────────────────────────────────────

    def _clear_chat(self) -> None:
        # Cancel any running animation
        self._anim_queue = []
        self._anim_idx = 0
        self._solve_gen += 1  # invalidate all pending after() callbacks
        self._auto_scroll = True
        self._graph_panels.clear()
        for w in self._chat_frame.winfo_children():
            w.destroy()
        self._show_welcome()
        self._canvas.yview_moveto(0.0)
        self._set_input_state(True)
        self._entry.focus_set()

    # ── Send equation ───────────────────────────────────────────────────

    def _on_send(self) -> None:
        equation = self._entry.get().strip()
        if not equation:
            return

        # Re-enable auto-scroll only for animated modes;
        # instant mode should never auto-scroll.
        if not (self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0):
            self._auto_scroll = True

        # remove welcome screen
        if hasattr(self, "_welcome_frame") and self._welcome_frame.winfo_exists():
            self._welcome_frame.destroy()

        self._entry.delete(0, tk.END)
        self._set_input_state(False)

        # show user bubble
        self._add_user_message(equation)

        # loading indicator
        loading_label = self._add_loading()

        # solve in background thread
        gen = self._solve_gen
        def _solve():
            try:
                result = solve_linear_equation(equation)
                self.after(0, lambda: self._show_result(result, loading_label)
                           if self._solve_gen == gen else None)
            except Exception as exc:
                msg = self._friendly_error(equation, exc)
                self.after(0, lambda: self._show_error(msg, loading_label)
                           if self._solve_gen == gen else None)

        threading.Thread(target=_solve, daemon=True).start()

    @staticmethod
    def _friendly_error(equation: str, exc: Exception) -> str:
        """Return a user-friendly error message for common mistakes."""
        msg = str(exc)
        # Already a clear ValueError from the solver — surface it cleanly.
        if isinstance(exc, ValueError):
            # Strip internal parser noise for parse errors
            if "Could not parse" in msg or "invalid syntax" in msg.lower():
                return (
                    f'Could not understand "{equation}".\n\n'
                    "Make sure your equation uses standard math notation.\n"
                    "Examples:  2x + 3 = 7  \u2022  as = 1  \u2022  x + y = 10, x - y = 2"
                )
            return msg
        # Generic fallback for unexpected failures.
        return (
            f'SymSolver could not process "{equation}".\n\n'
            "Supports linear equations with one or more variables,\n"
            "and systems separated by commas or semicolons.\n"
            "Examples:  2x + 3 = 7  \u2022  2x + 4y = 1  \u2022  x+y=10, x-y=2\n\n"
            f"Details: {msg}"
        )

    def _stop_solving(self) -> None:
        """Abort any running animation and re-enable input."""
        self._anim_queue = []
        self._anim_idx = 0
        self._solve_gen += 1  # invalidate pending callbacks
        self._set_input_state(True)
        self._entry.focus_set()

    def _set_input_state(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self._entry.configure(state=state)
        if enabled:
            # hide stop, show solve
            self._stop_btn.pack_forget()
            self._send_btn.pack(fill=tk.BOTH, expand=True)
        else:
            # In instant mode, skip showing stop button (solve is synchronous)
            if self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0:
                self._send_btn.pack_forget()
            else:
                # hide solve, show stop
                self._send_btn.pack_forget()
                self._stop_btn.pack(fill=tk.BOTH, expand=True)

    # ── Chat bubbles ────────────────────────────────────────────────────

    def _add_user_message(self, text: str) -> None:
        frame = tk.Frame(self._chat_frame, bg=USER_BG, padx=18, pady=14)
        frame.pack(fill=tk.X, padx=20, pady=(12, 4))
        tk.Label(frame, text="You", font=self._bold, bg=USER_BG, fg=ACCENT,
                 anchor="w").pack(fill=tk.X)
        tk.Label(frame, text=text, font=self._mono, bg=USER_BG, fg=TEXT_BRIGHT,
                 anchor="w").pack(fill=tk.X)
        if not (self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0):
            self._scroll_to_bottom()

    def _add_loading(self) -> tk.Label:
        label = tk.Label(
            self._chat_frame, text="  Processing…", font=self._default,
            bg=BG, fg=TEXT_DIM, anchor="w",
        )
        label.pack(fill=tk.X, padx=20, pady=6)
        if not (self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0):
            self._scroll_to_bottom()
        return label

    def _show_error(self, message: str, loading: tk.Label) -> None:
        loading.destroy()
        frame = tk.Frame(self._chat_frame, bg=BOT_BG, padx=18, pady=14)
        frame.pack(fill=tk.X, padx=20, pady=(4, 12))
        tk.Label(frame, text="⚠  Error", font=self._bold, bg=BOT_BG,
                 fg=ERROR, anchor="w").pack(fill=tk.X)
        tk.Label(frame, text=message, font=self._default, bg=BOT_BG,
                 fg=TEXT, anchor="w", wraplength=880, justify=tk.LEFT
                 ).pack(fill=tk.X, pady=(6, 0))
        self._set_input_state(True)
        self._entry.focus_set()
        if not (self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0):
            self._scroll_to_bottom()

    # ── Animation helpers ─────────────────────────────────────────────

    _TYPING_SPEED = 12          # ms per character
    _PHASE_PAUSE  = 1500        # pause after status label (ms)

    def _type_label(self, parent, full_text, font, bg, fg, anchor="w",
                    wraplength=880, justify=tk.LEFT, callback=None):
        """Create a label and type *full_text* into it character-by-character.
        When _TYPING_SPEED is 0 the full text appears instantly."""
        lbl = tk.Label(parent, text="", font=font, bg=bg, fg=fg,
                       anchor=anchor, wraplength=wraplength, justify=justify)
        lbl.pack(fill=tk.X)
        if self._TYPING_SPEED == 0:
            lbl.configure(text=full_text)
            self._scroll_to_bottom()
            if callback:
                callback()
        else:
            self._type_chars(lbl, full_text, 0, callback)

    def _type_chars(self, lbl, text, idx, callback):
        gen = self._solve_gen
        if idx <= len(text):
            lbl.configure(text=text[:idx])
            self._scroll_to_bottom()
            self.after(self._TYPING_SPEED,
                       lambda: self._type_chars(lbl, text, idx + 1, callback)
                       if self._solve_gen == gen else None)
        else:
            if callback:
                callback()

    def _show_status(self, parent, text, bg=None):
        """Show an italicised status line like 'Identifying Given...'
        When instant mode (_PHASE_PAUSE == 0) returns a hidden dummy
        label so callers can still call .destroy() safely."""
        if bg is None:
            bg = BOT_BG
        if self._PHASE_PAUSE == 0:
            # Instant mode — return a lightweight dummy with a no-op destroy()
            class _Dummy:
                def destroy(self): pass
                def winfo_exists(self): return False
            return _Dummy()
        status_font = tkfont.Font(family="Segoe UI", size=12, slant="italic")
        lbl = tk.Label(parent, text=text, font=status_font, bg=bg,
                       fg=TEXT_DIM, anchor="w")
        lbl.pack(fill=tk.X, pady=(6, 2))
        self._scroll_to_bottom()
        return lbl

    def _phase_then(self, status_lbl, callback):
        """Wait _PHASE_PAUSE ms then call *callback*.  If instant, call now.
        The callback is responsible for destroying *status_lbl*."""
        if self._PHASE_PAUSE == 0:
            callback()
        else:
            gen = self._solve_gen
            def _go():
                if self._solve_gen != gen:
                    return
                callback()
            self.after(self._PHASE_PAUSE, _go)

    def _step_verb(self, description: str) -> str:
        """Derive a contextual action word from a step description."""
        d = description.lower()
        if "subtract" in d:
            return "Subtracting..."
        if "add" in d:
            return "Adding..."
        if "divide" in d:
            return "Dividing..."
        if "multiply" in d:
            return "Multiplying..."
        if "expand" in d:
            return "Expanding..."
        if "combin" in d:
            return "Combining like terms..."
        if "simplif" in d:
            return "Simplifying..."
        if "substitut" in d:
            return "Substituting..."
        if "isolat" in d:
            return "Isolating variable..."
        if "original" in d or "start" in d:
            return "Writing equation..."
        if "answer" in d or "final" in d:
            return "Computing answer..."
        return "Processing..."

    # ── Animated result display ─────────────────────────────────────────

    def _show_result(self, result: dict, loading: tk.Label) -> None:
        loading.destroy()

        bot = tk.Frame(self._chat_frame, bg=BOT_BG, padx=18, pady=14)
        bot.pack(fill=tk.X, padx=20, pady=(4, 6))
        tk.Label(bot, text="SymSolver", font=self._bold, bg=BOT_BG,
                 fg=ACCENT, anchor="w").pack(fill=tk.X)

        # Build a sequential animation queue
        queue = []   # list of (callable,)  — each called in order

        # ── GIVEN ──────────────────────────────────────────────────────
        given = result.get("given", {})

        def _render_given():
            status = self._show_status(bot, "Identifying Given...")
            self._phase_then(status, lambda: self._animate_given(
                bot, given, result, status))

        queue.append(_render_given)

        # ── METHOD ─────────────────────────────────────────────────────
        method = result.get("method", {})

        def _render_method():
            status = self._show_status(bot, "Determining Approach...")
            self._phase_then(status, lambda: self._animate_method(
                bot, method, status))

        queue.append(_render_method)

        # ── STEPS ──────────────────────────────────────────────────────
        for step in result["steps"]:
            s = step  # capture

            def _render_step(s=s):
                verb = self._step_verb(s["description"])
                status = self._show_status(bot, verb)
                self._phase_then(status, lambda: self._animate_step(
                    bot, s, status))

            queue.append(_render_step)

        # ── FINAL ANSWER ───────────────────────────────────────────────
        _is_educational = result.get("nonlinear_education", False)

        def _render_answer():
            _status_text = (
                "Identifying equation type..."
                if _is_educational else "Finalizing answer..."
            )
            status = self._show_status(bot, _status_text)
            self._phase_then(status, lambda: self._animate_answer(
                bot, result["final_answer"], status,
                educational=_is_educational))

        queue.append(_render_answer)

        # ── VERIFICATION ───────────────────────────────────────────────
        if result.get("verification_steps"):
            v_steps = result["verification_steps"]

            def _render_verify():
                status = self._show_status(bot, "Verifying final answer...")
                self._phase_then(status, lambda: self._animate_verification(
                    bot, v_steps, status))

            queue.append(_render_verify)

        # ── GRAPH (skip for non-linear equations) ─────────────────────
        _method_name = result.get("method", {}).get("name", "")
        if "Linearity Check" not in _method_name:
            def _render_graph():
                self._animate_graph(bot, result)

            queue.append(_render_graph)

        # ── SUMMARY ────────────────────────────────────────────────────
        summary = result.get("summary", {})
        if summary:
            def _render_summary():
                status = self._show_status(bot, "Summarizing...")
                self._phase_then(status, lambda: self._animate_summary(
                    bot, summary, status))

            queue.append(_render_summary)

        # Final: re-enable input + record history
        _equation_text = result.get("equation", "")
        _answer_text = result.get("final_answer", "")

        def _finish():
            self._set_input_state(True)
            self._entry.focus_set()
            # Don't auto-scroll in instant mode — let user read from top
            if not (self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0):
                self._scroll_to_bottom()
            # Record to history if user is logged in
            self._sidebar.record_solve(_equation_text, _answer_text)

        queue.append(_finish)

        # Store queue and kick off
        self._anim_queue = queue
        self._anim_idx = 0
        self._steps_header_shown = False

        if self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0:
            # Instant mode: run entire queue synchronously, no scrolling
            self._instant_rendering = True
            while self._anim_idx < len(self._anim_queue):
                fn = self._anim_queue[self._anim_idx]
                self._anim_idx += 1
                fn()
            self._instant_rendering = False
            self._auto_scroll = False   # ensure nothing scrolls after render
            self.update_idletasks()
            # Do NOT auto-scroll — let user read from the top
        else:
            self._advance_queue()

    def _advance_queue(self):
        """Run the next item in the animation queue."""
        if self._anim_idx < len(self._anim_queue):
            fn = self._anim_queue[self._anim_idx]
            self._anim_idx += 1
            fn()
        # else: done

    def _schedule_next(self, delay_ms: int = 400):
        """Schedule the next queue item after a short pause.
        In instant mode the queue is driven by the sync loop in
        _show_result, so this is a no-op."""
        if getattr(self, '_instant_rendering', False):
            return  # sync loop handles advancement
        gen = self._solve_gen
        def _go():
            if self._solve_gen != gen:
                return  # chat was cleared — discard
            self._advance_queue()
        if self._PHASE_PAUSE == 0:
            self.after(0, _go)
        else:
            self.after(delay_ms, _go)

    # ── Individual animated section builders ────────────────────────────

    def _animate_given(self, parent, given, result, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "GIVEN", "✎")
        given_frame = self._make_card(parent, STEP_BG)
        problem_text = given.get("problem", result["equation"])
        inputs = given.get("inputs", {})
        input_lines = [f"  {k.replace('_', ' ').title()}:  {v}" for k, v in inputs.items()]

        def _after_problem():
            self._type_input_lines(given_frame, input_lines, 0)

        # Route through fraction-aware renderer if needed, else type animated
        if self._FRAC_RE.search(problem_text):
            w = self._render_math_expr(given_frame, problem_text,
                                       font=self._default,
                                       bg=STEP_BG, fg=TEXT_BRIGHT)
            w.pack(anchor="w")
            _after_problem()
        else:
            self._type_label(given_frame, problem_text, self._default,
                             STEP_BG, TEXT_BRIGHT, callback=_after_problem)

    def _type_input_lines(self, parent, lines, idx):
        if idx < len(lines):
            line = lines[idx]
            def _next(): self._type_input_lines(parent, lines, idx + 1)
            if self._FRAC_RE.search(line):
                w = self._render_math_expr(parent, line,
                                           font=self._small,
                                           bg=STEP_BG, fg=TEXT_DIM)
                w.pack(anchor="w")
                _next()
            else:
                self._type_label(parent, line, self._small, STEP_BG, TEXT_DIM,
                                 callback=_next)
        else:
            self._scroll_to_bottom()
            self._schedule_next()

    def _animate_method(self, parent, method, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "METHOD", "⚙")
        method_frame = self._make_card(parent, STEP_BG)
        name = method.get("name", "Algebraic Isolation")
        desc = method.get("description", "")
        params = method.get("parameters", {})
        param_lines = [f"  {k.replace('_', ' ').title()}:  {v}" for k, v in params.items()]

        def _after_name():
            if desc:
                self._type_label(method_frame, desc, self._small, STEP_BG, TEXT_DIM,
                                 wraplength=880, callback=_after_desc)
            else:
                _after_desc()

        def _after_desc():
            self._type_input_lines(method_frame, param_lines, 0)

        self._type_label(method_frame, name, self._bold, STEP_BG, ACCENT,
                         callback=_after_name)

    def _animate_step(self, parent, step, status_lbl):
        status_lbl.destroy()

        # Show STEPS header once (before the first step)
        if not getattr(self, '_steps_header_shown', False):
            self._steps_header_shown = True
            self._render_section_header(parent, "STEPS", "»")

        wrapper = tk.Frame(parent, bg=STEP_BORDER, padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=4)
        card = tk.Frame(wrapper, bg=STEP_BG, padx=14, pady=10)
        card.pack(fill=tk.X)

        step_num = step.get("step_number")
        desc = step["description"]
        if step_num is not None:
            desc = f"Step {step_num}:  {desc}"

        expr_text = step["expression"]
        expl_text = step.get("explanation", "")

        def _after_desc():
            # Show expression — use stacked fractions if markers present
            if self._FRAC_RE.search(expr_text):
                w = self._render_math_expr(card, expr_text,
                                           font=self._mono,
                                           bg=STEP_BG, fg=ACCENT)
                w.pack(anchor="w", pady=(2, 0))
                _after_expr()
            else:
                self._type_label(card, expr_text, self._mono, STEP_BG, ACCENT,
                                 callback=_after_expr)

        def _after_expr():
            if expl_text:
                self._animate_explanation(card, expl_text, _done)
            else:
                _done()

        def _done():
            self._scroll_to_bottom()
            self._schedule_next()

        self._type_label(card, desc, self._bold, STEP_BG, TEXT_BRIGHT,
                         callback=_after_desc)

    def _animate_explanation(self, card, expl_text, callback):
        """Type an explanation and add the collapsible toggle."""
        toggle_frame = tk.Frame(card, bg=STEP_BG)
        toggle_frame.pack(fill=tk.X, pady=(4, 0))

        content = tk.Frame(card, bg=STEP_BG)
        content.pack(fill=tk.X, pady=(2, 0))

        def _after_typed():
            visible = tk.BooleanVar(value=True)

            def _toggle(v=visible, c=content, b=None):
                if v.get():
                    c.pack_forget()
                    v.set(False)
                    b.configure(text="▸ Show Explanation")
                else:
                    c.pack(fill=tk.X, pady=(2, 0))
                    v.set(True)
                    b.configure(text="▾ Hide Explanation")

            btn = tk.Button(
                toggle_frame, text="▾ Hide Explanation", font=self._small,
                bg=STEP_BORDER, fg=ACCENT, activebackground=STEP_BG,
                activeforeground=ACCENT_HOVER, bd=0, cursor="hand2",
                anchor="w", padx=10, pady=4,
                relief=tk.FLAT, highlightthickness=1,
                highlightbackground=STEP_BORDER, highlightcolor=ACCENT,
            )
            btn.configure(command=lambda b=btn: _toggle(b=b))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=STEP_BG, fg=ACCENT_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=STEP_BORDER, fg=ACCENT))
            btn.pack(anchor="w", pady=(2, 0))
            if callback:
                callback()

        self._type_label(content, expl_text, self._small, STEP_BG, TEXT_DIM,
                         wraplength=840, callback=_after_typed)

    def _animate_answer(self, parent, final_answer, status_lbl,
                        educational: bool = False):
        status_lbl.destroy()
        if educational:
            # Amber-toned header and box for educational / not-linear results
            _border = "#c87800" if self._theme == "dark" else "#c86400"
            _inner_bg = "#1a1000" if self._theme == "dark" else "#fff8e1"
            _text_fg = "#ffc048" if self._theme == "dark" else "#7a3c00"
            self._render_section_header_colored(
                parent, "LINEARITY NOTE", "⚠", fg=_border)
            ans_frame = tk.Frame(parent, bg=_border, padx=1, pady=1)
            ans_frame.pack(fill=tk.X, pady=(2, 4))
            ans_inner = tk.Frame(ans_frame, bg=_inner_bg, padx=16, pady=12)
            ans_inner.pack(fill=tk.X)
            lines = final_answer.split("\n")
            self._type_answer_lines(ans_inner, lines, 0, bg=_inner_bg, fg=_text_fg)
        else:
            self._render_section_header(parent, "FINAL ANSWER", "✓")
            ans_frame = tk.Frame(parent, bg=SUCCESS, padx=1, pady=1)
            ans_frame.pack(fill=tk.X, pady=(2, 4))
            ans_inner = tk.Frame(ans_frame, bg=VERIFY_BG, padx=16, pady=12)
            ans_inner.pack(fill=tk.X)
            lines = final_answer.split("\n")
            self._type_answer_lines(ans_inner, lines, 0)

    def _type_answer_lines(self, parent, lines, idx,
                           bg=None, fg=None):
        _bg = bg if bg is not None else VERIFY_BG
        _fg = fg if fg is not None else TEXT_BRIGHT
        if idx < len(lines):
            line_text = lines[idx]
            # If line contains fraction markers, render as math expression
            if '⟦' in line_text and '⟧' in line_text:
                self._render_math_expr(parent, line_text, self._small, _bg, _fg)
                self._scroll_to_bottom()
                if self._TYPING_SPEED == 0:
                    self._type_answer_lines(parent, lines, idx + 1, bg=bg, fg=fg)
                else:
                    self.after(30, lambda: self._type_answer_lines(
                        parent, lines, idx + 1, bg=bg, fg=fg))
            else:
                self._type_label(parent, line_text, self._small, _bg, _fg,
                                 callback=lambda: self._type_answer_lines(
                                     parent, lines, idx + 1, bg=bg, fg=fg))
        else:
            self._scroll_to_bottom()
            self._schedule_next()

    def _animate_verification(self, parent, v_steps, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "VERIFICATION", "≡")

        container = tk.Frame(parent, bg=BOT_BG)
        container.pack(fill=tk.X, pady=(8, 0))

        content = tk.Frame(container, bg=VERIFY_BG, padx=14, pady=10)
        animated = {"done": False}

        # Respect auto-expand setting
        _auto_expand = self._show_verification
        visible = tk.BooleanVar(value=_auto_expand)

        def _toggle(v=visible, c=content, b=None):
            if v.get():
                c.pack_forget()
                v.set(False)
                b.configure(text="▸ Show Verification")
            else:
                c.pack(fill=tk.X)
                v.set(True)
                b.configure(text="▾ Hide Verification")
                # Animate only on first open
                if not animated["done"]:
                    animated["done"] = True
                    self._type_verify_steps(c, v_steps, 0)

        _init_text = "▾ Hide Verification" if _auto_expand else "▸ Show Verification"
        btn = tk.Button(
            container, text=_init_text, font=self._bold,
            bg=BOT_BG, fg=SUCCESS, activebackground=BOT_BG,
            activeforeground=SUCCESS, bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

        # If auto-expand, show content and animate immediately
        if _auto_expand:
            content.pack(fill=tk.X)
            animated["done"] = True
            self._type_verify_steps(content, v_steps, 0)

        # Move to next queue item immediately (verification is lazy)
        self._schedule_next()

    def _type_verify_steps(self, parent, steps, idx):
        if idx < len(steps):
            step = steps[idx]

            wrapper = tk.Frame(parent, bg=STEP_BORDER, padx=1, pady=1)
            wrapper.pack(fill=tk.X, pady=4)
            card = tk.Frame(wrapper, bg=STEP_BG, padx=14, pady=10)
            card.pack(fill=tk.X)

            step_num = step.get("step_number")
            desc = step["description"]
            if step_num is not None:
                desc = f"Step {step_num}:  {desc}"

            expr_text = step["expression"]
            expl_text = step.get("explanation", "")

            def _after_desc():
                if self._FRAC_RE.search(expr_text):
                    w = self._render_math_expr(card, expr_text,
                                               font=self._mono,
                                               bg=STEP_BG, fg=ACCENT)
                    w.pack(anchor="w", pady=(2, 0))
                    _after_expr()
                else:
                    self._type_label(card, expr_text, self._mono, STEP_BG, ACCENT,
                                     callback=_after_expr)

            def _after_expr():
                if expl_text:
                    self._animate_explanation(card, expl_text, _next)
                else:
                    _next()

            def _next():
                self._scroll_to_bottom()
                if self._PHASE_PAUSE == 0:
                    self._type_verify_steps(parent, steps, idx + 1)
                else:
                    gen = self._solve_gen
                    self.after(self._PHASE_PAUSE,
                               lambda: self._type_verify_steps(parent, steps, idx + 1)
                               if self._solve_gen == gen else None)

            self._type_label(card, desc, self._bold, STEP_BG, TEXT_BRIGHT,
                             callback=_after_desc)
        else:
            self._scroll_to_bottom()

    def _animate_summary(self, parent, summary, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "SUMMARY", "■")
        sum_frame = self._make_card(parent, STEP_BG)
        details = [
            ("Runtime", f"{summary.get('runtime_ms', '?')} ms"),
            ("Steps", str(summary.get('total_steps', '?'))),
            ("Verification Steps", str(summary.get('verification_steps', '?'))),
            ("Timestamp", summary.get('timestamp', '?')),
            ("Library", summary.get('library', '?')),
        ]
        self._type_summary_rows(sum_frame, details, 0)

    def _type_summary_rows(self, parent, details, idx):
        if idx < len(details):
            label, value = details[idx]
            row = tk.Frame(parent, bg=STEP_BG)
            row.pack(fill=tk.X, pady=1)
            full_text = f"  {label}:  {value}"
            lbl = tk.Label(row, text="", font=self._small,
                           bg=STEP_BG, fg=TEXT_DIM, anchor="w")
            lbl.pack(side=tk.LEFT)
            self._type_chars(lbl, full_text, 0,
                             lambda: self._type_summary_rows(parent, details, idx + 1))
        else:
            self._scroll_to_bottom()
            self._schedule_next()

    # ── Section header helpers ──────────────────────────────────────────

    def _render_section_header(self, parent: tk.Frame, title: str, icon: str = "") -> None:
        header = tk.Frame(parent, bg=BOT_BG)
        header.pack(fill=tk.X, pady=(14, 4))
        label_text = f"{icon}  {title}" if icon else title
        tk.Label(header, text=label_text, font=self._bold,
                 bg=BOT_BG, fg=ACCENT, anchor="w").pack(fill=tk.X)
        # thin accent line
        tk.Frame(header, bg=ACCENT, height=1).pack(fill=tk.X, pady=(2, 0))

    def _render_section_header_colored(self, parent: tk.Frame, title: str,
                                       icon: str = "", fg: str = "") -> None:
        """Like _render_section_header but with a custom foreground/accent colour."""
        _fg = fg or ACCENT
        header = tk.Frame(parent, bg=BOT_BG)
        header.pack(fill=tk.X, pady=(14, 4))
        label_text = f"{icon}  {title}" if icon else title
        tk.Label(header, text=label_text, font=self._bold,
                 bg=BOT_BG, fg=_fg, anchor="w").pack(fill=tk.X)
        tk.Frame(header, bg=_fg, height=1).pack(fill=tk.X, pady=(2, 0))

    def _make_card(self, parent: tk.Frame, bg: str) -> tk.Frame:
        wrapper = tk.Frame(parent, bg=STEP_BORDER, padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=4)
        card = tk.Frame(wrapper, bg=bg, padx=14, pady=10)
        card.pack(fill=tk.X)
        return card

    # ── Fraction-aware math expression renderer ───────────────────────

    # Pattern to split on fraction markers ⟦numerator|denominator⟧
    _FRAC_RE = re.compile(r'⟦([^|⟧]+)\|([^⟧]+)⟧')

    def _render_math_expr(self, parent: tk.Frame, text: str,
                          font=None, bg: str = STEP_BG,
                          fg: str = "#0F4C75") -> tk.Frame:
        """Render *text* inside *parent*, replacing ⟦num|den⟧ markers
        with stacked vertical fraction widgets.  Returns the container."""
        if font is None:
            font = self._mono

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.X)  # Pack the container so it's actually visible!

        # Handle multi-line expressions (e.g. system of equations)
        lines = text.split("\n")
        for line_text in lines:
            line_frame = tk.Frame(container, bg=bg)
            line_frame.pack(anchor="w")

            parts = self._FRAC_RE.split(line_text)
            # parts = [text, num, den, text, num, den, ...]
            idx = 0
            while idx < len(parts):
                if idx % 3 == 0:
                    # Regular text segment
                    seg = parts[idx]
                    if seg:
                        tk.Label(line_frame, text=seg, font=font,
                                 bg=bg, fg=fg).pack(side=tk.LEFT)
                elif idx % 3 == 1:
                    # Numerator (idx) and denominator (idx+1)
                    num = parts[idx]
                    den = parts[idx + 1] if idx + 1 < len(parts) else ""
                    self._make_fraction_widget(line_frame, num, den, bg, fg)
                    idx += 1  # skip denominator (consumed here)
                idx += 1

        return container

    def _make_fraction_widget(self, parent: tk.Frame,
                              numerator: str, denominator: str,
                              bg: str, fg: str) -> None:
        """Build a stacked fraction: numerator / line / denominator."""
        frac_frame = tk.Frame(parent, bg=bg)
        frac_frame.pack(side=tk.LEFT, padx=2)

        tk.Label(frac_frame, text=numerator.strip(), font=self._frac,
                 bg=bg, fg=fg).pack()
        # fraction bar
        bar = tk.Frame(frac_frame, bg=fg, height=2)
        bar.pack(fill=tk.X, padx=2, pady=1)
        tk.Label(frac_frame, text=denominator.strip(), font=self._frac,
                 bg=bg, fg=fg).pack()

    # ── Graph section ──────────────────────────────────────────────────

    def _type_analysis_items(self, card, card_bg, items, idx, callback):
        """Type analysis card fields one at a time, letter-by-letter."""
        if idx >= len(items):
            self._scroll_to_bottom()
            if callback:
                callback()
            return

        kind, text, color = items[idx]

        def _next():
            self._type_analysis_items(card, card_bg, items, idx + 1, callback)

        if kind == "sep":
            tk.Frame(card, bg=color, height=1).pack(fill=tk.X, pady=(8, 6))
            _next()
        elif kind == "math":
            # Render mathematical expressions with fraction support
            self._render_math_expr(card, text, self._bold, card_bg, color)
            self._scroll_to_bottom()
            if self._TYPING_SPEED == 0:
                _next()
            else:
                self.after(30, _next)
        elif kind == "bold":
            self._type_label(card, text, self._bold, card_bg, color, callback=_next)
        elif kind == "small":
            self._type_label(card, text, self._small, card_bg, color, callback=_next)
        elif kind == "mono":
            self._type_label(card, text, self._mono, card_bg, color, callback=_next)

    # ── Case badge colours ──────────────────────────────────────────────
    def _get_case_colors(self):
        """Return case-label color dict for the current theme."""
        return _LIGHT_CASE_COLORS if self._theme == "light" else _DARK_CASE_COLORS

    def _animate_graph(self, parent, result):
        """Collapsible Graph & Analysis panel — graph on top, analysis card below."""
        # Analyse — always attempt; sets analysis card data
        try:
            from solver.graph import analyze_result
            analysis = analyze_result(result)
        except Exception:
            analysis = None

        # Build figure — attempt independently so a graph error doesn't hide the card
        try:
            from solver.graph import build_figure
            fig = build_figure(result)
        except Exception:
            fig = None

        if analysis is None and fig is None:
            self._schedule_next()
            return

        self._render_section_header(parent, "GRAPH & ANALYSIS", "Δ")

        container = tk.Frame(parent, bg=BOT_BG)
        container.pack(fill=tk.X, pady=(4, 0))

        # The single toggleable content panel
        content = tk.Frame(container, bg=STEP_BG)
        drawn   = {"done": False}
        _auto_expand = self._show_graph
        visible = tk.BooleanVar(value=_auto_expand)

        def _build_content(c=content, cb=None):
            if drawn["done"]:
                return
            drawn["done"] = True

            # ── Graph (top) — rendered immediately ────────────────────
            if fig is not None:
                try:
                    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    canvas = FigureCanvasTkAgg(fig, master=c)
                    canvas.draw()
                    widget = canvas.get_tk_widget()
                    widget.configure(bg=STEP_BG, highlightthickness=0)
                    widget.pack(fill=tk.X, padx=2, pady=(8, 4))
                    self._graph_panels.append((fig, canvas, widget))
                except Exception as exc:
                    tk.Label(c, text=f"Graph error: {exc}", font=self._small,
                             bg=STEP_BG, fg=ERROR, anchor="w").pack(fill=tk.X, padx=8)

            # ── Analysis card (below graph) — typed letter by letter ───
            if analysis is None:
                if cb:
                    cb()
                return

            colors = self._get_case_colors().get(
                analysis.get("case", ""),
                {"bg": STEP_BG, "border": ACCENT, "fg": ACCENT},
            )
            card_bg     = colors["bg"]
            card_border = colors["border"]
            card_fg     = colors["fg"]

            outer = tk.Frame(c, bg=card_border, padx=1, pady=1)
            outer.pack(fill=tk.X, padx=2, pady=(4, 8))
            card = tk.Frame(outer, bg=card_bg, padx=16, pady=12)
            card.pack(fill=tk.X)

            # Build ordered list of items to animate
            items = [("bold", analysis["case_label"], card_fg)]
            items.append(("small", "General form:", TEXT_DIM))
            for line in analysis["form"].split("\n"):
                items.append(("mono", f"  {line}", TEXT_BRIGHT))
            items.append(("sep", None, card_border))
            for line in analysis["description"].split("\n"):
                items.append(("small", line, TEXT_DIM))
            if analysis.get("detail"):
                items.append(("mono", f"\n  Condition:  {analysis['detail']}", TEXT_DIM))
            if analysis.get("solution"):
                items.append(("sep", None, card_border))
                items.append(("math", f"Result:  {analysis['solution']}", card_fg))

            self._type_analysis_items(card, card_bg, items, 0, cb)

        def _toggle(v=visible, c=content, b=None):
            if v.get():
                c.pack_forget()
                v.set(False)
                b.configure(text="\u25b8 Show Graph & Analysis")
            else:
                c.pack(fill=tk.X)
                v.set(True)
                b.configure(text="\u25be Hide Graph & Analysis")
                _build_content(c)

        _init_graph_text = "\u25be Hide Graph & Analysis" if _auto_expand else "\u25b8 Show Graph & Analysis"
        btn = tk.Button(
            container, text=_init_graph_text, font=self._bold,
            bg=BOT_BG, fg=SUCCESS, activebackground=BOT_BG,
            activeforeground=SUCCESS, bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

        if _auto_expand:
            # Show content immediately; animation chain drives _schedule_next
            content.pack(fill=tk.X)
            _build_content(cb=self._schedule_next)
        else:
            self._schedule_next()

    # ── Step renderer ───────────────────────────────────────────────────
    # (kept for potential non-animated use; main flow uses _animate_step)

    # ── Full-page Settings ──────────────────────────────────────────────

    def show_settings_page(self) -> None:
        """Replace chat content with a full-page settings view."""
        from gui.storage import get_settings, save_settings

        # If already visible, destroy current page first (prevents duplicates)
        if hasattr(self, '_settings_frame') and self._settings_frame.winfo_exists():
            self._settings_frame.destroy()

        if not self._settings_visible:
            # Hide chat + input only once when entering settings mode
            self._chat_wrapper.pack_forget()
            self._input_bar.pack_forget()
            self._settings_visible = True
            # Hide header buttons while settings page is open
            self._theme_btn.pack_forget()
            self._new_btn.pack_forget()

        p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE

        # Build settings frame
        self._settings_frame = tk.Frame(self._content, bg=p["BG"])
        self._settings_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollable inner
        settings_canvas = tk.Canvas(self._settings_frame, bg=p["BG"],
                                    highlightthickness=0)
        settings_sb = ttk.Scrollbar(self._settings_frame, orient=tk.VERTICAL,
                                    command=settings_canvas.yview,
                                    style=self._sb_style_name)
        settings_inner = tk.Frame(settings_canvas, bg=p["BG"])
        settings_canvas.create_window((0, 0), window=settings_inner, anchor="nw",
                                      tags="settings_inner")
        settings_canvas.configure(yscrollcommand=settings_sb.set)
        settings_sb.pack(side=tk.RIGHT, fill=tk.Y)
        settings_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _update_settings_scroll(_=None):
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
            # Show/hide scrollbar based on content height
            settings_canvas.update_idletasks()
            content_h = settings_inner.winfo_reqheight()
            canvas_h = settings_canvas.winfo_height()
            if content_h <= canvas_h:
                settings_sb.pack_forget()
            elif not settings_sb.winfo_ismapped():
                settings_sb.pack(side=tk.RIGHT, fill=tk.Y)

        settings_inner.bind("<Configure>", _update_settings_scroll)
        settings_canvas.bind(
            "<Configure>",
            lambda e: (settings_canvas.itemconfig("settings_inner", width=e.width),
                       _update_settings_scroll()))

        # Store ref so we can unbind on close
        self._settings_canvas = settings_canvas

        def _settings_mousewheel(e):
            if settings_canvas.winfo_exists():
                settings_canvas.yview_scroll(int(-e.delta / 120), "units")

        self._settings_scroll_id = settings_canvas.bind_all(
            "<MouseWheel>", _settings_mousewheel)

        user_key = self._sidebar.current_user if hasattr(self, '_sidebar') else None
        settings = get_settings(user_key)

        # Centered container
        center = tk.Frame(settings_inner, bg=p["BG"])
        center.pack(anchor="n", pady=(40, 40), padx=60, fill=tk.X)

        # ── Header row with back button ────────────────────────────────
        header_row = tk.Frame(center, bg=p["BG"])
        header_row.pack(fill=tk.X, pady=(0, 20))

        back_font = tkfont.Font(family="Segoe UI", size=18)
        tk.Button(header_row, text="←", font=back_font,
                  bg=p["BG"], fg=p["TEXT_DIM"],
                  activebackground=p["BG"], activeforeground=p["TEXT_BRIGHT"],
                  bd=0, cursor="hand2", command=self.close_settings_page
                  ).pack(side=tk.LEFT)

        title_font = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        tk.Label(header_row, text="Settings", font=title_font,
                 bg=p["BG"], fg=p["TEXT_BRIGHT"]).pack(side=tk.LEFT, padx=(12, 0))

        # ── Card container ─────────────────────────────────────────────
        card_outer = tk.Frame(center, bg=p["STEP_BORDER"], padx=1, pady=1)
        card_outer.pack(fill=tk.X)
        card = tk.Frame(card_outer, bg=p["STEP_BG"], padx=30, pady=24)
        card.pack(fill=tk.X)

        section_font = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        label_font   = tkfont.Font(family="Segoe UI", size=13)
        small_font   = tkfont.Font(family="Segoe UI", size=11)

        # ── Theme ──────────────────────────────────────────────────────
        tk.Label(card, text="Appearance", font=section_font,
                 bg=p["STEP_BG"], fg=p["ACCENT"]).pack(anchor="w", pady=(0, 8))

        theme_var = tk.StringVar(value=self._theme)
        theme_frame = tk.Frame(card, bg=p["STEP_BG"])
        theme_frame.pack(fill=tk.X, pady=(0, 6))

        for val, label_text in [("dark", "🌙  Dark Mode"), ("light", "☀  Light Mode")]:
            rb_border = tk.Frame(theme_frame, bg=p["INPUT_BORDER"],
                                 highlightbackground=p["INPUT_BORDER"],
                                 highlightthickness=1, bd=0)
            rb_border.pack(fill=tk.X, pady=3)
            rb_inner = tk.Frame(rb_border, bg=p["STEP_BG"], padx=8, pady=5)
            rb_inner.pack(fill=tk.X)
            rb = tk.Radiobutton(
                rb_inner, text=label_text, variable=theme_var, value=val,
                font=label_font, bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
                selectcolor=p["BG"], activebackground=p["STEP_BG"],
                activeforeground=p["ACCENT"],
                highlightthickness=0, bd=0, cursor="hand2",
            )
            rb.pack(anchor="w")

        # Divider
        tk.Frame(card, bg=p["TEXT_DIM"], height=1).pack(fill=tk.X, pady=(12, 12))

        # ── Animation Speed ────────────────────────────────────────────
        tk.Label(card, text="Animation Speed", font=section_font,
                 bg=p["STEP_BG"], fg=p["ACCENT"]).pack(anchor="w", pady=(0, 8))

        speed_var = tk.StringVar(value=settings.get("animation_speed", "normal"))
        speed_frame = tk.Frame(card, bg=p["STEP_BG"])
        speed_frame.pack(fill=tk.X, pady=(0, 6))

        for val, label_text in [("slow", "🐢  Slow"), ("normal", "⚡  Normal"),
                                ("fast", "🚀  Fast"), ("instant", "⏭  Instant")]:
            rb_border = tk.Frame(speed_frame, bg=p["INPUT_BORDER"],
                                 highlightbackground=p["INPUT_BORDER"],
                                 highlightthickness=1, bd=0)
            rb_border.pack(fill=tk.X, pady=3)
            rb_inner = tk.Frame(rb_border, bg=p["STEP_BG"], padx=8, pady=5)
            rb_inner.pack(fill=tk.X)
            rb = tk.Radiobutton(
                rb_inner, text=label_text, variable=speed_var, value=val,
                font=label_font, bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
                selectcolor=p["BG"], activebackground=p["STEP_BG"],
                activeforeground=p["ACCENT"],
                highlightthickness=0, bd=0, cursor="hand2",
            )
            rb.pack(anchor="w")

        # Divider
        tk.Frame(card, bg=p["TEXT_DIM"], height=1).pack(fill=tk.X, pady=(12, 12))

        # ── Display Options ────────────────────────────────────────────
        tk.Label(card, text="Display", font=section_font,
                 bg=p["STEP_BG"], fg=p["ACCENT"]).pack(anchor="w", pady=(0, 8))

        verify_var = tk.BooleanVar(value=settings.get("show_verification", False))
        cb1_border = tk.Frame(card, bg=p["INPUT_BORDER"],
                              highlightbackground=p["INPUT_BORDER"],
                              highlightthickness=1, bd=0)
        cb1_border.pack(fill=tk.X, pady=3)
        cb1_inner = tk.Frame(cb1_border, bg=p["STEP_BG"], padx=8, pady=5)
        cb1_inner.pack(fill=tk.X)
        tk.Checkbutton(
            cb1_inner, text="  Auto-expand verification section", variable=verify_var,
            font=label_font, bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
            selectcolor=p["BG"], activebackground=p["STEP_BG"],
            activeforeground=p["ACCENT"],
            highlightthickness=0, bd=0, cursor="hand2",
        ).pack(anchor="w")

        graph_var = tk.BooleanVar(value=settings.get("show_graph", True))
        cb2_border = tk.Frame(card, bg=p["INPUT_BORDER"],
                              highlightbackground=p["INPUT_BORDER"],
                              highlightthickness=1, bd=0)
        cb2_border.pack(fill=tk.X, pady=3)
        cb2_inner = tk.Frame(cb2_border, bg=p["STEP_BG"], padx=8, pady=5)
        cb2_inner.pack(fill=tk.X)
        tk.Checkbutton(
            cb2_inner, text="  Auto-expand graph & analysis", variable=graph_var,
            font=label_font, bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
            selectcolor=p["BG"], activebackground=p["STEP_BG"],
            activeforeground=p["ACCENT"],
            highlightthickness=0, bd=0, cursor="hand2",
        ).pack(anchor="w")

        # ── Save button + message ──────────────────────────────────────
        bottom = tk.Frame(card, bg=p["STEP_BG"])
        bottom.pack(fill=tk.X, pady=(20, 0))

        msg_label = tk.Label(bottom, text="", font=small_font,
                             bg=p["STEP_BG"], fg=p["SUCCESS"])
        msg_label.pack(anchor="w", pady=(0, 8))

        def _save():
            new_settings = {
                "theme": theme_var.get(),
                "animation_speed": speed_var.get(),
                "show_verification": verify_var.get(),
                "show_graph": graph_var.get(),
            }
            save_settings(new_settings, user_key)
            self._sidebar._apply_settings_to_app(new_settings)
            msg_label.configure(text="✓  Settings saved!", fg=p["SUCCESS"])
            # If theme changed, rebuild the settings page with new colours
            new_p = _DARK_PALETTE if self._theme == "dark" else _LIGHT_PALETTE
            if new_p != p:
                # Preserve scroll position across rebuild
                self._settings_scroll_pos = settings_canvas.yview()[0]
                self.after(50, self._rebuild_settings_with_scroll)
            else:
                self.after(2000, lambda: msg_label.configure(text="") if msg_label.winfo_exists() else None)

        save_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        tk.Button(bottom, text="Save Settings", font=save_font,
                  bg=p["ACCENT"], fg="#ffffff",
                  activebackground=p["ACCENT_HOVER"],
                  activeforeground="#ffffff",
                  bd=0, padx=24, pady=10, cursor="hand2",
                  command=_save).pack(fill=tk.X)

    def _rebuild_settings_with_scroll(self) -> None:
        """Rebuild settings page and restore saved scroll position."""
        saved = getattr(self, '_settings_scroll_pos', None)
        self.show_settings_page()
        if saved is not None:
            def _restore():
                if hasattr(self, '_settings_canvas') and self._settings_canvas.winfo_exists():
                    self._settings_canvas.update_idletasks()
                    self._settings_canvas.yview_moveto(saved)
            self.after(80, _restore)

    def close_settings_page(self) -> None:
        """Destroy the settings page and restore the chat view."""
        if not self._settings_visible:
            return
        # Unbind settings mousewheel handler
        if hasattr(self, '_settings_scroll_id') and hasattr(self, '_settings_canvas'):
            try:
                self._settings_canvas.unbind_all("<MouseWheel>")
                # Re-bind the main chat mousewheel
                self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            except Exception:
                pass
        if hasattr(self, '_settings_frame') and self._settings_frame.winfo_exists():
            self._settings_frame.destroy()
        self._settings_visible = False
        self._chat_wrapper.pack(fill=tk.BOTH, expand=True)
        self._input_bar.pack(fill=tk.X, side=tk.BOTTOM)
        # Restore header buttons
        self._new_btn.pack(side=tk.RIGHT, padx=(0, 20))
        self._theme_btn.pack(side=tk.RIGHT, padx=(0, 8))
        self._entry.focus_set()


def main() -> None:
    app = SymSolverApp()
    app.mainloop()


if __name__ == "__main__":
    main()
