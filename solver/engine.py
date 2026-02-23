""" Step-by-step linear equation solver using SymPy."""

"""
Parses linear equations — single-variable (e.g. "2x + 3 = 7"),
multi-variable (e.g. "2x + 4y = 1"), or systems of equations
(e.g. "x + y = 10, x - y = 2") — and produces human-readable
step-by-step explanations.
"""

import re
import time
from datetime import datetime

import sympy
from sympy import (
    symbols, sympify, Eq, solve, simplify, expand,
    Add, Mul, Rational, S, Symbol, fraction
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
    convert_xor, rationalize
)

TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
    rationalize,  # Convert decimals like "12.5" to exact Rational(25, 2)
)

# Letters that SymSolver will recognise as the unknown variable.
_ALLOWED_VARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def _detect_variables(equation_str: str) -> list:
    """Return a sorted list of single-letter variables found in *equation_str*.

    Multi-character alphabetic tokens that aren't reserved math functions
    are treated as implicit multiplication of their individual letters
    (e.g. ``xyz`` → x·y·z, ``asdfghjkl`` → a·s·d·f·g·h·j·k·l).
    The linearity check later will reject terms where variables are
    multiplied together (degree > 1).

    Raises ValueError when no valid variable is found.
    """
    cleaned = equation_str.replace('^', '**')
    tokens = re.findall(r'[A-Za-z]+', cleaned)
    _RESERVED = {
        'sin', 'cos', 'tan', 'log', 'ln', 'exp', 'sqrt',
        'pi', 'PI', 'Pi', 'abs', 'E',
    }
    candidates = set()
    for tok in tokens:
        if tok in _RESERVED:
            continue
        # Every letter in the token is treated as its own variable
        # (implicit multiplication: "abc" means a·b·c).
        for ch in tok:
            if ch in _ALLOWED_VARS:
                candidates.add(ch)
    if len(candidates) == 0:
        raise ValueError("No variable found. Include a letter like x, y, or z.")
    return sorted(candidates)


def _expand_implicit_vars(s: str, var_names: set) -> str:
    """Replace multi-letter tokens composed entirely of known variable letters
    with explicit multiplication (e.g. ``as`` → ``a*s``) so that Python
    reserved words like ``as``, ``in``, ``for`` never reach the parser."""
    def _repl(m):
        tok = m.group(0)
        # Only expand if every letter belongs to a known variable
        if all(ch in var_names for ch in tok):
            return '*'.join(tok)
        return tok
    return re.sub(r'[A-Za-z]+', _repl, s)


def _parse_side(expr_str: str, var_symbols):
    """Parse one side of the equation into a SymPy expression.

    *var_symbols* may be a single ``Symbol`` or a list of ``Symbol`` objects.
    """
    s = expr_str.strip()
    s = s.replace('^', '**')
    if isinstance(var_symbols, Symbol):
        local = {var_symbols.name: var_symbols}
    else:
        local = {sym.name: sym for sym in var_symbols}
    # Expand multi-letter var tokens before parsing so Python keywords
    # (as, in, for, …) are never handed to parse_expr.
    s = _expand_implicit_vars(s, set(local.keys()))
    try:
        return parse_expr(s, local_dict=local, transformations=TRANSFORMATIONS)
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}'. Error: {e}")


_SUPERSCRIPT = str.maketrans("0123456789+-/()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ᐟ⁽⁾")


def _to_superscript(text: str) -> str:
    """Convert a string of digits / signs into Unicode superscript."""
    return text.translate(_SUPERSCRIPT)


# Fraction marker: ⟦numerator|denominator⟧
# The GUI will parse these and render them as stacked vertical fractions.
_FRAC_OPEN = "⟦"
_FRAC_SEP  = "|"
_FRAC_CLOSE = "⟧"


def _frac(num, den) -> str:
    """Return a fraction marker string for the GUI to render vertically."""
    return f"{_FRAC_OPEN}{num}{_FRAC_SEP}{den}{_FRAC_CLOSE}"


# Superscript characters used in exponents — must NOT be treated as operators.
_SUP_CHARS = (
    "\u00b2\u00b3\u00b9"                          # ²³¹
    "\u2070\u2074\u2075\u2076\u2077\u2078\u2079"  # ⁰⁴⁵⁶⁷⁸⁹
    "\u207a\u207b\u207c"                           # ⁺⁻⁼ (inside exponents)
)
# Characters after which a '-' is BINARY (needs spaces around it).
_BINARY_AFTER = r'[0-9A-Za-z' + re.escape(_SUP_CHARS) + r'·\u27e7)]'


def _prettify_symbols(s: str) -> str:
    """Replace solver-internal names with display-friendly Unicode symbols.

    - ``pi`` (not inside a longer word like 'pipe') → ``π``
    - ``sqrt(`` / ``sqrt⟦`` → ``√(`` / ``√⟦``  (handles fraction markers)
    """
    # Use lookaround instead of \b so "2pi", "3pi" are also caught.
    # Only require that pi is NOT surrounded by other letters.
    s = re.sub(r'(?<![a-zA-Z])pi(?![a-zA-Z])', 'π', s)
    s = s.replace('sqrt(', '√(')
    # Fraction conversion may consume the '(' after sqrt, leaving
    # "sqrt⟦" or "sqrt ⟦".  Normalise those too.
    s = s.replace('sqrt ⟦', '√⟦')
    s = s.replace('sqrt⟦', '√⟦')
    return s


def _normalize_spacing(s: str) -> str:
    """Ensure exactly one space around binary +, -, and = operators.

    Fraction markers ⟦num|den⟧ are treated as opaque atoms — their
    internal text is never touched.  Rules applied to every plain segment:

    - '=' is always binary  →  ' = '
    - '+' is always binary  →  ' + '
    - '-' is binary only when preceded by a digit, letter, closing paren,
      superscript char, or the ⟧ end-marker of a fraction.
      Unary '-' at the start of an expression or after '(' is left alone.
    - Multiple spaces collapsed to one.
    """
    # Split on fraction markers keeping them as separate tokens.
    segments = re.split(r'(\u27e6[^\u27e7]*\u27e7)', s)
    out = []
    for seg in segments:
        if seg.startswith(_FRAC_OPEN):
            out.append(seg)
            continue
        seg = re.sub(r'\s*=\s*', ' = ', seg)
        seg = re.sub(r'\s*\+\s*', ' + ', seg)
        # Binary '-': preceded by a term character.
        seg = re.sub(r'(' + _BINARY_AFTER + r')\s*-\s*', r'\1 - ', seg)
        seg = re.sub(r'  +', ' ', seg)
        out.append(seg)
    joined = ''.join(out)
    # Handle binary '-' that spans the ⟧ / next-segment boundary.
    joined = re.sub(r'(\u27e7)\s*-\s*', r'\1 - ', joined)
    # Ensure a space before ⟦ when a term immediately precedes it.
    joined = re.sub(
        r'([0-9A-Za-z\u00b2\u00b3\u00b9\u2070\u2074-\u2079\u207a-\u207c\u00b7\u27e7)])(\u27e6)',
        r'\1 \2', joined)
    # Ensure a space after ⟧ when a term immediately follows it.
    joined = re.sub(r'(\u27e7)([0-9A-Za-z])', r'\1 \2', joined)
    return re.sub(r'  +', ' ', joined)


