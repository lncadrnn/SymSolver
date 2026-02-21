"""
Graph builder for SymSolver.

Produces a dark-themed matplotlib Figure for embedding in the Tkinter GUI.
Handles three equation types:
  - single_var : one equation, one unknown  (e.g. "2x + 3 = 7")
  - two_var    : one equation, two unknowns (e.g. "2x + 3y = 6")
  - system     : two equations, two unknowns (e.g. "x+y=10, x-y=2")
"""

import re
import numpy as np
from sympy import symbols, sympify, solve as sym_solve, lambdify, Eq
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
)

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

# ── palette ────────────────────────────────────────────────────────────────
C_BG       = "#0f0f0f"
C_AX       = "#181818"
C_GRID     = "#252525"
C_TICK     = "#666666"
C_SPINE    = "#333333"
C_LINE1    = "#1a8cff"   # primary line
C_LINE2    = "#ff8c42"   # secondary line (system)
C_HLINE    = "#aaaaaa"   # horizontal RHS line (single-var)
C_DOT      = "#4caf50"   # intersection / solution dot
C_TEXT     = "#cccccc"


def _parse_eq(eq_str):
    """Return (lhs_expr, rhs_expr) as SymPy expressions."""
    sides = eq_str.split("=")
    if len(sides) != 2:
        raise ValueError("Equation must contain exactly one '='")
    lhs_s = sides[0].strip().replace("^", "**")
    rhs_s = sides[1].strip().replace("^", "**")
    # Collect all single-letter variable names
    letters = sorted(set(re.findall(r"[a-zA-Z]", lhs_s + rhs_s)))
    local = {c: symbols(c) for c in letters}
    lhs = parse_expr(lhs_s, local_dict=local, transformations=TRANSFORMATIONS)
    rhs = parse_expr(rhs_s, local_dict=local, transformations=TRANSFORMATIONS)
    return lhs, rhs, local


