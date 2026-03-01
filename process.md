# How DualSolver Parses and Solves Linear Equations

I'll walk you through the entire process using **`2x + 2 = 5`** as the primary example, with a secondary example **`2x + 5x + 3 = 1 + 5`** to show how like-term combining works. Additional sections cover multi-variable equations, systems of equations, non-linear detection, graphing, theming, and the animated trail rendering pipeline.

Every computation follows the **Standard Trail Format**, which ensures the UI always displays these seven sections: **GIVEN → METHOD → STEPS → FINAL ANSWER → VERIFICATION → GRAPH & ANALYSIS → SUMMARY**.

---

## 1. User Input → GUI

**User types:** `2x + 2 = 5`

**What happens:**
- The Tkinter entry widget in [`gui/app.py`](gui/app.py) captures the input
- When the user clicks **Solve** or presses **Enter**, the input is trimmed
- A user message bubble is added to the chat area, and a "Solving…" indicator appears
- The solver runs in a background thread to keep the GUI responsive

---

## 2. GUI → Solver

The GUI calls the solver directly (no HTTP/API layer):

```python
from solver import solve_linear_equation

result = solve_linear_equation(equation)
```

A `time.perf_counter()` timer starts at the top of `solve_linear_equation()` to measure runtime for the trail summary.

---

## 3. Parsing Phase ([`solver/engine.py`](solver/engine.py))

### Step 3.1: Check for `=` sign

```python
if '=' not in equation_str:
    raise ValueError("Equation must contain '='. Example: 3x + 2 = 7")
```

✅ **Pass:** `2x + 2 = 5` contains `=`

### Step 3.2: Split into left and right sides

```python
parts = equation_str.split('=')  # ["2x + 2", "5"]

if len(parts) != 2:
    raise ValueError("Equation must contain exactly one '=' sign.")

lhs_str = "2x + 2"
rhs_str = "5"
```

✅ **Pass:** Exactly one `=` sign

### Step 3.3: Parse each side using SymPy

The `_parse_side` function processes each side:

```python
def _parse_side(expr_str: str, var_symbol: Symbol):
    s = expr_str.strip()
    s = s.replace('^', '**')  # Convert user-friendly ^ to Python **
    local = {var_symbol.name: var_symbol}
    try:
        return parse_expr(s, 
                         local_dict=local, 
                         transformations=TRANSFORMATIONS)
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}'. Error: {e}")
```

**For `2x + 2`:**
- SymPy's `implicit_multiplication_application` transformation converts `2x` → `2*x`
- Result: `Add(Mul(2, x), 2)` (SymPy expression tree)

**For `5`:**
- Result: `Integer(5)`

> **Important:** SymPy auto-combines like terms during parsing. For example, `2x + 5x + 3` is parsed directly as `7*x + 3`. Similarly, `3(x + 4)` is auto-expanded to `3*x + 12`. The solver detects this and shows it as an explicit step (see §5.3).

### Step 3.4: Helper — `_count_terms_in_str`

To detect auto-simplification, the solver counts top-level additive terms in the **raw text** and compares with the parsed result:

```python
def _count_terms_in_str(expr_str: str) -> int:
    """Count top-level additive terms, respecting parentheses."""
    depth = 0
    count = 1
    i = 0
    # Skip leading sign
    if s[0] in ('+', '-'):
        i = 1
    while i < len(s):
        ch = s[i]
        if ch == '(':   depth += 1
        elif ch == ')': depth -= 1
        elif ch in ('+', '-') and depth == 0:
            count += 1
        i += 1
    return count
```

| Input string | Result |
|---|---|
| `"2x + 5x + 3"` | 3 |
| `"1 + 5"` | 2 |
| `"3(x + 4)"` | 1 (the `+` is inside parens) |
| `"2(x+1) + 3x"` | 2 |

---

## 4. Validation Phase

### Check if equation is linear

```python
combined = lhs - rhs  # (2x + 2) - 5 = 2x - 3
combined_expanded = expand(combined)
poly_degree = combined_expanded.as_poly(x)

if poly_degree.degree() > 1:
    raise ValueError("This is a degree-{degree} equation, not linear.")
if poly_degree.degree() == 0:
    raise ValueError("No variable 'x' found in the equation.")
```

