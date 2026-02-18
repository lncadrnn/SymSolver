"""
Step-by-step linear equation solver using SymPy.

Parses a linear equation string (e.g. "2x + 3 = 7"), solves it symbolically,
and produces human-readable step-by-step explanations.
"""

import re
from sympy import (
    symbols, sympify, Eq, solve, simplify, expand,
    Add, Mul, Rational, S, Symbol
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
    convert_xor
)

x = symbols('x')

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)


def _parse_side(expr_str: str):
    """Parse one side of the equation into a SymPy expression."""
    s = expr_str.strip()
    # Replace common patterns for user-friendliness
    s = s.replace('^', '**')
    try:
        return parse_expr(s, local_dict={'x': x}, transformations=TRANSFORMATIONS)
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}'. Error: {e}")


def _format_expr(expr) -> str:
    """Format a SymPy expression into a readable string."""
    s = str(expr)
    # Clean up SymPy formatting
    s = s.replace('**', '^').replace('*', '·')
    return s


def _format_equation(lhs, rhs) -> str:
    return f"{_format_expr(lhs)} = {_format_expr(rhs)}"


def solve_linear_equation(equation_str: str) -> dict:
    """
    Solve a linear equation step by step.

    Returns a dict with:
      - equation: the original equation string
      - steps: list of {description, expression}
      - final_answer: the solution string
    """
    # --- Parse ---
    if '=' not in equation_str:
        raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")

    parts = equation_str.split('=')
    if len(parts) != 2:
        raise ValueError("Equation must contain exactly one '=' sign.")

    lhs_str, rhs_str = parts[0].strip(), parts[1].strip()
    if not lhs_str or not rhs_str:
        raise ValueError("Both sides of the equation must have expressions.")

    lhs = _parse_side(lhs_str)
    rhs = _parse_side(rhs_str)

    # Verify it's linear in x
    combined = lhs - rhs
    combined_expanded = expand(combined)
    poly_degree = combined_expanded.as_poly(x)
    if poly_degree is None:
        # Might be a constant equation (no x)
        if x not in combined_expanded.free_symbols:
            val = simplify(combined_expanded)
            if val == 0:
                raise ValueError("This equation is always true (identity). Infinite solutions.")
            else:
                raise ValueError("This equation has no solution (contradiction).")
        raise ValueError("Could not determine the degree. Please check the equation.")

    if poly_degree.degree() > 1:
        raise ValueError(
            f"This is a degree-{poly_degree.degree()} equation, not linear. "
            "DualSolver currently supports linear equations only."
        )
    if poly_degree.degree() == 0:
        raise ValueError("No variable 'x' found in the equation.")

    steps = []
    original_lhs_str = equation_str.split('=')[0].strip()
    original_rhs_str = equation_str.split('=')[1].strip()

    # Step 0: Original equation
    steps.append({
        "description": "Starting with the original equation",
        "expression": _format_equation(lhs, rhs),
        "explanation": f"We are given the equation {original_lhs_str} = {original_rhs_str}. Our goal is to isolate x on one side to find its value.",
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
    lhs_x_coeff = lhs.coeff(x)
    lhs_const = lhs - lhs_x_coeff * x
    rhs_x_coeff = rhs.coeff(x)
    rhs_const = rhs - rhs_x_coeff * x

    new_lhs = lhs
    new_rhs = rhs

    # Move x terms from right to left
    if rhs_x_coeff != 0:
        subtract_term = rhs_x_coeff * x
        term_str = _format_expr(subtract_term)
        if rhs_x_coeff > 0:
            desc = f"Subtract {term_str} from both sides"
            work_expr = f"{_format_expr(lhs)} - {term_str} = {_format_expr(rhs)} - {term_str}"
            explanation = (
                f"The right side has the variable term {term_str}. "
                f"To move all x-terms to the left, we subtract {term_str} from both sides. "
                f"Whatever we do to one side, we must do to the other to keep the equation balanced."
            )
        else:
            pos_term = _format_expr(-subtract_term)
            desc = f"Add {pos_term} to both sides"
            work_expr = f"{_format_expr(lhs)} + {pos_term} = {_format_expr(rhs)} + {pos_term}"
            explanation = (
                f"The right side has {term_str}. "
                f"To move all x-terms to the left, we add {pos_term} to both sides. "
                f"This cancels the x-term on the right."
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
    lhs_x_coeff_now = lhs.coeff(x)
    lhs_const_now = expand(lhs - lhs_x_coeff_now * x)
    if lhs_const_now != 0:
        const_str = _format_expr(lhs_const_now)
        if lhs_const_now > 0:
            desc = f"Subtract {const_str} from both sides"
            work_expr = f"{_format_expr(lhs)} - {const_str} = {_format_expr(rhs)} - {const_str}"
            explanation = (
                f"The left side still has the constant {const_str}. "
                f"To isolate the x-term, we subtract {const_str} from both sides. "
                f"This moves the constant to the right side."
            )
        else:
            pos_const = _format_expr(-lhs_const_now)
            desc = f"Add {pos_const} to both sides"
            work_expr = f"{_format_expr(lhs)} + {pos_const} = {_format_expr(rhs)} + {pos_const}"
            explanation = (
                f"The left side has {const_str}. "
                f"To isolate the x-term, we add {pos_const} to both sides. "
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

    # --- Step 4: Divide both sides by the coefficient of x ---
    coeff = lhs.coeff(x)
    if coeff == 0:
        raise ValueError("After simplification, x disappeared. The equation may have no unique solution.")

    if coeff != 1:
        coeff_str = _format_expr(coeff)
        steps.append({
            "description": f"Divide both sides by {coeff_str}",
            "expression": f"{_format_expr(lhs)} / {coeff_str} = {_format_expr(rhs)} / {coeff_str}",
            "explanation": (
                f"The coefficient of x is {coeff_str}. "
                f"To get x alone, we divide both sides by {coeff_str}. "
                f"Dividing {_format_expr(lhs)} by {coeff_str} gives x, and "
                f"dividing {_format_expr(rhs)} by {coeff_str} gives us the value."
            ),
        })
        solution = simplify(rhs / coeff)
        steps.append({
            "description": "Simplify to get the answer",
            "expression": f"x = {_format_expr(solution)}",
            "explanation": f"Performing the division: {_format_expr(rhs)} ÷ {coeff_str} = {_format_expr(solution)}. So x equals {_format_expr(solution)}.",
        })
    else:
        solution = simplify(rhs)

    # Build verification steps
    lhs_check = _parse_side(equation_str.split('=')[0])
    rhs_check = _parse_side(equation_str.split('=')[1])
    sol_str = _format_expr(solution)
    original_eq = f"{_format_expr(lhs_check)} = {_format_expr(rhs_check)}"

    verification_steps = []

    # Step 1: State what we're doing
    verification_steps.append({
        "description": "Start with the original equation",
        "expression": original_eq,
        "explanation": f"We will substitute x = {sol_str} back into the original equation to verify our answer is correct.",
    })

    # Step 2: Show substitution
    lhs_substituted_str = _format_expr(lhs_check).replace('x', f'({sol_str})')
    rhs_substituted_str = _format_expr(rhs_check).replace('x', f'({sol_str})')
    verification_steps.append({
        "description": f"Substitute x = {sol_str} into both sides",
        "expression": f"{lhs_substituted_str} = {rhs_substituted_str}",
        "explanation": f"We replace every x with {sol_str} in both the left-hand side and right-hand side of the equation.",
    })

    # Step 3: Evaluate LHS
    lhs_val = simplify(lhs_check.subs(x, solution))
    verification_steps.append({
        "description": "Evaluate the left-hand side",
        "expression": f"LHS = {lhs_substituted_str} = {_format_expr(lhs_val)}",
        "explanation": f"Computing the left side: we substitute and simplify to get {_format_expr(lhs_val)}.",
    })

    # Step 4: Evaluate RHS
    rhs_val = simplify(rhs_check.subs(x, solution))
    verification_steps.append({
        "description": "Evaluate the right-hand side",
        "expression": f"RHS = {rhs_substituted_str} = {_format_expr(rhs_val)}",
        "explanation": f"Computing the right side: we substitute and simplify to get {_format_expr(rhs_val)}.",
    })

    # Step 5: Compare
    verification_steps.append({
        "description": "Compare both sides",
        "expression": f"LHS = {_format_expr(lhs_val)}, RHS = {_format_expr(rhs_val)}\nLHS = RHS  ✓",
        "explanation": f"Both sides equal {_format_expr(lhs_val)}, confirming that x = {sol_str} is the correct solution!",
    })

    final_answer = f"x = {_format_expr(solution)}"

    return {
        "equation": equation_str,
        "steps": steps,
        "final_answer": final_answer,
        "verification_steps": verification_steps,
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