def _style_axes(ax, fig):
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_AX)
    ax.tick_params(colors=C_TICK, labelsize=9)
    ax.xaxis.label.set_color(C_TEXT)
    ax.yaxis.label.set_color(C_TEXT)
    ax.title.set_color(C_TEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(C_SPINE)
    ax.grid(True, color=C_GRID, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.axhline(0, color=C_SPINE, linewidth=0.8)
    ax.axvline(0, color=C_SPINE, linewidth=0.8)


def analyze_result(result: dict) -> dict | None:
    """
    Return a structured analysis dict describing the mathematical case,
    form, and any anomalies.  Returns None if not analysable.

    Returned dict keys:
      eq_type   : "single_var" | "two_var" | "system"
      case      : "one_solution" | "no_solution" | "infinite" |
                  "degenerate_identity" | "degenerate_contradiction"
      case_label: human-readable short label
      form      : general algebraic form string
      description: multiline explanation of the case
      detail    : extra algebraic condition string (may be "")
      solution  : solution string or None
      graphable : bool
    """
    given  = result.get("given", {})
    inputs = given.get("inputs", {})
    final  = result.get("final_answer", "")

    if "equations" in inputs:
        return _analyze_system(inputs, final)
    if "variable" in inputs and "variables" not in inputs:
        return _analyze_single_var(inputs, final)
    if "variables" in inputs:
        var_list = [v.strip() for v in inputs["variables"].split(",")]
        if len(var_list) == 2:
            return _analyze_two_var(inputs, final)
    return None


def _analyze_single_var(inputs, final) -> dict:
    eq_str   = inputs.get("equation", "?")
    var_name = inputs.get("variable", "x")
    v        = var_name

    # Detect anomalies from final answer text
    if "Cannot solve" in final or "no solution" in final.lower():
        return {
            "eq_type":    "single_var",
            "case":       "no_solution",
            "case_label": "Contradiction — No Solution",
            "form":       f"a{v} + b = 0",
            "description": (
                f"When the coefficient of {v} is 0 but the constant is non-zero,\n"
                f"the equation reduces to a false statement like  5 = 0.\n"
                f"This is a contradiction — no value of {v} can satisfy it."
            ),
            "detail":   f"a = 0,  b ≠ 0   →   b = 0  is impossible",
            "solution": "No solution",
            "graphable": True,
        }
    if "infinite" in final.lower() or "every" in final.lower() or "all real" in final.lower():
        return {
            "eq_type":    "single_var",
            "case":       "infinite",
            "case_label": "Identity — Infinitely Many Solutions",
            "form":       f"a{v} + b = 0",
            "description": (
                f"When both the coefficient and constant are 0,\n"
                f"the equation reduces to  0 = 0  which is always true.\n"
                f"Every real number is a solution."
            ),
            "detail":   f"a = 0,  b = 0   →   0 = 0  (always true)",
            "solution": f"All real numbers (∞ solutions)",
            "graphable": True,
        }
    # Normal case — extract solution
    sol_str = ""
    for line in final.split("\n"):
        if "=" in line:
            sol_str = line.strip()
            break
    return {
        "eq_type":    "single_var",
        "case":       "one_solution",
        "case_label": "Normal Case — One Solution",
        "form":       f"a{v} + b = 0",
        "description": (
            f"The coefficient of {v} is non-zero (a ≠ 0), so there is\n"
            f"exactly one value of {v} that satisfies the equation.\n"
            f"Isolating {v} gives a unique solution."
        ),
        "detail":   f"a ≠ 0   →   {v} = –b / a",
        "solution": sol_str or final.strip(),
        "graphable": True,
    }


def _analyze_two_var(inputs, final) -> dict:
    eq_str   = inputs.get("equation", "?")
    var_list = [v.strip() for v in inputs.get("variables", "x, y").split(",")]
    xn       = var_list[0] if len(var_list) > 0 else "x"
    yn       = var_list[1] if len(var_list) > 1 else "y"

    try:
        lhs, rhs, local = _parse_eq(eq_str)
        from sympy import expand as sym_expand
        expr = sym_expand(lhs - rhs)
        # Degenerate: all coefficients zero
        xsym = local.get(xn, symbols(xn))
        ysym = local.get(yn, symbols(yn))
        a = expr.coeff(xsym)
        b = expr.coeff(ysym)
        c = -expr.subs([(xsym, 0), (ysym, 0)])
        a_zero = (a == 0)
        b_zero = (b == 0)
        c_zero = (c == 0)
    except Exception:
        a_zero = b_zero = c_zero = False

    if a_zero and b_zero:
        if c_zero:
            return {
                "eq_type":    "two_var",
                "case":       "degenerate_identity",
                "case_label": "Degenerate Identity — Entire Plane",
                "form":       f"a{xn} + b{yn} = c",
                "description": (
                    f"All coefficients are zero and the constant is also zero.\n"
                    f"The equation reduces to  0 = 0  which is true for every\n"
                    f"({xn}, {yn}) pair — the entire plane is the solution."
                ),
                "detail":   f"a = 0, b = 0, c = 0   →   0 = 0  (always true)",
                "solution": f"All ({xn}, {yn}) — entire plane",
                "graphable": False,
            }
        else:
            return {
                "eq_type":    "two_var",
                "case":       "degenerate_contradiction",
                "case_label": "Degenerate Contradiction — No Solution",
                "form":       f"a{xn} + b{yn} = c",
                "description": (
                    f"All variable coefficients are zero but the constant is non-zero.\n"
                    f"The equation reduces to a false statement like  c = 0.\n"
                    f"No ({xn}, {yn}) pair can satisfy it."
                ),
                "detail":   f"a = 0, b = 0, c ≠ 0   →   c = 0  is impossible",
                "solution": "No solution",
                "graphable": False,
            }

    return {
        "eq_type":    "two_var",
        "case":       "infinite",
        "case_label": "Normal Case — Infinitely Many Solutions (a Line)",
        "form":       f"a{xn} + b{yn} = c",
        "description": (
            f"At least one of a or b is non-zero, so this equation\n"
            f"represents a straight line in the {xn}{yn}-plane.\n"
            f"Every point on that line is a valid solution —\n"
            f"there are infinitely many solutions."
        ),
        "detail":   f"a ≠ 0 or b ≠ 0   →   a line with ∞ solutions",
        "solution": f"All points on the line  {eq_str.strip()}",
        "graphable": True,
    }


def _analyze_system(inputs, final) -> dict:
    eqs_str  = inputs.get("equations", "")
    var_list = [v.strip() for v in inputs.get("variables", "x, y").split(",")]
    xn       = var_list[0] if len(var_list) > 0 else "x"
    yn       = var_list[1] if len(var_list) > 1 else "y"

    eq_parts = re.split(r"[,;]", eqs_str)
    if len(eq_parts) < 2:
        return None

    try:
        from sympy import Rational, Matrix
        lhs1, rhs1, loc1 = _parse_eq(eq_parts[0].strip())
        lhs2, rhs2, loc2 = _parse_eq(eq_parts[1].strip())
        xsym = symbols(xn); ysym = symbols(yn)
        e1 = (lhs1 - rhs1).expand()
        e2 = (lhs2 - rhs2).expand()
        a1 = e1.coeff(xsym); b1 = e1.coeff(ysym); c1 = -e1.subs([(xsym,0),(ysym,0)])
        a2 = e2.coeff(xsym); b2 = e2.coeff(ysym); c2 = -e2.subs([(xsym,0),(ysym,0)])

        # Build augmented matrix determinant-style checks
        det = a1*b2 - a2*b1

        if det != 0:
            case = "one_solution"
        else:
            # parallel or same line: check if c ratios match
            # lines are identical if a1/a2 = b1/b2 = c1/c2
            try:
                same = (a1*c2 == a2*c1) and (b1*c2 == b2*c1)
            except Exception:
                same = False
            case = "infinite" if same else "no_solution"
    except Exception:
        # Fallback: infer from final answer text
        if "no solution" in final.lower() or "Cannot" in final:
            case = "no_solution"
        elif "infinite" in final.lower():
            case = "infinite"
        else:
            case = "one_solution"

    eq1_s = eq_parts[0].strip()
    eq2_s = eq_parts[1].strip()

    if case == "one_solution":
        sol_lines = [l.strip() for l in final.split("\n") if "=" in l]
        sol_str = "  ,  ".join(sol_lines) if sol_lines else final.strip()
        return {
            "eq_type":    "system",
            "case":       "one_solution",
            "case_label": "Consistent Independent — One Solution",
            "form":       f"a₁{xn} + b₁{yn} = c₁\na₂{xn} + b₂{yn} = c₂",
            "description": (
                f"The two lines have different slopes, so they intersect\n"
                f"at exactly one point. There is a unique ({xn}, {yn}) pair\n"
                f"that satisfies both equations simultaneously."
            ),
            "detail":   f"det([a₁b₂ − a₂b₁]) ≠ 0   →   unique intersection",
            "solution": sol_str,
            "graphable": True,
        }
    if case == "no_solution":
        return {
            "eq_type":    "system",
            "case":       "no_solution",
            "case_label": "Inconsistent System — No Solution",
            "form":       f"a₁{xn} + b₁{yn} = c₁\na₂{xn} + b₂{yn} = c₂",
            "description": (
                f"The two lines are parallel — they have the same slope\n"
                f"but different intercepts, so they never intersect.\n"
                f"No ({xn}, {yn}) pair satisfies both equations."
            ),
            "detail":   f"a₁/a₂ = b₁/b₂  but  c₁/c₂ ≠ a₁/a₂   →   parallel lines",
            "solution": "No solution",
            "graphable": True,
        }
    # infinite
    return {
        "eq_type":    "system",
        "case":       "infinite",
        "case_label": "Dependent System — Infinitely Many Solutions",
        "form":       f"a₁{xn} + b₁{yn} = c₁\na₂{xn} + b₂{yn} = c₂",
        "description": (
            f"Both equations represent the same line.\n"
            f"Every point on that line satisfies both equations,\n"
            f"so there are infinitely many solutions."
        ),
        "detail":   f"a₁/a₂ = b₁/b₂ = c₁/c₂   →   same line",
        "solution": f"All points on the line  {eq1_s}",
        "graphable": True,
    }


def build_figure(result: dict):
    """
    Build and return a dark-themed matplotlib Figure for *result*.
    Returns None if graphing is not applicable (>2 variables, no solution, etc.).
    """
    from matplotlib.figure import Figure

    given  = result.get("given", {})
    inputs = given.get("inputs", {})
    final  = result.get("final_answer", "")

    # ── Detect case ────────────────────────────────────────────────────
    if "equations" in inputs:
        # System of two equations
        return _build_system(inputs, final)

    if "variable" in inputs and "variables" not in inputs:
        # Single-variable equation
        return _build_single_var(inputs, final)

    if "variables" in inputs:
        var_list = [v.strip() for v in inputs["variables"].split(",")]
        if len(var_list) == 2:
            return _build_two_var(inputs, final)
        # >2 variables — not graphable in 2-D
        return None

    return None


# ── Single-variable ─────────────────────────────────────────────────────────

def _build_single_var(inputs, final):
    from matplotlib.figure import Figure

    eq_str = inputs.get("equation", "")
    var_name = inputs.get("variable", "x")

    try:
        lhs, rhs, local = _parse_eq(eq_str)
        x = local.get(var_name, symbols(var_name))
    except Exception:
        return None

    # Determine solution value
    sol_val = None
    match = re.search(r"=\s*(-?[\d./]+)", final)
    if match:
        try:
            sol_val = float(match.group(1))
        except ValueError:
            pass

    # Anomaly detection
    anomaly = None
    if "Cannot solve" in final or "no solution" in final.lower():
        anomaly = "no_solution"
    elif "infinite" in final.lower() or "every" in final.lower():
        anomaly = "infinite"

    # X range — centre around solution
    cx = sol_val if sol_val is not None else 0.0
    x_range = np.linspace(cx - 5, cx + 5, 400)

    try:
        f_lhs = lambdify(x, lhs, modules="numpy")
        f_rhs = lambdify(x, rhs, modules="numpy")
        y_lhs = np.array(f_lhs(x_range), dtype=float)
        # Evaluate RHS as a full function of x so diagonal RHS lines
        # (e.g. 2x + 7) are plotted correctly, not collapsed to a constant.
        _rhs_raw = f_rhs(x_range)
        if np.ndim(_rhs_raw) == 0:          # RHS is a pure constant
            y_rhs = np.full_like(x_range, float(_rhs_raw), dtype=float)
        else:
            y_rhs = np.array(_rhs_raw, dtype=float)
    except Exception:
        return None

    fig = Figure(figsize=(7, 3.4), dpi=100)
    ax  = fig.add_subplot(111)
    _style_axes(ax, fig)

    label_lhs = f"LHS: {inputs.get('left_side', 'f(x)')}"
    label_rhs = f"RHS: {inputs.get('right_side', 'g(x)')}"

    ax.plot(x_range, y_lhs, color=C_LINE1, linewidth=2, label=label_lhs)
    ax.plot(x_range, y_rhs, color=C_LINE2,  linewidth=2, label=label_rhs)

    if anomaly == "no_solution":
        ax.set_title("No Solution — Lines are parallel", color=C_TEXT, fontsize=10)
    elif anomaly == "infinite":
        ax.set_title("Infinite Solutions — Lines overlap", color=C_TEXT, fontsize=10)
    elif sol_val is not None:
        y_at_sol = float(f_rhs(sol_val))
        ax.scatter([sol_val], [y_at_sol], color=C_DOT, s=80, zorder=5,
                   label=f"Solution: {var_name} = {sol_val:g}")
        ax.axvline(sol_val, color=C_DOT, linewidth=1, linestyle=":", alpha=0.6)
        ax.set_title(f"Solution: {var_name} = {sol_val:g}", color=C_TEXT, fontsize=10)

    ax.set_xlabel(var_name, color=C_TEXT)
    ax.set_ylabel("value", color=C_TEXT)
    leg = ax.legend(fontsize=8, facecolor="#1e1e1e", edgecolor=C_SPINE,
                    labelcolor=C_TEXT)
    fig.tight_layout(pad=1.2)
    return fig


# ── Two-variable single equation ────────────────────────────────────────────

def _build_two_var(inputs, final):
    from matplotlib.figure import Figure

    eq_str   = inputs.get("equation", "")
    var_list = [v.strip() for v in inputs.get("variables", "x, y").split(",")]
    if len(var_list) < 2:
        return None
    xn, yn = var_list[0], var_list[1]

    try:
        lhs, rhs, local = _parse_eq(eq_str)
        xsym = local[xn]; ysym = local[yn]
    except Exception:
        return None

    # Solve for y in terms of x
    try:
        expr = lhs - rhs
        y_sols = sym_solve(expr, ysym)
        if not y_sols:
            return None
        y_expr = y_sols[0]
        f_y = lambdify(xsym, y_expr, modules="numpy")
    except Exception:
        return None

    x_range = np.linspace(-8, 8, 400)
    try:
        y_vals = np.array(f_y(x_range), dtype=float)
    except Exception:
        return None

    fig = Figure(figsize=(7, 3.4), dpi=100)
    ax  = fig.add_subplot(111)
    _style_axes(ax, fig)

    ax.plot(x_range, y_vals, color=C_LINE1, linewidth=2,
            label=f"{eq_str.strip()}")
    ax.set_title(f"Infinite solutions — every point on the line satisfies: {eq_str.strip()}",
                 color=C_TEXT, fontsize=9)
    ax.set_xlabel(xn, color=C_TEXT)
    ax.set_ylabel(yn, color=C_TEXT)
    leg = ax.legend(fontsize=8, facecolor="#1e1e1e", edgecolor=C_SPINE,
                    labelcolor=C_TEXT)
    fig.tight_layout(pad=1.2)
    return fig


# ── System of two equations ─────────────────────────────────────────────────

def _build_system(inputs, final):
    from matplotlib.figure import Figure

    eqs_str  = inputs.get("equations", "")
    var_list = [v.strip() for v in inputs.get("variables", "x, y").split(",")]
    if len(var_list) < 2:
        return None
    xn, yn = var_list[0], var_list[1]

    # Split on comma or semicolon
    eq_parts = re.split(r"[,;]", eqs_str)
    if len(eq_parts) < 2:
        return None
    eq1_str, eq2_str = eq_parts[0].strip(), eq_parts[1].strip()

    def _line_fn(eq_s):
        try:
            lhs, rhs, local = _parse_eq(eq_s)
            xsym = local.get(xn, symbols(xn))
            ysym = local.get(yn, symbols(yn))
            expr = lhs - rhs
            y_sols = sym_solve(expr, ysym)
            if not y_sols:
                return None, None
            return lambdify(xsym, y_sols[0], modules="numpy"), str(y_sols[0])
        except Exception:
            return None, None

    f1, expr1 = _line_fn(eq1_str)
    f2, expr2 = _line_fn(eq2_str)
    if f1 is None or f2 is None:
        return None

    # Parse solution coordinates
    sol_x = sol_y = None
    for line in final.split("\n"):
        if "=" in line:
            vname, _, vval = line.partition("=")
            vname = vname.strip(); vval = vval.strip()
            try:
                v = float(vval)
                if vname == xn:
                    sol_x = v
                elif vname == yn:
                    sol_y = v
            except ValueError:
                pass

    # Determine x range
    cx = sol_x if sol_x is not None else 0.0
    x_range = np.linspace(cx - 8, cx + 8, 400)

    try:
        y1 = np.array(f1(x_range), dtype=float)
        y2 = np.array(f2(x_range), dtype=float)
    except Exception:
        return None

    fig = Figure(figsize=(7, 3.8), dpi=100)
    ax  = fig.add_subplot(111)
    _style_axes(ax, fig)

    ax.plot(x_range, y1, color=C_LINE1, linewidth=2, label=eq1_str)
    ax.plot(x_range, y2, color=C_LINE2, linewidth=2, label=eq2_str)

    # Anomaly / intersection
    diff = np.abs(y1 - y2)
    if np.allclose(y1, y2, atol=1e-6):
        title = "Infinite solutions — same line (equations are equivalent)"
    elif np.all(diff > 1e-6):
        # Check if lines never cross in range → parallel
        slope1 = (y1[-1] - y1[0]) / (x_range[-1] - x_range[0])
        slope2 = (y2[-1] - y2[0]) / (x_range[-1] - x_range[0])
        if abs(slope1 - slope2) < 1e-6:
            title = "No solution — parallel lines (never intersect)"
        else:
            title = "One solution — lines intersect"
    else:
        title = "One solution — lines intersect"

    if sol_x is not None and sol_y is not None:
        ax.scatter([sol_x], [sol_y], color=C_DOT, s=90, zorder=5,
                   label=f"Intersection: ({sol_x:g}, {sol_y:g})")
        ax.set_title(f"{title}  at  ({sol_x:g}, {sol_y:g})", color=C_TEXT, fontsize=9)
    else:
        ax.set_title(title, color=C_TEXT, fontsize=9)

    ax.set_xlabel(xn, color=C_TEXT)
    ax.set_ylabel(yn, color=C_TEXT)

    # Clip y-axis to avoid extreme values
    y_all = np.concatenate([y1, y2])
    y_finite = y_all[np.isfinite(y_all)]
    if len(y_finite):
        ylo, yhi = np.percentile(y_finite, 2), np.percentile(y_finite, 98)
        pad = max((yhi - ylo) * 0.2, 1.0)
        ax.set_ylim(ylo - pad, yhi + pad)

    leg = ax.legend(fontsize=8, facecolor="#1e1e1e", edgecolor=C_SPINE,
                    labelcolor=C_TEXT)
    fig.tight_layout(pad=1.2)
    return fig