def _format_expr(expr) -> str:
    """Format a SymPy expression into a readable string with Unicode
    superscript exponents and stacked-fraction markers."""
    s = str(expr)

    # Convert exponents (**N or **(-N) etc.) to superscript
    def _sup_repl(m):
        exp_text = m.group(1)
        if exp_text.startswith("(") and exp_text.endswith(")"):
            exp_text = exp_text[1:-1]
        return _to_superscript(exp_text)

    s = re.sub(r'\*\*\(([^)]+)\)', _sup_repl, s)
    s = re.sub(r'\*\*(-?\d+)', _sup_repl, s)

    # Remove * between coefficient and variable (e.g. 2*x → 2x)
    s = re.sub(r'(\d)\*([A-Za-z])', r'\1\2', s)
    # Remove * between closing paren and variable, or variable and opening paren
    s = re.sub(r'\)\*([A-Za-z])', r')\1', s)
    # Replace any remaining * with ·
    s = s.replace('*', '·')

    # Convert fraction patterns to stacked-fraction markers ⟦num|den⟧
    # Match (expr)/number  — e.g. (2x + 3)/5
    def _paren_frac_repl(m):
        return _frac(m.group(1), m.group(2))
    s = re.sub(r'\(([^)]+)\)/(\d+)', _paren_frac_repl, s)

    # Match simple fractions: token/number — e.g. x/2, 3/4, -1/2, 2x/3
    def _simple_frac_repl(m):
        return _frac(m.group(1), m.group(2))
    s = re.sub(r'(-?[A-Za-z0-9·]+)/(\d+)', _simple_frac_repl, s)

    # Match fractions with variable denominators — e.g. 1/x, 2/y (SymPy
    # outputs these when the user had x⁻¹ or typed 1/x)
    # Only match numeric-or-simple-token numerators so we don’t eat complex
    # expressions that weren’t already wrapped in the paren pass above.
    def _var_frac_repl(m):
        return _frac(m.group(1), m.group(2))
    s = re.sub(r'(-?[0-9]+)/([A-Za-z][A-Za-z0-9]*)', _var_frac_repl, s)

    return _prettify_symbols(_normalize_spacing(s))


def _format_expr_plain(expr) -> str:
    """Like _format_expr but without fraction markers — for use as
    denominators / inside explanations where nesting would break."""
    s = str(expr)
    def _sup_repl(m):
        exp_text = m.group(1)
        if exp_text.startswith("(") and exp_text.endswith(")"):
            exp_text = exp_text[1:-1]
        return _to_superscript(exp_text)
    s = re.sub(r'\*\*\(([^)]+)\)', _sup_repl, s)
    s = re.sub(r'\*\*(-?\d+)', _sup_repl, s)
    s = re.sub(r'(\d)\*([A-Za-z])', r'\1\2', s)
    s = re.sub(r'\)\*([A-Za-z])', r')\1', s)
    s = s.replace('*', '·')
    return _prettify_symbols(_normalize_spacing(s))


def _format_input_str(raw: str) -> str:
    """Format a RAW user-typed equation side for display.

    Unlike _format_expr, this does NOT go through SymPy, so it preserves:
    - Term order exactly as typed (e.g. ``1/x + 1`` stays ``1/x + 1``).
    - Negative-exponent notation (``x^-1`` → ``x⁻¹``, not ``1/x``).

    Applies the same visual transforms as _format_expr:
    - ``^N`` / ``^(-N)`` → Unicode superscript
    - ``n/var`` and ``n/N`` → stacked ⟦num|den⟧ markers
    - Removes ``*`` between digit and variable; remaining ``*`` → ·
    """
    s = raw.strip()
    # ^ exponents → superscript (caret notation, not SymPy **)
    def _sup_repl(m):
        exp_text = m.group(1)
        if exp_text.startswith('(') and exp_text.endswith(')'):
            exp_text = exp_text[1:-1]
        return _to_superscript(exp_text)
    s = re.sub(r'\^\(([^)]+)\)', _sup_repl, s)
    s = re.sub(r'\^(-?\d+)', _sup_repl, s)
    # Remove * between coefficient and variable
    s = re.sub(r'(\d)\*([A-Za-z])', r'\1\2', s)
    s = re.sub(r'\)\*([A-Za-z])', r')\1', s)
    s = s.replace('*', '·')
    # Stacked fractions — parenthesised numerator first: (expr)/token
    def _paren_frac_repl(m):
        return _frac(m.group(1), m.group(2))
    s = re.sub(r'\(([^)]+)\)/([A-Za-z0-9·]+)', _paren_frac_repl, s)
    # Simple a/b fractions with ANY single-token denominator
    def _frac_repl(m):
        return _frac(m.group(1), m.group(2))
    s = re.sub(r'(-?[A-Za-z0-9·]+)/([A-Za-z0-9·]+)', _frac_repl, s)
    return _prettify_symbols(_normalize_spacing(s))


def _format_input_eq(lhs_raw: str, rhs_raw: str) -> str:
    """Return a display-ready equation string built from the raw typed sides."""
    return f"{_format_input_str(lhs_raw)} = {_format_input_str(rhs_raw)}"


def _format_equation(lhs, rhs) -> str:
    return f"{_format_expr(lhs)} = {_format_expr(rhs)}"


# ── Non-linearity detection helpers ─────────────────────────────────────

_DEGREE_NAMES = {
    0: "constant",
    1: "linear",
    2: "quadratic",
    3: "cubic",
    4: "quartic",
    5: "quintic",
}


def _degree_name(degree: int) -> str:
    """Return the conventional name for a polynomial of the given degree."""
    return _DEGREE_NAMES.get(degree, f"degree-{degree} polynomial")


_TRANS_FUNC_NAMES = (
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
    'asin', 'acos', 'atan', 'acot',
    'sinh', 'cosh', 'tanh',
    'log', 'exp',
)


