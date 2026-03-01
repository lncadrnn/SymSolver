"""Tests for the numerical (NumPy) solver and the engine dispatcher."""

import pytest
import numpy as np

from solver import engine
from solver.numerical import solve_numeric, _fmt_num


# ── _fmt_num helper ──────────────────────────────────────────────────────

class TestFmtNum:
    def test_integer(self):
        assert _fmt_num(7.0) == "7"

    def test_clean_decimal(self):
        assert _fmt_num(2.5) == "2.5"

    def test_trailing_zeros_stripped(self):
        result = _fmt_num(1.50000)
        assert result == "1.5"

    def test_very_small_rounds_to_int(self):
        assert _fmt_num(3.0000000000001) == "3"


# ── Single-variable numeric solve ───────────────────────────────────────

class TestSolveNumericSingle:
    def test_basic_equation(self):
        result = solve_numeric("2x + 3 = 7")
        assert "x = 2" in result["final_answer"]
        assert "NumPy" in result["summary"]["library"]

    def test_fractional_result(self):
        result = solve_numeric("3x + 1 = 2")
        # x = 1/3 ≈ 0.3333…
        answer = result["final_answer"]
        assert "x =" in answer
        # Should be a decimal, not a fraction
        val = float(answer.split("=")[1].strip())
        assert abs(val - 1/3) < 1e-9

    def test_negative_result(self):
        result = solve_numeric("x + 10 = 3")
        answer = result["final_answer"]
        val = float(answer.split("=")[1].strip())
        assert abs(val - (-7)) < 1e-9

    def test_has_required_fields(self):
        result = solve_numeric("2x + 2 = 5")
        required = {"equation", "given", "method", "steps",
                     "final_answer", "verification_steps", "summary"}
        assert required.issubset(set(result.keys()))

    def test_summary_fields(self):
        result = solve_numeric("x = 5")
        s = result["summary"]
        assert isinstance(s["runtime_ms"], (int, float))
        assert s["runtime_ms"] >= 0
        assert "NumPy" in s["library"]
        assert s["validation_status"] == "pass"


# ── System of equations numeric solve ────────────────────────────────────

class TestSolveNumericSystem:
    def test_two_by_two_system(self):
        result = solve_numeric("x + y = 10, x - y = 2")
        answer = result["final_answer"]
        assert "x =" in answer
        assert "y =" in answer
        # x=6, y=4
        lines = answer.strip().split("\n")
        vals = {}
        for line in lines:
            var, val = line.split("=")
            vals[var.strip()] = float(val.strip())
        assert abs(vals["x"] - 6) < 1e-9
        assert abs(vals["y"] - 4) < 1e-9
        assert "NumPy" in result["summary"]["library"]

    def test_system_verification_present(self):
        result = solve_numeric("2a + b = 5, a - b = 1")
        assert len(result["verification_steps"]) > 0

    def test_system_matrix_step(self):
        result = solve_numeric("x + y = 10, x - y = 2")
        step_descs = [s["description"] for s in result["steps"]]
        assert any("matrix" in d.lower() or "coefficient" in d.lower()
                    for d in step_descs)


# ── Nonlinear detection still works ─────────────────────────────────────

class TestNumericNonlinear:
    def test_quadratic_rejected(self):
        result = solve_numeric("x^2 + 1 = 0")
        assert result.get("nonlinear_education") is True

    def test_transcendental_rejected(self):
        result = solve_numeric("sin(x) = 0")
        assert result.get("nonlinear_education") is True


# ── Multi-variable numeric (single equation, multiple unknowns) ──────────

class TestNumericMultiVar:
    def test_two_var_single_eq(self):
        result = solve_numeric("2x + 4y = 1")
        answer = result["final_answer"]
        assert "x =" in answer or "y =" in answer

    def test_invalid_input(self):
        with pytest.raises(ValueError, match="must contain '='"):
            solve_numeric("2x + 3")


# ── Engine dispatcher ────────────────────────────────────────────────────

class TestDispatcher:
    def test_default_mode_is_symbolic(self):
        result = engine.solve_linear_equation("2x + 3 = 7")
        assert "SymPy" in result["summary"]["library"]

    def test_symbolic_mode_explicit(self):
        result = engine.solve_linear_equation("2x + 3 = 7", mode="symbolic")
        assert "SymPy" in result["summary"]["library"]

    def test_numerical_mode(self):
        result = engine.solve_linear_equation("2x + 3 = 7", mode="numerical")
        assert "NumPy" in result["summary"]["library"]

    def test_both_modes_same_answer(self):
        sym = engine.solve_linear_equation("5x - 2 = 3x + 8", mode="symbolic")
        num = engine.solve_linear_equation("5x - 2 = 3x + 8", mode="numerical")
        # Both should find x = 5
        assert "5" in sym["final_answer"]
        assert "5" in num["final_answer"]

    def test_system_both_modes(self):
        sym = engine.solve_linear_equation("x + y = 10, x - y = 2", mode="symbolic")
        num = engine.solve_linear_equation("x + y = 10, x - y = 2", mode="numerical")
        assert "x =" in sym["final_answer"]
        assert "x =" in num["final_answer"]
