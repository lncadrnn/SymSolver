"""SymSolver engine — dispatcher module.

Routes to the symbolic (SymPy) or numerical (NumPy) solver based on
the *mode* parameter.  Keeps backward-compatibility: calling
``solve_linear_equation(eq)`` without a mode still works and defaults
to symbolic.

All internal helpers that tests and other modules import from
`solver.engine` are re-exported from `solver.symbolic` so existing
imports continue to resolve.
"""

#  Re-export every public AND private name that existed before the split.
# This guarantees that `from solver.engine import X` keeps working for
# tests, the graph module, etc.
from solver.symbolic import (                         # noqa: F401
    # Constants / config
    TRANSFORMATIONS,
    _ALLOWED_VARS,
    _SUPERSCRIPT,
    _FRAC_OPEN,
    _FRAC_SEP,
    _FRAC_CLOSE,
    _SUP_CHARS,
    _BINARY_AFTER,
    _DEGREE_NAMES,
    _TRANS_FUNC_NAMES,
    # Helpers
    _detect_variables,
    _expand_implicit_vars,
    _parse_side,
    _to_superscript,
    _frac,
    _prettify_symbols,
    _normalize_spacing,
    _format_expr,
    _format_expr_plain,
    _format_input_str,
    _format_input_eq,
    _format_equation,
    _degree_name,
    _has_transcendental,
    _has_var_in_denominator,
    _detect_nonlinear_reason,
    _build_educational_message,
    _nonlinear_error_result,
    _count_terms_in_str,
    _validate_characters,
    _append_solution_step,
    # Original solver (symbolic)
    solve_linear_equation as _solve_symbolic,
)

from solver.numerical import solve_numeric as _solve_numeric


def solve_linear_equation(equation_str: str, *, mode: str = "symbolic") -> dict:
    """Solve a linear equation either symbolically or numerically.

    Parameters
    ----------
    equation_str : str
        The equation (or comma-separated system) to solve.
    mode : str, optional
        ``"symbolic"`` (default) — exact answer via SymPy.
        ``"numerical"`` — decimal approximation via NumPy.
    """
    if mode == "numerical":
        result = _solve_numeric(equation_str)
    else:
        result = _solve_symbolic(equation_str)

    # Inject computation type into the "given" section so the solution
    # trail shows which mode was used.
    if "given" in result and "inputs" in result["given"]:
        label = ("Numerical (NumPy)" if mode == "numerical"
                 else "Symbolic (SymPy)")
        result["given"]["inputs"]["computation"] = label

    return result


if __name__ == "__main__":
    tests = [
        "3x + 2 = 7",
        "x/3 + 1 = 4",
        "x + y = 10, x - y = 2",
    ]
    for eq in tests:
        for m in ("symbolic", "numerical"):
            print(f"\n{'='*50}")
            print(f"[{m.upper()}] Solving: {eq}")
            print('='*50)
            r = solve_linear_equation(eq, mode=m)
            print(f"  => {r['final_answer']}")
            print(f"  Library: {r['summary']['library']}")
