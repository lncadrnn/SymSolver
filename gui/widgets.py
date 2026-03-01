"""
DualSolver — Widget helpers & graph/analysis mixin

Reusable rendering primitives (section headers, cards, fraction widgets)
and the collapsible graph + analysis panel.
"""

import re
import tkinter as tk

from gui import themes


class WidgetMixin:
    """Mixed into DualSolverApp — UI building blocks and graph panel."""

    # Pattern to split on fraction markers ⟦numerator|denominator⟧
    _FRAC_RE = re.compile(r'⟦([^|⟧]+)\|([^⟧]+)⟧')

    # ── Section headers ────────────────────────────────────────────────

    def _render_section_header(self, parent: tk.Frame, title: str,
                               icon: str = "") -> None:
        header = tk.Frame(parent, bg=themes.BOT_BG)
        header.pack(fill=tk.X, pady=(14, 4))
        label_text = f"{icon}  {title}" if icon else title
        tk.Label(header, text=label_text, font=self._bold,
                 bg=themes.BOT_BG, fg=themes.ACCENT, anchor="w").pack(fill=tk.X)
        tk.Frame(header, bg=themes.ACCENT, height=1).pack(fill=tk.X, pady=(2, 0))

    def _render_section_header_colored(self, parent: tk.Frame, title: str,
                                       icon: str = "", fg: str = "") -> None:
        _fg = fg or themes.ACCENT
        header = tk.Frame(parent, bg=themes.BOT_BG)
        header.pack(fill=tk.X, pady=(14, 4))
        label_text = f"{icon}  {title}" if icon else title
        tk.Label(header, text=label_text, font=self._bold,
                 bg=themes.BOT_BG, fg=_fg, anchor="w").pack(fill=tk.X)
        tk.Frame(header, bg=_fg, height=1).pack(fill=tk.X, pady=(2, 0))

    # ── Card wrapper ───────────────────────────────────────────────────

    def _make_card(self, parent: tk.Frame, bg: str) -> tk.Frame:
        wrapper = tk.Frame(parent, bg=themes.STEP_BORDER, padx=1, pady=1)
        wrapper.pack(fill=tk.X, pady=4)
        card = tk.Frame(wrapper, bg=bg, padx=14, pady=10)
        card.pack(fill=tk.X)
        return card

    # ── Fraction-aware math expression renderer ────────────────────────

    def _render_math_expr(self, parent: tk.Frame, text: str,
                          font=None, bg: str | None = None,
                          fg: str = "#0F4C75") -> tk.Frame:
        """Render *text*, replacing ⟦num|den⟧ with stacked fractions."""
        if font is None:
            font = self._mono
        if bg is None:
            bg = themes.STEP_BG

        container = tk.Frame(parent, bg=bg)
        container.pack(fill=tk.X)

        lines = text.split("\n")
        for line_text in lines:
            line_frame = tk.Frame(container, bg=bg)
            line_frame.pack(anchor="w")

            parts = self._FRAC_RE.split(line_text)
            idx = 0
            while idx < len(parts):
                if idx % 3 == 0:
                    seg = parts[idx]
                    if seg:
                        tk.Label(line_frame, text=seg, font=font,
                                 bg=bg, fg=fg).pack(side=tk.LEFT)
                elif idx % 3 == 1:
                    num = parts[idx]
                    den = parts[idx + 1] if idx + 1 < len(parts) else ""
                    self._make_fraction_widget(line_frame, num, den, bg, fg)
                    idx += 1
                idx += 1

        return container

    def _make_fraction_widget(self, parent: tk.Frame,
                              numerator: str, denominator: str,
                              bg: str, fg: str) -> None:
        frac_frame = tk.Frame(parent, bg=bg)
        frac_frame.pack(side=tk.LEFT, padx=2)

        tk.Label(frac_frame, text=numerator.strip(), font=self._frac,
                 bg=bg, fg=fg).pack()
        bar = tk.Frame(frac_frame, bg=fg, height=2)
        bar.pack(fill=tk.X, padx=2, pady=1)
        tk.Label(frac_frame, text=denominator.strip(), font=self._frac,
                 bg=bg, fg=fg).pack()

    # ── Analysis card typing ───────────────────────────────────────────

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

    # ── Case badge colours ─────────────────────────────────────────────

    def _get_case_colors(self):
        return themes.LIGHT_CASE_COLORS if self._theme == "light" else themes.DARK_CASE_COLORS

    # ── Collapsible Graph & Analysis panel ─────────────────────────────

    def _animate_graph(self, parent, result):
        try:
            from solver.graph import analyze_result
            analysis = analyze_result(result)
        except Exception:
            analysis = None

        try:
            from solver.graph import build_figure
            fig = build_figure(result)
        except Exception:
            fig = None

        if analysis is None and fig is None:
            self._schedule_next()
            return

        self._render_section_header(parent, "GRAPH & ANALYSIS", "Δ")

        container = tk.Frame(parent, bg=themes.BOT_BG)
        container.pack(fill=tk.X, pady=(4, 0))

        content = tk.Frame(container, bg=themes.STEP_BG)
        drawn = {"done": False}
        _auto_expand = self._show_graph
        visible = tk.BooleanVar(value=_auto_expand)

        def _build_content(c=content, cb=None):
            if drawn["done"]:
                return
            drawn["done"] = True

            if fig is not None:
                try:
                    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                    canvas = FigureCanvasTkAgg(fig, master=c)
                    canvas.draw()
                    widget = canvas.get_tk_widget()
                    widget.configure(bg=themes.STEP_BG, highlightthickness=0)
                    widget.pack(fill=tk.X, padx=2, pady=(8, 4))
                    self._graph_panels.append((fig, canvas, widget))
                except Exception as exc:
                    tk.Label(c, text=f"Graph error: {exc}", font=self._small,
                             bg=themes.STEP_BG, fg=themes.ERROR, anchor="w").pack(fill=tk.X, padx=8)

            if analysis is None:
                if cb:
                    cb()
                return

            colors = self._get_case_colors().get(
                analysis.get("case", ""),
                {"bg": themes.STEP_BG, "border": themes.ACCENT, "fg": themes.ACCENT},
            )
            card_bg     = colors["bg"]
            card_border = colors["border"]
            card_fg     = colors["fg"]

            outer = tk.Frame(c, bg=card_border, padx=1, pady=1)
            outer.pack(fill=tk.X, padx=2, pady=(4, 8))
            card = tk.Frame(outer, bg=card_bg, padx=16, pady=12)
            card.pack(fill=tk.X)

            items = [("bold", analysis["case_label"], card_fg)]
            items.append(("small", "General form:", themes.TEXT_DIM))
            for line in analysis["form"].split("\n"):
                items.append(("mono", f"  {line}", themes.TEXT_BRIGHT))
            items.append(("sep", None, card_border))
            for line in analysis["description"].split("\n"):
                items.append(("small", line, themes.TEXT_DIM))
            if analysis.get("detail"):
                items.append(("mono", f"\n  Condition:  {analysis['detail']}", themes.TEXT_DIM))
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

        _init_graph_text = ("\u25be Hide Graph & Analysis" if _auto_expand
                            else "\u25b8 Show Graph & Analysis")
        btn = tk.Button(
            container, text=_init_graph_text, font=self._bold,
            bg=themes.BOT_BG, fg=themes.SUCCESS,
            activebackground=themes.BOT_BG,
            activeforeground=themes.SUCCESS,
            bd=0, cursor="hand2", anchor="w",
        )
        btn.configure(command=lambda b=btn: _toggle(b=b))
        btn.pack(anchor="w")

        if _auto_expand:
            content.pack(fill=tk.X)
            _build_content(cb=self._schedule_next)
        else:
            self._schedule_next()
