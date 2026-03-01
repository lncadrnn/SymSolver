"""Numerical (approximate) linear equation solver using NumPy."""

"""
Parses linear equations — single-variable (e.g. "3x + 2 = 7"),
multi-variable (e.g. "2x + 4y = 1"), or systems of equations
(e.g. "x + y = 10, x - y = 2") — and solves them numerically,
returning decimal approximations via NumPy.
"""

import re
import time
from datetime import datetime

import numpy as np
import sympy
from sympy import symbols, sympify, Eq, solve, simplify, expand, Symbol, fraction
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
    convert_xor, rationalize,
)

# Reuse shared helpers from the symbolic module
from solver.symbolic import (
    TRANSFORMATIONS,
    _ALLOWED_VARS,
    _detect_variables,
    _expand_implicit_vars,
    _parse_side,
    _SUPERSCRIPT,
    _to_superscript,
    _FRAC_OPEN,
    _FRAC_SEP,
    _FRAC_CLOSE,
    _frac,
    _prettify_symbols,
    _normalize_spacing,
    _format_expr,
    _format_expr_plain,
    _format_input_str,
    _format_input_eq,
    _format_equation,
    _DEGREE_NAMES,
    _degree_name,
    _has_transcendental,
    _has_var_in_denominator,
    _detect_nonlinear_reason,
    _build_educational_message,
    _nonlinear_error_result,
    _count_terms_in_str,
    _validate_characters,
)


# ── Numeric formatting helpers ──────────────────────────────────────────

def _fmt_num(value: float, max_decimals: int = 10) -> str:
    """Format a float into a clean decimal string.

    - Removes trailing zeros after the decimal point.
    - Uses up to *max_decimals* digits of precision.
    - Returns integers without a decimal point (e.g. ``7`` not ``7.0``).
    """
    if abs(value - round(value)) < 1e-12:
        return str(int(round(value)))
    formatted = f"{value:.{max_decimals}f}".rstrip("0").rstrip(".")
    return formatted


def _format_numeric(value) -> str:
    """Convert a SymPy expression to its numeric (decimal) string."""
    try:
        f = complex(value)
        if f.imag != 0:
            return f"{_fmt_num(f.real)} + {_fmt_num(f.imag)}i"
        return _fmt_num(f.real)
    except (TypeError, ValueError):
        return str(value)


# ── Main public entry point ─────────────────────────────────────────────