✅ **Pass:** Degree is 1 (linear)

---

## 5. Trail Format — How the Result is Built

After parsing and validation, the solver generates all six sections of the Standard Trail Format.

### 5.1 GIVEN — Problem Statement & Inputs

```python
given = {
    "problem": "Solve the linear equation: 2x + 2 = 5",
    "inputs": {
        "equation": "2x + 2 = 5",
        "left_side": "2x + 2",
        "right_side": "5",
        "variable": "x",
    },
}
```

This is built from the parsed input and displayed in the UI as the first card.

### 5.2 METHOD — Algorithm & Parameters

```python
method = {
    "name": "Algebraic Isolation (Linear)",
    "description": "Isolate the variable by performing inverse operations step-by-step.",
    "parameters": {
        "equation_type": "Linear (degree 1)",
        "variable": "x",
        "approach": "Expand → Collect like terms → Isolate variable → Simplify",
    },
}
```

This tells the reader exactly which algorithm is being used and what strategy the solver follows.

### 5.3 STEPS — Numbered Step-by-Step Solution

Each step is a dict with `step_number`, `description`, `expression`, and `explanation`.

**Step 1: Original equation (as the user typed it)**

```python
{
    "step_number": 1,
    "description": "Starting with the original equation",
    "expression": "2x + 2 = 5",  # exact user input, not SymPy's formatted version
    "explanation": "We are given the equation 2x + 2 = 5. Our goal is to isolate x..."
}
```

The expression is the **raw user input** (e.g. `2x + 5x + 3 = 1 + 5`), not SymPy's already-simplified form. This lets the next step show what changed.

**Step 2: Combine like terms / Expand (if needed)**

Before any algebraic moves, SymPy may have auto-simplified the parsed expression. The solver detects this by comparing:
- The number of top-level additive terms in the **original text** (via `_count_terms_in_str`)
- The number of terms in the **parsed SymPy expression** (via `Add.make_args`)
- Whether **parentheses disappeared** during parsing

Depending on what changed, the step is labelled:

| What happened | Step description |
|---|---|
| Like terms merged (e.g. `2x + 5x` → `7x`) | **Combine like terms** |
| Parentheses distributed (e.g. `3(x+4)` → `3x + 12`) | **Expand** |
| Both at once (e.g. `2(x+1) + 3x` → `5x + 2`) | **Expand and combine like terms** |
| Nothing changed (e.g. `2x + 2 = 5`) | *Step skipped entirely* |

**Example — `2x + 5x + 3 = 1 + 5`:**

```python
{
    "step_number": 2,
    "description": "Combine like terms",
    "expression": "7x + 3 = 6",
    "explanation": "On the left side, 2x + 5x + 3 simplifies to 7x + 3. "
                   "On the right side, 1 + 5 simplifies to 6."
}
```

**Example — `3(x + 4) = 2x - 1`:**

```python
{
    "step_number": 2,
    "description": "Expand",
    "expression": "3x + 12 = 2x - 1",
    "explanation": "On the left side, 3(x + 4) expands to 3x + 12."
}
```

For our primary example `2x + 2 = 5`, neither side changes during parsing, so this step is **skipped**.

**Step 2: Expand both sides (legacy — if still needed after combining)**

If the parsed expression still contains un-expanded terms (rare after the above step), SymPy's `expand()` is applied. Usually this is a no-op now.

**Step 2: Move constants to the right**

```python
{
    "step_number": 2,
    "description": "Subtract 2 from both sides",
    "expression": "2·x + 2 - 2 = 5 - 2",
    "explanation": "The left side still has the constant 2. To isolate the x-term, we subtract 2 from both sides..."
}
```

**Step 3: Simplify**

```python
{
    "step_number": 3,
    "description": "Simplify both sides",
    "expression": "2·x = 3",
    "explanation": "Combining like terms: the left side becomes 2·x and the right side becomes 3."
}
```

**Step 4: Divide by coefficient**

