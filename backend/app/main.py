from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.solver import solve_linear_equation

app = FastAPI(title="SymSolver API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EquationRequest(BaseModel):
    equation: str


class StepInfo(BaseModel):
    description: str
    expression: str
    explanation: str


class SolveResponse(BaseModel):
    equation: str
    steps: list[StepInfo]
    final_answer: str
    verification_steps: list[StepInfo]


@app.post("/api/solve", response_model=SolveResponse)
def solve(req: EquationRequest):
    equation = req.equation.strip()
    if not equation:
        raise HTTPException(status_code=400, detail="Equation cannot be empty.")

    try:
        result = solve_linear_equation(equation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")

    return result
