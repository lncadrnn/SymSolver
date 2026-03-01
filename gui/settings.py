"""
DualSolver — Full-page settings mixin

Renders the settings overlay that replaces the chat view.
"""

import tkinter as tk
from tkinter import ttk, font as tkfont

from gui import themes


class SettingsMixin:
    """Mixed into DualSolverApp — full-page settings panel."""

    def show_settings_page(self) -> None:
        """Replace chat content with a full-page settings view."""
        from gui.storage import get_settings, save_settings, clear_history, clear_all_data

        if hasattr(self, '_settings_frame') and self._settings_frame.winfo_exists():
            self._settings_frame.destroy()

        if not self._settings_visible:
            self._chat_wrapper.pack_forget()
            self._input_bar.pack_forget()
            self._settings_visible = True
            self._theme_btn.pack_forget()
            self._new_btn.pack_forget()

        p = themes.palette(self._theme)

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

        self._settings_canvas = settings_canvas

        def _settings_mousewheel(e):
            if settings_canvas.winfo_exists():
                settings_canvas.yview_scroll(int(-e.delta / 120), "units")

        self._settings_scroll_id = settings_canvas.bind_all(
            "<MouseWheel>", _settings_mousewheel)

        settings = get_settings()

        # Centered container
        center = tk.Frame(settings_inner, bg=p["BG"])
        center.pack(anchor="n", pady=(40, 40), padx=60, fill=tk.X)

        # ── Header row with back button ────────────────────────────
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

        # ── Card container ─────────────────────────────────────────
        card_outer = tk.Frame(center, bg=p["STEP_BORDER"], padx=1, pady=1)
        card_outer.pack(fill=tk.X)
        card = tk.Frame(card_outer, bg=p["STEP_BG"], padx=30, pady=24)
        card.pack(fill=tk.X)

        section_font = tkfont.Font(family="Segoe UI", size=15, weight="bold")
        label_font   = tkfont.Font(family="Segoe UI", size=13)
        small_font   = tkfont.Font(family="Segoe UI", size=11)

        # ── Theme ──────────────────────────────────────────────────
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

        # ── Animation Speed ────────────────────────────────────────
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

        # ── Display Options ────────────────────────────────────────
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

        # ── Save button + message ──────────────────────────────────
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
            save_settings(new_settings)
            self._sidebar._apply_settings_to_app(new_settings)
            new_p = themes.palette(self._theme)
            if new_p != p:
                self._settings_scroll_pos = settings_canvas.yview()[0]
                self.after(50, self._rebuild_settings_with_scroll)
            self._show_toast("Settings saved!")

        save_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        tk.Button(bottom, text="Save Settings", font=save_font,
                  bg=p["ACCENT"], fg="#ffffff",
                  activebackground=p["ACCENT_HOVER"],
                  activeforeground="#ffffff",
                  bd=0, padx=24, pady=10, cursor="hand2",
                  command=_save).pack(fill=tk.X)

        # ── Data Management card ───────────────────────────────────
        data_outer = tk.Frame(center, bg=p["STEP_BORDER"], padx=1, pady=1)
        data_outer.pack(fill=tk.X, pady=(20, 0))
        data_card = tk.Frame(data_outer, bg=p["STEP_BG"], padx=30, pady=24)
        data_card.pack(fill=tk.X)

        tk.Label(data_card, text="Data Management", font=section_font,
                 bg=p["STEP_BG"], fg=p["ACCENT"]).pack(anchor="w", pady=(0, 8))

        tk.Label(data_card, text="Manage your locally stored solve history and settings.",
                 font=small_font, bg=p["STEP_BG"],
                 fg=p["TEXT_DIM"]).pack(anchor="w", pady=(0, 12))

        data_msg = tk.Label(data_card, text="", font=small_font,
                            bg=p["STEP_BG"], fg=p["SUCCESS"])
        data_msg.pack(anchor="w", pady=(0, 8))

        # ── Clear History button ───────────────────────────────────
        def _clear_hist():
            clear_history()
            data_msg.configure(text="✓  History cleared!", fg=p["SUCCESS"])
            self._show_toast("History cleared!", icon="🗑")
            self.after(3000, lambda: data_msg.configure(text="")
                       if data_msg.winfo_exists() else None)

        def _confirm_clear_hist():
            _show_confirm(
                data_card, data_msg,
                "Clear all solve history?",
                "This will permanently delete all history entries.",
                "Clear History", _clear_hist,
            )

        btn_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")

        clear_hist_border = tk.Frame(data_card, bg=p["INPUT_BORDER"],
                                     highlightbackground=p["INPUT_BORDER"],
                                     highlightthickness=1, bd=0)
        clear_hist_border.pack(fill=tk.X, pady=3)
        tk.Button(clear_hist_border, text="🗑  Clear History", font=btn_font,
                  bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
                  activebackground=p["INPUT_BORDER"],
                  activeforeground=p["TEXT_BRIGHT"],
                  bd=0, padx=14, pady=10, cursor="hand2", anchor="w",
                  command=_confirm_clear_hist).pack(fill=tk.X)

        # ── Reset All Data button ──────────────────────────────────
        def _reset_all():
            clear_all_data()
            self._sidebar._apply_user_settings()
            data_msg.configure(text="✓  All data reset!", fg=p["SUCCESS"])
            self._show_toast("All data reset!", icon="⚠", kind="info")
            self.after(1500, lambda: (
                self._rebuild_settings_with_scroll()
                if self._settings_visible else None))

        def _confirm_reset():
            _show_confirm(
                data_card, data_msg,
                "Reset all data?",
                "This will erase all history AND reset settings to defaults.",
                "Reset Everything", _reset_all,
                danger=True,
            )

        reset_border = tk.Frame(data_card, bg=p["ERROR"],
                                highlightbackground=p["ERROR"],
                                highlightthickness=1, bd=0)
        reset_border.pack(fill=tk.X, pady=(8, 3))
        tk.Button(reset_border, text="⚠  Reset All Data", font=btn_font,
                  bg=p["STEP_BG"], fg=p["ERROR"],
                  activebackground=p["ERROR"],
                  activeforeground="#ffffff",
                  bd=0, padx=14, pady=10, cursor="hand2", anchor="w",
                  command=_confirm_reset).pack(fill=tk.X)

        # ── Confirmation helper (inline) ───────────────────────────
        def _show_confirm(parent, msg_lbl, title, desc, btn_text, action,
                          danger=False):
            """Show an inline confirmation prompt."""
            overlay = tk.Frame(parent, bg=p["STEP_BG"])
            overlay.pack(fill=tk.X, pady=(12, 0))

            tk.Label(overlay, text=title,
                     font=tkfont.Font(family="Segoe UI", size=14, weight="bold"),
                     bg=p["STEP_BG"], fg=p["ERROR"] if danger else p["TEXT_BRIGHT"]
                     ).pack(anchor="w")
            tk.Label(overlay, text=desc, font=small_font,
                     bg=p["STEP_BG"], fg=p["TEXT_DIM"]).pack(anchor="w", pady=(2, 10))

            btn_row = tk.Frame(overlay, bg=p["STEP_BG"])
            btn_row.pack(anchor="w")

            tk.Button(btn_row, text=btn_text, font=btn_font,
                      bg=p["ERROR"], fg="#ffffff",
                      activebackground="#cc0000", activeforeground="#ffffff",
                      bd=0, padx=16, pady=6, cursor="hand2",
                      command=lambda: (overlay.destroy(), action())
                      ).pack(side=tk.LEFT, padx=(0, 8))
            tk.Button(btn_row, text="Cancel", font=btn_font,
                      bg=p["STEP_BG"], fg=p["TEXT_DIM"],
                      activebackground=p["INPUT_BORDER"],
                      activeforeground=p["TEXT_BRIGHT"],
                      bd=0, padx=16, pady=6, cursor="hand2",
                      command=overlay.destroy).pack(side=tk.LEFT)

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
        if hasattr(self, '_settings_scroll_id') and hasattr(self, '_settings_canvas'):
            try:
                self._settings_canvas.unbind_all("<MouseWheel>")
                self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
            except Exception:
                pass
        if hasattr(self, '_settings_frame') and self._settings_frame.winfo_exists():
            self._settings_frame.destroy()
        self._settings_visible = False
        self._chat_wrapper.pack(fill=tk.BOTH, expand=True)
        self._input_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self._new_btn.pack(side=tk.RIGHT, padx=(0, 20))
        self._theme_btn.pack(side=tk.RIGHT, padx=(0, 8))
        self._entry.focus_set()
