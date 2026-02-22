"""
SymSolver — Export / clipboard mixin

Provides PDF export (with embedded graph) and plain-text clipboard copy.
"""

import os
import re
import tkinter as tk
from tkinter import font as tkfont, filedialog

from gui import themes


class ExportMixin:
    """Mixed into SymSolverApp — adds copy-to-clipboard and PDF export."""

    # ── Fraction normaliser (used by plain text and PDF) ───────────────

    @staticmethod
    def _frac_to_plain(text: str) -> str:
        """Convert fraction markers ⟦num|den⟧ to (num)/(den) for plain text."""
        return re.sub(r'⟦([^|⟧]+)\|([^⟧]+)⟧', r'(\1)/(\2)', text)

    # ── Plain-text builder (clipboard) ─────────────────────────────────

    def _build_plain_text(self, result: dict) -> str:
        """Convert a solver result dict into a readable plain-text trail."""
        lines: list[str] = []
        lines.append("=" * 56)
        lines.append("  SymSolver — Solution Trail")
        lines.append("=" * 56)

        # GIVEN
        given = result.get("given", {})
        lines.append("\n── GIVEN ──────────────────────────────────")
        if given.get("problem"):
            lines.append(self._frac_to_plain(given["problem"]))
        for key, val in given.get("inputs", {}).items():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {self._frac_to_plain(val)}")

        # METHOD
        method = result.get("method", {})
        lines.append("\n── METHOD ─────────────────────────────────")
        if method.get("name"):
            lines.append(f"  {method['name']}")
        if method.get("description"):
            lines.append(f"  {method['description']}")
        for key, val in method.get("parameters", {}).items():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {val}")

        # STEPS
        steps = result.get("steps", [])
        lines.append("\n── STEPS ──────────────────────────────────")
        for step in steps:
            num = step.get("step_number", "?")
            lines.append(f"\n  Step {num}: {self._frac_to_plain(step.get('description', ''))}")
            if step.get("expression"):
                lines.append(f"    {self._frac_to_plain(step['expression'])}")
            if step.get("explanation"):
                lines.append(f"    → {self._frac_to_plain(step['explanation'])}")

        # FINAL ANSWER
        lines.append("\n── FINAL ANSWER ───────────────────────────")
        lines.append(f"  {self._frac_to_plain(result.get('final_answer', '?'))}")

        # VERIFICATION
        v_steps = result.get("verification_steps", [])
        if v_steps:
            lines.append("\n── VERIFICATION ───────────────────────────")
            for step in v_steps:
                num = step.get("step_number", "?")
                lines.append(f"\n  Step {num}: {self._frac_to_plain(step.get('description', ''))}")
                if step.get("expression"):
                    lines.append(f"    {self._frac_to_plain(step['expression'])}")
                if step.get("explanation"):
                    lines.append(f"    → {self._frac_to_plain(step['explanation'])}")

        # SUMMARY
        summary = result.get("summary", {})
        if summary:
            lines.append("\n── SUMMARY ────────────────────────────────")
            lines.append(f"  Runtime: {summary.get('runtime_ms', '?')} ms")
            lines.append(f"  Steps: {summary.get('total_steps', '?')}")
            lines.append(f"  Verification Steps: {summary.get('verification_steps', '?')}")
            lines.append(f"  Timestamp: {summary.get('timestamp', '?')}")
            lines.append(f"  Library: {summary.get('library', '?')}")

        lines.append("\n" + "=" * 56)
        return "\n".join(lines)

    # ── Export bar (buttons below the solution) ────────────────────────

    def _add_export_bar(self, parent: tk.Frame, result: dict) -> None:
        """Add a copy/save action bar at the bottom of the bot message."""
        p = themes.palette(self._theme)
        bar = tk.Frame(parent, bg=p["BOT_BG"])
        bar.pack(fill=tk.X, pady=(12, 0))

        btn_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        copy_btn = tk.Button(
            bar, text="📋 Copy to Clipboard", font=btn_font,
            bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
            activebackground=p["ACCENT"], activeforeground="#ffffff",
            bd=0, padx=14, pady=6, cursor="hand2", relief=tk.FLAT,
            command=lambda: self._copy_to_clipboard(result, copy_btn),
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 8))

        save_btn = tk.Button(
            bar, text="📄 Save as PDF", font=btn_font,
            bg=p["STEP_BG"], fg=p["TEXT_BRIGHT"],
            activebackground=p["ACCENT"], activeforeground="#ffffff",
            bd=0, padx=14, pady=6, cursor="hand2", relief=tk.FLAT,
            command=lambda: self._save_as_pdf(result),
        )
        save_btn.pack(side=tk.LEFT)

    # ── Clipboard ──────────────────────────────────────────────────────

    def _copy_to_clipboard(self, result: dict, btn: tk.Button) -> None:
        """Copy the full solution trail as plain text to the clipboard."""
        text = self._build_plain_text(result)
        self.clipboard_clear()
        self.clipboard_append(text)
        original = btn.cget("text")
        btn.configure(text="✓ Copied!")
        self.after(1500, lambda: btn.configure(text=original))

    # ── PDF export ─────────────────────────────────────────────────────

    @staticmethod
    def _safe_filename(equation: str) -> str:
        safe = re.sub(r'[<>:"/\\|?*]', '', equation)[:50].strip()
        return re.sub(r'\s+', '', safe)

    def _save_as_pdf(self, result: dict) -> None:
        """Export the full solution trail as a styled PDF with graph & analysis."""
        eq = result.get("equation", "equation").strip()
        safe = self._safe_filename(eq)
        path = filedialog.asksaveasfilename(
            title="Save Solution as PDF",
            defaultextension=".pdf",
            initialfile=f"SymSolver_{safe}",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return

        import tempfile
        try:
            from fpdf import FPDF
        except ImportError:
            from tkinter import messagebox
            messagebox.showerror("Missing dependency",
                                 "PDF export requires 'fpdf2'.\n\n"
                                 "Install it with:  pip install fpdf2")
            return

        # ── Set up PDF ──────────────────────────────────────────────
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Register Unicode fonts
        fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        try:
            pdf.add_font("Arial", "", os.path.join(fonts_dir, "arial.ttf"))
            pdf.add_font("Arial", "B", os.path.join(fonts_dir, "arialbd.ttf"))
            pdf.add_font("Consolas", "", os.path.join(fonts_dir, "consola.ttf"))
            _font = "Arial"
            _mono = "Consolas"
        except Exception:
            _font = "Helvetica"
            _mono = "Courier"

        frac = self._frac_to_plain

        def safe(text: str) -> str:
            """Replace glyphs missing from embedded PDF fonts."""
            return (
                text
                .replace('\u2713', 'OK')    # ✓
                .replace('\u2714', 'OK')    # ✔
                .replace('\u27A4', '->')    # ➤
            )

        # ── Title ───────────────────────────────────────────────────
        pdf.set_font(_font, "B", 20)
        pdf.set_text_color(26, 140, 255)
        pdf.cell(0, 12, "SymSolver - Solution Trail", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(26, 140, 255)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        def _section(title: str) -> None:
            pdf.ln(4)
            pdf.set_font(_font, "B", 13)
            pdf.set_text_color(26, 140, 255)
            pdf.cell(0, 8, safe(title), new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(26, 140, 255)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(3)

        def _label_value(label: str, value: str) -> None:
            pdf.set_font(_font, "B", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(40, 6, safe(f"{label}:"), new_x="END")
            pdf.set_font(_mono, "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, safe(f"  {frac(value)}"), new_x="LMARGIN", new_y="NEXT")

        def _body(text: str, bold: bool = False, size: int = 10) -> None:
            pdf.set_font(_font, "B" if bold else "", size)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, safe(frac(text)), new_x="LMARGIN", new_y="NEXT")

        def _mono_text(text: str, size: int = 10) -> None:
            pdf.set_font(_mono, "", size)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, safe(frac(text)), new_x="LMARGIN", new_y="NEXT")

        # ── GIVEN ───────────────────────────────────────────────────
        given = result.get("given", {})
        _section("GIVEN")
        if given.get("problem"):
            _body(frac(given["problem"]), bold=True)
        for key, val in given.get("inputs", {}).items():
            _label_value(key.replace("_", " ").title(), val)

        # ── METHOD ──────────────────────────────────────────────────
        method = result.get("method", {})
        _section("METHOD")
        if method.get("name"):
            _body(method["name"], bold=True, size=12)
        if method.get("description"):
            _body(method["description"])
        for key, val in method.get("parameters", {}).items():
            _label_value(key.replace("_", " ").title(), val)

        # ── STEPS ───────────────────────────────────────────────────
        _section("STEPS")
        for step in result.get("steps", []):
            num = step.get("step_number", "?")
            pdf.ln(2)
            _body(f"Step {num}: {frac(step.get('description', ''))}", bold=True)
            if step.get("expression"):
                _mono_text(f"    {frac(step['expression'])}")
            if step.get("explanation"):
                pdf.set_font(_font, "", 9)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(0, 5, safe(f"    {frac(step['explanation'])}"), new_x="LMARGIN", new_y="NEXT")

        # ── FINAL ANSWER ────────────────────────────────────────────
        _section("FINAL ANSWER")
        pdf.set_font(_mono, "", 14)
        pdf.set_text_color(76, 175, 80)
        pdf.cell(0, 10, safe(frac(result.get("final_answer", "?"))), new_x="LMARGIN", new_y="NEXT")

        # ── VERIFICATION ────────────────────────────────────────────
        v_steps = result.get("verification_steps", [])
        if v_steps:
            _section("VERIFICATION")
            for step in v_steps:
                num = step.get("step_number", "?")
                pdf.ln(2)
                _body(f"Step {num}: {frac(step.get('description', ''))}", bold=True)
                if step.get("expression"):
                    _mono_text(f"    {frac(step['expression'])}")
                if step.get("explanation"):
                    pdf.set_font(_font, "", 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.multi_cell(0, 5, safe(f"    {frac(step['explanation'])}"), new_x="LMARGIN", new_y="NEXT")

        # ── GRAPH & ANALYSIS ────────────────────────────────────────
        graph_img_path = None
        try:
            from solver.graph import build_figure, analyze_result
            fig = build_figure(result)
            if fig is not None:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                fig.savefig(tmp.name, dpi=150, bbox_inches="tight",
                            facecolor="#ffffff", edgecolor="none")
                tmp.close()
                graph_img_path = tmp.name

                _section("GRAPH")
                img_w = pdf.w - 20
                pdf.image(graph_img_path, x=10, w=img_w)
                pdf.ln(4)

            analysis = analyze_result(result)
            if analysis:
                _section("ANALYSIS")
                _body(analysis.get("case_label", ""), bold=True, size=12)
                pdf.ln(1)
                _body(f"General form: {analysis.get('form', '')}")
                pdf.ln(1)
                _body(analysis.get("description", ""))
                if analysis.get("detail"):
                    _body(f"Condition: {analysis['detail']}")
                if analysis.get("solution"):
                    pdf.ln(2)
                    pdf.set_font(_mono, "", 12)
                    pdf.set_text_color(76, 175, 80)
                    pdf.cell(0, 8, safe(f"Result: {frac(analysis['solution'])}"), new_x="LMARGIN", new_y="NEXT")
        except Exception:
            pass

        # ── SUMMARY ─────────────────────────────────────────────────
        summary = result.get("summary", {})
        if summary:
            _section("SUMMARY")
            _label_value("Runtime", f"{summary.get('runtime_ms', '?')} ms")
            _label_value("Steps", str(summary.get('total_steps', '?')))
            _label_value("Verification Steps", str(summary.get('verification_steps', '?')))
            _label_value("Timestamp", summary.get('timestamp', '?'))
            _label_value("Library", summary.get('library', '?'))

        # ── Write ───────────────────────────────────────────────────
        try:
            pdf.output(path)
        except Exception as exc:
            from tkinter import messagebox
            messagebox.showerror("Export error", f"Could not save PDF:\n{exc}")
        finally:
            if graph_img_path:
                try:
                    os.remove(graph_img_path)
                except OSError:
                    pass