```python
{
    "step_number": 4,
    "description": "Divide both sides by 2",
    "expression": "2·x / 2 = 3 / 2",
    "explanation": "The coefficient of x is 2. To get x alone, we divide both sides by 2..."
}
```

**Step 5: Simplify to get the answer**

```python
{
    "step_number": 5,
    "description": "Simplify to get the answer",
    "expression": "x = 3/2",
    "explanation": "Performing the division: 3 ÷ 2 = 3/2. So x equals 3/2."
}
```

Steps are numbered automatically:
```python
for i, step in enumerate(steps, start=1):
    step["step_number"] = i
```

### 5.4 FINAL ANSWER — Highlighted Result

```python
final_answer = "x = 3/2"
```

Displayed in a green-bordered card in the UI.

### 5.5 VERIFICATION — Substitution Check

The solver generates numbered verification steps to prove the answer:

```python
verification_steps = [
    {
        "step_number": 1,
        "description": "Start with the original equation",
        "expression": "2·x + 2 = 5",
        "explanation": "We will substitute x = 3/2 back into the original equation..."
    },
    {
        "step_number": 2,
        "description": "Substitute x = 3/2 into both sides",
        "expression": "2·(3/2) + 2 = 5",
        "explanation": "We replace every x with 3/2..."
    },
    {
        "step_number": 3,
        "description": "Evaluate the left-hand side",
        "expression": "LHS = 2·(3/2) + 2 = 5",
        "explanation": "Computing: 2 × 3/2 = 3, then 3 + 2 = 5"
    },
    {
        "step_number": 4,
        "description": "Evaluate the right-hand side",
        "expression": "RHS = 5",
        "explanation": "The right side is already simplified to 5"
    },
    {
        "step_number": 5,
        "description": "Compare both sides",
        "expression": "LHS = 5, RHS = 5\nLHS = RHS  ✓",
        "explanation": "Both sides equal 5, confirming that x = 3/2 is the correct solution!"
    }
]
```

### 5.6 SUMMARY — Runtime, Metadata & Library Versions

```python
t_end = time.perf_counter()
runtime_ms = round((t_end - t_start) * 1000, 2)

summary = {
    "runtime_ms": 165.72,
    "total_steps": 5,
    "verification_steps": 5,
    "timestamp": "2026-02-20 20:34:26",
    "library": "SymPy 1.14.0",
    "python": None,
}
```

---

## 6. Return Value — Complete Trail Dict

The solver returns everything in a single dict:

```python
return {
    "equation": "2x + 2 = 5",
    "given": { ... },
    "method": { ... },
    "steps": [ ... ],              # numbered step dicts
    "final_answer": "x = 3/2",
    "verification_steps": [ ... ], # numbered verification dicts
    "summary": { ... },
}
```

---

## 7. GUI Rendering — Standard Trail Format (Animated)

Back in [`gui/app.py`](gui/app.py), the `_show_result` method builds an **animation queue** — a list of callables that fire one-by-one with short pauses between them. Each callable renders one trail section with a "phase status" indicator (e.g. *"Identifying Given…"*, *"Verifying final answer…"*) that is replaced by the actual content after a brief delay.

| # | Section | Icon | What the UI shows |
|---|---------|------|-------------------|
| 1 | **GIVEN** | ✎ | Problem statement, equation, left/right sides, variable(s) |
| 2 | **METHOD** | ⚙ | Algorithm name, description, parameters (equation type, approach) |
| 3 | **STEPS** | » | Numbered step cards — each with bold description, monospace expression, and collapsible explanation |
| 4 | **FINAL ANSWER** | ✓ | Green-bordered card with the solution (e.g. `x = 3/2`). For non-linear equations this is a multi-line educational explanation with a red/orange badge |
| 5 | **VERIFICATION** | ≡ | Collapsible section with numbered substitution-check steps |
| 6 | **GRAPH & ANALYSIS** | Δ | Embedded matplotlib figure + structured case-analysis card (see §9) |
| 7 | **SUMMARY** | ■ | Runtime (ms), step counts, timestamp, SymPy version |

