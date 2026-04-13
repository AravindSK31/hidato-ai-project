# 🧩 Hidato AI Solver – Comparative Analysis of Search Algorithms

## 📌 Overview
This project implements and analyzes multiple Artificial Intelligence algorithms for solving **Hidato puzzles**, a number-placement puzzle where consecutive numbers must be adjacent.

The goal of this project is to **compare the performance of different search strategies** across puzzles of varying difficulty and structure.

---

## 🤖 Algorithms Implemented
- Depth-First Search (**DFS**)
- DFS with Heuristic Guidance (**DFS + Heuristic**)
- Constraint Satisfaction Problem (**CSP with Constraint Propagation**)
- A* Search (**A\***)
- Genetic Algorithm (**GA**)

---

## 🎯 Key Features
- Interactive puzzle board (React + TypeScript frontend)
- Puzzle generator (Easy / Medium / Hard)
- Solver execution with metrics tracking
- Analysis dashboard for comparing algorithms
- Adversarial puzzle generation (hardest-case scenarios)

---

## 📊 Evaluation Metrics
Each algorithm is evaluated using:
- ✅ Solve Success (within time limit)
- ⏱ Runtime (seconds)
- 🔍 Nodes Expanded
- 🔁 Backtracks

---

## 🧠 Project Motivation
Hidato presents a challenging combinatorial search problem with spatial constraints. This project explores:
- How different AI search strategies perform
- The effect of puzzle structure (size, clue density, clustering)
- Trade-offs between completeness, efficiency, and scalability

---

## 🏗️ Project Structure
project/
│
├── backend/ # Python backend (FastAPI)
│ ├── main.py
│ ├── dfs_solver.py
│ ├── dfs_heuristic_solver.py
│ ├── astar_solver.py
│ ├── csp_solver.py
│ ├── ga_solver.py
│ ├── benchmark_runner.py
│ ├── adversarial_analysis.py
│ ├── solvers_registry.py
│
├── src/ # React frontend
│ ├── Hidato.tsx
│ ├── AnalysisPage.tsx
│ ├── App.tsx
│
├── package.json
├── README.md

---

## ⚙️ Setup & Run Instructions

### 1️⃣ Backend Setup (Python)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
uvicorn main:app --reload

Backend runs at : http://127.0.0.1:8000
Frontend Setup (React):
front end runs at: http://localhost:5173

 Adversarial Analysis

The system includes an adversarial benchmark that:

Generates difficult puzzle configurations
Evaluates all algorithms under a time constraint
Identifies the hardest puzzle instances
⚠️ Notes
A 15-second timeout is used for solver evaluation
CSP performs best overall in most cases
A* struggles due to heuristic limitations
Genetic Algorithm does not scale well for large puzzles

📚 Technologies Used
Python (FastAPI)
React + TypeScript
Vite
Recharts (for visualization)


GitHub: https://github.com/AravindSK31/hidato-ai-project

 Authors
Aravind Shyam Kattepur
Shantesh Vinayka