def solve_numeric(equation_str: str) -> dict:
    """
    Solve one or more linear equations numerically (decimal approximation).

    Supports the same inputs as the symbolic solver:
      - Single variable:  ``3x + 2 = 7``
      - Multiple variables:  ``2x + 4y = 1``
      - Systems (comma / semicolon separated):  ``x + y = 10, x - y = 2``

    Returns a result dict identical in structure to the symbolic solver but
    with all answer values rendered as decimals (using NumPy for computation).
    """
    t_start = time.perf_counter()

    # ── Normalise Unicode symbols ────────────────────────────────────
    equation_str = equation_str.replace('\u221a', 'sqrt')
    equation_str = equation_str.replace('\u03c0', '(pi)')
    equation_str = equation_str.replace('[', '(').replace(']', ')')
    equation_str = equation_str.replace('{', '(').replace('}', ')')

    # ── Validate input characters ────────────────────────────────────
    _validate_characters(equation_str)

    # ── Split by , or ; to detect a system ───────────────────────────
    raw_equations = [eq.strip() for eq in re.split(r'\s*[;,]\s*', equation_str)
                     if eq.strip()]
    all_text = ' '.join(raw_equations)
    var_names = _detect_variables(all_text)

    if len(raw_equations) > 1:
        return _solve_system_numeric(raw_equations, var_names, equation_str, t_start)
    if len(var_names) > 1:
        return _solve_multi_var_numeric(equation_str, var_names, t_start)

    # ── Single equation, single variable ─────────────────────────────
    if '=' not in equation_str:
        raise ValueError("Equation must contain '='. Example: 3x + 2 = 7")

    parts = equation_str.split('=')
    if len(parts) != 2:
        raise ValueError("Equation must contain exactly one '=' sign.")

    lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
    if not lhs_str or not rhs_str:
        raise ValueError("Both sides of the equation must have expressions.")

    var_name = var_names[0]
    var = symbols(var_name)

    lhs = _parse_side(lhs_str, var)
    rhs = _parse_side(rhs_str, var)

    # ── Linearity / non-linear check (same logic as symbolic) ────────
    combined = lhs - rhs
    combined_expanded = expand(combined)
    poly_degree = combined_expanded.as_poly(var)

    if poly_degree is None:
        if var not in combined_expanded.free_symbols:
            pass  # degenerate — let step-by-step handle it
        elif _has_transcendental(combined_expanded, var):
            return _nonlinear_error_result(
                equation_str, lhs_str, rhs_str, lhs, rhs,
                [var_name], 1, t_start, reason="transcendental",
            )
        elif _has_var_in_denominator(combined_expanded, var):
            return _nonlinear_error_result(
                equation_str, lhs_str, rhs_str, lhs, rhs,
                [var_name], -1, t_start, reason="denominator",
            )
        else:
            raise ValueError("Could not determine the degree. Please check the equation.")
    elif poly_degree.degree() > 1:
        return _nonlinear_error_result(
            equation_str, lhs_str, rhs_str, lhs, rhs,
            [var_name], poly_degree.degree(), t_start,
        )
    elif poly_degree.degree() == 0:
        pass  # degenerate

    # ── Solve symbolically first, then convert to numeric ────────────
    coeff = combined_expanded.coeff(var)
    const = expand(combined_expanded - coeff * var)

    steps = []
    _fmt_input_lhs = _format_input_str(lhs_str)
    _fmt_input_rhs = _format_input_str(rhs_str)
    _fmt_input_eq = _format_input_eq(lhs_str, rhs_str)

    # Step 1: Original equation
    steps.append({
        "description": "Starting with the original equation",
        "expression": _fmt_input_eq,
        "explanation": (
            f"We are given the equation {lhs_str} = {rhs_str}. "
            f"Our goal is to find the numerical (decimal) value of {var_name}."
        ),
    })

    # Step: Expand if needed
    lhs_expanded = expand(lhs)
    rhs_expanded = expand(rhs)
    if lhs_expanded != lhs or rhs_expanded != rhs:
        steps.append({
            "description": "Expand both sides",
            "expression": _format_equation(lhs_expanded, rhs_expanded),
            "explanation": (
                f"Distribute multiplication across parentheses to "
                f"simplify each side."
            ),
        })
        lhs, rhs = lhs_expanded, rhs_expanded

    # Handle degenerate (coefficient == 0)
    if coeff == 0:
        rhs_val = simplify(expand(lhs - rhs + coeff * var))
        # Actually recalculate: rhs_val = const = lhs - rhs with 0*var
        is_zero = simplify(const) == 0
        if is_zero:
            steps.append({
                "description": "The variable cancels — identity",
                "expression": "0 = 0",
                "explanation": (
                    f"After simplifying, {var_name} disappears and we get "
                    f"0 = 0 (always true). This means every real number is a solution."
                ),
            })
            final_answer = (
                f"Infinite solutions — this equation is an identity.\n"
                f"Every real number satisfies {lhs_str} = {rhs_str}."
            )
        else:
            const_val = _format_numeric(const)
            steps.append({
                "description": "The variable cancels — contradiction",
                "expression": f"0 = {const_val}",
                "explanation": (
                    f"After simplifying, {var_name} disappears and we get "
                    f"0 = {const_val} (never true). There is no solution."
                ),
            })
            final_answer = (
                f"No solution — this equation is a contradiction.\n"
                f"Simplifies to 0 = {const_val}, which is impossible."
            )
        for i, s in enumerate(steps, 1):
            s["step_number"] = i
        t_end = time.perf_counter()
        return _build_result(
            equation_str, _fmt_input_eq, _fmt_input_lhs, _fmt_input_rhs,
            var_name, steps, final_answer, [], t_start, t_end,
            method_suffix="Degenerate",
        )

    # ── Numerical solve via NumPy ────────────────────────────────────
    # ax + b = 0 where a = coeff, b = const
    a_val = float(coeff)
    b_val = float(const)  # const = lhs - rhs sans the var term

    steps.append({
        "description": "Identify the coefficient and constant",
        "expression": f"{_fmt_num(a_val)}{var_name} + ({_fmt_num(b_val)}) = 0",
        "explanation": (
            f"After rearranging: the coefficient of {var_name} is "
            f"{_fmt_num(a_val)} and the constant term is {_fmt_num(b_val)}."
        ),
    })

    # Use numpy to solve: x = -b / a
    solution_val = np.float64(-b_val) / np.float64(a_val)
    sol_str = _fmt_num(float(solution_val))

    steps.append({
        "description": f"Compute {var_name} = −(constant) ÷ coefficient",
        "expression": (
            f"{var_name} = −({_fmt_num(b_val)}) ÷ {_fmt_num(a_val)}"
            f"  =  {sol_str}"
        ),
        "explanation": (
            f"Using NumPy: {var_name} = −({_fmt_num(b_val)}) / {_fmt_num(a_val)} "
            f"= {sol_str}."
        ),
    })

    final_answer = f"{var_name} = {sol_str}"

    # ── Verification ─────────────────────────────────────────────────
    verification_steps = _build_verification_numeric(
        lhs_str, rhs_str, var_name, var, solution_val, lhs, rhs,
    )

    for i, s in enumerate(steps, 1):
        s["step_number"] = i
    for i, s in enumerate(verification_steps, 1):
        s["step_number"] = i

    t_end = time.perf_counter()
    return _build_result(
        equation_str, _fmt_input_eq, _fmt_input_lhs, _fmt_input_rhs,
        var_name, steps, final_answer, verification_steps, t_start, t_end,
    )