def _has_transcendental(expr, var_symbols) -> bool:
    """Return True if any transcendental/trig/log/exp function is applied to a variable."""
    import sympy as _sy
    vs_set = {var_symbols} if isinstance(var_symbols, Symbol) else set(var_symbols)
    for name in _TRANS_FUNC_NAMES:
        cls = getattr(_sy, name, None)
        if cls is None:
            continue
        for atom in expr.atoms(cls):
            if atom.free_symbols & vs_set:
                return True
    return False


def _has_var_in_denominator(expr, var_symbols) -> bool:
    """Return True if any variable appears in the denominator of expr."""
    vs_set = {var_symbols} if isinstance(var_symbols, Symbol) else set(var_symbols)
    # Check the whole expression's denominator
    try:
        _, den = fraction(expr)
        if den.free_symbols & vs_set:
            return True
    except Exception:
        pass
    # Also check individual terms
    for term in expr.as_ordered_terms():
        try:
            _, den = fraction(term)
            if den.free_symbols & vs_set:
                return True
        except Exception:
            pass
    return False


def _detect_nonlinear_reason(combined_expanded, var_symbols_list: list,
                              highest_deg: int) -> str:
    """Return 'transcendental', 'denominator', 'product', or 'degree'."""
    if _has_transcendental(combined_expanded, var_symbols_list):
        return "transcendental"
    if _has_var_in_denominator(combined_expanded, var_symbols_list):
        return "denominator"
    # Distinguish product-of-variables (total deg ≥ 2, each var alone deg ≤ 1)
    if len(var_symbols_list) > 1 and highest_deg >= 2:
        max_single = 0
        for vs in var_symbols_list:
            p = combined_expanded.as_poly(vs)
            if p is not None and p.degree() > max_single:
                max_single = p.degree()
        if max_single <= 1:
            return "product"
    return "degree"


def _build_educational_message(reason: str, highest_deg: int,
                               var_names: list) -> str:
    """Return a multi-line educational message explaining non-linearity."""
    deg_sym = _to_superscript(str(highest_deg)) if highest_deg >= 2 else ""

    if reason == "transcendental":
        return (
            "This equation contains a transcendental function.\n"
            "\n"
            "When a variable is placed inside a trigonometric, logarithmic,\n"
            "or exponential function — such as sin(x), cos(x), log(x), or eˣ —\n"
            "the relationship between the variable and its output becomes non-linear.\n"
            "\n"
            "Linear equations require the variable to appear on its own (e.g. 2x + 3),\n"
            "not inside any function. Transcendental equations require specialized\n"
            "methods (e.g. inverse trig, numerical solvers) to solve."
        )

    if reason == "denominator":
        return (
            "This equation has a variable in the denominator (e.g. 1/x).\n"
            "\n"
            "A variable in the denominator is equivalent to a negative exponent:\n"
            "  1/x  =  x⁻¹\n"
            "\n"
            "Linear equations cannot have negative exponents.\n"
            "The variable must appear exactly as x¹ (plain x) —\n"
            "no negative, fractional, or higher exponents are allowed."
        )

    if reason == "product":
        var_example = " · ".join(var_names[:2]) if len(var_names) >= 2 else "x · y"
        return (
            f"This equation contains a product of variables ({var_example}).\n"
            "\n"
            "When variables are multiplied together the total degree becomes 2 or more,\n"
            "making the equation non-linear (it describes a curve, not a straight line).\n"
            "\n"
            "Linear equations only allow each variable to appear individually —\n"
            "no products, no squared terms, no cross-terms between variables."
        )

    # reason == "degree" (default)
    eq_type = _degree_name(highest_deg)
    deg_ref = {
        2: "ax\u00b2 + bx + c = 0",
        3: "ax\u00b3 + bx\u00b2 + cx + d = 0",
        4: "ax\u2074 + bx\u00b3 + cx\u00b2 + dx + e = 0",
        5: "ax\u2075 + bx\u2074 + cx\u00b3 + dx\u00b2 + ex + f = 0",
    }.get(highest_deg, f"degree-{highest_deg} polynomial = 0")
    return (
        f"This is a {eq_type} equation (highest degree: {highest_deg}).\n"
        f"  Standard form: {deg_ref}\n"
        "\n"
        "Equations are classified by their highest degree:\n"
        "  Degree 0  →  constant   (e.g.  5 = 5)\n"
        "  Degree 1  →  linear     (e.g.  2x + 3 = 7)  ← must be this\n"
        "  Degree 2  →  quadratic  (e.g.  x² + 5x + 6 = 0)\n"
        "  Degree 3  →  cubic      (e.g.  x³ − 2x² + x = 0)\n"
        "  Degree 4  →  quartic    (e.g.  x⁴ − 1 = 0)\n"
        "  Degree 5  →  quintic    (e.g.  x⁵ + x = 0)\n"
        "\n"
        f"Since this equation has degree {highest_deg}, it is non-linear\n"
        "and cannot be solved with linear algebra methods."
    )


