# SymSolver

SymSolver is a step-by-step linear equation solver that uses SymPy for symbolic computation. It helps students understand how equations are solved by displaying each algebraic step, from initial equation to final answer, through a chat-style Tkinter interface with animated solution trails, interactive graphs, and dark/light theming.

## Features

- **Step-by-step solving** — Breaks down each equation into individual algebraic steps using SymPy
- **Solution verification** — Substitutes the answer back into the original equation to confirm correctness
- **Interactive graphs** — Embedded Matplotlib plots showing intersections and solution points
- **Non-linear detection** — Identifies unsupported equation types and provides educational explanations
- **Solution history** — Local log of all solved equations with timestamps, clearable from the sidebar
- **Animation controls** — Adjustable speed (slow, normal, fast, instant) for step reveals
- **Dark / light theme** — Live theme toggle across all widgets, graphs, and logos
- **Symbol pad** — On-screen math keyboard for inserting special characters
- **Export** — Copy or export solutions externally
- **Clear input** — Trash icon to quickly clear the input field
- **Welcome screen** — Clickable example equations to get started instantly
- **New Chat / Stop** — Reset the conversation or cancel a running solve mid-stream

## Symbolic Computation

SymSolver leverages **SymPy** for symbolic algebra — solving equations exactly (fractions, radicals), generating step-by-step breakdowns, detecting auto-simplifications, and validating linearity before solving.

The solver produces a **Standard Trail Format**: **GIVEN → METHOD → STEPS → FINAL ANSWER → VERIFICATION → GRAPH & ANALYSIS → SUMMARY**.

## Prerequisites

- **Python 3.10+**
- **SymPy** ≥ 1.13
- **Matplotlib** ≥ 3.8
- **NumPy** ≥ 1.26
- **Pillow** (optional, for PNG logo rendering in the header)

## Project Structure

```
SymSolver/
├── main.py                  # Entry point — launches the Tkinter app
├── requirements.txt         # Python dependencies (sympy, matplotlib, numpy, pillow)
├── README.md
├── process.md               # Detailed walkthrough of how the solver works
│
├── assets/
│   ├── darkmode-logo.png    # Logo for dark theme
│   └── lightmode-logo.png   # Logo for light theme
│
├── data/
│   └── symsolver.json       # Local storage (history, settings, preferences)
│
├── tests/
│   ├── conftest.py          # Test config (matplotlib Agg backend)
│   ├── VALIDATION_RULES.md  # Validation checklist + invalid input documentation
│   ├── test_engine_unit.py
│   ├── test_graph_unit.py
│   ├── test_storage_unit.py
│   ├── test_themes_unit.py
│   └── test_app_and_main_unit.py
│
├── solver/
│   ├── __init__.py          # Exports solve_linear_equation
│   ├── engine.py            # SymPy-powered solver with step generation (1 520 lines)
│   └── graph.py             # Matplotlib graph builder + case analysis (820 lines)
│
└── gui/
    ├── __init__.py          # Exports SymSolverApp
    ├── app.py               # Main Tkinter window — chat-style interface (569 lines)
    ├── animation.py         # Step-by-step animation engine (464 lines)
    ├── widgets.py           # Reusable UI widget builders (200 lines)
    ├── sidebar.py           # Slide-in sidebar — history, settings (602 lines)
    ├── settings.py          # Full-page settings panel (215 lines)
    ├── storage.py           # Local JSON storage — history & preferences (125 lines)
    ├── export.py            # Solution export / copy functionality (291 lines)
    ├── symbolpad.py         # On-screen math symbol keyboard (93 lines)
    └── themes.py            # Dark / light colour palettes (96 lines)
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

| Type                             | Example Input                 | Method                                              |
| -------------------------------- | ----------------------------- | --------------------------------------------------- |
| Single-variable                  | `2x + 3 = 7`                  | Algebraic Isolation                                 |
| With fractions / exponents       | `x/2 + 1 = 4`, `x^2` detected | Isolation or non-linear education                   |
| Multi-variable (1 equation)      | `2x + 4y = 1`                 | Solve for each variable in terms of the others      |
| System (2 equations)             | `x + y = 10, x - y = 2`       | Substitution method with back-substitution          |
| Larger / underdetermined systems | `a + b + c = 6, a - c = 2`    | Parametric solution with free variables             |
| Degenerate (identity)            | `2x + 3 = 2x + 3`             | Detects 0 = 0 → infinite solutions                  |
| Degenerate (contradiction)       | `2x + 3 = 2x + 5`             | Detects 0 = 2 → no solution                         |
| Non-linear (polynomial)          | `x^2 + 2 = 5`                 | Educational explanation of degree classification    |
| Non-linear (transcendental)      | `sin(x) = 1`                  | Educational explanation of transcendental functions |
| Non-linear (denominator)         | `1/x + 1 = 3`                 | Educational explanation of negative exponents       |
| Non-linear (product)             | `x*y = 6`                     | Educational explanation of variable products        |

## Technologies Used

- **Tkinter** — Python's built-in GUI toolkit (desktop interface with dark/light theming)
- **SymPy** — Symbolic mathematics library for parsing, solving, and validating equations
- **Matplotlib** — Embedded graphs for visualising equations and solutions
- **NumPy** — Numerical evaluation for graph data points
- **Pillow** — Optional; loads PNG logos in the header bar