Each section has an accent-coloured header with a thin underline, rendered by `_render_section_header()`. Step cards are produced by the animation pipeline which shows a step-number prefix, and explanations are toggled via "▸ Show Explanation" / "▾ Hide Explanation" buttons.

### Animation Pipeline

```
_show_result() builds queue: [_render_given, _render_method, _render_step×N, _render_answer, _render_verify, _render_graph, _render_summary, _finish]
    ↓
_advance_queue() pops the next callable
    ↓
Callable shows a status label ("Solving step 3…")
    ↓
After _PHASE_PAUSE ms → status replaced by actual content
    ↓
_schedule_next() → Tk.after(400ms) → _advance_queue()
    ↓
Repeat until queue is empty
```

A **Stop button** (⏹) appears during animation and cancels the queue when clicked, leaving partial results visible.

---

## 8. Error Handling & Fallbacks

### Character validation

Before any parsing, `_validate_characters()` rejects input containing characters outside the allowed set (letters, digits, whitespace, and `+ - * / ^ = ( ) . , ;`).

### Missing `=` sign
```python
if '=' not in equation_str:
    raise ValueError("Equation must contain '='. Example: 3x + 2 = 7")
```
**GUI shows:** Red error message card

### Multiple `=` signs
```python
if len(parts) != 2:
    raise ValueError("Equation must contain exactly one '=' sign.")
```

### Unparseable input
```python
try:
    return parse_expr(s, ...)
except Exception as e:
    raise ValueError(f"Could not parse expression: '{expr_str}'. Error: {e}")
```
**Example:** `2x + + = 5` → "Could not parse expression"

### Not linear (quadratic, cubic, etc.)
Instead of raising an error, non-linear equations return a **full educational result dict** via `_nonlinear_error_result()`. See §10 for details.

### No variable found
```python
if poly_degree.degree() == 0:
    raise ValueError("No variable 'x' found in the equation.")
```
**Example:** `2 + 3 = 5` → "No variable 'x' found"

### Infinite solutions (identity)
```python
if val == 0:
    # "identity" — 0 = 0
    final_answer = "Infinite solutions — this equation is an identity."
```
**Example:** `2x + 3 = 2x + 3`

### No solution (contradiction)
```python
else:
    # "contradiction" — 0 = non-zero
    final_answer = "No solution — this equation is a contradiction."
```
**Example:** `2x + 3 = 2x + 5`

---

## 9. Multi-Variable Equations ([`solver/engine.py`](solver/engine.py) — `_solve_multi_var_single_eq`)

When `_detect_variables()` finds more than one variable but there is only one equation (no comma/semicolon separator), the solver uses the multi-variable path.

**Example:** `2x + 4y = 1`

### 9.1 Variable Detection

```python
var_names = _detect_variables("2x + 4y = 1")  # → ['x', 'y']
```

`_detect_variables()` scans for single-letter tokens, ignoring reserved math functions (`sin`, `cos`, `log`, `exp`, `sqrt`, `pi`, `abs`, `E`). Multi-character alphabetic tokens that aren't reserved are treated as implicit multiplication of their letters (e.g. `xyz` → `x·y·z`).

### 9.2 Implicit Variable Expansion

Before parsing, `_expand_implicit_vars()` converts multi-letter tokens composed entirely of known variable letters into explicit multiplication. This prevents Python reserved words (e.g. `as`, `in`, `for`) from causing syntax errors:

```python
_expand_implicit_vars("2as + 3", {"a", "s"})  # → "2a*s + 3"
```

### 9.3 Linearity Validation

The solver checks:
1. **Per-variable degree** — each variable individually must be degree ≤ 1
2. **Total degree** — the combined polynomial degree must be ≤ 1 (catches cross-products like `x·y`)
3. **Transcendental functions** — `sin(x)`, `log(y)`, etc. make the equation non-linear
4. **Denominator variables** — `1/x` is equivalent to `x⁻¹`, also non-linear

If any check fails, the solver returns an educational non-linear result (§10).

### 9.4 Solving

For each variable, SymPy's `solve()` isolates it in terms of the remaining variables:

```python
# For 2x + 4y = 1:
#   x = (1 - 4y) / 2 = 1/2 - 2y
#   y = (1 - 2x) / 4 = 1/4 - x/2
```

### 9.5 Trail Output

The method card shows **"Algebraic Isolation (Multi-Variable)"** and the given card lists all detected variables. The final answer shows each variable expressed in terms of the others.

---

## 10. Non-Linear Equation Detection & Education

When the solver determines an equation is not linear, it does **not** raise an error. Instead, `_nonlinear_error_result()` builds a complete trail dict with:

- A **GIVEN** card showing the original equation
- A **METHOD** card labelled "Linearity Check"
- **STEPS** that expand and identify the non-linear element
- A **FINAL ANSWER** containing a multi-line educational explanation

### 10.1 Detection Reasons

`_detect_nonlinear_reason()` classifies the non-linearity:

| Reason | Detection | Example |
|--------|-----------|---------|
| `degree` | Polynomial degree > 1 | `x² + 2 = 5` |
| `transcendental` | Variable inside trig/log/exp | `sin(x) = 1` |
| `denominator` | Variable in denominator | `1/x + 1 = 3` |
| `product` | Total degree ≥ 2 from cross-terms | `x·y = 6` |

### 10.2 Educational Messages

`_build_educational_message()` generates a detailed explanation for each reason. For degree-based cases, it includes a classification table:

```
Degree 0  →  constant   (e.g.  5 = 5)
Degree 1  →  linear     (e.g.  3x + 2 = 7)  ← must be this
Degree 2  →  quadratic  (e.g.  x² + 5x + 6 = 0)
Degree 3  →  cubic      (e.g.  x³ − 2x² + x = 0)
...
```

For denominator cases it explains negative exponents; for transcendental cases it explains why functions like `sin(x)` break linearity.

### 10.3 Trail Differences

Non-linear results include `"nonlinear_education": True` which tells the GUI to:
- Use a coloured badge (red/orange) instead of the green success badge
- Skip the verification section (no solution to verify)
- Skip the graph section (non-linear equations are not graphed)

---

## 11. Systems of Equations ([`solver/engine.py`](solver/engine.py) — `_solve_system`)

When the input contains commas or semicolons, `solve_linear_equation()` splits it into multiple equations and dispatches to `_solve_system()`.

**Example:** `x + y = 10, x - y = 2`

### 11.1 Parsing

Each equation is parsed independently. All detected variables are shared across the system:

```python
raw_equations = ["x + y = 10", "x - y = 2"]
var_names = _detect_variables("x + y = 10 x - y = 2")  # → ['x', 'y']
```

### 11.2 Linearity Check

Every equation in the system is individually checked for linearity (degree, transcendental, denominator, product). If any equation is non-linear, the entire system returns an educational result.

### 11.3 Solving (2×2 Systems — Substitution Method)

For a 2-equation, 2-variable system, the solver shows detailed substitution steps:

```
Step 1: System of equations
Step 2: From equation (1), isolate x  →  x = 10 - y
Step 3: Substitute into equation (2)  →  (10 - y) - y = 2
Step 4: Solve for y  →  y = 4
Step 5: Back-substitute to find x  →  x = 6
```

### 11.4 Inconsistent Systems (No Solution)

When `solve()` returns an empty solution, the solver shows **elimination steps** to expose the contradiction:

```
Step 1: System of equations
Step 2: Subtract equation (1) from equation (2)
Step 3: Simplify both sides  →  0 = 3
Step 4: Contradiction — No Solution
```

The method card shows **"Elimination Method (Inconsistent System)"**.

### 11.5 Underdetermined Systems (Free Variables)

When there are fewer equations than variables, some variables are marked as free:

```python
final_answer = "x = ...\ny is a free variable"
```

A "Parametric solution" step identifies the free variables.

### 11.6 Larger Systems

For systems with more than 2 equations or more than 2 variables, the solver uses SymPy's general `solve()` and shows a generic solution step. The method card shows **"Linear System Solver"** with approach "Row reduction → Back-substitution".

### 11.7 Single-Variable Systems