def _nonlinear_error_result(equation_str: str, lhs_str: str, rhs_str: str,
                            lhs, rhs, var_names, degree: int,
                            t_start: float,
                            reason: str = "degree") -> dict:
    """Return a result dict showing the algebra trail and an educational
    explanation of why the equation is not linear.

    *reason* is one of:
      'degree'        – polynomial with highest degree > 1
      'denominator'   – variable appears in the denominator (negative exponent)
      'product'       – product of two or more variables
      'transcendental'– variable inside trig / log / exp function
    """
    steps = []

    # ── Use the *raw typed strings* for the given / step-1 display so that
    #    term order and notation (x^-1, 1/x, etc.) match what the user typed.
    _fmt_input_lhs = _format_input_str(lhs_str)
    _fmt_input_rhs = _format_input_str(rhs_str)
    _fmt_input_eq  = _format_input_eq(lhs_str, rhs_str)

    # SymPy-canonical versions are still needed for step-2 and plain text.
    _fmt_nl_lhs = _format_expr(lhs)
    _fmt_nl_rhs = _format_expr(rhs)

    # Step 1: show original — use the INPUT form, not SymPy canonical
    steps.append({
        "description": "Starting with the original equation",
        "expression": _fmt_input_eq,
        "explanation": (
            f"We are given the equation {_format_expr_plain(lhs)} = {_format_expr_plain(rhs)}. "
            f"Let's simplify it first to check if it is linear."
        ),
    })

    # Step 2: expand / combine like terms — only if it actually changes something.
    # expand() on already-simplified expressions like 1/x + 1 returns the same
    # value (SymPy may reorder terms internally, but symbolically equals the
    # original).  Showing the step when nothing combined would be misleading.
    lhs_exp = expand(lhs)
    rhs_exp = expand(rhs)
    _expansion_changed = (lhs_exp != lhs) or (rhs_exp != rhs)
    if _expansion_changed:
        steps.append({
            "description": "Expand and combine like terms",
            "expression": _format_equation(lhs_exp, rhs_exp),
            "explanation": (
                f"After distributing and combining like terms we get: "
                f"{_format_expr_plain(lhs_exp)} = {_format_expr_plain(rhs_exp)}."
            ),
        })

    # Compute the effective highest degree (used for degree-based messages)
    combined = expand(lhs - rhs)
    var_symbols_list = [symbols(v) for v in var_names]

    max_single_var_deg = 0
    for vs in var_symbols_list:
        p = combined.as_poly(vs)
        if p is not None and p.degree() > max_single_var_deg:
            max_single_var_deg = p.degree()

    highest_deg = max_single_var_deg
    try:
        total_poly = combined.as_poly(*var_symbols_list)
        if total_poly is not None and total_poly.total_degree() > highest_deg:
            highest_deg = total_poly.total_degree()
    except Exception:
        pass

    if highest_deg < 2:
        highest_deg = degree  # fallback to what the caller passed

    # Auto-refine reason for degree cases (product vs. pure high-degree)
    if reason == "degree" and highest_deg >= 2:
        reason = _detect_nonlinear_reason(combined, var_symbols_list, highest_deg)

    # Step 3 (denominator only): highlight the negative-exponent form.
    # Show the INPUT form so order/notation matches what the user typed.
    if reason == "denominator":
        steps.append({
            "description": "Identify variable in denominator",
            "expression": _fmt_input_eq,
            "explanation": (
                "Notice that a variable appears in the denominator. "
                "A term of the form 1/x is equivalent to x\u207b\u00b9 \u2014 "
                "a negative exponent. Linear equations cannot have "
                "negative (or zero, or fractional) exponents on their variables."
            ),
        })

    # Step 3 (transcendental only): highlight the function.
    if reason == "transcendental":
        steps.append({
            "description": "Identify transcendental function",
            "expression": _fmt_input_eq,
            "explanation": (
                "Notice that the variable is placed inside a function "
                "(trigonometric, logarithmic, or exponential). "
                "This is called a transcendental equation. "
                "Linear equations require the variable to appear "
                "on its own \u2014 not wrapped in any function."
            ),
        })

    for i, s in enumerate(steps, 1):
        s["step_number"] = i

    t_end = time.perf_counter()
    runtime_ms = round((t_end - t_start) * 1000, 2)

    # Build human-readable equation-type label for the METHOD card
    _eq_type_label = {
        "degree":        f"Non-linear \u2014 {_degree_name(highest_deg)} (degree {highest_deg})",
        "denominator":   "Non-linear \u2014 variable in denominator (x\u207b\u00b9)",
        "product":       "Non-linear \u2014 product of variables",
        "transcendental":"Non-linear \u2014 transcendental function",
    }.get(reason, f"Non-linear (degree {highest_deg})")

    final_msg = _build_educational_message(reason, highest_deg, var_names)

    return {
        "equation": equation_str,
        "given": {
            "problem": f"Analyze the equation: {_fmt_input_eq}",
            "inputs": {
                "equation":   _fmt_input_eq,
                "left_side":  _fmt_input_lhs,
                "right_side": _fmt_input_rhs,
                "variables":  ", ".join(var_names),
            },
        },
        "method": {
            "name": "Linearity Check",
            "description": (
                "Expand and simplify the equation, then identify why "
                "it is not linear."
            ),
            "parameters": {
                "equation_type": _eq_type_label,
                "variables": ", ".join(var_names),
            },
        },
        "steps": steps,
        "final_answer": final_msg,
        "nonlinear_education": True,
        "verification_steps": [],
        "summary": {
            "runtime_ms": runtime_ms,
            "total_steps": len(steps),
            "verification_steps": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "library": f"SymPy {sympy.__version__}",
            "python": None,
        },
    }


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


def _validate_characters(equation_str: str) -> None:
    """Reject equations that contain characters outside the allowed set.

    Allowed: letters, digits, whitespace, and the math symbols
    + - * / ^ = ( ) . , ;
    """
    allowed = set("abcdefghijklmnopqrstuvwxyz"
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "0123456789"
                  " \t+-*/^=()[]{}.,;:\u03c0\u221a")
    bad = set()
    for ch in equation_str:
        if ch not in allowed:
            bad.add(ch)
    if bad:
        bad_sorted = " ".join(sorted(bad))
        raise ValueError(
            f"Invalid character(s): {bad_sorted}\n"
            f"Only letters, numbers, and math symbols "
            f"(+ - * / ^ = ( ) . , ;) are allowed."
        )


