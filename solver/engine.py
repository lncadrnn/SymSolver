"""
Step-by-step linear equation solver using SymPy.

Parses a linear equation string (e.g. "2x + 3 = 7"), solves it symbolically,
and produces human-readable step-by-step explanations.
"""

import re
import time
from datetime import datetime

import sympy
from sympy import (
    symbols, sympify, Eq, solve, simplify, expand,
    Add, Mul, Rational, S, Symbol
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
    convert_xor
)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)

# Letters that SymSolver will recognise as the unknown variable.
_ALLOWED_VARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _detect_variable(equation_str: str) -> str:
    """Return the single-letter variable found in *equation_str*.

    Raises ValueError when zero or more than one distinct letter is found.
    """
    # Remove anything that isn't a letter or is part of known function/
    # constant names we want to ignore (e.g. 'sin', 'cos', 'pi', 'exp', …).
    cleaned = equation_str.replace('^', '**')
    # Tokenise: pull out all purely-alpha runs
    tokens = re.findall(r'[A-Za-z]+', cleaned)
    # Ignore common math words / SymPy built-ins
    _RESERVED = {
        'sin', 'cos', 'tan', 'log', 'ln', 'exp', 'sqrt',
        'pi', 'PI', 'Pi', 'abs', 'E',
    }
    candidates = set()
    for tok in tokens:
        if tok in _RESERVED:
            continue
        # Only single-letter names count as unknowns
        if len(tok) == 1 and tok in _ALLOWED_VARS:
            candidates.add(tok)
    if len(candidates) == 0:
        raise ValueError("No variable found. Include a letter like x, y, or z.")
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple variables detected ({', '.join(sorted(candidates))}). "
            "SymSolver supports equations with a single unknown variable."
        )
    return candidates.pop()


def _parse_side(expr_str: str, var_symbol: Symbol):
    """Parse one side of the equation into a SymPy expression."""
    s = expr_str.strip()
    s = s.replace('^', '**')
    local = {var_symbol.name: var_symbol}
    try:
        return parse_expr(s, local_dict=local, transformations=TRANSFORMATIONS)
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}'. Error: {e}")


def _format_expr(expr) -> str:
    """Format a SymPy expression into a readable string."""
    s = str(expr)
    # Clean up SymPy formatting
    s = s.replace('**', '^')
    # Remove * between coefficient and variable (e.g. 2*x → 2x)
    s = re.sub(r'(\d)\*([A-Za-z])', r'\1\2', s)
    # Replace any remaining * with ·
    s = s.replace('*', '·')
    return s


def _format_equation(lhs, rhs) -> str:
    return f"{_format_expr(lhs)} = {_format_expr(rhs)}"


def _count_terms_in_str(expr_str: str) -> int:
    """Count the number of top-level additive terms in an expression string.

    Respects parentheses so that terms inside (...) are not counted separately.
    A leading sign (+ or -) is not treated as a term separator.
    """
    s = expr_str.strip()
    if not s:
        return 0
    depth = 0
    count = 1
    i = 0
    # Skip leading sign
    if s[0] in ('+', '-'):
        i = 1
    while i < len(s):
        ch = s[i]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch in ('+', '-') and depth == 0:
            count += 1
        i += 1
    return count