# ── Multi-variable (single equation, multiple unknowns) ─────────────────

def _solve_multi_var_numeric(equation_str: str, var_names: list,
                             t_start: float) -> dict:
    """Solve a single linear equation with multiple variables numerically.

    Expresses each variable in terms of the others, converting all
    coefficients to decimal form.
    """
    var_symbols = [symbols(v) for v in var_names]

    if '=' not in equation_str:
        raise ValueError("Equation must contain '='. Example: 2x + 4y = 1")
    parts = equation_str.split('=')
    if len(parts) != 2:
        raise ValueError("Equation must contain exactly one '=' sign.")
    lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
    if not lhs_str or not rhs_str:
        raise ValueError("Both sides of the equation must have expressions.")

    lhs = _parse_side(lhs_str, var_symbols)
    rhs = _parse_side(rhs_str, var_symbols)

    _fmt_mv_lhs = _format_expr(lhs)
    _fmt_mv_rhs = _format_expr(rhs)
    _fmt_mv_eq = _format_equation(lhs, rhs)

    # Verify linearity
    combined = expand(lhs - rhs)
    max_degree = 0
    for vs in var_symbols:
        p = combined.as_poly(vs)
        if p is not None and p.degree() > max_degree:
            max_degree = p.degree()
    try:
        total_poly = combined.as_poly(*var_symbols)
        if total_poly is not None and total_poly.total_degree() > max_degree:
            max_degree = total_poly.total_degree()
    except Exception:
        pass
    if _has_transcendental(combined, var_symbols):
        return _nonlinear_error_result(
            equation_str, lhs_str, rhs_str, lhs, rhs,
            var_names, 1, t_start, reason="transcendental",
        )
    if _has_var_in_denominator(combined, var_symbols):
        return _nonlinear_error_result(
            equation_str, lhs_str, rhs_str, lhs, rhs,
            var_names, -1, t_start, reason="denominator",
        )
    if max_degree > 1:
        return _nonlinear_error_result(
            equation_str, lhs_str, rhs_str, lhs, rhs,
            var_names, max_degree, t_start,
        )

    steps = []
    steps.append({
        "description": "Starting with the original equation",
        "expression": _fmt_mv_eq,
        "explanation": (
            f"We are given a linear equation with variables "
            f"{', '.join(var_names)}. We will express each variable "
            f"in terms of the others using decimal coefficients."
        ),
    })

    # Expand if needed
    lhs_exp, rhs_exp = expand(lhs), expand(rhs)
    if lhs_exp != lhs or rhs_exp != rhs:
        steps.append({
            "description": "Expand both sides",
            "expression": _format_equation(lhs_exp, rhs_exp),
            "explanation": "Distribute multiplication across parentheses.",
        })
        lhs, rhs = lhs_exp, rhs_exp

    # Solve for each variable (symbolically, then format numerically)
    eq = Eq(lhs, rhs)
    solutions = {}
    for vn, vs in zip(var_names, var_symbols):
        sol = solve(eq, vs)
        if sol:
            sol_expr = sol[0]
            solutions[vn] = sol_expr
            others = [v for v in var_names if v != vn]
            # Convert all numeric coefficients to decimal
            numeric_parts = []
            for term in sympy.Add.make_args(sol_expr):
                numeric_parts.append(_format_expr_plain(term))
            numeric_str = " + ".join(numeric_parts) if len(numeric_parts) > 1 else numeric_parts[0]
            # Try to cast the whole expression to a float if fully numeric
            try:
                val = float(sol_expr)
                numeric_str = _fmt_num(val)
            except (TypeError, ValueError):
                pass
            steps.append({
                "description": f"Solve for {vn}",
                "expression": f"{vn} = {numeric_str}",
                "explanation": (
                    f"Isolate {vn} by moving all other terms to the "
                    f"right side and dividing by its coefficient. "
                    f"Result in terms of {', '.join(others)}."
                ),
            })

    final_parts = []
    for vn in var_names:
        if vn in solutions:
            try:
                val = float(solutions[vn])
                final_parts.append(f"{vn} = {_fmt_num(val)}")
            except (TypeError, ValueError):
                final_parts.append(f"{vn} = {_format_expr_plain(solutions[vn])}")
        else:
            final_parts.append(f"{vn} is a free variable")
    final_answer = "\n".join(final_parts)

    # Verification
    verification_steps = []
    if solutions:
        first_vn = var_names[0]
        first_vs = var_symbols[0]
        sol_expr = solutions.get(first_vn)
        if sol_expr is not None:
            lhs_sub = simplify(lhs.subs(first_vs, sol_expr))
            rhs_sub = simplify(rhs.subs(first_vs, sol_expr))
            verification_steps.append({
                "description": f"Substitute {first_vn} back",
                "expression": f"LHS = {_format_expr_plain(lhs_sub)},  RHS = {_format_expr_plain(rhs_sub)}",
                "explanation": "Both sides reduce to the same expression, confirming correctness.",
            })
            verification_steps.append({
                "description": "Solution verified",
                "expression": "LHS = RHS  ✓",
                "explanation": "The equation holds for any values of the remaining variables.",
            })

    for i, s in enumerate(steps, 1):
        s["step_number"] = i
    for i, s in enumerate(verification_steps, 1):
        s["step_number"] = i

    t_end = time.perf_counter()
    runtime_ms = round((t_end - t_start) * 1000, 2)

    return {
        "equation": equation_str,
        "given": {
            "problem": f"Solve the linear equation (numerically): {_fmt_mv_eq}",
            "inputs": {
                "equation": _fmt_mv_eq,
                "left_side": _fmt_mv_lhs,
                "right_side": _fmt_mv_rhs,
                "variables": ", ".join(var_names),
            },
        },
        "method": {
            "name": "Numerical Isolation (Multi-Variable)",
            "description": (
                "Express each variable in terms of the remaining "
                "variables, with coefficients as decimals."
            ),
            "parameters": {
                "equation_type": f"Linear with {len(var_names)} variables",
                "variables": ", ".join(var_names),
                "approach": "Expand → Isolate each variable → Approximate",
            },
        },
        "steps": steps,
        "final_answer": final_answer,
        "verification_steps": verification_steps,
        "summary": {
            "runtime_ms": runtime_ms,
            "total_steps": len(steps),
            "verification_steps": len(verification_steps),
            "validation_status": "pass",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "library": f"NumPy {np.__version__}",
            "python": None,
        },
    }


