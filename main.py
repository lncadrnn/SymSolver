"""
SymSolver — Entry point.

Launch the Tkinter desktop application.
"""

from gui import SymSolverApp


def main() -> None:
    app = SymSolverApp()
    app.mainloop()


if __name__ == "__main__":
    main()
