# How SymSolver Parses and Solves Linear Equations

I'll walk you through the entire process using **`2x + 2 = 5`** as an example.

Every computation follows the **Standard Trail Format**, which ensures the UI always displays these six sections: **GIVEN → METHOD → STEPS → FINAL ANSWER → VERIFICATION → SUMMARY**.

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
    raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")
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
def _parse_side(expr_str: str):
    s = expr_str.strip()
    s = s.replace('^', '**')  # Convert user-friendly ^ to Python **
    
    try:
        return parse_expr(s, 
                         local_dict={'x': x}, 
                         transformations=TRANSFORMATIONS)
    except Exception as e:
        raise ValueError(f"Could not parse expression: '{expr_str}'. Error: {e}")
```

**For `2x + 2`:**
- SymPy's `implicit_multiplication_application` transformation converts `2x` → `2*x`
- Result: `Add(Mul(2, x), 2)` (SymPy expression tree)

**For `5`:**
- Result: `Integer(5)`

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

**Step 1: Original equation**

```python
{
    "step_number": 1,
    "description": "Starting with the original equation",
    "expression": "2·x + 2 = 5",
    "explanation": "We are given the equation 2x + 2 = 5. Our goal is to isolate x..."
}
```

**Step 2: Expand (if needed)**

Since `2x + 2` and `5` have no parentheses to expand, this step is **skipped**.

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

## 7. GUI Rendering — Standard Trail Format

Back in [`gui/app.py`](gui/app.py), the `_show_result` method renders each trail section in order:

| # | Section | Icon | What the UI shows |
|---|---------|------|-------------------|
| 1 | **GIVEN** | 📋 | Problem statement, equation, left/right sides, variable |
| 2 | **METHOD** | ⚙ | Algorithm name, description, parameters (equation type, approach) |
| 3 | **STEPS** | 📝 | Numbered step cards — each with bold description, monospace expression, and collapsible explanation |
| 4 | **FINAL ANSWER** | ✓ | Green-bordered card with the solution (e.g. `x = 3/2`) |
| 5 | **VERIFICATION** | 🔍 | Collapsible section with numbered substitution-check steps |
| 6 | **SUMMARY** | 📊 | Runtime (ms), step counts, timestamp, SymPy version |

Each section has an accent-coloured header with a thin underline, rendered by `_render_section_header()`. Step cards are produced by `_render_step()` which shows the step number prefix, and explanations are toggled via "▸ Show Explanation" / "▾ Hide Explanation" buttons.

---

## 8. Error Handling & Fallbacks

### Missing `=` sign
```python
if '=' not in equation_str:
    raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")
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
```python
if poly_degree.degree() > 1:
    raise ValueError("This is a degree-{degree} equation, not linear. SymSolver currently supports linear equations only.")
```
**Example:** `x^2 + 2 = 5` → "This is a degree-2 equation, not linear"

### No variable found
```python
if poly_degree.degree() == 0:
    raise ValueError("No variable 'x' found in the equation.")
```
**Example:** `2 + 3 = 5` → "No variable 'x' found"

### Infinite solutions (identity)
```python
if val == 0:
    raise ValueError("This equation is always true (identity). Infinite solutions.")
```
**Example:** `2x + 3 = 2x + 3`

### No solution (contradiction)
```python
else:
    raise ValueError("This equation has no solution (contradiction).")
```
**Example:** `2x + 3 = 2x + 5`

---

## Summary Flow Diagram

```
User Input: "2x + 2 = 5"
    ↓
GUI validates (not empty)
    ↓
Background thread: solve_linear_equation()
    ↓
Start timer (time.perf_counter)
    ↓
Check for '='  ✓
    ↓
Split into ["2x + 2", "5"]
    ↓
Parse with SymPy → (2*x + 2, 5)
    ↓
Validate: degree == 1?  ✓
    ↓
Generate trail sections:
  ┌─ GIVEN:        problem + inputs
  ├─ METHOD:       Algebraic Isolation + parameters
  ├─ STEPS:        numbered solving steps
  ├─ FINAL ANSWER: x = 3/2
  ├─ VERIFICATION: substitution check (5 steps)
  └─ SUMMARY:      runtime, timestamp, SymPy version
    ↓
Return result dict
    ↓
GUI renders all 6 trail sections
    ↓
User sees complete Standard Trail Format
```

---

## Architecture Summary

This architecture separates concerns cleanly:
- **GUI** (`gui/app.py`) handles the Tkinter desktop interface and renders the Standard Trail Format
- **Solver** (`solver/engine.py`) focuses on symbolic math, validation, and producing the trail data

The system uses:
- **SymPy** for symbolic mathematics and parsing
- **Tkinter** for the desktop GUI
- **Standard Trail Format** for consistent, structured output on every computation