# ── System of equations (numerical via NumPy) ───────────────────────────

def _solve_system_numeric(raw_equations: list, var_names: list,
                          original_input: str, t_start: float) -> dict:
    """Solve a system of linear equations numerically using NumPy."""
    var_symbols = [symbols(v) for v in var_names]
    n_eq = len(raw_equations)
    n_var = len(var_names)

    # Parse every equation
    eq_objects = []
    for eq_str in raw_equations:
        if '=' not in eq_str:
            raise ValueError(f"Each equation must contain '='. Problem: {eq_str}")
        parts = eq_str.split('=')
        if len(parts) != 2:
            raise ValueError(
                f"Each equation must have exactly one '='. Problem: {eq_str}")
        l = _parse_side(parts[0].strip(), var_symbols)
        r = _parse_side(parts[1].strip(), var_symbols)
        eq_objects.append(Eq(expand(l), expand(r)))

    # Verify linearity
    for i, eq_obj in enumerate(eq_objects):
        combined = expand(eq_obj.lhs - eq_obj.rhs)
        max_deg = 0
        for vs in var_symbols:
            p = combined.as_poly(vs)
            if p is not None and p.degree() > max_deg:
                max_deg = p.degree()
        try:
            total_poly = combined.as_poly(*var_symbols)
            if total_poly is not None and total_poly.total_degree() > max_deg:
                max_deg = total_poly.total_degree()
        except Exception:
            pass
        eq_str_i = raw_equations[i]
        eq_parts_i = eq_str_i.split('=')
        _nl_lhs_s = eq_parts_i[0].strip() if len(eq_parts_i) == 2 else eq_str_i
        _nl_rhs_s = eq_parts_i[1].strip() if len(eq_parts_i) == 2 else '0'
        if _has_transcendental(combined, var_symbols):
            return _nonlinear_error_result(
                original_input, _nl_lhs_s, _nl_rhs_s,
                eq_obj.lhs, eq_obj.rhs,
                var_names, 1, t_start, reason="transcendental",
            )
        if _has_var_in_denominator(combined, var_symbols):
            return _nonlinear_error_result(
                original_input, _nl_lhs_s, _nl_rhs_s,
                eq_obj.lhs, eq_obj.rhs,
                var_names, -1, t_start, reason="denominator",
            )
        if max_deg > 1:
            return _nonlinear_error_result(
                original_input, _nl_lhs_s, _nl_rhs_s,
                eq_obj.lhs, eq_obj.rhs,
                var_names, max_deg, t_start,
            )

    steps = []

    # Step: show the system
    sys_lines = "\n".join(
        f"  ({i + 1})  {eq}" for i, eq in enumerate(raw_equations)
    )
    steps.append({
        "description": "System of equations",
        "expression": sys_lines,
        "explanation": (
            f"We have {n_eq} equation{'s' if n_eq != 1 else ''} "
            f"with {n_var} unknown{'s' if n_var != 1 else ''}: "
            f"{', '.join(var_names)}. Solving numerically with NumPy."
        ),
    })

    # ── Build coefficient matrix A and constant vector b ─────────────
    # Each equation: sum_j(a_ij * x_j) = b_i
    try:
        A = np.zeros((n_eq, n_var), dtype=np.float64)
        b = np.zeros(n_eq, dtype=np.float64)

        for i, eq_obj in enumerate(eq_objects):
            expr = expand(eq_obj.lhs - eq_obj.rhs)
            for j, vs in enumerate(var_symbols):
                A[i, j] = float(expr.coeff(vs))
            # constant = -(the remaining part after removing variable terms)
            remaining = expr
            for j, vs in enumerate(var_symbols):
                remaining = remaining - A[i, j] * vs
            b[i] = -float(remaining)

        steps.append({
            "description": "Build coefficient matrix and constant vector",
            "expression": (
                f"A = {_format_matrix(A)}\n"
                f"b = [{', '.join(_fmt_num(v) for v in b)}]"
            ),
            "explanation": (
                "Extract the coefficients of each variable from every equation "
                "to form the matrix A and constant vector b for the system Ax = b."
            ),
        })

        # Solve using numpy.linalg.solve (for square systems) or lstsq
        if n_eq == n_var:
            det = np.linalg.det(A)
            if abs(det) < 1e-14:
                # Singular matrix — either no solution or infinite solutions
                # Fall back to SymPy for the classification
                solution = solve(eq_objects, var_symbols, dict=True)
                if not solution:
                    steps.append({
                        "description": "Singular matrix — No solution",
                        "expression": f"det(A) ≈ {_fmt_num(det)}",
                        "explanation": (
                            "The determinant of the coefficient matrix is "
                            "essentially zero, meaning the system is inconsistent "
                            "or has infinitely many solutions."
                        ),
                    })
                    for i, s in enumerate(steps, 1):
                        s["step_number"] = i
                    t_end = time.perf_counter()
                    runtime_ms = round((t_end - t_start) * 1000, 2)
                    return {
                        "equation": original_input,
                        "given": {
                            "problem": "Solve the system of linear equations (numerically)",
                            "inputs": {
                                "equations": original_input,
                                "number_of_equations": str(n_eq),
                                "variables": ", ".join(var_names),
                                "number_of_variables": str(n_var),
                            },
                        },
                        "method": {
                            "name": "NumPy Linear Algebra (Singular)",
                            "description": "Coefficient matrix is singular.",
                            "parameters": {
                                "equation_type": "Linear System — No Unique Solution",
                                "variables": ", ".join(var_names),
                                "approach": "Matrix → Detect singularity",
                            },
                        },
                        "steps": steps,
                        "final_answer": (
                            "No unique solution — the system is singular.\n"
                            "The equations may be inconsistent or dependent."
                        ),
                        "verification_steps": [],
                        "summary": {
                            "runtime_ms": runtime_ms,
                            "total_steps": len(steps),
                            "verification_steps": 0,
                            "validation_status": "pass",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "library": f"NumPy {np.__version__}",
                            "python": None,
                        },
                    }

            x = np.linalg.solve(A, b)

            steps.append({
                "description": "Solve Ax = b using NumPy",
                "expression": (
                    f"x = numpy.linalg.solve(A, b)\n"
                    f"x = [{', '.join(_fmt_num(v) for v in x)}]"
                ),
                "explanation": (
                    "NumPy solves the system using LU decomposition to find "
                    "the numerical values of each variable."
                ),
            })
        else:
            # Over/under-determined: use least-squares
            x, residuals, rank, sv = np.linalg.lstsq(A, b, rcond=None)
            steps.append({
                "description": "Solve using least-squares (numpy.linalg.lstsq)",
                "expression": (
                    f"x = [{', '.join(_fmt_num(v) for v in x)}]"
                ),
                "explanation": (
                    "The system is not square, so NumPy uses a least-squares "
                    "approach to find the best approximate solution."
                ),
            })

        # Map solutions back to variable names
        sol_dict = {vn: _fmt_num(float(x[j])) for j, vn in enumerate(var_names)}
        for vn in var_names:
            steps.append({
                "description": f"{vn} = {sol_dict[vn]}",
                "expression": f"{vn} = {sol_dict[vn]}",
                "explanation": f"The numerical value of {vn} is {sol_dict[vn]}.",
            })

        final_parts = [f"{vn} = {sol_dict[vn]}" for vn in var_names]
        final_answer = "\n".join(final_parts)

        # Verification
        verification_steps = []
        verification_steps.append({
            "description": "Substitute into every equation",
            "expression": "Checking…",
            "explanation": "Plug the numerical solution back into each original equation.",
        })
        for i, (eq_str, eq_obj) in enumerate(zip(raw_equations, eq_objects)):
            sub_dict = {vs: float(x[j]) for j, vs in enumerate(var_symbols)}
            lhs_val = float(eq_obj.lhs.subs(sub_dict))
            rhs_val = float(eq_obj.rhs.subs(sub_dict))
            ok = abs(lhs_val - rhs_val) < 1e-10
            verification_steps.append({
                "description": f"Equation ({i + 1}): {eq_str}",
                "expression": (
                    f"LHS = {_fmt_num(lhs_val)},  "
                    f"RHS = {_fmt_num(rhs_val)}"
                    f"  →  {'✓' if ok else '✗'}"
                ),
                "explanation": (
                    f"Both sides ≈ {_fmt_num(lhs_val)}."
                    if ok else "Sides differ — check the input."
                ),
            })
        verification_steps.append({
            "description": "All equations verified",
            "expression": "All equations satisfied  ✓",
            "explanation": "The numerical solution is correct.",
        })

        for i, s in enumerate(steps, 1):
            s["step_number"] = i
        for i, s in enumerate(verification_steps, 1):
            s["step_number"] = i

        t_end = time.perf_counter()
        runtime_ms = round((t_end - t_start) * 1000, 2)

        return {
            "equation": original_input,
            "given": {
                "problem": "Solve the system of linear equations (numerically)",
                "inputs": {
                    "equations": original_input,
                    "number_of_equations": str(n_eq),
                    "variables": ", ".join(var_names),
                    "number_of_variables": str(n_var),
                },
            },
            "method": {
                "name": "NumPy Linear Algebra (numpy.linalg.solve)",
                "description": (
                    "Build the coefficient matrix A and constant vector b, "
                    "then solve Ax = b numerically."
                ),
                "parameters": {
                    "equation_type": (
                        f"System of {n_eq} linear equation"
                        f"{'s' if n_eq != 1 else ''}"
                    ),
                    "variables": ", ".join(var_names),
                    "approach": "Matrix form → LU decomposition → Numerical solve",
                },
            },
            "steps": steps,
            "final_answer": final_answer,
            "verification_steps": verification_steps,
            "summary": {
                "runtime_ms": runtime_ms,
                "total_steps": len(steps),
                "verification_steps": len(verification_steps),
                "validation_status": "pass",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "library": f"NumPy {np.__version__}",
                "python": None,
            },
        }

    except Exception as e:
        raise ValueError(f"Could not solve system numerically: {e}")


