# SymSolver

SymSolver is a desktop application that helps you solve linear equations step-by-step. It provides a clean, chat-style Tkinter interface to input mathematical equations and receive detailed solutions with explanations for each step.

## Features

- **Interactive equation solver** — Enter any linear equation and get detailed step-by-step solutions
- **Visual explanations** — Each solving step includes a description and collapsible explanation
- **Verification** — Every solution is verified by substituting back into the original equation
- **Dark-themed GUI** — Modern, user-friendly interface built with Tkinter
- **Example equations** — Welcome screen with clickable example equations

## Symbolic Computation

SymSolver leverages **SymPy**, a powerful Python library for symbolic mathematics, to provide accurate and detailed equation solving. Key capabilities include:

- **Symbolic solving** — Solves equations algebraically rather than numerically, preserving exact mathematical expressions
- **Step-by-step breakdown** — Decomposes complex solutions into understandable, isolated steps
- **Algebraic manipulation** — Performs correct algebraic transformations (adding/subtracting, multiplying/dividing) while maintaining equation balance
- **Expression simplification** — Automatically simplifies expressions to their most reduced form

The solver intercepts and logs each intermediate step of the solution process, allowing SymSolver to display not just the final answer, but the complete mathematical reasoning behind it.

## Prerequisites

- **Python 3.10+**
- **SymPy** (`pip install sympy`)

## Project Structure

```
SymSolver/
├── main.py              # Entry point — run this to start the app
├── requirements.txt     # Python dependencies
├── README.md
├── process.md           # Detailed walkthrough of how the solver works
├── todo.md              # Project roadmap and known issues
├── solver/
│   ├── __init__.py
│   └── engine.py        # SymPy-powered equation solver with step generation
└── gui/
    ├── __init__.py
    └── app.py           # Tkinter desktop GUI (chat-style interface)
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

## Technologies Used

- **Tkinter** — Python's built-in GUI toolkit (desktop interface)
- **SymPy** — Symbolic mathematics library for equation solving
