# SymSolver — Project Overview & Roadmap

---

## Current Scope (SymPy Solver)

### What it can solve
- **Linear equations in one variable (`x`)** — degree 1 only
- Examples: `2x + 3 = 7`, `5x - 2 = 3x + 8`, `3(x + 4) = 2x - 1`, `x/2 + 1 = 4`

### Supported math operations
- Basic arithmetic: `+`, `-`, `*`, `/`
- Parentheses / grouping: `3(x + 4)`
- Implicit multiplication: `2x` treated as `2 * x`
- Exponentiation: `^` (converted to `**` internally)
- Fractions / rational coefficients: `x/2 + 1 = 4`

### Solving features
- Step-by-step breakdown (expand → collect variable terms → move constants → divide by coefficient)
- Human-readable explanations per step (toggleable "Show Explanation" panel)
- Verification section: substitutes the answer back into the original equation to prove correctness
- Error handling: missing `=`, more than one `=`, non-linear equations, no solution, infinite solutions, unparseable input

### Frontend features
- Chat-based UI (user sends equation, bot responds with solution)
- Typewriter animation for step descriptions and expressions
- Welcome screen with example equations
- Loading spinner while solving
- Responsive layout (mobile-friendly)
- Dark theme with accent colors

### Tech stack
- **Solver:** SymPy (Python)
- **GUI:** Tkinter (Python)

---

## Current Bugs & Issues

*(None known — fresh Tkinter rewrite)*

---

## Future Features

### High Priority
- [ ] **Graph generation after solving** — plot the equation (LHS and RHS as separate lines) on a coordinate plane, highlight the intersection point at the solution. Libraries: Plotly, Chart.js, Desmos API, or JSXGraph.
- [ ] **Math keyboard / symbol pad** — on-screen buttons for `sin`, `cos`, `tan`, `√`, `π`, `^`, `log`, `|x|`, `(`, `)`, fractions, etc. Especially useful on mobile where these symbols are hard to type.
- [ ] **Quadratic equation support** — extend the solver to handle degree-2 equations with factoring, completing the square, and the quadratic formula as step options.

### Medium Priority
- [ ] **LaTeX / KaTeX rendering** — render equations in proper math notation instead of plain text (e.g., display fractions as $\frac{a}{b}$ instead of `a/b`).
- [ ] **Multiple variables** — support equations with `y`, `z`, etc., and eventually systems of equations (2×2, 3×3).
- [ ] **Equation history / session memory** — save past equations in a sidebar or local storage so users can revisit previous solutions.
- [ ] **Copy solution to clipboard** — one-click copy for the final answer or the full step-by-step breakdown.
- [ ] **Light / dark theme toggle** — currently dark-only; add a light theme and system-preference detection.
- [ ] **Export solution** — download the step-by-step solution as PDF, PNG, or Markdown.

### Nice to Have
- [ ] **Polynomial equations (degree 3+)** — cubic, quartic with appropriate methods.
- [ ] **Trigonometric equations** — solve equations involving `sin(x)`, `cos(x)`, `tan(x)` with periodic solutions.
- [ ] **Logarithmic & exponential equations** — `log(x) + 2 = 5`, `2^x = 16`, etc.
- [ ] **Inequality solver** — solve and graph `2x + 3 > 7` with number-line visualization.
- [ ] **Matrix operations** — determinants, inverses, eigenvalues with step-by-step.
- [ ] **Word problem parser** — natural language input like "twice a number plus three equals seven" converted to `2x + 3 = 7`.
- [ ] **Step-by-step animation speed control** — slider to adjust typewriter speed or skip animation entirely.
- [ ] **Multilingual support** — explanations in different languages.
- [ ] **Accessibility improvements** — ARIA labels, keyboard navigation, screen reader support for equations.
- [ ] **PWA / offline mode** — install as a desktop/mobile app, cache the solver for offline use.
- [ ] **Share solution via link** — generate a shareable URL encoding the equation and solution.
- [ ] **Unit conversion helper** — side feature for converting between units in physics/chemistry problems.