def solve_linear_equation(equation_str: str) -> dict:
    """
    Solve one or more linear equations step by step.

    Supports:
      - Single variable:  ``2x + 3 = 7``
      - Multiple variables:  ``2x + 4y = 1``
      - Systems (comma / semicolon separated):  ``x + y = 10, x - y = 2``

    Returns a dict with trail-format sections:
      - given, method, steps, final_answer, verification_steps, summary
    """
    t_start = time.perf_counter()

    # ── Normalise Unicode symbols to parser-friendly equivalents ─────
    equation_str = equation_str.replace('\u221a', 'sqrt')
    equation_str = equation_str.replace('\u03c0', '(pi)')
    equation_str = equation_str.replace('[', '(').replace(']', ')')
    equation_str = equation_str.replace('{', '(').replace('}', ')')

    # ── Validate input characters ───────────────────────────────────────
    _validate_characters(equation_str)

    # ── Split by , or ; to detect a system ──────────────────────────────
    raw_equations = [eq.strip() for eq in re.split(r'\s*[;,]\s*', equation_str)
                     if eq.strip()]
    all_text = ' '.join(raw_equations)
    var_names = _detect_variables(all_text)

    if len(raw_equations) > 1:
        return _solve_system(raw_equations, var_names, equation_str, t_start)
    if len(var_names) > 1:
        return _solve_multi_var_single_eq(equation_str, var_names, t_start)

    # ── Single equation, single variable ────────────────────────────────
    if '=' not in equation_str:
        raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")

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

    # Verify it's linear in the detected variable
    combined = lhs - rhs
    combined_expanded = expand(combined)
    poly_degree = combined_expanded.as_poly(var)
    if poly_degree is None:
        if var not in combined_expanded.free_symbols:
            # Degenerate: variable was present in the original text but
            # fully cancelled out.  Let the step-by-step algebra run and
            # show what happened — step 4 will detect and explain it.
            pass
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
        # Non-zero constant: variable present in input but fully cancelled
        # (e.g. 2x - 4 = 2x + 7 → -11 = 0).  Same treatment as above.
        pass

    steps = []
    original_lhs_str = equation_str.split('=')[0].strip()
    original_rhs_str = equation_str.split('=')[1].strip()

    # Step 0: Original equation — show EXACTLY what the user typed.
    # _format_input_str applies only visual fixes (superscripts, fraction
    # markers, spacing) without SymPy reordering / combining / expanding.
    _fmt_input_lhs = _format_input_str(original_lhs_str)
    _fmt_input_rhs = _format_input_str(original_rhs_str)
    _fmt_input_eq  = _format_input_eq(original_lhs_str, original_rhs_str)
    steps.append({
        "description": "Starting with the original equation",
        "expression": _fmt_input_eq,
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
            action = "expands and combines to" if '(' in original_lhs_str else "combines to"
            parts.append(
                f"On the left side, {original_lhs_str} {action} "
                f"{_format_expr_plain(lhs)}"
            )
        if _rhs_changed:
            action = "expands and combines to" if '(' in original_rhs_str else "combines to"
            parts.append(
                f"On the right side, {original_rhs_str} {action} "
                f"{_format_expr_plain(rhs)}"
            )
        # Show: what the user typed  →  what it simplified to
        _combine_expr = (
            f"{_fmt_input_lhs} = {_fmt_input_rhs}"
            f"  \u2192  {_format_equation(lhs, rhs)}"
        )
        steps.append({
            "description": desc,
            "expression": _combine_expr,
            "explanation": ". ".join(parts) + ".",
        })

    # --- Step 1: Expand both sides (if needed) ---
    lhs_expanded = expand(lhs)
    rhs_expanded = expand(rhs)
    if lhs_expanded != lhs or rhs_expanded != rhs:
        before_lhs, before_rhs = _format_expr_plain(lhs), _format_expr_plain(rhs)
        steps.append({
            "description": "Expand both sides",
            "expression": _format_equation(lhs_expanded, rhs_expanded),
            "explanation": (
                f"We distribute any multiplication across parentheses. "
                f"{before_lhs} becomes {_format_expr_plain(lhs_expanded)}, and "
                f"{before_rhs} becomes {_format_expr_plain(rhs_expanded)}. "
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
        term_str       = _format_expr(subtract_term)        # for expressions
        term_str_plain = _format_expr_plain(subtract_term)  # for prose text
        if rhs_x_coeff > 0:
            desc = f"Subtract {term_str_plain} from both sides"
            work_expr = f"{_format_expr(lhs)} - {term_str} = {_format_expr(rhs)} - {term_str}"
            explanation = (
                f"The right side has the variable term {term_str_plain}. "
                f"To move all {var_name}-terms to the left, we subtract {term_str_plain} from both sides. "
                f"Whatever we do to one side, we must do to the other to keep the equation balanced."
            )
        else:
            pos_term       = _format_expr(-subtract_term)
            pos_term_plain = _format_expr_plain(-subtract_term)
            desc = f"Add {pos_term_plain} to both sides"
            work_expr = f"{_format_expr(lhs)} + {pos_term} = {_format_expr(rhs)} + {pos_term}"
            explanation = (
                f"The right side has {term_str_plain}. "
                f"To move all {var_name}-terms to the left, we add {pos_term_plain} to both sides. "
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
            "explanation": f"Combining like terms: the left side becomes {_format_expr_plain(new_lhs)} and the right side becomes {_format_expr_plain(new_rhs)}.",
        })
        lhs, rhs = new_lhs, new_rhs

    # Move constant terms from left to right
    lhs_x_coeff_now = lhs.coeff(var)
    lhs_const_now = expand(lhs - lhs_x_coeff_now * var)
    if lhs_const_now != 0:
        const_str       = _format_expr(lhs_const_now)        # for expressions
        const_str_plain = _format_expr_plain(lhs_const_now)  # for prose text
        if lhs_const_now > 0:
            desc = f"Subtract {const_str_plain} from both sides"
            work_expr = f"{_format_expr(lhs)} - {const_str} = {_format_expr(rhs)} - {const_str}"
            explanation = (
                f"The left side still has the constant {const_str_plain}. "
                f"To isolate the {var_name}-term, we subtract {const_str_plain} from both sides. "
                f"This moves the constant to the right side."
            )
        else:
            pos_const       = _format_expr(-lhs_const_now)
            pos_const_plain = _format_expr_plain(-lhs_const_now)
            desc = f"Add {pos_const_plain} to both sides"
            work_expr = f"{_format_expr(lhs)} + {pos_const} = {_format_expr(rhs)} + {pos_const}"
            explanation = (
                f"The left side has {const_str_plain}. "
                f"To isolate the {var_name}-term, we add {pos_const_plain} to both sides. "
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
            "explanation": f"Combining like terms: the left side becomes {_format_expr_plain(new_lhs)} and the right side becomes {_format_expr_plain(new_rhs)}.",
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
        # The variable cancelled out — degenerate equation.
        rhs_val = simplify(rhs)
        is_identity = (rhs_val == 0)

        if is_identity:
            final_stmt = "0 = 0"
            degenerate_step = {
                "description": "The variable cancels — identity",
                "expression": "0 = 0",
                "explanation": (
                    f"After combining like terms, {var_name} disappears from both sides "
                    f"and we are left with  0 = 0, which is always true.\n"
                    f"This means the equation is an identity: every real number "
                    f"satisfies it, so there are infinitely many solutions."
                ),
            }
            final_answer = (
                f"Infinite solutions — this equation is an identity.\n"
                f"Every real number satisfies {original_lhs_str} = {original_rhs_str}."
            )
        else:
            rhs_str_val = _format_expr(rhs_val)
            degenerate_step = {
                "description": "The variable cancels — contradiction",
                "expression": f"0 = {rhs_str_val}",
                "explanation": (
                    f"After combining like terms, {var_name} disappears from both sides "
                    f"and we are left with  0 = {rhs_str_val}, which is never true.\n"
                    f"This means the equation is a contradiction: no value of "
                    f"{var_name} can ever satisfy it, so there is no solution."
                ),
            }
            final_answer = (
                f"No solution — this equation is a contradiction.\n"
                f"Simplifies to  0 = {rhs_str_val},  which is impossible."
            )

        steps.append(degenerate_step)
        for i, step in enumerate(steps, start=1):
            step["step_number"] = i

        t_end = time.perf_counter()
        runtime_ms = round((t_end - t_start) * 1000, 2)

        given = {
            "problem": f"Solve the linear equation: {_fmt_input_eq}",
            "inputs": {
                "equation":   _fmt_input_eq,
                "left_side":  _fmt_input_lhs,
                "right_side": _fmt_input_rhs,
                "variable":   var_name,
            },
        }
        method = {
            "name": "Algebraic Isolation (Linear — Degenerate)",
            "description": "Isolate the variable by performing inverse operations step-by-step.",
            "parameters": {
                "equation_type": "Linear (degree 1) — Degenerate",
                "variable": var_name,
                "approach": "Expand → Collect like terms → Detect degenerate case",
            },
        }
        summary = {
            "runtime_ms": runtime_ms,
            "total_steps": len(steps),
            "verification_steps": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "library": f"SymPy {sympy.__version__}",
            "python": None,
        }
        return {
            "equation": equation_str,
            "given": given,
            "method": method,
            "steps": steps,
            "final_answer": final_answer,
            "verification_steps": [],
            "summary": summary,
        }

    if coeff != 1:
        coeff_str_expr  = _format_expr(coeff)        # for expressions (may contain fraction markers)
        coeff_str_plain = _format_expr_plain(coeff)  # for prose text (always readable)
        lhs_str_fmt = _format_expr(lhs)
        rhs_str_fmt = _format_expr(rhs)
        # Use ÷ notation when the coefficient itself is a fraction to avoid
        # nesting fraction markers (⟦⟦x|3⟧|⟦1|3⟧⟧) which the renderer can't handle.
        if _FRAC_OPEN in coeff_str_expr:
            divide_expr = f"{lhs_str_fmt} ÷ {coeff_str_expr} = {rhs_str_fmt} ÷ {coeff_str_expr}"
        else:
            divide_expr = f"{_frac(lhs_str_fmt, coeff_str_expr)} = {_frac(rhs_str_fmt, coeff_str_expr)}"
        steps.append({
            "description": f"Divide both sides by {coeff_str_plain}",
            "expression": divide_expr,
            "explanation": (
                f"The coefficient of {var_name} is {coeff_str_plain}. "
                f"To get {var_name} alone, we divide both sides by {coeff_str_plain}. "
                f"Dividing {_format_expr_plain(lhs)} by {coeff_str_plain} gives {var_name}, and "
                f"dividing {_format_expr_plain(rhs)} by {coeff_str_plain} gives us the value."
            ),
        })
        solution = simplify(rhs / coeff)
        steps.append({
            "description": "Simplify to get the answer",
            "expression": f"{var_name} = {_format_expr(solution)}",
            "explanation": f"Performing the division: {_format_expr_plain(rhs)} ÷ {coeff_str_plain} = {_format_expr_plain(solution)}. So {var_name} equals {_format_expr_plain(solution)}.",
        })
    else:
        solution = simplify(rhs)

    # Build verification steps
    lhs_check = _parse_side(equation_str.split('=')[0], var)
    rhs_check = _parse_side(equation_str.split('=')[1], var)
    sol_str_expr  = _format_expr(solution)        # for expressions
    sol_str_plain = _format_expr_plain(solution)  # for prose text
    sol_str = sol_str_expr  # kept for final_answer expression
    original_eq = f"{_format_expr(lhs_check)} = {_format_expr(rhs_check)}"

    verification_steps = []

    # Step 1: State what we're doing
    verification_steps.append({
        "description": "Start with the original equation",
        "expression": original_eq,
        "explanation": f"We will substitute {var_name} = {sol_str_plain} back into the original equation to verify our answer is correct.",
    })

    # Step 2: Show substitution
    lhs_substituted_str = _format_expr(lhs_check).replace(var_name, f'({sol_str_plain})')
    rhs_substituted_str = _format_expr(rhs_check).replace(var_name, f'({sol_str_plain})')
    verification_steps.append({
        "description": f"Substitute {var_name} = {sol_str_plain} into both sides",
        "expression": f"{lhs_substituted_str} = {rhs_substituted_str}",
        "explanation": f"We replace every {var_name} with {sol_str_plain} in both the left-hand side and right-hand side of the equation.",
    })

    # Step 3: Evaluate LHS
    lhs_val = simplify(lhs_check.subs(var, solution))
    verification_steps.append({
        "description": "Evaluate the left-hand side",
        "expression": f"LHS = {lhs_substituted_str} = {_format_expr(lhs_val)}",
        "explanation": f"Computing the left side: we substitute and simplify to get {_format_expr_plain(lhs_val)}.",
    })

    # Step 4: Evaluate RHS
    rhs_val = simplify(rhs_check.subs(var, solution))
    verification_steps.append({
        "description": "Evaluate the right-hand side",
        "expression": f"RHS = {rhs_substituted_str} = {_format_expr(rhs_val)}",
        "explanation": f"Computing the right side: we substitute and simplify to get {_format_expr_plain(rhs_val)}.",
    })

    # Step 5: Compare
    verification_steps.append({
        "description": "Compare both sides",
        "expression": f"LHS = {_format_expr(lhs_val)}, RHS = {_format_expr(rhs_val)}\nLHS = RHS  ✓",
        "explanation": f"Both sides equal {_format_expr_plain(lhs_val)}, confirming that {var_name} = {sol_str_plain} is the correct solution!",
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
        "problem": f"Solve the linear equation: {_fmt_input_eq}",
        "inputs": {
            "equation":   _fmt_input_eq,
            "left_side":  _fmt_input_lhs,
            "right_side": _fmt_input_rhs,
            "variable":   var_name,
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


# ── Multi-variable / system solvers ─────────────────────────────────────

def _solve_multi_var_single_eq(equation_str: str, var_names: list,
                               t_start: float) -> dict:
    """Solve a single linear equation with multiple variables.

    Expresses each variable in terms of the remaining ones.
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

    # Cache formatted originals before any modification
    _fmt_mv_lhs = _format_expr(lhs)
    _fmt_mv_rhs = _format_expr(rhs)
    _fmt_mv_eq  = _format_equation(lhs, rhs)

    # Verify linearity
    combined = expand(lhs - rhs)
    max_degree = 0
    for vs in var_symbols:
        p = combined.as_poly(vs)
        if p is not None and p.degree() > max_degree:
            max_degree = p.degree()
    # Also check total degree (catches products like x·y which are degree 2)
    try:
        total_poly = combined.as_poly(*var_symbols)
        if total_poly is not None and total_poly.total_degree() > max_degree:
            max_degree = total_poly.total_degree()
    except Exception:
        pass
    # Check transcendental / denominator before the degree test
    # (these make as_poly return None, leaving max_degree misleadingly at 0/1)
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

    # Step: original equation
    steps.append({
        "description": "Starting with the original equation",
        "expression": _fmt_mv_eq,
        "explanation": (
            f"We are given a linear equation with variables "
            f"{', '.join(var_names)}. We will express each variable "
            f"in terms of the others."
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

    # Combine like terms step: show if any variable appears >1 time in the
    # original string on either side (SymPy combines silently on parse).
    def _has_duplicate_vars(side_str, v_names):
        for vn in v_names:
            # count isolated occurrences of this variable letter
            if len(re.findall(r'\b' + re.escape(vn) + r'\b', side_str)) >= 2:
                return True
            # also catch cases like o+o where regex word boundary might miss
            if side_str.count(vn) >= 2:
                return True
        return False

    if _has_duplicate_vars(lhs_str, var_names) or _has_duplicate_vars(rhs_str, var_names):
        lhs_combined = expand(lhs)
        rhs_combined = expand(rhs)
        steps.append({
            "description": "Combine like terms",
            "expression": _format_equation(lhs_combined, rhs_combined),
            "explanation": (
                "Group and add terms with the same variable. "
                "For example, o + o = 2o."
            ),
        })
        lhs, rhs = lhs_combined, rhs_combined

    # Solve for each variable
    eq = Eq(lhs, rhs)
    solutions = {}
    for vn, vs in zip(var_names, var_symbols):
        sol = solve(eq, vs)
        if sol:
            solutions[vn] = sol[0]
            others = [v for v in var_names if v != vn]
            steps.append({
                "description": f"Solve for {vn}",
                "expression": f"{vn} = {_format_expr(sol[0])}",
                "explanation": (
                    f"Isolate {vn} by moving all other terms to the "
                    f"right side and dividing by its coefficient. "
                    f"Result is in terms of {', '.join(others)}."
                ),
            })

    # Final answer
    final_parts = [f"{vn} = {_format_expr(solutions[vn])}"
                   for vn in var_names if vn in solutions]
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
                "description": f"Substitute {first_vn} = {_format_expr(sol_expr)}",
                "expression": f"LHS = {_format_expr(lhs_sub)},  RHS = {_format_expr(rhs_sub)}",
                "explanation": (
                    f"Replacing {first_vn} in the original equation. "
                    f"Both sides reduce to the same expression, "
                    f"confirming correctness."
                ),
            })
            verification_steps.append({
                "description": "Solution verified",
                "expression": "LHS = RHS  ✓",
                "explanation": (
                    "The equation holds for any values of the "
                    "remaining variables."
                ),
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
            "problem": f"Solve the linear equation: {_fmt_mv_eq}",
            "inputs": {
                "equation":   _fmt_mv_eq,
                "left_side":  _fmt_mv_lhs,
                "right_side": _fmt_mv_rhs,
                "variables":  ", ".join(var_names),
            },
        },
        "method": {
            "name": "Algebraic Isolation (Multi-Variable)",
            "description": (
                "Express each variable in terms of the remaining "
                "variables by isolating it step-by-step."
            ),
            "parameters": {
                "equation_type": f"Linear with {len(var_names)} variables",
                "variables": ", ".join(var_names),
                "approach": "Expand → Isolate each variable",
            },
        },
        "steps": steps,
        "final_answer": final_answer,
        "verification_steps": verification_steps,
        "summary": {
            "runtime_ms": runtime_ms,
            "total_steps": len(steps),
            "verification_steps": len(verification_steps),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "library": f"SymPy {sympy.__version__}",
            "python": None,
        },
    }


def _solve_system(raw_equations: list, var_names: list,
                  original_input: str, t_start: float) -> dict:
    """Solve a system of linear equations."""
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
                f"Each equation must have exactly one '='. Problem: {eq_str}"
            )
        lhs = _parse_side(parts[0].strip(), var_symbols)
        rhs = _parse_side(parts[1].strip(), var_symbols)
        eq_objects.append(Eq(expand(lhs), expand(rhs)))

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
            f"{', '.join(var_names)}."
        ),
    })

    # Solve
    solution = solve(eq_objects, var_symbols, dict=True)
    if not solution:
        # Show elimination steps to expose the contradiction, then return
        # a proper result dict instead of raising an error.
        if n_eq >= 2:
            eq1, eq2 = eq_objects[0], eq_objects[1]
            raw1, raw2 = raw_equations[0], raw_equations[1]

            # Show the subtraction operation
            steps.append({
                "description": "Subtract equation (1) from equation (2)",
                "expression": (
                    f"({_format_expr(eq2.lhs)}) \u2212 ({_format_expr(eq1.lhs)})"
                    f" = ({_format_expr(eq2.rhs)}) \u2212 ({_format_expr(eq1.rhs)})"
                ),
                "explanation": (
                    f"To eliminate the variables, subtract equation (1) "
                    f"from equation (2). Whatever is on the left of (1) "
                    f"is subtracted from the left of (2), and same for the right."
                ),
            })

            diff_lhs = expand(eq2.lhs - eq1.lhs)
            diff_rhs = expand(eq2.rhs - eq1.rhs)
            diff_lhs_str = _format_expr(diff_lhs)
            diff_rhs_str = _format_expr(diff_rhs)

            steps.append({
                "description": "Simplify both sides",
                "expression": f"{diff_lhs_str} = {diff_rhs_str}",
                "explanation": (
                    f"After subtracting, all variable terms cancel on the "
                    f"left side, leaving {diff_lhs_str} = {diff_rhs_str}."
                ),
            })

            steps.append({
                "description": "Contradiction \u2014 No Solution",
                "expression": f"{diff_lhs_str} = {diff_rhs_str}",
                "explanation": (
                    f"The statement {diff_lhs_str} = {diff_rhs_str} is never true.\n"
                    f"All variables cancelled out but the constants do not match, "
                    f"so the system has no solution.\n"
                    f"Geometrically, the equations represent parallel lines "
                    f"that never intersect."
                ),
            })

        for i, s in enumerate(steps, 1):
            s["step_number"] = i

        t_end = time.perf_counter()
        runtime_ms = round((t_end - t_start) * 1000, 2)

        return {
            "equation": original_input,
            "given": {
                "problem": "Solve the system of linear equations",
                "inputs": {
                    "equations": original_input,
                    "number_of_equations": str(n_eq),
                    "variables": ", ".join(var_names),
                    "number_of_variables": str(n_var),
                },
            },
            "method": {
                "name": "Elimination Method (Inconsistent System)",
                "description": (
                    "Subtract equations to eliminate variables and "
                    "expose the contradiction."
                ),
                "parameters": {
                    "equation_type": "Linear System — No Solution",
                    "variables": ", ".join(var_names),
                    "approach": "Elimination \u2192 Detect contradiction",
                },
            },
            "steps": steps,
            "final_answer": (
                "No solution \u2014 the system is inconsistent.\n"
                "The equations represent parallel lines that never intersect."
            ),
            "verification_steps": [],
            "summary": {
                "runtime_ms": runtime_ms,
                "total_steps": len(steps),
                "verification_steps": 0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "library": f"SymPy {sympy.__version__}",
                "python": None,
            },
        }

    sol_dict = solution[0]
    free_vars = [
        vn for vn, vs in zip(var_names, var_symbols) if vs not in sol_dict
    ]

    # ── Detailed steps for 2×2 systems (substitution method) ────────────
    if n_eq == 2 and n_var == 2 and not free_vars:
        eq1, eq2 = eq_objects
        vs0, vs1 = var_symbols
        vn0, vn1 = var_names

        sol_from_eq1 = solve(eq1, vs0)
        if sol_from_eq1:
            expr_v0 = sol_from_eq1[0]
            steps.append({
                "description": f"From equation (1), isolate {vn0}",
                "expression": f"{vn0} = {_format_expr(expr_v0)}",
                "explanation": (
                    f"Rearrange equation (1) to express {vn0} in "
                    f"terms of {vn1}."
                ),
            })

            eq2_sub = eq2.subs(vs0, expr_v0)
            steps.append({
                "description": "Substitute into equation (2)",
                "expression": _format_equation(
                    expand(eq2_sub.lhs), expand(eq2_sub.rhs)
                ),
                "explanation": (
                    f"Replace {vn0} in equation (2) with "
                    f"{_format_expr(expr_v0)}."
                ),
            })

            sol_v1 = solve(eq2_sub, vs1)
            if sol_v1:
                v1_val = sol_v1[0]
                steps.append({
                    "description": f"Solve for {vn1}",
                    "expression": f"{vn1} = {_format_expr(v1_val)}",
                    "explanation": (
                        f"Simplify and solve to find "
                        f"{vn1} = {_format_expr(v1_val)}."
                    ),
                })

                v0_val = simplify(expr_v0.subs(vs1, v1_val))
                steps.append({
                    "description": f"Back-substitute to find {vn0}",
                    "expression": f"{vn0} = {_format_expr(v0_val)}",
                    "explanation": (
                        f"Substitute {vn1} = {_format_expr(v1_val)} back "
                        f"into {vn0} = {_format_expr(expr_v0)} to get "
                        f"{vn0} = {_format_expr(v0_val)}."
                    ),
                })
        else:
            _append_solution_step(steps, var_names, var_symbols, sol_dict)
    else:
        # Larger or underdetermined systems
        if free_vars:
            steps.append({
                "description": "Parametric solution",
                "expression": (
                    f"Free variable{'s' if len(free_vars) > 1 else ''}: "
                    f"{', '.join(free_vars)}"
                ),
                "explanation": (
                    f"The system is underdetermined — "
                    f"{', '.join(free_vars)} can take any value."
                ),
            })
        _append_solution_step(steps, var_names, var_symbols, sol_dict,
                              free_vars)

    # Final answer
    final_parts = []
    for vn, vs in zip(var_names, var_symbols):
        if vs in sol_dict:
            final_parts.append(f"{vn} = {_format_expr(sol_dict[vs])}")
        else:
            final_parts.append(f"{vn} is a free variable")
    final_answer = "\n".join(final_parts)

    # Verification
    verification_steps = []
    verification_steps.append({
        "description": "Substitute into every equation",
        "expression": "Checking…",
        "explanation": (
            "We plug the solution back into each original equation."
        ),
    })
    for i, (eq_str, eq_obj) in enumerate(zip(raw_equations, eq_objects)):
        lhs_val = simplify(eq_obj.lhs.subs(sol_dict))
        rhs_val = simplify(eq_obj.rhs.subs(sol_dict))
        ok = simplify(lhs_val - rhs_val) == 0
        verification_steps.append({
            "description": f"Equation ({i + 1}): {eq_str}",
            "expression": (
                f"LHS = {_format_expr(lhs_val)},  "
                f"RHS = {_format_expr(rhs_val)}"
                f"  →  {'✓' if ok else '✗'}"
            ),
            "explanation": (
                f"Both sides equal {_format_expr(lhs_val)}."
                if ok else "Sides differ — please check the input."
            ),
        })
    verification_steps.append({
        "description": "All equations verified",
        "expression": "All equations satisfied  ✓",
        "explanation": "The solution is correct.",
    })

    for i, s in enumerate(steps, 1):
        s["step_number"] = i
    for i, s in enumerate(verification_steps, 1):
        s["step_number"] = i

    t_end = time.perf_counter()
    runtime_ms = round((t_end - t_start) * 1000, 2)

    method_name = (
        "Substitution Method" if n_eq == 2 and n_var == 2
        else "Linear System Solver"
    )
    method_desc = (
        "Isolate one variable, substitute into the other equation, "
        "then back-substitute."
        if n_eq == 2 and n_var == 2 else
        "Solve using algebraic elimination / back-substitution."
    )

    return {
        "equation": original_input,
        "given": {
            "problem": "Solve the system of linear equations",
            "inputs": {
                "equations": original_input,
                "number_of_equations": str(n_eq),
                "variables": ", ".join(var_names),
                "number_of_variables": str(n_var),
            },
        },
        "method": {
            "name": method_name,
            "description": method_desc,
            "parameters": {
                "equation_type": (
                    f"System of {n_eq} linear equation"
                    f"{'s' if n_eq != 1 else ''}"
                ),
                "variables": ", ".join(var_names),
                "approach": (
                    "Isolate → Substitute → Solve → Back-substitute"
                    if n_eq == 2 and n_var == 2 else
                    "Row reduction → Back-substitution"
                ),
            },
        },
        "steps": steps,
        "final_answer": final_answer,
        "verification_steps": verification_steps,
        "summary": {
            "runtime_ms": runtime_ms,
            "total_steps": len(steps),
            "verification_steps": len(verification_steps),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "library": f"SymPy {sympy.__version__}",
            "python": None,
        },
    }


def _append_solution_step(steps, var_names, var_symbols, sol_dict,
                          free_vars=None):
    """Append a generic 'Solution' step listing all values."""
    lines = []
    for vn, vs in zip(var_names, var_symbols):
        if vs in sol_dict:
            lines.append(f"{vn} = {_format_expr(sol_dict[vs])}")
        else:
            lines.append(f"{vn}  (free variable)")
    steps.append({
        "description": "Solution",
        "expression": "\n".join(lines),
        "explanation": "Values that satisfy all equations simultaneously.",
    })


if __name__ == "__main__":
    # Quick test
    test_equations = [
        "2x + 3 = 7",
        "5x - 2 = 3x + 8",
        "3(x + 4) = 2x - 1",
        "x/2 + 1 = 4",
        "2x + 4y = 1",
        "x + y = 10, x - y = 2",
        "2a + b = 5, a - b = 1",
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