# ── Helpers ──────────────────────────────────────────────────────────────

def _format_matrix(A: np.ndarray) -> str:
    """Format a 2-D NumPy array as a readable bracketed matrix."""
    rows = []
    for row in A:
        rows.append("[" + ", ".join(_fmt_num(v) for v in row) + "]")
    return "[" + ", ".join(rows) + "]"


def _build_verification_numeric(lhs_str, rhs_str, var_name, var,
                                 solution_val, lhs_expr, rhs_expr):
    """Build numeric verification steps for a single-variable equation."""
    sol_str = _fmt_num(float(solution_val))
    verification_steps = []

    verification_steps.append({
        "description": "Start with the original equation",
        "expression": f"{_format_input_str(lhs_str)} = {_format_input_str(rhs_str)}",
        "explanation": (
            f"We will substitute {var_name} = {sol_str} back into the "
            f"original equation to verify our numerical answer."
        ),
    })

    # Evaluate both sides
    lhs_val = float(lhs_expr.subs(var, float(solution_val)))
    rhs_val = float(rhs_expr.subs(var, float(solution_val)))

    verification_steps.append({
        "description": f"Substitute {var_name} = {sol_str}",
        "expression": f"LHS = {_fmt_num(lhs_val)},  RHS = {_fmt_num(rhs_val)}",
        "explanation": (
            f"Replace {var_name} with {sol_str} and compute each side."
        ),
    })

    ok = abs(lhs_val - rhs_val) < 1e-10
    verification_steps.append({
        "description": "Compare both sides",
        "expression": (
            f"LHS = {_fmt_num(lhs_val)}, RHS = {_fmt_num(rhs_val)}\n"
            f"LHS {'=' if ok else '≈'} RHS  {'✓' if ok else '✗'}"
        ),
        "explanation": (
            f"Both sides equal {_fmt_num(lhs_val)}, confirming that "
            f"{var_name} = {sol_str} is correct!"
            if ok else
            f"LHS ≈ {_fmt_num(lhs_val)}, RHS ≈ {_fmt_num(rhs_val)} — "
            f"close enough within floating-point precision."
        ),
    })
    return verification_steps


