import pytest
from sympy import symbols, sympify

from solver import engine


def test_detect_variables_and_expand_implicit_vars() -> None:
    assert engine._detect_variables("3x + 2 = 7") == ["x"]
    assert engine._detect_variables("as + in = 1") == ["a", "i", "n", "s"]
    expanded = engine._expand_implicit_vars("as + in + x", {"a", "s", "i", "n", "x"})
    assert expanded == "a*s + i*n + x"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("3x+2=7", "3x + 2 = 7"),
        ("x-2=1", "x - 2 = 1"),
        ("(x+1)/2=3", "⟦x+1|2⟧ = 3"),
    ],
)
def test_formatting_helpers(raw: str, expected: str) -> None:
    lhs_raw, rhs_raw = raw.split("=")
    assert engine._format_input_eq(lhs_raw, rhs_raw) == expected


def test_expression_helpers() -> None:
    x = symbols("x")
    expr = engine._parse_side("2x + 1", x)
    assert str(expr) == "2*x + 1"
    assert engine._to_superscript("12-3") == "¹²⁻³"
    assert engine._frac("1", "2") == "⟦1|2⟧"
    assert "π" in engine._prettify_symbols("2pi + sqrt(x)")
    assert "√(" in engine._prettify_symbols("sqrt(x)")
    assert engine._normalize_spacing("2x+3=5-1") == "2x + 3 = 5 - 1"
    assert "⟦x|2⟧" in engine._format_expr(x / 2)
    assert "⟦" not in engine._format_expr_plain(x / 2)


def test_degree_and_nonlinear_detectors() -> None:
    x, y = symbols("x y")
    assert engine._degree_name(2) == "quadratic"
    assert engine._degree_name(7) == "degree-7 polynomial"
    assert engine._has_transcendental(sympify("sin(x) + 1"), x)
    assert engine._has_var_in_denominator(sympify("1/x + 2"), x)
    assert engine._detect_nonlinear_reason(sympify("x*y + 1"), [x, y], 2) == "product"
    assert "quadratic" in engine._build_educational_message("degree", 2, ["x"]).lower()


def test_count_terms_and_character_validation() -> None:
    assert engine._count_terms_in_str("2x + 5x + 3") == 3
    assert engine._count_terms_in_str("3(x + 4)") == 1
    with pytest.raises(ValueError):
        engine._validate_characters("2x @ 1 = 0")


def test_solve_linear_equation_required_fields_type_and_range_checks() -> None:
    result = engine.solve_linear_equation("2x + 2 = 5")

    required_fields = {
        "equation",
        "given",
        "method",
        "steps",
        "final_answer",
        "verification_steps",
        "summary",
    }
    assert required_fields.issubset(set(result.keys()))

    summary = result["summary"]
    assert isinstance(summary["runtime_ms"], (int, float)) and summary["runtime_ms"] >= 0
    assert isinstance(summary["total_steps"], int) and summary["total_steps"] >= 0
    assert isinstance(summary["verification_steps"], int) and summary["verification_steps"] >= 0
    assert summary["validation_status"] == "pass"


def test_nonlinear_trail_logs_validation_fail() -> None:
    result = engine.solve_linear_equation("x^2 + 1 = 0")
    assert result.get("nonlinear_education") is True
    assert result["summary"]["validation_status"] == "fail"


def test_system_solution_trail_logs_validation_pass() -> None:
    result = engine.solve_linear_equation("x + y = 10, x - y = 2")
    assert "x =" in result["final_answer"]
    assert "y =" in result["final_answer"]
    assert result["summary"]["validation_status"] == "pass"


def test_invalid_input_missing_equal_sign() -> None:
    with pytest.raises(ValueError, match="must contain '='"):
        engine.solve_linear_equation("2x + 3")


def test_invalid_input_multiple_equal_signs() -> None:
    with pytest.raises(ValueError, match="exactly one '='"):
        engine.solve_linear_equation("x = 1 = 2")


def test_invalid_input_bad_characters() -> None:
    with pytest.raises(ValueError, match="Invalid character"):
        engine.solve_linear_equation("3x + 2 = 7$")
