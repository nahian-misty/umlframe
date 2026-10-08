<p align="center">
  <!-- Replace assets/logo.svg with your logo (keep the filename, or update the path below) -->
  <img src="assets/logo.svg" alt="UMLFrame logo" width="360">
</p>

<h1 align="center">UMLFrame</h1>

<p align="center">
  A bidirectional <b>UML ↔ Code</b> engineering platform.<br>
  Draw a class or activity diagram and get scaffold code, or point it at source code and get the diagram back.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white">
  <img alt="Tests" src="https://img.shields.io/badge/tests-700%2B%20passing-brightgreen">
</p>

---

## Features

- **Visual editor** – infinite pan/zoom canvas with grid and snap, three-compartment class boxes, all five relationship types (plus realization), PNG export.
- **UML → Code** – generate scaffold code for **Python, Java and JavaScript**, one file per class.
- **Image → UML** – upload a diagram image (or the editor's own export) and rebuild it with OpenCV + OCR.
- **Code → UML** – reverse-engineer Python, Java or JavaScript into a class diagram, with inferred inheritance, composition, aggregation, association and dependency.
- **Activity diagrams, both ways** – activity image → structured `if`/`else`/`while` function, and source method → activity diagram (Mermaid or a re-importable PNG).
- **Mermaid preview** – render any diagram as a Mermaid `classDiagram` or `flowchart`.
- **Accounts & projects** – JWT auth, bcrypt passwords, per-user projects that save the canvas.
- **One contract** – every module speaks the validated *Unified UML JSON*, so each stage is independently testable.

## Screenshots

<table>
  <tr>
    <td><img src="assets/screenshots/class-editor.png" alt="Class diagram editor"><br><sub>Class diagram editor</sub></td>
    <td><img src="assets/screenshots/generated-code.png" alt="Generated code"><br><sub>Generated code</sub></td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/code-to-uml.png" alt="Code to UML"><br><sub>Code → UML</sub></td>
    <td><img src="assets/screenshots/activity-editor.png" alt="Activity diagram editor"><br><sub>Activity diagram editor</sub></td>
  </tr>
  <tr>
    <td><img src="assets/screenshots/code-to-activity.png" alt="Code to Activity"><br><sub>Code → Activity</sub></td>
    <td><img src="assets/screenshots/dashboard.png" alt="Dashboard"><br><sub>Project dashboard</sub></td>
  </tr>
</table>

## Getting started

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Node.js | 20+ | for the frontend |
| Tesseract OCR | any recent | required by the image pipelines (`sudo apt install tesseract-ocr`, `brew install tesseract`) |

### 1. Clone

```bash
git clone https://github.com/nahian-misty/umlframe.git
cd umlframe
```

### 2. Backend (http://localhost:8000)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env                 # defaults to a local SQLite file
uvicorn backend.main:app --reload --port 8000
```

Interactive API docs are served at <http://localhost:8000/docs>. Tables are created on startup.

### 3. Frontend (http://localhost:3000)

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>, register an account, create a project and start drawing.

### Configuration

Settings are read from `.env` at the repo root.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `mysql+pymysql://…` if unset; `.env.example` sets `sqlite:///./umlframe.db` | SQLAlchemy URL |
| `JWT_SECRET_KEY` | `dev-secret-change-me` | **Change this outside local development** |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |
| `VITE_API_BASE_URL` (frontend) | `http://localhost:8000` | Where the UI finds the API |

### Tests and checks

```bash
pytest                                # backend, from the repo root
ruff check backend/ && mypy backend/  # lint and types
cd frontend && npm run typecheck && npm run lint
```

## Architecture

Everything flows through a single intermediate representation, the **Unified UML JSON** (`UmlDocument`), with a sibling `ActivityDocument` for activity diagrams. Pipelines are one-directional and modules never call each other directly.

```mermaid
flowchart LR
    subgraph Forward
        A[Canvas / image] --> B[OpenCV + OCR] --> C[(Unified UML JSON)] --> D[Jinja2 templates] --> E[Python / Java / JS]
    end
    subgraph Reverse
        F[Source code] --> G[AST parsers] --> H[(Unified UML JSON /<br/>ActivityDocument)] --> I[Mermaid] --> J[Rendered diagram]
    end
```

Backend layers, each with one job:

```mermaid
flowchart TB
    R[routes<br/>URL patterns only] --> C[controllers<br/>HTTP in/out, error mapping] --> S[services<br/>pipeline orchestration]
    S --> M[domain modules<br/>cv · ocr · parser · generator · reverse · mermaid]
    S --> DB[(db<br/>users, projects)]
    M --> SC[schemas<br/>Unified UML JSON]
```

```
umlframe/
├── frontend/        React + TypeScript editor (canvas, activity canvas, dashboard)
├── backend/
│   ├── api/         routes, controllers, auth dependency
│   ├── services/    one service per pipeline use case
│   ├── schemas/     UmlDocument, ActivityDocument (Pydantic)
│   ├── cv/ ocr/ parser/        image → structured data
│   ├── generator/   language maps + Jinja2 templates
│   ├── reverse/     AST parsers (python, java, javascript)
│   ├── mermaid/     class + activity diagram text
│   └── db/          SQLAlchemy models and session
├── shared/schema/   canonical JSON Schema
├── tests/           mirrors backend/
└── wiki/            project wiki (see below)
```

## Wiki

Longer documentation lives in [`wiki/`](wiki/Home.md):

[Getting started](wiki/Getting-Started.md) · [Architecture](wiki/Architecture.md) · [Unified UML JSON](wiki/Unified-UML-JSON.md) · [API reference](wiki/API-Reference.md) · [Pipelines](wiki/Pipelines.md) · [UI guide](wiki/UI-Guide.md) · [Testing](wiki/Testing.md) · [Extending UMLFrame](wiki/Extending-UMLFrame.md) · [Limitations](wiki/Limitations.md)

## Notes

- Generated code is a **scaffold**: structure and signatures, never business logic. Activity-to-code reproduces the `if`/`while` shape only; every action and condition is a placeholder.
- Image pipelines are tuned for clean, programmatically rendered diagrams (including the editor's own export). See [Limitations](wiki/Limitations.md).

## Author

Sheikh Nahian (BSSE-1403), Institute of Information Technology, University of Dhaka. Supervised by Dr. Sumon Ahmed. Built as Software Project Lab III.
