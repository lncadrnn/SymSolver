# How SymSolver Parses and Solves Linear Equations

I'll walk you through the entire process using **`2x + 2 = 5`** as an example.

---

## 1. User Input → Frontend

**User types:** `2x + 2 = 5`

**What happens:**
- [`InputBar.jsx`](frontend/src/components/InputBar.jsx) captures the input
- When user clicks send or presses Enter, the input is trimmed and passed to [`App.jsx`](frontend/src/App.jsx)
- [`App.jsx`](frontend/src/App.jsx) creates a user message and adds a placeholder bot message with `loading: true`

---

## 2. Frontend → Backend API Call

**Request:**
```javascript
fetch('/api/solve', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ equation: "2x + 2 = 5" })
})
```

The request goes to the **FastAPI backend** at [`backend/app/main.py`](backend/app/main.py).

---

## 3. Backend Receives Request

In [`main.py`](backend/app/main.py):

```python
@app.post("/api/solve", response_model=SolveResponse)
def solve(req: EquationRequest):
    equation = req.equation.strip()  # "2x + 2 = 5"
    
    # Initial validation
    if not equation:
        raise HTTPException(status_code=400, detail="Equation cannot be empty.")
    
    try:
        result = solve_linear_equation(equation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")
```

---

## 4. Parsing Phase ([`solver.py`](backend/app/solver.py))

### Step 4.1: Check for `=` sign

```python
if '=' not in equation_str:
    raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")
```

✅ **Pass:** `2x + 2 = 5` contains `=`

### Step 4.2: Split into left and right sides

```python
parts = equation_str.split('=')  # ["2x + 2", "5"]

if len(parts) != 2:
    raise ValueError("Equation must contain exactly one '=' sign.")

lhs_str = "2x + 2"
rhs_str = "5"
```

✅ **Pass:** Exactly one `=` sign

### Step 4.3: Parse each side using SymPy

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

## 5. Validation Phase

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

## 6. Step-by-Step Solving

Now the solver generates human-readable steps:

### **Step 0: Original equation**

```python
steps.append({
    "description": "Starting with the original equation",
    "expression": "2·x + 2 = 5",
    "explanation": "We are given the equation 2x + 2 = 5. Our goal is to isolate x..."
})
```

### **Step 1: Expand (if needed)**

Since `2x + 2` and `5` have no parentheses to expand, this step is **skipped**.

### **Step 2: Move constants to the right**

```python
lhs_const_now = 2  # Constant term on left side

# Subtract 2 from both sides
steps.append({
    "description": "Subtract 2 from both sides",
    "expression": "2·x + 2 - 2 = 5 - 2",
    "explanation": "The left side still has the constant 2. To isolate the x-term, we subtract 2 from both sides..."
})

new_lhs = 2*x  # 2x + 2 - 2 = 2x
new_rhs = 3    # 5 - 2 = 3

steps.append({
    "description": "Simplify both sides",
    "expression": "2·x = 3",
    "explanation": "Combining like terms: the left side becomes 2·x and the right side becomes 3."
})
```

### **Step 3: Divide by coefficient**

```python
coeff = 2  # Coefficient of x

steps.append({
    "description": "Divide both sides by 2",
    "expression": "2·x / 2 = 3 / 2",
    "explanation": "The coefficient of x is 2. To get x alone, we divide both sides by 2..."
})

solution = 3/2  # Rational(3, 2) in SymPy

steps.append({
    "description": "Simplify to get the answer",
    "expression": "x = 3/2",
    "explanation": "Performing the division: 3 ÷ 2 = 3/2. So x equals 3/2."
})
```

---

## 7. Verification Steps

The solver also generates verification steps to prove the answer:

```python
verification_steps = [
    {
        "description": "Start with the original equation",
        "expression": "2·x + 2 = 5",
        "explanation": "We will substitute x = 3/2 back into the original equation..."
    },
    {
        "description": "Substitute x = 3/2 into both sides",
        "expression": "2·(3/2) + 2 = 5",
        "explanation": "We replace every x with 3/2..."
    },
    {
        "description": "Evaluate the left-hand side",
        "expression": "LHS = 2·(3/2) + 2 = 5",
        "explanation": "Computing: 2 × 3/2 = 3, then 3 + 2 = 5"
    },
    {
        "description": "Evaluate the right-hand side",
        "expression": "RHS = 5",
        "explanation": "The right side is already simplified to 5"
    },
    {
        "description": "Compare both sides",
        "expression": "LHS = 5, RHS = 5\nLHS = RHS  ✓",
        "explanation": "Both sides equal 5, confirming that x = 3/2 is the correct solution!"
    }
]
```

---

## 8. Response Sent to Frontend

The backend returns:

```json
{
  "equation": "2x + 2 = 5",
  "steps": [ /* 4-5 step objects */ ],
  "final_answer": "x = 3/2",
  "verification_steps": [ /* 5 verification step objects */ ]
}
```

---

## 9. Frontend Rendering

In [`ChatMessage.jsx`](frontend/src/components/ChatMessage.jsx):

1. **Typewriter animation** displays each step's `description` character-by-character
2. After description completes, the `expression` animates
3. User can click "Show Explanation" to reveal the detailed `explanation`
4. After all steps, the **Final Answer** card appears
5. User can expand **Verification** section to see the proof

---

## Error Handling & Fallbacks

### Missing `=` sign
```python
if '=' not in equation_str:
    raise ValueError("Equation must contain '='. Example: 2x + 3 = 7")
```
**Frontend shows:** Red error message

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
Frontend validates (not empty)
    ↓
POST /api/solve
    ↓
Backend: Check for '='  ✓
    ↓
Split into ["2x + 2", "5"]
    ↓
Parse with SymPy → (2*x + 2, 5)
    ↓
Validate: degree == 1?  ✓
    ↓
Generate steps:
  1. Original: 2x + 2 = 5
  2. Subtract 2: 2x = 3
  3. Divide by 2: x = 3/2
  4. Verification steps
    ↓
Return JSON response
    ↓
Frontend renders with typewriter animation
    ↓
User sees step-by-step solution
```

---

## Architecture Summary

This architecture separates concerns cleanly:
- **Frontend** handles UI/UX and animations
- **Backend** focuses on symbolic math and validation
- All error cases are caught and displayed gracefully to the user

The system uses:
- **SymPy** for symbolic mathematics and parsing
- **FastAPI** for the REST API
- **React** with typewriter animations for an engaging user experience