When all equations in a comma-separated system share a single variable (e.g. `3x = 6, 2x = 4`), the solver detects this and still uses the system path but with 1-variable-specific handling.

---

## 12. Graphing & Analysis ([`solver/graph.py`](solver/graph.py))

After the solver returns a result dict, the GUI builds a matplotlib figure and a structured analysis card.

### 12.1 Graph Builder — `build_figure()`

`build_figure()` inspects the result's `given.inputs` to determine the equation type and dispatches to the appropriate builder:

| Equation type | Builder function | What it plots |
|--------------|-----------------|---------------|
| Single-variable (`"variable"` key) | `_build_single_var()` | LHS and RHS as functions of x; intersection dot at solution |
| Two-variable (`"variables"` with 2 vars) | `_build_two_var()` | y solved in terms of x; line in xy-plane |
| System (`"equations"` key) | `_build_system()` | Two lines in xy-plane; intersection point, parallel lines, or overlapping lines |
| 3+ variables | `_build_multi_var_projection()` | Projects onto the first two variables |
| 1-variable system | `_build_single_var_system()` | LHS and RHS of each equation; solid vs dotted lines |

All figures use a consistent style via `_style_axes()`:
- Dark/light background matching the current theme
- Grid lines, axis labels, tick colours from the theme palette
- Colour-coded lines (blue for line 1, orange for line 2)
- Green dot at the solution point
- Legend with transparent background

**Anomaly handling:** Figures show special titles for no-solution ("Lines are parallel") and infinite-solution ("Lines overlap") cases.

### 12.2 Case Analysis — `analyze_result()`

`analyze_result()` returns a structured dict describing the mathematical case:

```python
{
    "eq_type":     "single_var" | "two_var" | "system",
    "case":        "one_solution" | "no_solution" | "infinite" | "degenerate_identity" | "degenerate_contradiction",
    "case_label":  "Normal Case — One Solution",
    "form":        "ax + b = 0",
    "description": "The coefficient of x is non-zero...",
    "detail":      "a ≠ 0  →  x = –b / a",
    "solution":    "x = 3/2",
    "graphable":   True,
}
```

The GUI renders this as a bordered card with:
- A colour-coded case badge (green for one solution, yellow for infinite, red for no solution)
- The algebraic form
- A multi-line description of the mathematical case
- The algebraic condition that leads to this case

### 12.3 Live Theme Switching

`restyle_figure()` re-colours an already-built figure in-place when the theme toggles. It builds a colour translation table from the old palette to the new one and applies it to every figure element (background, axes, spines, lines, scatter points, grid, text, legend).

---

## 13. Display Formatting ([`solver/engine.py`](solver/engine.py))

### 13.1 Expression Formatting — `_format_expr()`

Converts SymPy expressions into human-readable strings:
- `**N` → Unicode superscript (`x**2` → `x²`)
- `*` between coefficient and variable removed (`2*x` → `2x`)
- Remaining `*` replaced with `·`
- Simple fractions converted to stacked markers: `3/2` → `⟦3|2⟧`
- Parenthesised fractions: `(2x + 3)/5` → `⟦2x + 3|5⟧`

The GUI's `_render_fraction()` method parses `⟦num|den⟧` markers and renders them as vertically stacked fractions with a horizontal line.

### 13.2 Input Formatting — `_format_input_str()`

