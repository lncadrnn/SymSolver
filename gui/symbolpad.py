"""
DualSolver — Symbol-pad mixin

Floating popup with math-symbol buttons for fast input.
"""

import tkinter as tk
from tkinter import font as tkfont

from gui import themes


class SymbolPadMixin:
    """Mixed into DualSolverApp — adds the ⌨ symbol-pad popup."""

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
        p = themes.palette(self._theme)
        pad = tk.Toplevel(self)
        pad.overrideredirect(True)
        pad.configure(bg=p["STEP_BORDER"])
        pad.attributes("-topmost", True)
        self._symbol_pad_win = pad

        inner = tk.Frame(pad, bg=p["BG_DARKER"], padx=10, pady=8)
        inner.pack(padx=1, pady=1)

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
        x = bx + self._sympad_btn.winfo_width() - pw
        y = by - ph - 4
        if x < 0:
            x = bx
        pad.geometry(f"+{x}+{y}")

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
