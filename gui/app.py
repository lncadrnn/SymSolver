"""
SymSolver — Tkinter GUI

A chat-style interface for solving linear equations step-by-step.
Dark theme, scrollable solution area, and collapsible explanations.
"""

import re
import tkinter as tk
from tkinter import ttk, font as tkfont
import threading

from solver import solve_linear_equation


# ── colour palette ──────────────────────────────────────────────────────────
BG           = "#0a0a0a"
BG_DARKER    = "#050505"
HEADER_BG    = "#111111"
ACCENT       = "#0F4C75"
ACCENT_HOVER = "#0a3a5c"
TEXT         = "#d0d0d0"
TEXT_DIM     = "#cccccc"
TEXT_BRIGHT  = "#f0f0f0"
USER_BG      = "#1a1a1a"
BOT_BG       = "#121212"
STEP_BG      = "#181818"
STEP_BORDER  = "#2a2a2a"
SUCCESS      = "#4caf50"
ERROR        = "#ff5555"
INPUT_BG     = "#181818"
INPUT_BORDER = "#2a2a2a"
VERIFY_BG    = "#0f1a0f"


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

        self._build_ui()
        self._show_welcome()

        # bind Enter
        self.bind("<Return>", lambda _: self._on_send())

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # header
        header = tk.Frame(self, bg=HEADER_BG, height=72)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header, text="⬡  SymSolver", font=self._title,
            bg=HEADER_BG, fg=ACCENT,
        ).pack(side=tk.LEFT, padx=20)
        tk.Label(
            header, text="Linear Equation Solver", font=self._small,
            bg=HEADER_BG, fg=TEXT_DIM,
        ).pack(side=tk.LEFT, padx=(0, 20), pady=(6, 0))

        # new chat button
        self._new_btn = tk.Button(
            header, text="✦ New Chat", font=self._small,
            bg=ACCENT, fg=TEXT_BRIGHT, activebackground=ACCENT_HOVER,
            activeforeground=TEXT_BRIGHT, bd=0, padx=16, pady=6,
            cursor="hand2", command=self._clear_chat,
        )
        self._new_btn.pack(side=tk.RIGHT, padx=20)

        # chat area (canvas + scrollbar for widget embedding)
        chat_wrapper = tk.Frame(self, bg=BG)
        chat_wrapper.pack(fill=tk.BOTH, expand=True)

        # Custom dark scrollbar style
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Vertical.TScrollbar",
                        background="#2a2a2a", troughcolor=BG,
                        bordercolor=BG, arrowcolor="#555555",
                        relief=tk.FLAT, borderwidth=0)
        style.map("Dark.Vertical.TScrollbar",
                  background=[("active", "#444444"), ("!active", "#2a2a2a")],
                  arrowcolor=[("active", "#888888"), ("!active", "#555555")])
        style.layout("Dark.Vertical.TScrollbar", [
            ("Vertical.Scrollbar.trough", {
                "sticky": "ns",
                "children": [
                    ("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
                ]
            })
        ])

        self._canvas = tk.Canvas(chat_wrapper, bg=BG, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(
            chat_wrapper, orient=tk.VERTICAL, command=self._canvas.yview,
            style="Dark.Vertical.TScrollbar",
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
        input_bar = tk.Frame(self, bg=BG_DARKER, pady=14)
        input_bar.pack(fill=tk.X, side=tk.BOTTOM)

        inner = tk.Frame(input_bar, bg=INPUT_BG, highlightbackground=INPUT_BORDER,
                         highlightthickness=1)
        inner.pack(fill=tk.X, padx=20)

        self._entry = tk.Entry(
            inner, font=self._mono, bg=INPUT_BG, fg=TEXT_BRIGHT,
            insertbackground=TEXT_BRIGHT, bd=0, relief=tk.FLAT,
            disabledbackground=INPUT_BG, disabledforeground="#666666",
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(14, 6), pady=10)
        self._entry.focus_set()

        self._send_btn = tk.Button(
            inner, text="Solve ➤", font=self._bold,
            bg=ACCENT, fg=TEXT_BRIGHT, activebackground=ACCENT_HOVER,
            activeforeground=TEXT_BRIGHT, bd=0, padx=18, pady=6,
            cursor="hand2", command=self._on_send,
        )
        self._send_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=6)

        # Stop button — shown only during solving/animation
        self._stop_btn = tk.Button(
            inner, text="⏹", font=self._bold,
            bg="#3a1a1a", fg="#ff6b6b", activebackground="#4a2020",
            activeforeground="#ff9999", bd=0, padx=14, pady=6,
            cursor="hand2", relief=tk.FLAT,
            command=self._stop_solving,
        )
        # not packed yet — shown on demand

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
        if not self._auto_scroll:
            return
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── Welcome screen ──────────────────────────────────────────────────

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
                activeforeground=TEXT_BRIGHT, bd=0, padx=20, pady=8,
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
        self._auto_scroll = True
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

        self._auto_scroll = True  # re-enable for each new solve

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
        def _solve():
            try:
                result = solve_linear_equation(equation)
                self.after(0, lambda: self._show_result(result, loading_label))
            except Exception as exc:
                msg = self._friendly_error(equation, exc)
                self.after(0, lambda: self._show_error(msg, loading_label))

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
        self._set_input_state(True)
        self._entry.focus_set()

    def _set_input_state(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self._entry.configure(state=state)
        if enabled:
            # hide stop, show solve
            self._stop_btn.pack_forget()
            self._send_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=6)
        else:
            # hide solve, show stop
            self._send_btn.pack_forget()
            self._stop_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=6)

    # ── Chat bubbles ────────────────────────────────────────────────────

    def _add_user_message(self, text: str) -> None:
        frame = tk.Frame(self._chat_frame, bg=USER_BG, padx=18, pady=14)
        frame.pack(fill=tk.X, padx=20, pady=(12, 4))
        tk.Label(frame, text="You", font=self._bold, bg=USER_BG, fg=ACCENT,
                 anchor="w").pack(fill=tk.X)
        tk.Label(frame, text=text, font=self._mono, bg=USER_BG, fg=TEXT_BRIGHT,
                 anchor="w").pack(fill=tk.X)
        self._scroll_to_bottom()

    def _add_loading(self) -> tk.Label:
        label = tk.Label(
            self._chat_frame, text="  Processing…", font=self._default,
            bg=BG, fg=TEXT_DIM, anchor="w",
        )
        label.pack(fill=tk.X, padx=20, pady=6)
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
        self._scroll_to_bottom()

    # ── Animation helpers ─────────────────────────────────────────────

    _TYPING_SPEED = 12          # ms per character
    _PHASE_PAUSE  = 1500        # pause after status label (ms)

    def _type_label(self, parent, full_text, font, bg, fg, anchor="w",
                    wraplength=880, justify=tk.LEFT, callback=None):
        """Create a label and type *full_text* into it character-by-character."""
        lbl = tk.Label(parent, text="", font=font, bg=bg, fg=fg,
                       anchor=anchor, wraplength=wraplength, justify=justify)
        lbl.pack(fill=tk.X)
        self._type_chars(lbl, full_text, 0, callback)

    def _type_chars(self, lbl, text, idx, callback):
        if idx <= len(text):
            lbl.configure(text=text[:idx])
            self._scroll_to_bottom()
            self.after(self._TYPING_SPEED, self._type_chars, lbl, text, idx + 1, callback)
        else:
            if callback:
                callback()

    def _show_status(self, parent, text, bg=None):
        """Show an italicised status line like 'Identifying Given...'."""
        if bg is None:
            bg = BOT_BG
        status_font = tkfont.Font(family="Segoe UI", size=12, slant="italic")
        lbl = tk.Label(parent, text=text, font=status_font, bg=bg,
                       fg=TEXT_DIM, anchor="w")
        lbl.pack(fill=tk.X, pady=(6, 2))
        self._scroll_to_bottom()
        return lbl

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
            self.after(self._PHASE_PAUSE, lambda: self._animate_given(
                bot, given, result, status))

        queue.append(_render_given)

        # ── METHOD ─────────────────────────────────────────────────────
        method = result.get("method", {})

        def _render_method():
            status = self._show_status(bot, "Determining Approach...")
            self.after(self._PHASE_PAUSE, lambda: self._animate_method(
                bot, method, status))

        queue.append(_render_method)

        # ── STEPS ──────────────────────────────────────────────────────
        for step in result["steps"]:
            s = step  # capture

            def _render_step(s=s):
                verb = self._step_verb(s["description"])
                status = self._show_status(bot, verb)
                self.after(self._PHASE_PAUSE, lambda: self._animate_step(
                    bot, s, status))

            queue.append(_render_step)

        # ── FINAL ANSWER ───────────────────────────────────────────────
        def _render_answer():
            status = self._show_status(bot, "Finalizing answer...")
            self.after(self._PHASE_PAUSE, lambda: self._animate_answer(
                bot, result["final_answer"], status))

        queue.append(_render_answer)

        # ── VERIFICATION ───────────────────────────────────────────────
        if result.get("verification_steps"):
            v_steps = result["verification_steps"]

            def _render_verify():
                status = self._show_status(bot, "Verifying final answer...")
                self.after(self._PHASE_PAUSE, lambda: self._animate_verification(
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
                self.after(self._PHASE_PAUSE, lambda: self._animate_summary(
                    bot, summary, status))

            queue.append(_render_summary)

        # Final: re-enable input
        def _finish():
            self._set_input_state(True)
            self._entry.focus_set()
            self._scroll_to_bottom()

        queue.append(_finish)

        # Store queue and kick off
        self._anim_queue = queue
        self._anim_idx = 0
        self._steps_header_shown = False
        self._advance_queue()

    def _advance_queue(self):
        """Run the next item in the animation queue."""
        if self._anim_idx < len(self._anim_queue):
            fn = self._anim_queue[self._anim_idx]
            self._anim_idx += 1
            fn()
        # else: done

    def _schedule_next(self, delay_ms: int = 400):
        """Schedule the next queue item after a short pause."""
        self.after(delay_ms, self._advance_queue)

    # ── Individual animated section builders ────────────────────────────

    def _animate_given(self, parent, given, result, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "GIVEN", "📋")
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
            self._render_section_header(parent, "STEPS", "📝")

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
                bg="#252525", fg=ACCENT, activebackground="#303030",
                activeforeground="#3d8ecf", bd=0, cursor="hand2",
                anchor="w", padx=10, pady=4,
                relief=tk.FLAT, highlightthickness=1,
                highlightbackground="#333333", highlightcolor=ACCENT,
            )
            btn.configure(command=lambda b=btn: _toggle(b=b))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#303030", fg="#3d8ecf"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="#252525", fg=ACCENT))
            btn.pack(anchor="w", pady=(2, 0))
            if callback:
                callback()

        self._type_label(content, expl_text, self._small, STEP_BG, TEXT_DIM,
                         wraplength=840, callback=_after_typed)

    def _animate_answer(self, parent, final_answer, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "FINAL ANSWER", "✓")
        ans_frame = tk.Frame(parent, bg=SUCCESS, padx=1, pady=1)
        ans_frame.pack(fill=tk.X, pady=(2, 4))
        ans_inner = tk.Frame(ans_frame, bg="#0f1a0f", padx=16, pady=12)
        ans_inner.pack(fill=tk.X)

        lines = final_answer.split("\n")
        self._type_answer_lines(ans_inner, lines, 0)

    def _type_answer_lines(self, parent, lines, idx):
        if idx < len(lines):
            self._type_label(parent, lines[idx], self._mono, "#0f1a0f", TEXT_BRIGHT,
                             callback=lambda: self._type_answer_lines(parent, lines, idx + 1))
        else:
            self._scroll_to_bottom()
            self._schedule_next()

    def _animate_verification(self, parent, v_steps, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "VERIFICATION", "🔍")

        container = tk.Frame(parent, bg=BOT_BG)
        container.pack(fill=tk.X, pady=(8, 0))

        content = tk.Frame(container, bg=VERIFY_BG, padx=14, pady=10)
        animated = {"done": False}

        visible = tk.BooleanVar(value=False)
        # Start hidden — content is NOT packed

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

        btn = tk.Button(
            container, text="▸ Show Verification", font=self._bold,
            bg=BOT_BG, fg=SUCCESS, activebackground=BOT_BG,
            activeforeground=SUCCESS, bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

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
                self.after(self._PHASE_PAUSE,
                           lambda: self._type_verify_steps(parent, steps, idx + 1))

            self._type_label(card, desc, self._bold, STEP_BG, TEXT_BRIGHT,
                             callback=_after_desc)
        else:
            self._scroll_to_bottom()

    def _animate_summary(self, parent, summary, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "SUMMARY", "📊")
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

    # ── Section header helper ───────────────────────────────────────────

    def _render_section_header(self, parent: tk.Frame, title: str, icon: str = "") -> None:
        header = tk.Frame(parent, bg=BOT_BG)
        header.pack(fill=tk.X, pady=(14, 4))
        label_text = f"{icon}  {title}" if icon else title
        tk.Label(header, text=label_text, font=self._bold,
                 bg=BOT_BG, fg=ACCENT, anchor="w").pack(fill=tk.X)
        # thin accent line
        tk.Frame(header, bg=ACCENT, height=1).pack(fill=tk.X, pady=(2, 0))

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
        elif kind == "bold":
            self._type_label(card, text, self._bold, card_bg, color, callback=_next)
        elif kind == "small":
            self._type_label(card, text, self._small, card_bg, color, callback=_next)
        elif kind == "mono":
            self._type_label(card, text, self._mono, card_bg, color, callback=_next)

    # ── Case badge colours ──────────────────────────────────────────────
    _CASE_COLORS = {
        "one_solution":             {"bg": "#0d1f0d", "border": "#4caf50", "fg": "#4caf50"},
        "infinite":                 {"bg": "#1a1500", "border": "#f0c040", "fg": "#f0c040"},
        "no_solution":              {"bg": "#1f0d0d", "border": "#ff5555", "fg": "#ff5555"},
        "degenerate_identity":      {"bg": "#1a1500", "border": "#f0c040", "fg": "#f0c040"},
        "degenerate_contradiction": {"bg": "#1f0d0d", "border": "#ff5555", "fg": "#ff5555"},
    }

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

        self._render_section_header(parent, "GRAPH & ANALYSIS", "\U0001f4c8")

        container = tk.Frame(parent, bg=BOT_BG)
        container.pack(fill=tk.X, pady=(4, 0))

        # The single toggleable content panel
        content = tk.Frame(container, bg=STEP_BG)
        drawn   = {"done": False}
        visible = tk.BooleanVar(value=True)

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
                except Exception as exc:
                    tk.Label(c, text=f"Graph error: {exc}", font=self._small,
                             bg=STEP_BG, fg=ERROR, anchor="w").pack(fill=tk.X, padx=8)

            # ── Analysis card (below graph) — typed letter by letter ───
            if analysis is None:
                if cb:
                    cb()
                return

            colors = self._CASE_COLORS.get(
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
                items.append(("mono", f"\n  Condition:  {analysis['detail']}", "#888888"))
            if analysis.get("solution"):
                items.append(("sep", None, card_border))
                items.append(("bold", f"Result:  {analysis['solution']}", card_fg))

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

        btn = tk.Button(
            container, text="\u25be Hide Graph & Analysis", font=self._bold,
            bg=BOT_BG, fg=SUCCESS, activebackground=BOT_BG,
            activeforeground=SUCCESS, bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

        # Show content immediately; animation chain drives _schedule_next
        content.pack(fill=tk.X)
        _build_content(cb=self._schedule_next)

    # ── Step renderer ───────────────────────────────────────────────────
    # (kept for potential non-animated use; main flow uses _animate_step)


def main() -> None:
    app = SymSolverApp()
    app.mainloop()


if __name__ == "__main__":
    main()