Like `_format_expr()` but operates on the **raw user input** rather than a SymPy expression. This preserves the exact term order and notation the user typed (e.g. `1/x + 1` stays `1/x + 1`, not SymPy's reordered form).

### 13.3 Spacing Normalisation — `_normalize_spacing()`

Ensures exactly one space around binary operators (`+`, `-`, `=`). Respects:
- Fraction markers (content inside `⟦…⟧` is never touched)
- Unary minus (no space before a leading `-`)
- Superscript characters (not treated as operators)

---

## 14. Dark / Light Theming ([`gui/app.py`](gui/app.py))

### 14.1 Palette System

Two palette dicts (`_DARK_PALETTE`, `_LIGHT_PALETTE`) define every colour used in the UI — background, text, accents, step cards, input bar, scrollbar, success/error colours, and verification backgrounds.

The graph module has its own palettes (`_DARK_GRAPH`, `_LIGHT_GRAPH`) for figure-specific colours.

Case-analysis badge colours are defined in `_DARK_CASE_COLORS` and `_LIGHT_CASE_COLORS`.

### 14.2 Theme Toggle

Clicking "☀ Light" / "🌙 Dark" in the header triggers `_toggle_theme()`:

1. Flips `self._theme` between `"dark"` and `"light"`
2. Calls `_refresh_header_logo()` to swap the PNG logo
3. Calls `_apply_theme()` which:
   - Updates all module-level colour globals
   - Re-styles every static widget (header, input bar, scrollbar, canvas)
   - Calls `_retheme_chat()` to translate colours on every widget already in the chat
   - Calls `_retheme_graphs()` to re-colour all embedded matplotlib figures via `restyle_figure()`

### 14.3 Logo Loading

The header logo is loaded from `assets/darkmode-logo.png` or `assets/lightmode-logo.png` via Pillow. If Pillow is unavailable or the image is missing, a text label ("DualSolver") is shown as a fallback.

---

## 15. Summary Flow Diagram

```
User Input: "2x + 5x + 3 = 1 + 5"
    ↓
GUI validates (not empty)
    ↓
Background thread: solve_linear_equation()
    ↓
Start timer (time.perf_counter)
    ↓
Validate characters (_validate_characters)
    ↓
Split on , or ; → detect system vs single equation
    ↓
_detect_variables() → ['x']   (single variable)
    ↓
Check for '='  ✓
    ↓
Split into ["2x + 5x + 3", "1 + 5"]
    ↓
_expand_implicit_vars() (no-op for single-letter vars)
    ↓
Parse with SymPy → (7*x + 3, 6)   ← auto-combines like terms
    ↓
Validate: degree == 1?  ✓
    ↓
Step 1: Show original equation as typed (_format_input_eq)
    ↓
Detect auto-simplification:
  _count_terms_in_str("2x + 5x + 3") = 3,  Add.make_args(7x + 3) = 2
  _count_terms_in_str("1 + 5") = 2,         Add.make_args(6) = 1
  → terms decreased → Step 2: "Combine like terms"
    ↓
Expand (if needed) — usually no-op after combining
    ↓
Generate remaining solving steps:
  ├─ Move variable terms left / constants right
  ├─ Simplify both sides
  ├─ Divide by coefficient
  └─ Simplify to get the answer
    ↓
Generate trail sections:
  ┌─ GIVEN:           problem + inputs
  ├─ METHOD:          Algebraic Isolation + parameters
  ├─ STEPS:           numbered solving steps (with combine/expand)
  ├─ FINAL ANSWER:    x = 3/7
  ├─ VERIFICATION:    substitution check (5 steps)
  └─ SUMMARY:         runtime, timestamp, SymPy version
    ↓
Return result dict
    ↓
GUI builds animation queue
    ↓
Animated rendering: GIVEN → METHOD → STEPS → FINAL ANSWER → VERIFICATION → GRAPH & ANALYSIS → SUMMARY
    ↓
build_figure() → matplotlib Figure (LHS/RHS intersection plot)
analyze_result() → case analysis card (one_solution badge)
    ↓
User sees complete Standard Trail Format with embedded graph
```

---

## Architecture Summary

This architecture separates concerns cleanly:
- **GUI** (`gui/app.py`) handles the Tkinter desktop interface, animated trail rendering, and live theme switching
- **Solver** (`solver/engine.py`) focuses on symbolic math, validation, step generation, and non-linearity education
- **Graph** (`solver/graph.py`) builds matplotlib figures for each equation type and provides structured case analysis

The system uses:
- **SymPy** for symbolic mathematics, parsing, and solving
- **Matplotlib** + **NumPy** for embedded equation graphs
- **Tkinter** for the desktop GUI with dark/light theming
- **Pillow** (optional) for PNG logo rendering
- **Standard Trail Format** for consistent, structured output on every computation
- **Animated queue pipeline** for sequential section-by-section rendering
