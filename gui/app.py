"""
SymSolver — Tkinter GUI

A chat-style interface for solving linear equations step-by-step.
Dark theme, scrollable solution area, and collapsible explanations.
"""

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

        self._canvas = tk.Canvas(chat_wrapper, bg=BG, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(
            chat_wrapper, orient=tk.VERTICAL, command=self._canvas.yview,
        )
        self._chat_frame = tk.Frame(self._canvas, bg=BG)

        self._chat_frame.bind(
            "<Configure>",
            lambda _: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
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

    # ── Canvas helpers ──────────────────────────────────────────────────

    def _on_canvas_resize(self, event: tk.Event) -> None:
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def _scroll_to_bottom(self) -> None:
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    # ── Welcome screen ──────────────────────────────────────────────────

    def _show_welcome(self) -> None:
        self._welcome_frame = tk.Frame(self._chat_frame, bg=BG)
        self._welcome_frame.pack(fill=tk.BOTH, expand=True, pady=50)

        tk.Label(
            self._welcome_frame, text="⬡", font=tkfont.Font(size=56),
            bg=BG, fg=ACCENT,
        ).pack()
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

        examples = ["2x + 3 = 7", "5y - 2 = 3y + 8",
                     "2x + 4y = 1",
                     "x + y = 10, x - y = 2"]
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
        for w in self._chat_frame.winfo_children():
            w.destroy()
        self._show_welcome()

    # ── Send equation ───────────────────────────────────────────────────

    def _on_send(self) -> None:
        equation = self._entry.get().strip()
        if not equation:
            return

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
        # Already a clear ValueError from the solver — keep it.
        if isinstance(exc, ValueError):
            return msg
        # Generic fallback for unexpected failures.
        return (
            f"SymSolver could not process \"{equation}\".\n\n"
            "Supports linear equations with one or more variables,\n"
            "and systems separated by commas or semicolons.\n"
            "Examples:  2x + 3 = 7  \u2022  2x + 4y = 1  \u2022  x+y=10, x-y=2\n\n"
            f"Details: {msg}"
        )

    def _set_input_state(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self._entry.configure(state=state)
        self._send_btn.configure(state=state)

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
            self._chat_frame, text="  Solving…", font=self._default,
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

    def _show_result(self, result: dict, loading: tk.Label) -> None:
        loading.destroy()

        bot = tk.Frame(self._chat_frame, bg=BOT_BG, padx=18, pady=14)
        bot.pack(fill=tk.X, padx=20, pady=(4, 6))
        tk.Label(bot, text="SymSolver", font=self._bold, bg=BOT_BG,
                 fg=ACCENT, anchor="w").pack(fill=tk.X)

        # ── GIVEN ──────────────────────────────────────────────────────
        given = result.get("given", {})
        self._render_section_header(bot, "GIVEN", "📋")
        given_frame = self._make_card(bot, STEP_BG)
        tk.Label(given_frame, text=given.get("problem", result["equation"]),
                 font=self._default, bg=STEP_BG, fg=TEXT_BRIGHT, anchor="w",
                 wraplength=880, justify=tk.LEFT).pack(fill=tk.X)
        inputs = given.get("inputs", {})
        if inputs:
            for key, val in inputs.items():
                tk.Label(given_frame,
                         text=f"  {key.replace('_', ' ').title()}:  {val}",
                         font=self._small, bg=STEP_BG, fg=TEXT_DIM,
                         anchor="w").pack(fill=tk.X)

        # ── METHOD ─────────────────────────────────────────────────────
        method = result.get("method", {})
        self._render_section_header(bot, "METHOD", "⚙")
        method_frame = self._make_card(bot, STEP_BG)
        tk.Label(method_frame, text=method.get("name", "Algebraic Isolation"),
                 font=self._bold, bg=STEP_BG, fg=ACCENT, anchor="w").pack(fill=tk.X)
        if method.get("description"):
            tk.Label(method_frame, text=method["description"],
                     font=self._small, bg=STEP_BG, fg=TEXT_DIM, anchor="w",
                     wraplength=880, justify=tk.LEFT).pack(fill=tk.X, pady=(2, 0))
        params = method.get("parameters", {})
        if params:
            for key, val in params.items():
                tk.Label(method_frame,
                         text=f"  {key.replace('_', ' ').title()}:  {val}",
                         font=self._small, bg=STEP_BG, fg=TEXT_DIM,
                         anchor="w").pack(fill=tk.X)

        # ── STEPS ──────────────────────────────────────────────────────
        self._render_section_header(bot, "STEPS", "📝")
        for step in result["steps"]:
            self._render_step(bot, step)

        # ── FINAL ANSWER ───────────────────────────────────────────────
        self._render_section_header(bot, "FINAL ANSWER", "✓")
        ans_frame = tk.Frame(bot, bg=SUCCESS, padx=1, pady=1)
        ans_frame.pack(fill=tk.X, pady=(2, 4))
        ans_inner = tk.Frame(ans_frame, bg="#0f1a0f", padx=16, pady=12)
        ans_inner.pack(fill=tk.X)
        for _ans_line in result["final_answer"].split("\n"):
            tk.Label(ans_inner, text=_ans_line, font=self._mono,
                     bg="#0f1a0f", fg=TEXT_BRIGHT, anchor="w"
                     ).pack(fill=tk.X)

        # ── VERIFICATION ───────────────────────────────────────────────
        if result.get("verification_steps"):
            self._render_section_header(bot, "VERIFICATION", "🔍")
            self._render_verification(bot, result["verification_steps"])

        # ── SUMMARY ────────────────────────────────────────────────────
        summary = result.get("summary", {})
        if summary:
            self._render_section_header(bot, "SUMMARY", "📊")
            sum_frame = self._make_card(bot, STEP_BG)
            details = [
                ("Runtime", f"{summary.get('runtime_ms', '?')} ms"),
                ("Steps", str(summary.get('total_steps', '?'))),
                ("Verification Steps", str(summary.get('verification_steps', '?'))),
                ("Timestamp", summary.get('timestamp', '?')),
                ("Library", summary.get('library', '?')),
            ]
            for label, value in details:
                row = tk.Frame(sum_frame, bg=STEP_BG)
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=f"  {label}:", font=self._small,
                         bg=STEP_BG, fg=TEXT_DIM, anchor="w",
                         width=26).pack(side=tk.LEFT)
                tk.Label(row, text=value, font=self._small,
                         bg=STEP_BG, fg=TEXT_BRIGHT, anchor="w"
                         ).pack(side=tk.LEFT)

        self._set_input_state(True)
        self._entry.focus_set()
        self._scroll_to_bottom()

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

    # ── Step renderer ───────────────────────────────────────────────────

    def _render_step(self, parent: tk.Frame, step: dict) -> None:
        wrapper = tk.Frame(parent, bg=STEP_BORDER, padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=4)

        card = tk.Frame(wrapper, bg=STEP_BG, padx=14, pady=10)
        card.pack(fill=tk.X)

        # description with step number
        step_num = step.get("step_number")
        desc = step["description"]
        if step_num is not None:
            desc = f"Step {step_num}:  {desc}"
        tk.Label(card, text=desc, font=self._bold,
                 bg=STEP_BG, fg=TEXT_BRIGHT, anchor="w").pack(fill=tk.X)
        # expression
        tk.Label(card, text=step["expression"], font=self._mono,
                 bg=STEP_BG, fg=ACCENT, anchor="w").pack(fill=tk.X, pady=(2, 0))

        # explanation (collapsible)
        if step.get("explanation"):
            expl_text = step["explanation"]
            toggle_frame = tk.Frame(card, bg=STEP_BG)
            toggle_frame.pack(fill=tk.X, pady=(4, 0))

            content = tk.Frame(card, bg=STEP_BG)
            lbl = tk.Label(content, text=expl_text, font=self._small,
                           bg=STEP_BG, fg=TEXT_DIM, anchor="w",
                           wraplength=840, justify=tk.LEFT)
            lbl.pack(fill=tk.X, pady=(2, 0))

            visible = tk.BooleanVar(value=False)

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
                toggle_frame, text="▸ Show Explanation", font=self._small,
                bg=STEP_BG, fg=TEXT_DIM, activebackground=STEP_BG,
                activeforeground=TEXT, bd=0, cursor="hand2",
                anchor="w",
            )
            btn.configure(command=lambda b=btn: _toggle(b=b))
            btn.pack(anchor="w")

    # ── Verification renderer ───────────────────────────────────────────

    def _render_verification(self, parent: tk.Frame, steps: list) -> None:
        container = tk.Frame(parent, bg=BOT_BG)
        container.pack(fill=tk.X, pady=(8, 0))

        content = tk.Frame(container, bg=VERIFY_BG, padx=14, pady=10)

        visible = tk.BooleanVar(value=False)

        def _toggle(v=visible, c=content, b=None):
            if v.get():
                c.pack_forget()
                v.set(False)
                b.configure(text="▸ Show Verification")
            else:
                c.pack(fill=tk.X)
                v.set(True)
                b.configure(text="▾ Hide Verification")

        btn = tk.Button(
            container, text="▸ Show Verification", font=self._bold,
            bg=BOT_BG, fg=SUCCESS, activebackground=BOT_BG,
            activeforeground=SUCCESS, bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

        for step in steps:
            self._render_step(content, step)


def main() -> None:
    app = SymSolverApp()
    app.mainloop()


if __name__ == "__main__":
    main()
