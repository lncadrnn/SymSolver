"""
SymSolver — Animation mixin

Step-by-step animated rendering of solver results into the chat area.
"""

import tkinter as tk
from tkinter import font as tkfont

from gui import themes


class AnimationMixin:
    """Mixed into SymSolverApp — drives the queued step-by-step animation."""

    # Class-level defaults (overridden at runtime via Settings)
    _TYPING_SPEED = 12          # ms per character
    _PHASE_PAUSE  = 1500        # pause after status label (ms)

    # ── Low-level typing helpers ───────────────────────────────────────

    def _type_label(self, parent, full_text, font, bg, fg, anchor="w",
                    wraplength=880, justify=tk.LEFT, callback=None):
        """Create a label and type *full_text* character-by-character."""
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
        """Show an italicised status line (e.g. 'Identifying Given…')."""
        if bg is None:
            bg = themes.BOT_BG
        if self._PHASE_PAUSE == 0:
            class _Dummy:
                def destroy(self): pass
                def winfo_exists(self): return False
            return _Dummy()
        status_font = tkfont.Font(family="Segoe UI", size=12, slant="italic")
        lbl = tk.Label(parent, text=text, font=status_font, bg=bg,
                       fg=themes.TEXT_DIM, anchor="w")
        lbl.pack(fill=tk.X, pady=(6, 2))
        self._scroll_to_bottom()
        return lbl

    def _phase_then(self, status_lbl, callback):
        """Wait _PHASE_PAUSE ms then call *callback*."""
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
        if "subtract" in d:  return "Subtracting..."
        if "add" in d:       return "Adding..."
        if "divide" in d:    return "Dividing..."
        if "multiply" in d:  return "Multiplying..."
        if "expand" in d:    return "Expanding..."
        if "combin" in d:    return "Combining like terms..."
        if "simplif" in d:   return "Simplifying..."
        if "substitut" in d: return "Substituting..."
        if "isolat" in d:    return "Isolating variable..."
        if "original" in d or "start" in d:
            return "Writing equation..."
        if "answer" in d or "final" in d:
            return "Computing answer..."
        return "Processing..."

    # ── Queue driver ───────────────────────────────────────────────────

    def _show_result(self, result: dict, loading: tk.Label) -> None:
        """Build animation queue from *result* and kick it off."""
        loading.destroy()

        bot = tk.Frame(self._chat_frame, bg=themes.BOT_BG, padx=18, pady=14)
        bot.pack(fill=tk.X, padx=20, pady=(4, 6))
        tk.Label(bot, text="SymSolver", font=self._bold, bg=themes.BOT_BG,
                 fg=themes.ACCENT, anchor="w").pack(fill=tk.X)

        queue: list = []

        # ── GIVEN ──────────────────────────────────────────────────
        given = result.get("given", {})
        def _render_given():
            status = self._show_status(bot, "Identifying Given...")
            self._phase_then(status, lambda: self._animate_given(
                bot, given, result, status))
        queue.append(_render_given)

        # ── METHOD ─────────────────────────────────────────────────
        method = result.get("method", {})
        def _render_method():
            status = self._show_status(bot, "Determining Approach...")
            self._phase_then(status, lambda: self._animate_method(
                bot, method, status))
        queue.append(_render_method)

        # ── STEPS ──────────────────────────────────────────────────
        for step in result["steps"]:
            s = step
            def _render_step(s=s):
                verb = self._step_verb(s["description"])
                status = self._show_status(bot, verb)
                self._phase_then(status, lambda: self._animate_step(
                    bot, s, status))
            queue.append(_render_step)

        # ── FINAL ANSWER ───────────────────────────────────────────
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

        # ── VERIFICATION ───────────────────────────────────────────
        if result.get("verification_steps"):
            v_steps = result["verification_steps"]
            def _render_verify():
                status = self._show_status(bot, "Verifying final answer...")
                self._phase_then(status, lambda: self._animate_verification(
                    bot, v_steps, status))
            queue.append(_render_verify)

        # ── GRAPH (skip for non-linear) ────────────────────────────
        _method_name = result.get("method", {}).get("name", "")
        if "Linearity Check" not in _method_name:
            def _render_graph():
                self._animate_graph(bot, result)
            queue.append(_render_graph)

        # ── SUMMARY ────────────────────────────────────────────────
        summary = result.get("summary", {})
        if summary:
            def _render_summary():
                status = self._show_status(bot, "Summarizing...")
                self._phase_then(status, lambda: self._animate_summary(
                    bot, summary, status))
            queue.append(_render_summary)

        # ── Finish ─────────────────────────────────────────────────
        _equation_text = result.get("equation", "")
        _answer_text = result.get("final_answer", "")
        def _finish():
            self._add_export_bar(bot, result)
            self._set_input_state(True)
            self._entry.focus_set()
            if not (self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0):
                self._scroll_to_bottom()
            self._sidebar.record_solve(_equation_text, _answer_text)
        queue.append(_finish)

        # Store queue and kick off
        self._anim_queue = queue
        self._anim_idx = 0
        self._steps_header_shown = False

        if self._PHASE_PAUSE == 0 and self._TYPING_SPEED == 0:
            self._instant_rendering = True
            while self._anim_idx < len(self._anim_queue):
                fn = self._anim_queue[self._anim_idx]
                self._anim_idx += 1
                fn()
            self._instant_rendering = False
            self.update_idletasks()
            self._update_scroll_region()
            self._canvas.yview_moveto(1.0)
            self._auto_scroll = False
        else:
            self._advance_queue()

    def _advance_queue(self):
        """Run the next item in the animation queue."""
        if self._anim_idx < len(self._anim_queue):
            fn = self._anim_queue[self._anim_idx]
            self._anim_idx += 1
            fn()

    def _schedule_next(self, delay_ms: int = 400):
        """Schedule the next queue item after a short pause."""
        if getattr(self, '_instant_rendering', False):
            return
        gen = self._solve_gen
        def _go():
            if self._solve_gen != gen:
                return
            self._advance_queue()
        if self._PHASE_PAUSE == 0:
            self.after(0, _go)
        else:
            self.after(delay_ms, _go)

    # ── Individual section animators ───────────────────────────────────

    def _animate_given(self, parent, given, result, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "GIVEN", "✎")
        given_frame = self._make_card(parent, themes.STEP_BG)
        problem_text = given.get("problem", result["equation"])
        inputs = given.get("inputs", {})
        input_lines = [f"  {k.replace('_', ' ').title()}:  {v}" for k, v in inputs.items()]

        def _after_problem():
            self._type_input_lines(given_frame, input_lines, 0)

        if self._FRAC_RE.search(problem_text):
            w = self._render_math_expr(given_frame, problem_text,
                                       font=self._default,
                                       bg=themes.STEP_BG, fg=themes.TEXT_BRIGHT)
            w.pack(anchor="w")
            _after_problem()
        else:
            self._type_label(given_frame, problem_text, self._default,
                             themes.STEP_BG, themes.TEXT_BRIGHT, callback=_after_problem)

    def _type_input_lines(self, parent, lines, idx):
        if idx < len(lines):
            line = lines[idx]
            def _next(): self._type_input_lines(parent, lines, idx + 1)
            if self._FRAC_RE.search(line):
                w = self._render_math_expr(parent, line,
                                           font=self._small,
                                           bg=themes.STEP_BG, fg=themes.TEXT_DIM)
                w.pack(anchor="w")
                _next()
            else:
                self._type_label(parent, line, self._small, themes.STEP_BG, themes.TEXT_DIM,
                                 callback=_next)
        else:
            self._scroll_to_bottom()
            self._schedule_next()

    def _animate_method(self, parent, method, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "METHOD", "⚙")
        method_frame = self._make_card(parent, themes.STEP_BG)
        name = method.get("name", "Algebraic Isolation")
        desc = method.get("description", "")
        params = method.get("parameters", {})
        param_lines = [f"  {k.replace('_', ' ').title()}:  {v}" for k, v in params.items()]

        def _after_name():
            if desc:
                self._type_label(method_frame, desc, self._small, themes.STEP_BG, themes.TEXT_DIM,
                                 wraplength=880, callback=_after_desc)
            else:
                _after_desc()

        def _after_desc():
            self._type_input_lines(method_frame, param_lines, 0)

        self._type_label(method_frame, name, self._bold, themes.STEP_BG, themes.ACCENT,
                         callback=_after_name)

    def _animate_step(self, parent, step, status_lbl):
        status_lbl.destroy()

        if not getattr(self, '_steps_header_shown', False):
            self._steps_header_shown = True
            self._render_section_header(parent, "STEPS", "»")

        wrapper = tk.Frame(parent, bg=themes.STEP_BORDER, padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=4)
        card = tk.Frame(wrapper, bg=themes.STEP_BG, padx=14, pady=10)
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
                                           bg=themes.STEP_BG, fg=themes.ACCENT)
                w.pack(anchor="w", pady=(2, 0))
                _after_expr()
            else:
                self._type_label(card, expr_text, self._mono, themes.STEP_BG, themes.ACCENT,
                                 callback=_after_expr)

        def _after_expr():
            if expl_text:
                self._animate_explanation(card, expl_text, _done)
            else:
                _done()

        def _done():
            self._scroll_to_bottom()
            self._schedule_next()

        self._type_label(card, desc, self._bold, themes.STEP_BG, themes.TEXT_BRIGHT,
                         callback=_after_desc)

    def _animate_explanation(self, card, expl_text, callback):
        """Type an explanation and add the collapsible toggle."""
        toggle_frame = tk.Frame(card, bg=themes.STEP_BG)
        toggle_frame.pack(fill=tk.X, pady=(4, 0))

        content = tk.Frame(card, bg=themes.STEP_BG)
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
                bg=themes.STEP_BORDER, fg=themes.ACCENT,
                activebackground=themes.STEP_BG,
                activeforeground=themes.ACCENT_HOVER,
                bd=0, cursor="hand2",
                anchor="w", padx=10, pady=4,
                relief=tk.FLAT, highlightthickness=1,
                highlightbackground=themes.STEP_BORDER,
                highlightcolor=themes.ACCENT,
            )
            btn.configure(command=lambda b=btn: _toggle(b=b))
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=themes.STEP_BG, fg=themes.ACCENT_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=themes.STEP_BORDER, fg=themes.ACCENT))
            btn.pack(anchor="w", pady=(2, 0))
            if callback:
                callback()

        self._type_label(content, expl_text, self._small, themes.STEP_BG, themes.TEXT_DIM,
                         wraplength=840, callback=_after_typed)

    def _animate_answer(self, parent, final_answer, status_lbl,
                        educational: bool = False):
        status_lbl.destroy()
        if educational:
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
            ans_frame = tk.Frame(parent, bg=themes.SUCCESS, padx=1, pady=1)
            ans_frame.pack(fill=tk.X, pady=(2, 4))
            ans_inner = tk.Frame(ans_frame, bg=themes.VERIFY_BG, padx=16, pady=12)
            ans_inner.pack(fill=tk.X)
            lines = final_answer.split("\n")
            self._type_answer_lines(ans_inner, lines, 0)

    def _type_answer_lines(self, parent, lines, idx,
                           bg=None, fg=None):
        _bg = bg if bg is not None else themes.VERIFY_BG
        _fg = fg if fg is not None else themes.TEXT_BRIGHT
        if idx < len(lines):
            line_text = lines[idx]
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

        container = tk.Frame(parent, bg=themes.BOT_BG)
        container.pack(fill=tk.X, pady=(8, 0))

        content = tk.Frame(container, bg=themes.VERIFY_BG, padx=14, pady=10)
        animated = {"done": False}

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
                if not animated["done"]:
                    animated["done"] = True
                    self._type_verify_steps(c, v_steps, 0)

        _init_text = "▾ Hide Verification" if _auto_expand else "▸ Show Verification"
        btn = tk.Button(
            container, text=_init_text, font=self._bold,
            bg=themes.BOT_BG, fg=themes.SUCCESS,
            activebackground=themes.BOT_BG,
            activeforeground=themes.SUCCESS,
            bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

        if _auto_expand:
            content.pack(fill=tk.X)
            animated["done"] = True
            self._type_verify_steps(content, v_steps, 0)

        self._schedule_next()

    def _type_verify_steps(self, parent, steps, idx):
        if idx < len(steps):
            step = steps[idx]

            wrapper = tk.Frame(parent, bg=themes.STEP_BORDER, padx=1, pady=1)
            wrapper.pack(fill=tk.X, pady=4)
            card = tk.Frame(wrapper, bg=themes.STEP_BG, padx=14, pady=10)
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
                                               bg=themes.STEP_BG, fg=themes.ACCENT)
                    w.pack(anchor="w", pady=(2, 0))
                    _after_expr()
                else:
                    self._type_label(card, expr_text, self._mono, themes.STEP_BG, themes.ACCENT,
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

            self._type_label(card, desc, self._bold, themes.STEP_BG, themes.TEXT_BRIGHT,
                             callback=_after_desc)
        else:
            self._scroll_to_bottom()

    def _animate_summary(self, parent, summary, status_lbl):
        status_lbl.destroy()
        self._render_section_header(parent, "SUMMARY", "■")
        sum_frame = self._make_card(parent, themes.STEP_BG)
        details = [
            ("Runtime", f"{summary.get('runtime_ms', '?')} ms"),
            ("Steps", str(summary.get('total_steps', '?'))),
            ("Verification Steps", str(summary.get('verification_steps', '?'))),
            ("Validation Status", summary.get('validation_status', '?').upper()),
            ("Timestamp", summary.get('timestamp', '?')),
            ("Library", summary.get('library', '?')),
        ]
        self._type_summary_rows(sum_frame, details, 0)

    def _type_summary_rows(self, parent, details, idx):
        if idx < len(details):
            label, value = details[idx]
            row = tk.Frame(parent, bg=themes.STEP_BG)
            row.pack(fill=tk.X, pady=1)
            full_text = f"  {label}:  {value}"
            lbl = tk.Label(row, text="", font=self._small,
                           bg=themes.STEP_BG, fg=themes.TEXT_DIM, anchor="w")
            lbl.pack(side=tk.LEFT)
            self._type_chars(lbl, full_text, 0,
                             lambda: self._type_summary_rows(parent, details, idx + 1))
        else:
            self._scroll_to_bottom()
            self._schedule_next()