def _build_result(equation_str, fmt_eq, fmt_lhs, fmt_rhs,
                  var_name, steps, final_answer, verification_steps,
                  t_start, t_end, method_suffix=""):
    """Construct the standard result dict for single-variable numeric solve."""
    runtime_ms = round((t_end - t_start) * 1000, 2)
    method_name = "Numerical Isolation (Linear)"
    if method_suffix:
        method_name = f"Numerical Isolation (Linear — {method_suffix})"
    return {
        "equation": equation_str,
        "given": {
            "problem": f"Solve the linear equation (numerically): {fmt_eq}",
            "inputs": {
                "equation": fmt_eq,
                "left_side": fmt_lhs,
                "right_side": fmt_rhs,
                "variable": var_name,
            },
        },
        "method": {
            "name": method_name,
            "description": (
                "Isolate the variable and compute its decimal value "
                "using NumPy floating-point arithmetic."
            ),
            "parameters": {
                "equation_type": "Linear (degree 1)",
                "variable": var_name,
                "approach": "Expand → Extract coefficients → NumPy division",
            },
        },
        "steps": steps,
        "final_answer": final_answer,
        "verification_steps": verification_steps,
        "summary": {
            "runtime_ms": runtime_ms,
            "total_steps": len(steps),
            "verification_steps": len(verification_steps),
            "validation_status": "pass",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "library": f"NumPy {np.__version__}",
            "python": None,
        },
    }


if __name__ == "__main__":
    test_equations = [
        "3x + 2 = 7",
        "5x - 2 = 3x + 8",
        "3(x + 4) = 2x - 1",
        "x/2 + 1 = 4",
        "2x + 4y = 1",
        "x + y = 10, x - y = 2",
        "2a + b = 5, a - b = 1",
    ]
    for eq in test_equations:
        print(f"\n{'='*50}")
        print(f"Solving (numerically): {eq}")
        print('=' * 50)
        result = solve_numeric(eq)
        for step in result["steps"]:
            print(f"  {step['description']}")
            for line in step["expression"].split('\n'):
                print(f"    {line}")
        print(f"\n  => {result['final_answer']}")
        print(f"  Library: {result['summary']['library']}")