def solve_linear_equation(equation_str: str) -> dict:
    """
    Solve a linear equation step by step.

    Returns a dict with trail-format sections:
      - given: problem statement and inputs
      - method: method name and parameters
      - steps: list of {step_number, description, expression, explanation}
      - final_answer: the solution string
      - verification_steps: substitution check
      - summary: runtime, timestamp, library versions
    """
    t_start = time.perf_counter()
    # --- Parse ---
    if '=' not in equation_str:
        raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")

    parts = equation_str.split('=')
    if len(parts) != 2:
        raise ValueError("Equation must contain exactly one '=' sign.")

    lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
    if not lhs_str or not rhs_str:
        raise ValueError("Both sides of the equation must have expressions.")

    # Detect which variable the user is solving for
    var_name = _detect_variable(equation_str)
    var = symbols(var_name)

    lhs = _parse_side(lhs_str, var)
    rhs = _parse_side(rhs_str, var)

    # Verify it's linear in the detected variable
    combined = lhs - rhs
    combined_expanded = expand(combined)
    poly_degree = combined_expanded.as_poly(var)
    if poly_degree is None:
        if var not in combined_expanded.free_symbols:
            val = simplify(combined_expanded)
            if val == 0:
                raise ValueError("This equation is always true (identity). Infinite solutions.")
            else:
                raise ValueError("This equation has no solution (contradiction).")
        raise ValueError("Could not determine the degree. Please check the equation.")

    if poly_degree.degree() > 1:
        raise ValueError(
            f"This is a degree-{poly_degree.degree()} equation, not linear. "
            "SymSolver currently supports linear equations only."
        )
    if poly_degree.degree() == 0:
        raise ValueError(f"No variable '{var_name}' found in the equation.")

    steps = []
    original_lhs_str = equation_str.split('=')[0].strip()
    original_rhs_str = equation_str.split('=')[1].strip()

    # Step 0: Original equation (show as user typed it)
    steps.append({
        "description": "Starting with the original equation",
        "expression": f"{original_lhs_str} = {original_rhs_str}",
        "explanation": f"We are given the equation {original_lhs_str} = {original_rhs_str}. Our goal is to isolate {var_name} on one side to find its value.",
    })

    # --- Step: Combine like terms / Expand (if parsing auto-simplified) ---
    # SymPy may auto-combine like terms (2x + 5x → 7x) or auto-expand
    # (3(x+4) → 3x + 12) during parsing.  Detect this and show a step.
    _orig_lhs_terms = _count_terms_in_str(original_lhs_str)
    _orig_rhs_terms = _count_terms_in_str(original_rhs_str)
    _parsed_lhs_terms = len(Add.make_args(lhs))
    _parsed_rhs_terms = len(Add.make_args(rhs))

    _lhs_term_changed = _orig_lhs_terms != _parsed_lhs_terms
    _rhs_term_changed = _orig_rhs_terms != _parsed_rhs_terms
    # Also detect when parentheses disappeared (expansion + combining may
    # leave the same term count, e.g. "2(x+1) + 3x" → "5x + 2").
    _parens_gone = (
        ('(' in original_lhs_str and '(' not in _format_expr(lhs)) or
        ('(' in original_rhs_str and '(' not in _format_expr(rhs))
    )

    if _lhs_term_changed or _rhs_term_changed or _parens_gone:
        _has_parens = '(' in original_lhs_str or '(' in original_rhs_str
        _terms_decreased = (_orig_lhs_terms > _parsed_lhs_terms or
                            _orig_rhs_terms > _parsed_rhs_terms)

        if _has_parens and _terms_decreased:
            desc = "Expand and combine like terms"
        elif _has_parens:
            # Parens present; if term count didn't change, both expansion and
            # combining happened (they cancelled out in count).
            desc = ("Expand and combine like terms"
                    if _parens_gone and not _lhs_term_changed and not _rhs_term_changed
                    else "Expand")
        else:
            desc = "Combine like terms"

        parts = []
        _lhs_changed = _lhs_term_changed or ('(' in original_lhs_str and '(' not in _format_expr(lhs))
        _rhs_changed = _rhs_term_changed or ('(' in original_rhs_str and '(' not in _format_expr(rhs))
        if _lhs_changed:
            action = "expands to" if '(' in original_lhs_str else "simplifies to"
            parts.append(
                f"On the left side, {original_lhs_str} {action} "
                f"{_format_expr(lhs)}"
            )
        if _rhs_changed:
            action = "expands to" if '(' in original_rhs_str else "simplifies to"
            parts.append(
                f"On the right side, {original_rhs_str} {action} "
                f"{_format_expr(rhs)}"
            )
        steps.append({
            "description": desc,
            "expression": _format_equation(lhs, rhs),
            "explanation": ". ".join(parts) + ".",
        })

    # --- Step 1: Expand both sides (if needed) ---
    lhs_expanded = expand(lhs)
    rhs_expanded = expand(rhs)
    if lhs_expanded != lhs or rhs_expanded != rhs:
        before_lhs, before_rhs = _format_expr(lhs), _format_expr(rhs)
        steps.append({
            "description": "Expand both sides",
            "expression": _format_equation(lhs_expanded, rhs_expanded),
            "explanation": (
                f"We distribute any multiplication across parentheses. "
                f"{before_lhs} becomes {_format_expr(lhs_expanded)}, and "
                f"{before_rhs} becomes {_format_expr(rhs_expanded)}. "
                f"This removes the parentheses so we can work with individual terms."
            ),
        })
        lhs, rhs = lhs_expanded, rhs_expanded

    # --- Step 2: Collect variable terms on the left, constants on the right ---
    lhs_x_coeff = lhs.coeff(var)
    lhs_const = lhs - lhs_x_coeff * var
    rhs_x_coeff = rhs.coeff(var)
    rhs_const = rhs - rhs_x_coeff * var

    new_lhs = lhs
    new_rhs = rhs

    # Move variable terms from right to left
    if rhs_x_coeff != 0:
        subtract_term = rhs_x_coeff * var
        term_str = _format_expr(subtract_term)
        if rhs_x_coeff > 0:
            desc = f"Subtract {term_str} from both sides"
            work_expr = f"{_format_expr(lhs)} - {term_str} = {_format_expr(rhs)} - {term_str}"
            explanation = (
                f"The right side has the variable term {term_str}. "
                f"To move all {var_name}-terms to the left, we subtract {term_str} from both sides. "
                f"Whatever we do to one side, we must do to the other to keep the equation balanced."
            )
        else:
            pos_term = _format_expr(-subtract_term)
            desc = f"Add {pos_term} to both sides"
            work_expr = f"{_format_expr(lhs)} + {pos_term} = {_format_expr(rhs)} + {pos_term}"
            explanation = (
                f"The right side has {term_str}. "
                f"To move all {var_name}-terms to the left, we add {pos_term} to both sides. "
                f"This cancels the {var_name}-term on the right."
            )
        steps.append({
            "description": desc,
            "expression": work_expr,
            "explanation": explanation,
        })
        new_lhs = expand(lhs - subtract_term)
        new_rhs = expand(rhs - subtract_term)
        steps.append({
            "description": "Simplify both sides",
            "expression": _format_equation(new_lhs, new_rhs),
            "explanation": f"Combining like terms: the left side becomes {_format_expr(new_lhs)} and the right side becomes {_format_expr(new_rhs)}.",
        })
        lhs, rhs = new_lhs, new_rhs

    # Move constant terms from left to right
    lhs_x_coeff_now = lhs.coeff(var)
    lhs_const_now = expand(lhs - lhs_x_coeff_now * var)
    if lhs_const_now != 0:
        const_str = _format_expr(lhs_const_now)
        if lhs_const_now > 0:
            desc = f"Subtract {const_str} from both sides"
            work_expr = f"{_format_expr(lhs)} - {const_str} = {_format_expr(rhs)} - {const_str}"
            explanation = (
                f"The left side still has the constant {const_str}. "
                f"To isolate the {var_name}-term, we subtract {const_str} from both sides. "
                f"This moves the constant to the right side."
            )
        else:
            pos_const = _format_expr(-lhs_const_now)
            desc = f"Add {pos_const} to both sides"
            work_expr = f"{_format_expr(lhs)} + {pos_const} = {_format_expr(rhs)} + {pos_const}"
            explanation = (
                f"The left side has {const_str}. "
                f"To isolate the {var_name}-term, we add {pos_const} to both sides. "
                f"This cancels the constant on the left."
            )
        steps.append({
            "description": desc,
            "expression": work_expr,
            "explanation": explanation,
        })
        new_lhs = expand(lhs - lhs_const_now)
        new_rhs = expand(rhs - lhs_const_now)
        steps.append({
            "description": "Simplify both sides",
            "expression": _format_equation(new_lhs, new_rhs),
            "explanation": f"Combining like terms: the left side becomes {_format_expr(new_lhs)} and the right side becomes {_format_expr(new_rhs)}.",
        })
        lhs, rhs = new_lhs, new_rhs

    # --- Step 3: Simplify both sides ---
    lhs_simplified = simplify(lhs)
    rhs_simplified = simplify(rhs)
    if lhs_simplified != lhs or rhs_simplified != rhs:
        lhs, rhs = lhs_simplified, rhs_simplified
        steps.append({
            "description": "Simplify both sides",
            "expression": _format_equation(lhs, rhs),
            "explanation": "We combine like terms on each side to simplify the equation.",
        })

    # --- Step 4: Divide both sides by the coefficient of the variable ---
    coeff = lhs.coeff(var)
    if coeff == 0:
        raise ValueError(f"After simplification, {var_name} disappeared. The equation may have no unique solution.")

    if coeff != 1:
        coeff_str = _format_expr(coeff)
        steps.append({
            "description": f"Divide both sides by {coeff_str}",
            "expression": f"{_format_expr(lhs)} / {coeff_str} = {_format_expr(rhs)} / {coeff_str}",
            "explanation": (
                f"The coefficient of {var_name} is {coeff_str}. "
                f"To get {var_name} alone, we divide both sides by {coeff_str}. "
                f"Dividing {_format_expr(lhs)} by {coeff_str} gives {var_name}, and "
                f"dividing {_format_expr(rhs)} by {coeff_str} gives us the value."
            ),
        })
        solution = simplify(rhs / coeff)
        steps.append({
            "description": "Simplify to get the answer",
            "expression": f"{var_name} = {_format_expr(solution)}",
            "explanation": f"Performing the division: {_format_expr(rhs)} ÷ {coeff_str} = {_format_expr(solution)}. So {var_name} equals {_format_expr(solution)}.",
        })
    else:
        solution = simplify(rhs)

    # Build verification steps
    lhs_check = _parse_side(equation_str.split('=')[0], var)
    rhs_check = _parse_side(equation_str.split('=')[1], var)
    sol_str = _format_expr(solution)
    original_eq = f"{_format_expr(lhs_check)} = {_format_expr(rhs_check)}"

    verification_steps = []

    # Step 1: State what we're doing
    verification_steps.append({
        "description": "Start with the original equation",
        "expression": original_eq,
        "explanation": f"We will substitute {var_name} = {sol_str} back into the original equation to verify our answer is correct.",
    })

    # Step 2: Show substitution
    lhs_substituted_str = _format_expr(lhs_check).replace(var_name, f'({sol_str})')
    rhs_substituted_str = _format_expr(rhs_check).replace(var_name, f'({sol_str})')
    verification_steps.append({
        "description": f"Substitute {var_name} = {sol_str} into both sides",
        "expression": f"{lhs_substituted_str} = {rhs_substituted_str}",
        "explanation": f"We replace every {var_name} with {sol_str} in both the left-hand side and right-hand side of the equation.",
    })

    # Step 3: Evaluate LHS
    lhs_val = simplify(lhs_check.subs(var, solution))
    verification_steps.append({
        "description": "Evaluate the left-hand side",
        "expression": f"LHS = {lhs_substituted_str} = {_format_expr(lhs_val)}",
        "explanation": f"Computing the left side: we substitute and simplify to get {_format_expr(lhs_val)}.",
    })

    # Step 4: Evaluate RHS
    rhs_val = simplify(rhs_check.subs(var, solution))
    verification_steps.append({
        "description": "Evaluate the right-hand side",
        "expression": f"RHS = {rhs_substituted_str} = {_format_expr(rhs_val)}",
        "explanation": f"Computing the right side: we substitute and simplify to get {_format_expr(rhs_val)}.",
    })

    # Step 5: Compare
    verification_steps.append({
        "description": "Compare both sides",
        "expression": f"LHS = {_format_expr(lhs_val)}, RHS = {_format_expr(rhs_val)}\nLHS = RHS  ✓",
        "explanation": f"Both sides equal {_format_expr(lhs_val)}, confirming that {var_name} = {sol_str} is the correct solution!",
    })

    final_answer = f"{var_name} = {_format_expr(solution)}"

    # ── Number the steps ────────────────────────────────────────────────
    for i, step in enumerate(steps, start=1):
        step["step_number"] = i
    for i, step in enumerate(verification_steps, start=1):
        step["step_number"] = i

    # ── Build trail metadata ────────────────────────────────────────────
    t_end = time.perf_counter()
    runtime_ms = round((t_end - t_start) * 1000, 2)

    given = {
        "problem": f"Solve the linear equation: {equation_str}",
        "inputs": {
            "equation": equation_str,
            "left_side": original_lhs_str,
            "right_side": original_rhs_str,
            "variable": var_name,
        },
    }

    method = {
        "name": "Algebraic Isolation (Linear)",
        "description": "Isolate the variable by performing inverse operations step-by-step.",
        "parameters": {
            "equation_type": "Linear (degree 1)",
            "variable": var_name,
            "approach": "Expand → Collect like terms → Isolate variable → Simplify",
        },
    }

    summary = {
        "runtime_ms": runtime_ms,
        "total_steps": len(steps),
        "verification_steps": len(verification_steps),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "library": f"SymPy {sympy.__version__}",
        "python": None,  # filled by caller if desired
    }

    return {
        "equation": equation_str,
        "given": given,
        "method": method,
        "steps": steps,
        "final_answer": final_answer,
        "verification_steps": verification_steps,
        "summary": summary,
    }


if __name__ == "__main__":
    # Quick test
    test_equations = [
        "2x + 3 = 7",
        "5x - 2 = 3x + 8",
        "3(x + 4) = 2x - 1",
        "x/2 + 1 = 4",
    ]
    for eq in test_equations:
        print(f"\n{'='*50}")
        print(f"Solving: {eq}")
        print('='*50)
        result = solve_linear_equation(eq)
        for step in result["steps"]:
            print(f"  {step['description']}")
            for line in step["expression"].split('\n'):
                print(f"    {line}")
        print(f"\n  => {result['final_answer']}")
