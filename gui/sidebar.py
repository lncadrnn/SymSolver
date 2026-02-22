"""
SymSolver — Sidebar panel (hamburger menu).

Provides login/register, settings (all users), and history (logged-in only).
The sidebar overlays on top of the main content with a dimmed backdrop.
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

from gui.storage import (
    register_user, login_user,
    get_settings, save_settings,
    get_history, clear_history, add_history,
    DEFAULT_SETTINGS,
)


# ── Sidebar dimensions ──────────────────────────────────────────────────
_SIDEBAR_W = 340


class Sidebar:
    """Manages the slide-in sidebar overlay with dimmed backdrop."""

    def __init__(self, app: "SymSolverApp") -> None:  # type: ignore[name-defined]
        self.app = app
        self._open = False
        self._current_user: Optional[str] = None  # display name (None = guest)
        self._current_user_key: Optional[str] = None  # lowercase key

        # ── Fonts ────────────────────────────────────────────────────────
        self._font       = tkfont.Font(family="Segoe UI", size=13)
        self._font_bold  = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self._font_small = tkfont.Font(family="Segoe UI", size=11)
        self._font_title = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self._font_icon  = tkfont.Font(family="Segoe UI", size=18)
        self._font_hist  = tkfont.Font(family="Consolas", size=12)

        # ── Backdrop — dark overlay behind sidebar ───────────────────────
        self._backdrop = tk.Frame(app, bg="#000000")
        # Not placed yet — shown on open

        # ── Sidebar panel — overlays on top using place() ────────────────
        self._panel = tk.Frame(app, width=_SIDEBAR_W, bg="#050505")
        self._panel.place_forget()  # hidden initially
        self._panel.pack_propagate(False)

        # inner scrollable area
        self._canvas = tk.Canvas(self._panel, highlightthickness=0, width=_SIDEBAR_W)
        self._inner = tk.Frame(self._canvas)
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw",
                                   tags="inner")
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._inner.bind("<Configure>",
                         lambda _: self._canvas.configure(
                             scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig("inner", width=e.width))

        # Track current "page" inside sidebar
        self._page = "main"  # "main" | "login" | "register" | "history" | "settings"

        self._build_colours()

    # ── Colour helpers ──────────────────────────────────────────────────

    def _build_colours(self) -> None:
        from gui.app import (
            _DARK_PALETTE, _LIGHT_PALETTE,
        )
        p = _DARK_PALETTE if self.app._theme == "dark" else _LIGHT_PALETTE
        self.c = {
            "bg":       p["BG_DARKER"],
            "bg2":      p["BG"],
            "fg":       p["TEXT_BRIGHT"],
            "dim":      p["TEXT_DIM"],
            "accent":   p["ACCENT"],
            "accent_h": p["ACCENT_HOVER"],
            "card":     p["STEP_BG"],
            "border":   p["STEP_BORDER"],
            "input_bg": p["INPUT_BG"],
            "input_bd": p["INPUT_BORDER"],
            "error":    p["ERROR"],
            "success":  p["SUCCESS"],
            "header":   p["HEADER_BG"],
        }

    def refresh_theme(self) -> None:
        """Re-apply colours after a theme switch."""
        self._build_colours()
        self._apply_colours()
        if self._open:
            self._render_page()

    def _apply_colours(self) -> None:
        c = self.c
        self._panel.configure(bg=c["bg"])
        self._canvas.configure(bg=c["bg"])
        self._inner.configure(bg=c["bg"])

    # ── Scrolling ───────────────────────────────────────────────────────

    def _on_scroll(self, event: tk.Event) -> None:
        if self._open:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"  # consume event so main chat doesn't scroll

    # ── Open / Close (instant overlay) ──────────────────────────────────

    @property
    def is_open(self) -> bool:
        return self._open

    def toggle(self) -> None:
        if self._open:
            self.close()
        else:
            self.open()

    def open(self) -> None:
        if self._open:
            return
        self._open = True
        self._build_colours()
        self._apply_colours()

        self._page = "main"
        self._render_page()

        # Show backdrop (dark overlay) then sidebar on top
        self._backdrop.place(x=0, y=0, relwidth=1, relheight=1)
        _dim = "#b0b4ba" if self.app._theme == "light" else "#1a1a1a"
        self._backdrop.configure(bg=_dim)
        self._backdrop.lift()
        self._panel.place(x=0, y=0, width=_SIDEBAR_W, relheight=1)
        self._panel.lift()

        # Bind backdrop click to close
        self._backdrop.bind("<Button-1>", lambda e: self.close())
        # Bind mousewheel on sidebar canvas
        self._canvas.bind("<MouseWheel>", self._on_scroll)

    def close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._panel.place_forget()
        self._backdrop.place_forget()
        self._canvas.unbind("<MouseWheel>")
        self._clear_inner()

    # ── Page rendering ──────────────────────────────────────────────────

    def _clear_inner(self) -> None:
        for w in self._inner.winfo_children():
            w.destroy()

    def _render_page(self) -> None:
        self._clear_inner()
        c = self.c
        self._inner.configure(bg=c["bg"])

        if self._page == "main":
            self._render_main()
        elif self._page == "login":
            self._render_login()
        elif self._page == "register":
            self._render_register()
        elif self._page == "history":
            self._render_history()

        self._canvas.yview_moveto(0)

    # ── Main page ───────────────────────────────────────────────────────

    def _render_main(self) -> None:
        c = self.c

        # Close button row
        top = tk.Frame(self._inner, bg=c["bg"])
        top.pack(fill=tk.X, padx=12, pady=(14, 0))
        tk.Button(top, text="✕", font=self._font_icon, bg=c["bg"], fg=c["dim"],
                  activebackground=c["bg"], activeforeground=c["fg"],
                  bd=0, cursor="hand2", command=self.close).pack(side=tk.RIGHT)

        # User section
        user_frame = tk.Frame(self._inner, bg=c["bg"])
        user_frame.pack(fill=tk.X, padx=20, pady=(18, 10))

        if self._current_user:
            # Logged-in state
            avatar = tk.Label(user_frame, text="👤", font=self._font_icon,
                              bg=c["bg"], fg=c["accent"])
            avatar.pack(anchor="w")
            tk.Label(user_frame, text=self._current_user, font=self._font_title,
                     bg=c["bg"], fg=c["fg"]).pack(anchor="w", pady=(2, 0))
            tk.Label(user_frame, text="Logged in", font=self._font_small,
                     bg=c["bg"], fg=c["success"]).pack(anchor="w")

            # Logout button
            self._make_menu_button(user_frame, "↪  Log Out", self._logout,
                                   fg=c["error"], pady=(8, 0))
        else:
            # Guest state
            avatar = tk.Label(user_frame, text="👤", font=self._font_icon,
                              bg=c["bg"], fg=c["dim"])
            avatar.pack(anchor="w")
            tk.Label(user_frame, text="Guest", font=self._font_title,
                     bg=c["bg"], fg=c["fg"]).pack(anchor="w", pady=(2, 0))
            tk.Label(user_frame, text="Log in to save your history",
                     font=self._font_small, bg=c["bg"],
                     fg=c["dim"]).pack(anchor="w")

            btn_row = tk.Frame(user_frame, bg=c["bg"])
            btn_row.pack(anchor="w", pady=(10, 0))

            self._make_accent_button(btn_row, "Log In",
                                     lambda: self._go_page("login"))
            self._make_outline_button(btn_row, "Register",
                                      lambda: self._go_page("register"))

        # Divider
        self._divider()

        # Menu items
        menu = tk.Frame(self._inner, bg=c["bg"])
        menu.pack(fill=tk.X, padx=12, pady=(4, 0))

        if self._current_user:
            self._make_menu_button(menu, "📋  History", lambda: self._go_page("history"))

        self._make_menu_button(menu, "⚙  Settings", self._open_settings)

        # Divider + version
        self._divider()
        tk.Label(self._inner, text="SymSolver v1.0", font=self._font_small,
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", padx=20, pady=(4, 20))

    # ── Login page ──────────────────────────────────────────────────────

    def _render_login(self) -> None:
        c = self.c
        self._back_header("Log In")

        form = tk.Frame(self._inner, bg=c["bg"])
        form.pack(fill=tk.X, padx=20, pady=(20, 0))

        tk.Label(form, text="Username", font=self._font_bold, bg=c["bg"],
                 fg=c["fg"]).pack(anchor="w", pady=(0, 4))
        user_entry = tk.Entry(form, font=self._font, bg=c["input_bg"],
                              fg=c["fg"], insertbackground=c["fg"],
                              highlightbackground=c["input_bd"],
                              highlightthickness=1, bd=0, relief=tk.FLAT)
        user_entry.pack(fill=tk.X, ipady=8)

        tk.Label(form, text="Password", font=self._font_bold, bg=c["bg"],
                 fg=c["fg"]).pack(anchor="w", pady=(14, 4))
        pass_entry = tk.Entry(form, font=self._font, bg=c["input_bg"],
                              fg=c["fg"], insertbackground=c["fg"],
                              show="•",
                              highlightbackground=c["input_bd"],
                              highlightthickness=1, bd=0, relief=tk.FLAT)
        pass_entry.pack(fill=tk.X, ipady=8)

        msg_label = tk.Label(form, text="", font=self._font_small, bg=c["bg"],
                             fg=c["error"], wraplength=280, justify=tk.LEFT)
        msg_label.pack(anchor="w", pady=(10, 0))

        def _do_login():
            u, p = user_entry.get().strip(), pass_entry.get()
            ok, result = login_user(u, p)
            if ok:
                self._current_user = result  # display_name
                self._current_user_key = u.lower()
                # Load user settings
                self._apply_user_settings()
                self._page = "main"
                self._render_page()
            else:
                msg_label.configure(text=result, fg=c["error"])

        btn_frame = tk.Frame(form, bg=c["bg"])
        btn_frame.pack(fill=tk.X, pady=(16, 0))
        self._make_accent_button(btn_frame, "Log In", _do_login, fill=True)

        tk.Label(form, text="Don't have an account?", font=self._font_small,
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", pady=(20, 2))
        self._make_link_button(form, "Create one here",
                               lambda: self._go_page("register"))

        user_entry.focus_set()

        # Bind Enter to login
        def _enter(e):
            _do_login()
        pass_entry.bind("<Return>", _enter)
        user_entry.bind("<Return>", lambda e: pass_entry.focus_set())

    # ── Register page ───────────────────────────────────────────────────

    def _render_register(self) -> None:
        c = self.c
        self._back_header("Create Account")

        form = tk.Frame(self._inner, bg=c["bg"])
        form.pack(fill=tk.X, padx=20, pady=(20, 0))

        tk.Label(form, text="Username", font=self._font_bold, bg=c["bg"],
                 fg=c["fg"]).pack(anchor="w", pady=(0, 4))
        user_entry = tk.Entry(form, font=self._font, bg=c["input_bg"],
                              fg=c["fg"], insertbackground=c["fg"],
                              highlightbackground=c["input_bd"],
                              highlightthickness=1, bd=0, relief=tk.FLAT)
        user_entry.pack(fill=tk.X, ipady=8)

        tk.Label(form, text="Password", font=self._font_bold, bg=c["bg"],
                 fg=c["fg"]).pack(anchor="w", pady=(14, 4))
        pass_entry = tk.Entry(form, font=self._font, bg=c["input_bg"],
                              fg=c["fg"], insertbackground=c["fg"],
                              show="•",
                              highlightbackground=c["input_bd"],
                              highlightthickness=1, bd=0, relief=tk.FLAT)
        pass_entry.pack(fill=tk.X, ipady=8)

        tk.Label(form, text="Confirm Password", font=self._font_bold,
                 bg=c["bg"], fg=c["fg"]).pack(anchor="w", pady=(14, 4))
        conf_entry = tk.Entry(form, font=self._font, bg=c["input_bg"],
                              fg=c["fg"], insertbackground=c["fg"],
                              show="•",
                              highlightbackground=c["input_bd"],
                              highlightthickness=1, bd=0, relief=tk.FLAT)
        conf_entry.pack(fill=tk.X, ipady=8)

        msg_label = tk.Label(form, text="", font=self._font_small, bg=c["bg"],
                             fg=c["error"], wraplength=280, justify=tk.LEFT)
        msg_label.pack(anchor="w", pady=(10, 0))

        def _do_register():
            u = user_entry.get().strip()
            p = pass_entry.get()
            cp = conf_entry.get()
            if p != cp:
                msg_label.configure(text="Passwords do not match.", fg=c["error"])
                return
            ok, result = register_user(u, p)
            if ok:
                msg_label.configure(text=result, fg=c["success"])
                # Auto-login after short delay
                self.app.after(800, lambda: self._auto_login_after_register(u, p))
            else:
                msg_label.configure(text=result, fg=c["error"])

        btn_frame = tk.Frame(form, bg=c["bg"])
        btn_frame.pack(fill=tk.X, pady=(16, 0))
        self._make_accent_button(btn_frame, "Create Account", _do_register,
                                 fill=True)

        tk.Label(form, text="Already have an account?", font=self._font_small,
                 bg=c["bg"], fg=c["dim"]).pack(anchor="w", pady=(20, 2))
        self._make_link_button(form, "Log in here",
                               lambda: self._go_page("login"))

        user_entry.focus_set()
        conf_entry.bind("<Return>", lambda e: _do_register())

    def _auto_login_after_register(self, username: str, password: str) -> None:
        ok, result = login_user(username, password)
        if ok:
            self._current_user = result
            self._current_user_key = username.lower()
            self._apply_user_settings()
            self._page = "main"
            self._render_page()

    # ── History page ────────────────────────────────────────────────────

    def _render_history(self) -> None:
        c = self.c
        self._back_header("History")

        if not self._current_user_key:
            tk.Label(self._inner, text="Log in to view history.",
                     font=self._font, bg=c["bg"], fg=c["dim"]).pack(
                         padx=20, pady=40)
            return

        history = get_history(self._current_user_key)

        if not history:
            empty = tk.Frame(self._inner, bg=c["bg"])
            empty.pack(fill=tk.X, padx=20, pady=(40, 0))
            tk.Label(empty, text="📭", font=tkfont.Font(family="Segoe UI", size=32),
                     bg=c["bg"], fg=c["dim"]).pack()
            tk.Label(empty, text="No history yet", font=self._font_bold,
                     bg=c["bg"], fg=c["dim"]).pack(pady=(8, 2))
            tk.Label(empty, text="Solved equations will appear here.",
                     font=self._font_small, bg=c["bg"],
                     fg=c["border"]).pack()
            return

        # Clear history button
        top_actions = tk.Frame(self._inner, bg=c["bg"])
        top_actions.pack(fill=tk.X, padx=20, pady=(10, 4))
        tk.Button(top_actions, text="🗑 Clear All", font=self._font_small,
                  bg=c["bg"], fg=c["error"],
                  activebackground=c["bg"], activeforeground=c["error"],
                  bd=0, cursor="hand2",
                  command=self._confirm_clear_history).pack(side=tk.RIGHT)

        # History list
        for i, rec in enumerate(history):
            self._render_history_item(rec, i)

    def _render_history_item(self, rec: dict, index: int) -> None:
        c = self.c
        card = tk.Frame(self._inner, bg=c["card"],
                        highlightbackground=c["border"],
                        highlightthickness=1)
        card.pack(fill=tk.X, padx=16, pady=(4, 2))

        inner = tk.Frame(card, bg=c["card"], padx=12, pady=10)
        inner.pack(fill=tk.X)

        # Equation
        eq_text = rec.get("equation", "?")
        if len(eq_text) > 38:
            eq_text = eq_text[:35] + "…"
        tk.Label(inner, text=eq_text, font=self._font_hist, bg=c["card"],
                 fg=c["accent"], anchor="w", cursor="hand2").pack(fill=tk.X)

        # Answer (truncated)
        ans_text = rec.get("answer", "")
        first_line = ans_text.split("\n")[0] if ans_text else ""
        if len(first_line) > 44:
            first_line = first_line[:41] + "…"
        tk.Label(inner, text=first_line, font=self._font_small, bg=c["card"],
                 fg=c["dim"], anchor="w").pack(fill=tk.X, pady=(2, 0))

        # Timestamp
        ts = rec.get("timestamp", "")
        tk.Label(inner, text=ts, font=self._font_small, bg=c["card"],
                 fg=c["border"], anchor="w").pack(fill=tk.X, pady=(2, 0))

        # Clickable — re-solve
        eq_full = rec.get("equation", "")

        def _use(eq=eq_full):
            self.close()
            self.app._entry.delete(0, tk.END)
            self.app._entry.insert(0, eq)
            self.app._on_send()

        card.bind("<Button-1>", lambda e: _use())
        for child in inner.winfo_children():
            child.bind("<Button-1>", lambda e: _use())
            child.configure(cursor="hand2")

    def _confirm_clear_history(self) -> None:
        """Simple confirm: replace the history list with a confirmation prompt."""
        c = self.c
        self._clear_inner()
        self._inner.configure(bg=c["bg"])
        self._back_header("Clear History")

        frame = tk.Frame(self._inner, bg=c["bg"])
        frame.pack(fill=tk.X, padx=20, pady=(40, 0))

        tk.Label(frame, text="Are you sure?", font=self._font_title,
                 bg=c["bg"], fg=c["fg"]).pack()
        tk.Label(frame, text="This will permanently delete all your\nsolve history.",
                 font=self._font, bg=c["bg"], fg=c["dim"],
                 justify=tk.CENTER).pack(pady=(8, 20))

        btn_row = tk.Frame(frame, bg=c["bg"])
        btn_row.pack()

        def _confirm():
            if self._current_user_key:
                clear_history(self._current_user_key)
            self._page = "history"
            self._render_page()

        tk.Button(btn_row, text="Delete All", font=self._font_bold,
                  bg=c["error"], fg="#ffffff",
                  activebackground="#cc0000", activeforeground="#ffffff",
                  bd=0, padx=20, pady=8, cursor="hand2",
                  command=_confirm).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_row, text="Cancel", font=self._font_bold,
                  bg=c["card"], fg=c["fg"],
                  activebackground=c["border"], activeforeground=c["fg"],
                  bd=0, padx=20, pady=8, cursor="hand2",
                  command=lambda: self._go_page("history")).pack(side=tk.LEFT)

    # ── Settings page — now opens as full page in the app ─────────────

    def _open_settings(self) -> None:
        """Close sidebar and open the full-page settings view."""
        self.close()
        self.app.show_settings_page()

    # ── Apply user settings to the running app ──────────────────────────

    def _apply_user_settings(self) -> None:
        """Load the user's saved settings and apply them to the app."""
        settings = get_settings(self._current_user_key)
        self._apply_settings_to_app(settings)

    def _apply_settings_to_app(self, settings: dict) -> None:
        """Push a settings dict into the running app state."""
        # Theme
        desired = settings.get("theme", "dark")
        if desired != self.app._theme:
            self.app._theme = desired
            self.app._refresh_header_logo()
            self.app._apply_theme()
            self._build_colours()
            self._apply_colours()
            # Re-render sidebar page if open so colours update
            if self._open:
                self._render_page()

        # Animation speed
        speed = settings.get("animation_speed", "normal")
        speed_map = {"slow": 24, "normal": 12, "fast": 4, "instant": 0}
        self.app._TYPING_SPEED = speed_map.get(speed, 12)
        pause_map = {"slow": 2200, "normal": 1500, "fast": 600, "instant": 0}
        self.app._PHASE_PAUSE = pause_map.get(speed, 1500)

        # Display toggles
        self.app._show_verification = settings.get("show_verification", False)
        self.app._show_graph = settings.get("show_graph", True)

    # ── Logout ──────────────────────────────────────────────────────────

    def _logout(self) -> None:
        self._current_user = None
        self._current_user_key = None
        # Revert to guest settings
        self._apply_user_settings()
        self._page = "main"
        self._render_page()

    # ── Navigation helpers ──────────────────────────────────────────────

    def _go_page(self, page: str) -> None:
        self._page = page
        self._render_page()

    def _back_header(self, title: str) -> None:
        c = self.c
        top = tk.Frame(self._inner, bg=c["bg"])
        top.pack(fill=tk.X, padx=12, pady=(14, 0))

        tk.Button(top, text="←", font=self._font_icon, bg=c["bg"], fg=c["dim"],
                  activebackground=c["bg"], activeforeground=c["fg"],
                  bd=0, cursor="hand2",
                  command=lambda: self._go_page("main")).pack(side=tk.LEFT)
        tk.Label(top, text=title, font=self._font_title, bg=c["bg"],
                 fg=c["fg"]).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(top, text="✕", font=self._font_icon, bg=c["bg"], fg=c["dim"],
                  activebackground=c["bg"], activeforeground=c["fg"],
                  bd=0, cursor="hand2", command=self.close).pack(side=tk.RIGHT)

    def _divider(self) -> None:
        c = self.c
        tk.Frame(self._inner, bg=c["dim"], height=1).pack(
            fill=tk.X, padx=20, pady=(12, 8))

    def _divider_in(self, parent: tk.Frame) -> None:
        c = self.c
        tk.Frame(parent, bg=c["dim"], height=1).pack(
            fill=tk.X, pady=(6, 2))

    # ── Button helpers ──────────────────────────────────────────────────

    def _make_menu_button(self, parent, text, command, fg=None,
                          pady=(6, 2)) -> tk.Button:
        c = self.c
        _fg = fg or c["fg"]
        btn = tk.Button(parent, text=text, font=self._font, bg=c["bg"],
                        fg=_fg, activebackground=c["card"],
                        activeforeground=c["accent"],
                        bd=0, anchor="w", padx=8, pady=8,
                        cursor="hand2", command=command)
        btn.pack(fill=tk.X, pady=pady)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=c["card"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=c["bg"]))
        return btn

    def _make_accent_button(self, parent, text, command,
                            fill=False) -> tk.Button:
        c = self.c
        btn = tk.Button(parent, text=text, font=self._font_bold,
                        bg=c["accent"], fg="#ffffff",
                        activebackground=c["accent_h"],
                        activeforeground="#ffffff",
                        bd=0, padx=20, pady=8, cursor="hand2",
                        command=command)
        if fill:
            btn.pack(fill=tk.X)
        else:
            btn.pack(side=tk.LEFT, padx=(0, 8))
        return btn

    def _make_outline_button(self, parent, text, command) -> tk.Button:
        c = self.c
        btn = tk.Button(parent, text=text, font=self._font_bold,
                        bg=c["bg"], fg=c["accent"],
                        activebackground=c["card"],
                        activeforeground=c["accent"],
                        bd=0, padx=20, pady=8, cursor="hand2",
                        highlightbackground=c["accent"],
                        highlightthickness=1,
                        command=command)
        btn.pack(side=tk.LEFT, padx=(0, 8))
        return btn

    def _make_link_button(self, parent, text, command) -> None:
        c = self.c
        btn = tk.Label(parent, text=text, font=self._font_small,
                       bg=c["bg"], fg=c["accent"], cursor="hand2")
        btn.pack(anchor="w")
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=c["accent_h"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=c["accent"]))

    # ── Public API for the app ──────────────────────────────────────────

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user_key

    def record_solve(self, equation: str, answer: str) -> None:
        """Call after a successful solve to log it (if logged in)."""
        if self._current_user_key:
            add_history(self._current_user_key, equation, answer)
