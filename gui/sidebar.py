"""
DualSolver — Sidebar panel (hamburger menu).

ChatGPT-style sidebar with history logs, settings link, and three-dot menus.
No login/register — all history is stored locally for everyone.
"""

import time
import tkinter as tk
from tkinter import ttk, font as tkfont

from gui.storage import (
    get_settings, save_settings,
    get_history, get_archived_history,
    clear_history, add_history,
    delete_history_item, toggle_pin, toggle_archive,
    DEFAULT_SETTINGS,
)


# ── Sidebar dimensions ──────────────────────────────────────────────────
_SIDEBAR_W = 340


class Sidebar:
    """Manages the slide-in sidebar overlay with dimmed backdrop."""

    def __init__(self, app) -> None:
        self.app = app
        self._open = False

        # ── Fonts ────────────────────────────────────────────────────────
        self._font       = tkfont.Font(family="Segoe UI", size=13)
        self._font_bold  = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self._font_small = tkfont.Font(family="Segoe UI", size=11)
        self._font_title = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        self._font_icon  = tkfont.Font(family="Segoe UI", size=18)
        self._font_hist  = tkfont.Font(family="Consolas", size=12)
        self._font_dots  = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self._font_menu  = tkfont.Font(family="Segoe UI", size=12)

        # ── Backdrop — dark overlay behind sidebar ───────────────────────
        self._backdrop = tk.Frame(app, bg="#000000")

        # ── Sidebar panel — overlays on top using place() ────────────────
        self._panel = tk.Frame(app, width=_SIDEBAR_W, bg="#050505")
        self._panel.place_forget()
        self._panel.pack_propagate(False)

        # inner scrollable area + scrollbar
        self._sb_style_name = "Sidebar.Vertical.TScrollbar"
        self._style = ttk.Style()
        self._update_sidebar_scrollbar_style()

        # Use grid so canvas + scrollbar coexist reliably inside place()'d panel
        self._panel.grid_rowconfigure(0, weight=1)
        self._panel.grid_columnconfigure(0, weight=1)
        self._panel.grid_columnconfigure(1, weight=0)

        self._canvas = tk.Canvas(self._panel, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(
            self._panel, orient=tk.VERTICAL,
            command=self._canvas.yview,
            style=self._sb_style_name,
        )
        self._inner = tk.Frame(self._canvas)
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw",
                                   tags="inner")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        # scrollbar starts hidden — shown only when content overflows
        self._inner.bind("<Configure>", self._update_sidebar_scroll)
        self._canvas.bind("<Configure>",
                          lambda e: (self._canvas.itemconfig("inner",
                                      width=e.width),
                                     self._update_sidebar_scroll()))

        # Track current "page" inside sidebar
        self._page = "main"  # "main" | "history" | "archived"

        # Active popup menu ref (so we can close it)
        self._popup_menu = None

        self._build_colours()

    # ── Colour helpers ──────────────────────────────────────────────────

    def _build_colours(self) -> None:
        from gui.themes import DARK_PALETTE, LIGHT_PALETTE
        p = DARK_PALETTE if self.app._theme == "dark" else LIGHT_PALETTE
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
        self._update_sidebar_scrollbar_style()

    def _update_sidebar_scrollbar_style(self) -> None:
        """Style the sidebar scrollbar to match the current theme."""
        from gui.themes import DARK_PALETTE, LIGHT_PALETTE
        p = DARK_PALETTE if self.app._theme == "dark" else LIGHT_PALETTE
        bg  = p["BG_DARKER"]
        sbg = p["SCROLLBAR_BG"]
        sac = p["SCROLLBAR_ACT"]
        self._style.configure(
            self._sb_style_name,
            background=sbg, troughcolor=bg,
            bordercolor=bg, arrowcolor=sbg,
            relief=tk.FLAT, borderwidth=0,
        )
        self._style.map(
            self._sb_style_name,
            background=[("active", sac), ("!active", sbg)],
        )
        self._style.layout(self._sb_style_name, [
            ("Vertical.Scrollbar.trough", {
                "sticky": "ns",
                "children": [
                    ("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
                ]
            })
        ])

    def _update_sidebar_scroll(self, _event=None) -> None:
        """Show/hide the scrollbar depending on whether content overflows."""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._canvas.update_idletasks()
        content_h = self._inner.winfo_reqheight()
        canvas_h = self._canvas.winfo_height()
        if content_h <= canvas_h:
            self._scrollbar.grid_remove()
        else:
            self._scrollbar.grid(row=0, column=1, sticky="ns")

    # ── Scrolling ───────────────────────────────────────────────────────

    def _on_scroll(self, event: tk.Event) -> None:
        if self._open:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

    # ── Open / Close ────────────────────────────────────────────────────

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

        _dim = "#b0b4ba" if self.app._theme == "light" else "#1a1a1a"
        self._backdrop.place(x=0, y=0, relwidth=1, relheight=1)
        self._backdrop.configure(bg=_dim)
        self._backdrop.lift()
        self._panel.place(x=0, y=0, width=_SIDEBAR_W, relheight=1)
        self._panel.lift()

        self._backdrop.bind("<Button-1>", lambda e: self.close())
        self._canvas.bind("<MouseWheel>", self._on_scroll)

    def close(self) -> None:
        if not self._open:
            return
        self._open = False
        self._close_popup()
        self._panel.place_forget()
        self._backdrop.place_forget()
        self._canvas.unbind("<MouseWheel>")
        self._clear_inner()

    def _close_popup(self) -> None:
        """Destroy any open three-dot popup menu."""
        if self._popup_menu and self._popup_menu.winfo_exists():
            self._popup_menu.destroy()
        self._popup_menu = None

    # ── Page rendering ──────────────────────────────────────────────────

    def _clear_inner(self) -> None:
        for w in self._inner.winfo_children():
            w.destroy()

    def _render_page(self) -> None:
        self._clear_inner()
        self._close_popup()
        c = self.c
        self._inner.configure(bg=c["bg"])

        if self._page == "main":
            self._render_main()
        elif self._page == "history":
            self._render_full_history()
        elif self._page == "archived":
            self._render_archived()

        self._canvas.yview_moveto(0)

    # ── Main page (ChatGPT-style) ──────────────────────────────────────

    def _render_main(self) -> None:
        c = self.c

        # Top row: logo + close button
        top = tk.Frame(self._inner, bg=c["bg"])
        top.pack(fill=tk.X, padx=12, pady=(14, 0))

        try:
            import os
            from PIL import Image, ImageTk
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "assets")
            fname = ("darkmode-logo.png" if self.app._theme == "dark"
                     else "lightmode-logo.png")
            path = os.path.normpath(os.path.join(base, fname))
            img = Image.open(path)
            h = 56
            w = int(h * img.width / img.height)
            img = img.resize((w, h), Image.Resampling.LANCZOS)
            self._sidebar_logo_photo = ImageTk.PhotoImage(img)
            tk.Label(top, image=self._sidebar_logo_photo,
                     bg=c["bg"]).pack(side=tk.LEFT)
            tk.Label(top, text="DualSolver", font=self._font_title,
                     bg=c["bg"], fg=c["fg"]).pack(side=tk.LEFT, padx=(6, 0))
        except Exception:
            tk.Label(top, text="DualSolver", font=self._font_title,
                     bg=c["bg"], fg=c["accent"]).pack(side=tk.LEFT)

        tk.Button(top, text="✕", font=self._font_icon, bg=c["bg"], fg=c["dim"],
                  activebackground=c["bg"], activeforeground=c["fg"],
                  bd=0, cursor="hand2", command=self.close).pack(side=tk.RIGHT)

        # ── Menu items ───────────────────────────────────────────────
        menu = tk.Frame(self._inner, bg=c["bg"])
        menu.pack(fill=tk.X, padx=12, pady=(10, 0))

        self._make_menu_button(menu, "💬  DualSolver", self._new_chat)
        self._make_menu_button(menu, "⚙  Settings", self._open_settings)
        self._make_menu_button(menu, "📦  Archived", lambda: self._go_page("archived"))

        # Divider
        self._divider()

        # ── History section ──────────────────────────────────────────
        history = get_history(include_archived=False)

        if not history:
            empty_frame = tk.Frame(self._inner, bg=c["bg"])
            empty_frame.pack(fill=tk.X, padx=20, pady=(20, 0))
            tk.Label(empty_frame, text="No history yet",
                     font=self._font_small, bg=c["bg"],
                     fg=c["dim"]).pack(anchor="w")
            tk.Label(empty_frame, text="Solved equations will appear here.",
                     font=self._font_small, bg=c["bg"],
                     fg=c["border"]).pack(anchor="w", pady=(2, 0))
        else:
            # Separate pinned and regular
            pinned = [r for r in history if r.get("pinned", False)]
            regular = [r for r in history if not r.get("pinned", False)]

            # ── Pinned section ───────────────────────────────────────
            if pinned:
                lbl_frame = tk.Frame(self._inner, bg=c["bg"])
                lbl_frame.pack(fill=tk.X, padx=20, pady=(6, 2))
                tk.Label(lbl_frame, text="📌  Pinned", font=self._font_small,
                         bg=c["bg"], fg=c["dim"]).pack(anchor="w")
                for rec in pinned:
                    self._render_history_card(rec)

                if regular:
                    self._divider()

            # ── Regular (grouped by time) ────────────────────────────
            if regular:
                groups = self._group_by_time(regular)
                for label, items in groups:
                    lbl_frame = tk.Frame(self._inner, bg=c["bg"])
                    lbl_frame.pack(fill=tk.X, padx=20, pady=(8, 2))
                    tk.Label(lbl_frame, text=label, font=self._font_small,
                             bg=c["bg"], fg=c["dim"]).pack(anchor="w")
                    for rec in items:
                        self._render_history_card(rec)

            # ── View all link ────────────────────────────────────────
            if len(history) > 20:
                link_frame = tk.Frame(self._inner, bg=c["bg"])
                link_frame.pack(fill=tk.X, padx=20, pady=(10, 4))
                self._make_link_button(link_frame, "View all history →",
                                       lambda: self._go_page("history"))

        # Bottom padding
        tk.Frame(self._inner, bg=c["bg"], height=20).pack()

    # ── Time grouping helper ────────────────────────────────────────────

    @staticmethod
    def _group_by_time(records: list[dict]) -> list[tuple[str, list[dict]]]:
        """Group records into Today, Yesterday, Previous 7 Days, Earlier."""
        now = time.time()
        today_start = now - (now % 86400)  # approximate
        yesterday_start = today_start - 86400
        week_start = today_start - 7 * 86400

        groups: dict[str, list[dict]] = {
            "Today": [],
            "Yesterday": [],
            "Previous 7 Days": [],
            "Earlier": [],
        }
        for r in records:
            epoch = r.get("epoch", 0)
            if epoch >= today_start:
                groups["Today"].append(r)
            elif epoch >= yesterday_start:
                groups["Yesterday"].append(r)
            elif epoch >= week_start:
                groups["Previous 7 Days"].append(r)
            else:
                groups["Earlier"].append(r)

        result = []
        for key in ("Today", "Yesterday", "Previous 7 Days", "Earlier"):
            if groups[key]:
                result.append((key, groups[key]))
        return result

    # ── History card with three-dot menu ────────────────────────────────

    def _render_history_card(self, rec: dict) -> None:
        c = self.c
        record_id = rec.get("id", "")

        card = tk.Frame(self._inner, bg=c["card"],
                        highlightbackground=c["border"],
                        highlightthickness=1)
        card.pack(fill=tk.X, padx=16, pady=(3, 1))

        inner = tk.Frame(card, bg=c["card"], padx=10, pady=6)
        inner.pack(fill=tk.X)

        # Top row: equation + three-dot button
        top_row = tk.Frame(inner, bg=c["card"])
        top_row.pack(fill=tk.X)

        eq_text = rec.get("equation", "?")
        if len(eq_text) > 32:
            eq_text = eq_text[:29] + "…"

        pin_prefix = "📌 " if rec.get("pinned", False) else ""
        eq_label = tk.Label(top_row, text=pin_prefix + eq_text,
                            font=self._font_hist, bg=c["card"],
                            fg=c["accent"], anchor="w", cursor="hand2")
        eq_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Three-dot menu button
        dots_btn = tk.Button(
            top_row, text="⋮", font=self._font_dots,
            bg=c["card"], fg=c["dim"],
            activebackground=c["card"], activeforeground=c["fg"],
            bd=0, padx=4, pady=0, cursor="hand2",
            command=lambda rid=record_id, btn=None: None,
        )
        dots_btn.pack(side=tk.RIGHT)
        dots_btn.configure(
            command=lambda rid=record_id, b=dots_btn: self._show_popup(rid, b, rec))

        # Timestamp — tight below equation, readable colour per theme
        ts = rec.get("timestamp", "")
        ts_fg = c["fg"]  # white in dark mode, black in light mode
        tk.Label(inner, text=ts, font=self._font_small, bg=c["card"],
                 fg=ts_fg, anchor="w").pack(fill=tk.X, pady=(0, 0))

        # Click card to re-solve
        eq_full = rec.get("equation", "")

        def _use(eq=eq_full):
            self.close()
            self.app._entry.delete(0, tk.END)
            self.app._entry.insert(0, eq)
            self.app._on_send()

        for widget in (card, inner, eq_label):
            widget.bind("<Button-1>", lambda e: _use())

    # ── Three-dot popup menu ────────────────────────────────────────────

    def _show_popup(self, record_id: str, anchor_widget: tk.Widget,
                    rec: dict) -> None:
        """Show a popup context menu near the three-dot button."""
        self._close_popup()
        c = self.c

        popup = tk.Toplevel(self.app)
        popup.overrideredirect(True)
        popup.configure(bg=c["border"])
        self._popup_menu = popup

        inner_frame = tk.Frame(popup, bg=c["card"], padx=1, pady=1)
        inner_frame.pack(fill=tk.BOTH, expand=True)

        is_pinned = rec.get("pinned", False)
        is_archived = rec.get("archived", False)

        items = []
        items.append((
            "📌  Unpin" if is_pinned else "📌  Pin",
            lambda: self._action_pin(record_id),
        ))
        items.append((
            "📦  Unarchive" if is_archived else "📦  Archive",
            lambda: self._action_archive(record_id),
        ))
        items.append(("🗑  Delete", lambda: self._action_delete(record_id)))

        for text, cmd in items:
            fg_color = c["error"] if "Delete" in text else c["fg"]
            btn = tk.Button(
                inner_frame, text=text, font=self._font_menu,
                bg=c["card"], fg=fg_color,
                activebackground=c["border"], activeforeground=c["fg"],
                bd=0, anchor="w", padx=14, pady=6, cursor="hand2",
                command=lambda fn=cmd: (fn(), self._close_popup()),
            )
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=c["border"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=c["card"]))

        # Position popup near the anchor widget
        popup.update_idletasks()
        x = anchor_widget.winfo_rootx() - popup.winfo_reqwidth() + anchor_widget.winfo_width()
        y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height()
        popup.geometry(f"+{x}+{y}")

        # Close popup when clicking elsewhere
        def _on_click_outside(e):
            try:
                if popup.winfo_exists():
                    w = e.widget
                    if w != popup and w.master != inner_frame:
                        self._close_popup()
            except Exception:
                self._close_popup()

        popup.bind("<FocusOut>", lambda e: self._close_popup())
        self.app.bind("<Button-1>", _on_click_outside, add="+")
        popup.after(100, lambda: popup.focus_force() if popup.winfo_exists() else None)

    def _action_pin(self, record_id: str) -> None:
        toggle_pin(record_id)
        self._render_page()

    def _action_archive(self, record_id: str) -> None:
        toggle_archive(record_id)
        self._render_page()

    def _action_delete(self, record_id: str) -> None:
        delete_history_item(record_id)
        self._render_page()

    # ── Full history page ───────────────────────────────────────────────

    def _render_full_history(self) -> None:
        c = self.c
        self._back_header("History")

        history = get_history(include_archived=False)

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

        # Clear all button
        top_actions = tk.Frame(self._inner, bg=c["bg"])
        top_actions.pack(fill=tk.X, padx=20, pady=(10, 4))
        tk.Button(top_actions, text="🗑 Clear All", font=self._font_small,
                  bg=c["bg"], fg=c["error"],
                  activebackground=c["bg"], activeforeground=c["error"],
                  bd=0, cursor="hand2",
                  command=self._confirm_clear_history).pack(side=tk.RIGHT)

        archived = get_archived_history()
        if archived:
            tk.Button(top_actions, text=f"📦 Archived ({len(archived)})",
                      font=self._font_small,
                      bg=c["bg"], fg=c["accent"],
                      activebackground=c["bg"], activeforeground=c["accent_h"],
                      bd=0, cursor="hand2",
                      command=lambda: self._go_page("archived")).pack(side=tk.LEFT)

        for rec in history:
            self._render_history_card(rec)

    # ── Archived page ───────────────────────────────────────────────────

    def _render_archived(self) -> None:
        c = self.c
        self._back_header("Archived")

        archived = get_archived_history()

        if not archived:
            empty = tk.Frame(self._inner, bg=c["bg"])
            empty.pack(fill=tk.X, padx=20, pady=(40, 0))
            tk.Label(empty, text="📦", font=tkfont.Font(family="Segoe UI", size=32),
                     bg=c["bg"], fg=c["dim"]).pack()
            tk.Label(empty, text="No archived items", font=self._font_bold,
                     bg=c["bg"], fg=c["dim"]).pack(pady=(8, 2))
            tk.Label(empty, text="Archived equations will appear here.",
                     font=self._font_small, bg=c["bg"],
                     fg=c["border"]).pack()
            return

        for rec in archived:
            self._render_history_card(rec)

    # ── Clear history confirmation ──────────────────────────────────────

    def _confirm_clear_history(self) -> None:
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
            clear_history()
            self._page = "main"
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
                  command=lambda: self._go_page("main")).pack(side=tk.LEFT)

    # ── Settings — opens full page in app ───────────────────────────────

    def _go_chat(self) -> None:
        self.close()
        if getattr(self.app, '_settings_visible', False):
            self.app.close_settings_page()

    def _open_settings(self) -> None:
        self.close()
        self.app.show_settings_page()

    def _new_chat(self) -> None:
        """Start a new chat — clears the current view."""
        self.close()
        if getattr(self.app, '_settings_visible', False):
            self.app.close_settings_page()
        self.app._clear_chat()

    # ── Apply settings to the running app ───────────────────────────────

    def _apply_user_settings(self) -> None:
        settings = get_settings()
        self._apply_settings_to_app(settings)

    def _apply_settings_to_app(self, settings: dict) -> None:
        # Theme
        desired = settings.get("theme", "dark")
        if desired != self.app._theme:
            self.app._theme = desired
            self.app._refresh_header_logo()
            self.app._apply_theme()
            self._build_colours()
            self._apply_colours()
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

    def _make_link_button(self, parent, text, command) -> None:
        c = self.c
        btn = tk.Label(parent, text=text, font=self._font_small,
                       bg=c["bg"], fg=c["accent"], cursor="hand2")
        btn.pack(anchor="w", pady=(4, 0))
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=c["accent_h"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=c["accent"]))

    # ── Public API for the app ──────────────────────────────────────────

    @property
    def current_user(self):
        return None  # No user system — kept for compatibility

    def record_solve(self, equation: str, answer: str) -> None:
        """Log a solved equation to local history."""
        add_history(equation, answer)
