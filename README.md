# DualSolver

DualSolver is a web application that helps you solve linear equations step-by-step. It provides a clean, interactive interface to input mathematical equations and receive detailed solutions with explanations for each step.

## Features

- **Interactive equation solver** - Enter any linear equation and get detailed step-by-step solutions
- **Visual explanations** - Each solving step includes a description and explanation
- **Clean UI** - Modern, user-friendly interface built with React and Vite
- **Real-time processing** - Fast equation solving powered by FastAPI and SymPy

## Symbolic Computation

DualSolver leverages **SymPy**, a powerful Python library for symbolic mathematics, to provide accurate and detailed equation solving. Key capabilities include:

- **Symbolic solving** - Solves equations algebraically rather than numerically, preserving exact mathematical expressions
- **Step-by-step breakdown** - Decomposes complex solutions into understandable, isolated steps
- **Algebraic manipulation** - Performs correct algebraic transformations (adding/subtracting, multiplying/dividing) while maintaining equation balance
- **Expression simplification** - Automatically simplifies expressions to their most reduced form
- **Multi-variable support** - Handles equations with variables and constants symbolically

The backend intercepts and logs each intermediate step of the solution process, allowing DualSolver to display not just the final answer, but the complete mathematical reasoning behind it.

## Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 16+** (for frontend)
- **npm** (comes with Node.js)

## Installation & Setup

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   The backend will be available at: `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install npm dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at: `http://localhost:5173`

## Running Both Servers

To run both the frontend and backend simultaneously:

**Terminal 1 - Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open your browser and navigate to: `http://localhost:5173`

## Technologies Used

### Frontend
- **React** - UI library
- **Vite** - Build tool and dev server
- **CSS** - Styling

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI web server
- **SymPy** - Symbolic mathematics library for equation solving
- **Pydantic** - Data validation

## Development

The application uses hot-reload on both frontend and backend:
- Frontend changes auto-reload in the browser via Vite
- Backend changes auto-reload via Uvicorn's `--reload` flag
