# SymSolver

SymSolver is a desktop application that solves linear equations step-by-step. It supports single-variable equations, multi-variable equations, and systems of equations — all through a chat-style Tkinter interface with animated solution trails, interactive graphs, and dark/light theming.

## Features

- **Single-variable equations** — e.g. `2x + 3 = 7`, `x/2 + 1 = 4`
- **Multi-variable equations** — e.g. `2x + 4y = 1` (expresses each variable in terms of the others)
- **Systems of equations** — e.g. `x + y = 10, x - y = 2` (substitution / elimination method)
- **Step-by-step solutions** — Every solving step shows the description, expression, and a collapsible explanation
- **Animated trail rendering** — Results appear section-by-section with phase-by-phase animation
- **Verification** — Every solution is verified by substituting back into the original equation(s)
- **Interactive graphs** — Matplotlib plots embedded in the GUI showing LHS vs RHS intersections, lines in the xy-plane, or system intersection points
- **Graph analysis cards** — Structured case analysis (one solution / infinite / no solution / degenerate) with colour-coded badges
- **Non-linear detection** — Recognises quadratic, cubic, transcendental, denominator-variable, and product-of-variables equations and returns educational explanations instead of crashing
- **Dark / Light theme** — Toggle between themes at runtime; all widgets, graphs, and logos update live
- **Welcome screen** — Clickable example equations to get started instantly
- **New Chat button** — Clear the conversation and start fresh
- **Stop button** — Cancel a running solve or animation mid-stream
- **Unicode formatting** — Superscript exponents (`x²`), stacked fraction markers (`⟦num|den⟧`), and normalised spacing for clean display

## Symbolic Computation

SymSolver leverages **SymPy** for symbolic mathematics. Key capabilities include:

- **Symbolic solving** — Solves equations algebraically, preserving exact expressions (fractions, radicals)
- **Step-by-step breakdown** — Decomposes complex solutions into individual algebraic moves
- **Algebraic manipulation** — Adding/subtracting, multiplying/dividing, expanding, combining like terms — each shown as an explicit step
- **Auto-simplification detection** — When SymPy auto-combines like terms or expands parentheses during parsing, the solver detects the change and shows it as a visible "Combine like terms" or "Expand" step
- **Expression simplification** — Automatically reduces expressions to their simplest form
- **Linearity validation** — Checks polynomial degree, transcendental functions, denominator variables, and cross-products before solving

The solver produces a **Standard Trail Format** on every computation: **GIVEN → METHOD → STEPS → FINAL ANSWER → VERIFICATION → GRAPH & ANALYSIS → SUMMARY**.

## Prerequisites

- **Python 3.10+**
- **SymPy** ≥ 1.13
- **Matplotlib** ≥ 3.8
- **NumPy** ≥ 1.26
- **Pillow** (optional, for PNG logo rendering in the header)

## Project Structure

```
SymSolver/
├── main.py              # Entry point — launches the Tkinter app
├── requirements.txt     # Python dependencies (sympy, matplotlib, numpy)
├── README.md
├── process.md           # Detailed walkthrough of how the solver works
├── assets/
│   ├── darkmode-logo.png
│   └── lightmode-logo.png
├── solver/
│   ├── __init__.py      # Exports solve_linear_equation
│   ├── engine.py        # SymPy-powered solver with step generation (1 689 lines)
│   └── graph.py         # Matplotlib graph builder + case analysis (920 lines)
└── gui/
    ├── __init__.py      # Exports SymSolverApp
    └── app.py           # Tkinter desktop GUI — chat-style interface (1 338 lines)
```

## Installation & Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main.py
   ```

## Supported Equation Types

| Type | Example Input | Method |
|---|---|---|
| Single-variable | `2x + 3 = 7` | Algebraic Isolation |
| With fractions / exponents | `x/2 + 1 = 4`, `x^2` detected | Isolation or non-linear education |
| Multi-variable (1 equation) | `2x + 4y = 1` | Solve for each variable in terms of the others |
| System (2 equations) | `x + y = 10, x - y = 2` | Substitution method with back-substitution |
| Larger / underdetermined systems | `a + b + c = 6, a - c = 2` | Parametric solution with free variables |
| Degenerate (identity) | `2x + 3 = 2x + 3` | Detects 0 = 0 → infinite solutions |
| Degenerate (contradiction) | `2x + 3 = 2x + 5` | Detects 0 = 2 → no solution |
| Non-linear (polynomial) | `x^2 + 2 = 5` | Educational explanation of degree classification |
| Non-linear (transcendental) | `sin(x) = 1` | Educational explanation of transcendental functions |
| Non-linear (denominator) | `1/x + 1 = 3` | Educational explanation of negative exponents |
| Non-linear (product) | `x*y = 6` | Educational explanation of variable products |

## Technologies Used

- **Tkinter** — Python's built-in GUI toolkit (desktop interface with dark/light theming)
- **SymPy** — Symbolic mathematics library for parsing, solving, and validating equations
- **Matplotlib** — Embedded graphs for visualising equations and solutions
- **NumPy** — Numerical evaluation for graph data points
- **Pillow** — Optional; loads PNG logos in the header bar
