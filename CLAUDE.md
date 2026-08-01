# UMLFrame — Claude Code Reference

## Project Overview

UMLFrame is a bidirectional UML ↔ Code Engineering platform. Users draw UML Class Diagrams visually, and the system either generates source code from those diagrams or reverse-engineers existing source code back into diagrams.

Two complete pipelines share a single intermediate representation — the Unified UML JSON:

**Forward Pipeline:** UML Canvas → Export Image → Computer Vision + OCR → Unified UML JSON → Source Code

**Reverse Pipeline:** Source Code → AST Parser → Unified UML JSON → Mermaid Generator → Rendered UML Diagram

The reverse pipeline targets two distinct diagram outputs from the same AST pass: reconstructing the **class structure** of the parsed code (the existing Unified UML JSON → Mermaid `classDiagram` path above), and — planned, not yet implemented — extracting the **control flow of each parsed function/method** and rendering it as an **Activity Diagram** (Mermaid `flowchart`/activity syntax). Both share the same "source → AST → structured representation → Mermaid" shape; the class-diagram path is scoped under Milestone 5/6 below, and the activity-diagram path is scoped as an extension of that same milestone (see Milestone 6 and the Roadmap).

The forward pipeline is likewise planned to grow a second, parallel track — planned, not yet implemented — that mirrors the class-diagram forward pipeline but for **activity diagrams**: a user uploads an image of a hand-drawn/exported activity diagram (start/end nodes, action boxes, decision diamonds, fork/join bars), and the system reconstructs real control-flow structure (`if`/`else`, `while`) as a standalone generated function, with action bodies left as placeholders (never fabricated logic), consistent with principle 7 below. This uses its own sibling schema (`ActivityDocument`, alongside `UmlDocument`) rather than extending the Unified UML JSON — see Milestone 9.

Together with the reverse-pipeline activity-diagram extraction described above (code → control flow → Mermaid activity diagram, Milestone 6), this makes the Activity Diagram itself **bidirectional** — activity image → code (Milestone 9) and code → activity diagram (Milestone 6) — the same bidirectionality the Class Diagram already has (image ↔ code), just for the second diagram type. The two directions share nothing but the concept: Milestone 9 does not consume Milestone 6's control-flow representation or vice versa, per the one-directional-pipelines principle (Design Principle 2).

The Unified UML JSON is the canonical representation for every subsystem. No subsystem communicates with another directly. Everything either produces or consumes this schema.

UMLFrame is a multi-user platform. Users register and log in before using the editor. Each user owns many **projects**; a project is a named workspace holding one diagram (its canvas state serialized as a Unified UML JSON document). The user's dashboard lists their projects; opening a project loads its diagram into the editor canvas. All pipeline operations run in the context of the authenticated user's project.

---

## Current Implementation Status

This section reflects what actually exists in the repo today, as distinct from the target architecture and roadmap described below. Update it whenever a milestone's deliverables land.

| Milestone | Status | Notes |
|---|---|---|
| M1 — Frontend UML Editor | Mostly done | Canvas (pan/zoom/grid/snap), shape library, `UmlClassBox` with three compartments, relationship tools, selection, PNG export, and JSON serialization all exist under `frontend/src/`. There is a single `EditorPage`; no routing between multiple pages yet. |
| M2 — Image Processing Pipeline | Done | `backend/cv/preprocessor.py`, `backend/cv/shape_detector.py`, `backend/ocr/extractor.py` implemented and wired via `image_service`. |
| M3 — Unified UML JSON Layer | Done | `backend/schemas/uml.py` defines `UmlDocument`, `UmlClass`, `Attribute`, `Method`, `Relationship`, etc. Cross-field validation (e.g. relationship endpoints must reference known class ids) is implemented as a `model_validator` directly on `UmlDocument` — there is no separate `backend/schemas/validators.py` file. `shared/schema/uml_schema.json` exists. |
| M4 — Code Generation | Done | `backend/generator/` has `language_maps/` and `templates/` for Python, Java, and JavaScript, plus `registry.py`. `/api/generate-code`, `/api/languages`, `/api/templates` are implemented in `backend/api/routes/codegen.py`. |
| M5 — Reverse Engineering | Not started | `backend/reverse/python/`, `backend/reverse/java/`, `backend/reverse/javascript/` exist as empty directories. No `registry.py`, no parser modules, no `/api/reverse` route or controller. `ReverseRequest`/`ReverseResponse` models exist in `backend/models/` but are unused. |
| M6 — Diagram Generation | Not started | `backend/mermaid/` exists as an empty directory — no generator module, no service, no `/api/json-to-mermaid` route. `JsonToMermaidRequest`/`MermaidResponse` models exist but are unused. Scope now also includes generating an Activity Diagram from each parsed function/method's control flow (see Roadmap); no schema, extraction logic, or generator exists for this yet either. |
| M7 — Full Integration | Partial | `scripts/e2e_demo.py` demonstrates the forward pipeline end-to-end (image → JSON → code). No reverse-pipeline integration test yet since M5/M6 aren't built. |
| M8 — Authentication & Projects | Done | `backend/db/models.py` defines `User`/`Project` (SQLite via SQLAlchemy, `backend/db/session.py`); `backend/services/auth_service.py` (bcrypt + PyJWT) and `project_service.py` (ownership-scoped CRUD) implemented; `backend/api/dependencies/auth.py` provides the `get_current_user` bearer-token guard; `/api/auth/*` and `/api/projects/*` routes+controllers registered in `main.py`. Frontend has real `react-router-dom` routing (`/`, `/login`, `/register`, `/dashboard`, `/editor/:projectId`), an `AuthContext` with persisted JWT sessions, a `ProtectedRoute` guard, a real project-CRUD `DashboardPage`, and `EditorPage` load/save wired to a project's diagram. New marketing `HomePage` added at `/`. |
| M9 — Activity Diagram Forward Pipeline | Not started | Planned extension of the forward pipeline: activity-diagram image → CV/OCR → new `ActivityDocument` schema → control-flow structuring → codegen producing real `if`/`while` structure. No schema, CV detector, structuring algorithm, codegen, or endpoints exist yet. See Milestone 9 in the Roadmap for the full design. |

Four route/controller pairs are currently registered in `backend/main.py`: `auth`, `projects`, `codegen`, and `image`. `reverse` and `mermaid` (and their `backend/db/`-adjacent M9 siblings) are still target-state, not yet-implemented code — build them out per the Roadmap, don't assume they already exist.

---

## Architecture

```
umlframe/
├── frontend/                  # React application
│   ├── components/
│   │   ├── canvas/            # Infinite pan/zoom canvas, grid, snapping
│   │   ├── toolbar/           # Drawing tools, relationship selectors
│   │   └── uml/               # UML class box components
│   ├── hooks/                 # Shared React hooks
│   └── pages/                 # Top-level route pages (login, register, dashboard, editor)
│
├── backend/                   # Python application
│   ├── api/
│   │   ├── routes/            # FastAPI APIRouter definitions — URL patterns only
│   │   │   ├── auth.py        # /api/auth/register, /api/auth/login, /api/auth/logout, /api/auth/me
│   │   │   ├── projects.py    # /api/projects CRUD
│   │   │   ├── image.py       # /api/image-to-json
│   │   │   ├── codegen.py     # /api/generate-code, /api/languages, /api/templates
│   │   │   ├── reverse.py     # /api/reverse
│   │   │   ├── mermaid.py     # /api/json-to-mermaid
│   │   │   ├── activity_image.py    # Planned (M9): /api/activity-image-to-json
│   │   │   └── activity_codegen.py  # Planned (M9): /api/generate-activity-code
│   │   ├── controllers/       # Request/response handling; calls services; no domain logic
│   │   │   ├── auth_controller.py
│   │   │   ├── project_controller.py
│   │   │   ├── image_controller.py
│   │   │   ├── codegen_controller.py
│   │   │   ├── reverse_controller.py
│   │   │   ├── mermaid_controller.py
│   │   │   ├── activity_image_controller.py    # Planned (M9)
│   │   │   └── activity_codegen_controller.py  # Planned (M9)
│   │   └── dependencies/      # FastAPI dependency injection (auth guard, shared across routes)
│   ├── models/                # Pydantic models for the HTTP boundary (requests + responses)
│   │   ├── requests.py        # ImageUploadRequest, GenerateCodeRequest, ReverseRequest, etc. (planned M9: + GenerateActivityCodeRequest)
│   │   └── responses.py       # CodeGenerationResponse, MermaidResponse, etc. (planned M9: + ActivityReverseResponse; CodeGenerationResponse is reused as-is)
│   ├── schemas/               # Unified UML JSON — Pydantic data models + validation rules
│   │   ├── uml.py             # UmlDocument, UmlClass, Attribute, Method, Relationship
│   │   ├── validators.py      # Cross-field validation and business-rule constraints
│   │   └── activity.py        # Planned (M9): ActivityDocument, ActivityNode, ActivityEdge — sibling schema, not an extension of UmlDocument
│   ├── services/              # Business logic orchestration; owns pipeline sequencing
│   │   ├── auth_service.py    # Registration, login, password hashing, token issuing
│   │   ├── project_service.py # Project CRUD scoped to the authenticated user
│   │   ├── image_service.py   # Sequences cv/ → ocr/ → parser/ → schemas/
│   │   ├── codegen_service.py # Sequences schemas/ → generator/
│   │   ├── reverse_service.py # Sequences reverse/ → schemas/
│   │   ├── mermaid_service.py # Sequences schemas/ → mermaid/
│   │   ├── activity_image_service.py    # Planned (M9): sequences cv/ → ocr/ → parser/ → schemas/activity.py, resolves edge direction via DFS-from-START
│   │   ├── activity_structuring.py      # Planned (M9): reconstructs if/else + while structure from the ActivityDocument graph
│   │   └── activity_codegen_service.py  # Planned (M9): sequences the structured IR → generator/templates/*/activity.j2
│   ├── db/                    # Persistence layer (SQLAlchemy)
│   │   ├── models.py          # ORM models: User, Project
│   │   └── session.py         # Engine/session setup and dependency provider
│   ├── cv/                    # OpenCV image preprocessing + shape detection
│   │   ├── preprocessor.py
│   │   ├── shape_detector.py
│   │   └── activity_shape_detector.py   # Planned (M9): detects start/end/action/decision/fork-join shapes; reuses preprocessor.py as-is
│   ├── ocr/                   # OCR execution scoped to detected bounding boxes
│   │   ├── extractor.py
│   │   └── activity_extractor.py        # Planned (M9): reuses extractor.py's crop/pad/upscale/Otsu pattern for action/guard labels
│   ├── parser/                # OCR-text-to-structured-data parser
│   │   ├── text_parser.py
│   │   └── activity_text_parser.py      # Planned (M9): label/guard normalization, mirrors text_parser.py's OCR-fix idiom
│   ├── generator/             # Code generation engine
│   │   ├── language_maps/     # Language-neutral → language-specific type mappings
│   │   │   ├── python.py
│   │   │   ├── java.py
│   │   │   └── javascript.py
│   │   ├── registry.py        # Maps language name → (language_map, template_dir)
│   │   └── templates/
│   │       ├── python/        # Jinja2 templates for Python output (class.j2; planned M9: + activity.j2)
│   │       ├── java/          # Jinja2 templates for Java output (class.j2; planned M9: + activity.j2)
│   │       └── javascript/    # Jinja2 templates for JavaScript output (class.j2; planned M9: + activity.j2)
│   ├── reverse/               # AST parsers for reverse engineering
│   │   ├── python/
│   │   ├── java/
│   │   ├── javascript/
│   │   └── registry.py        # Maps language name → parser module
│   └── mermaid/               # Mermaid diagram generator
│
├── shared/
│   └── schema/                # Canonical JSON schema definition (single source of truth)
│
├── tests/                     # All tests mirroring backend/ structure
└── docs/                      # Architecture diagrams, ADRs
```

---

## The Unified UML JSON Schema

This is the most important construct in the entire system. Every module must use exactly this schema — no ad-hoc extensions, no parallel representations.

```json
{
  "classes": [
    {
      "id": "class_1",
      "name": "User",
      "attributes": [
        {
          "name": "email",
          "datatype": "String",
          "visibility": "private",
          "default_value": null,
          "static": false,
          "final": false
        }
      ],
      "methods": [
        {
          "name": "login",
          "visibility": "public",
          "parameters": [],
          "return_type": "void",
          "static": false,
          "abstract": false
        }
      ],
      "position": { "x": 100, "y": 200 },
      "size": { "width": 160, "height": 120 }
    }
  ],
  "relationships": [
    {
      "id": "rel_1",
      "source": "class_1",
      "destination": "class_2",
      "type": "association",
      "multiplicity": { "source": "1", "destination": "*" },
      "label": ""
    }
  ]
}
```

### Schema Field Reference

**Class object**

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier (`class_N`) |
| `name` | string | Class name in PascalCase |
| `attributes` | Attribute[] | Ordered list of attributes |
| `methods` | Method[] | Ordered list of methods |
| `position` | `{x, y}` | Canvas coordinates |
| `size` | `{width, height}` | Bounding box in pixels |

**Attribute object**

| Field | Type | Description |
|---|---|---|
| `name` | string | Attribute name in camelCase |
| `datatype` | string | Language-neutral type (e.g., `String`, `int`, `List`) |
| `visibility` | enum | `public`, `private`, `protected`, `package` |
| `default_value` | string \| null | Optional default |
| `static` | bool | Static modifier |
| `final` | bool | Final/const modifier |

**Method object**

| Field | Type | Description |
|---|---|---|
| `name` | string | Method name in camelCase |
| `visibility` | enum | `public`, `private`, `protected`, `package` |
| `parameters` | `{name, datatype}[]` | Ordered parameter list |
| `return_type` | string | Language-neutral return type or `void` |
| `static` | bool | Static modifier |
| `abstract` | bool | Abstract modifier |

**Relationship object**

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier (`rel_N`) |
| `source` | string | Source class `id` |
| `destination` | string | Destination class `id` |
| `type` | enum | `association`, `aggregation`, `composition`, `inheritance`, `dependency` |
| `multiplicity` | `{source, destination}` | UML multiplicity strings (e.g., `"1"`, `"*"`, `"0..1"`) |
| `label` | string | Optional edge label |

---

## Folder Responsibilities

### `frontend/components/canvas/`
Owns the infinite canvas: pan, zoom, grid rendering, snap-to-grid. Does not know about UML semantics. Treats shapes as generic drawable objects.

### `frontend/components/uml/`
Owns the UML class box rendering and editing: the three-compartment layout (name / attributes / methods), inline text editing, and serializing a class to/from the Unified JSON format. Never talks to the backend directly.

### `frontend/components/toolbar/`
Tool selection (select, draw shape, draw relationship), export triggers, relationship type picker.

### `frontend/hooks/`
Shared state, canvas interaction hooks (useCanvas, useDiagram, useSelection). Do not put business logic in components; put it here.

### `backend/api/routes/`
Defines URL patterns and HTTP methods only. Each file is a FastAPI `APIRouter`. Routes call controller functions and do nothing else — no validation logic, no service calls, no error handling.

### `backend/api/controllers/`
One controller per domain (image, codegen, reverse, mermaid). Each controller function: deserializes the request model, calls exactly one service method, maps service exceptions to HTTP error responses, and returns the response model. Controllers know HTTP; they do not know domain logic.

### `backend/api/dependencies/`
FastAPI dependency injection providers shared across multiple routes (e.g., content-type guards, file-size limits). Keeps route signatures clean.

### `backend/models/`
Pydantic models that define the HTTP API boundary — what clients send and receive. These are separate from the Unified UML JSON schema models. `requests.py` holds all request body shapes; `responses.py` holds all response body shapes. No business logic lives here.

### `backend/schemas/`
Owns the Unified UML JSON as Pydantic models. `uml.py` defines `UmlDocument`, `UmlClass`, `Attribute`, `Method`, and `Relationship`. `validators.py` contains cross-field and business-rule validators (e.g., relationship source/destination must reference valid class IDs). Every module that works with UML data imports from here — never from `backend/models/`. Planned, not yet implemented: `activity.py` will define a sibling document type, `ActivityDocument` (`ActivityNode`, `ActivityEdge`, `ActivityNodeType`), for Milestone 9. It is deliberately not an extension of `UmlDocument` — an activity diagram's graph shape has nothing in common with a class diagram's — but it follows the same conventions (`str, Enum` subclasses, a `model_validator` checking referential integrity, reusing `Position`/`Size` from `uml.py`). Its validator checks only structural validity (edge references resolve, exactly one START, at least one END); whether a given graph shape is *codegen-able* (e.g. binary decisions only, no fork/join) is a concern of `activity_structuring.py`, not the schema — the same layering the existing schema already uses (it never enforces inheritance-hierarchy shape either, only referential integrity).

### `backend/services/`
One service per pipeline use case. Services orchestrate domain modules (cv, ocr, parser, generator, reverse, mermaid) in sequence and own the pipeline logic. Services accept and return `backend/schemas/` types, not HTTP models. Services have no knowledge of HTTP, request parsing, or response shaping.

### `backend/db/`
Persistence layer. SQLAlchemy ORM models (`User`, `Project`) and session management. A `Project` row stores its diagram as a Unified UML JSON document (validated against `backend/schemas/` before write). Only `auth_service` and `project_service` touch this layer — pipeline modules (cv, ocr, parser, generator, reverse, mermaid) never import from it.

### `backend/cv/`
OpenCV-based image processing: grayscale, threshold, denoise, edge enhancement, contour extraction, rectangle detection, arrow/diamond detection. Input: raw image bytes. Output: bounding boxes and shape descriptors. No HTTP, no schema imports. Planned, not yet implemented: `activity_shape_detector.py` for Milestone 9, classifying contours into start (filled circle), end (ringed circle), action (rounded rect), decision (diamond), and fork/join (bar) via circularity/vertex-position/aspect-ratio heuristics — reuses `preprocessor.py` unchanged; is a new module rather than an extension of `shape_detector.py` because class-box detection is hole-based and does not generalize to these shapes.

### `backend/ocr/`
OCR execution and raw text extraction scoped to detected bounding boxes. Converts pixel regions to raw text strings. Does not parse or interpret the text. No HTTP, no schema imports. Planned, not yet implemented: `activity_extractor.py` for Milestone 9, reusing `extractor.py`'s crop/pad/upscale/Otsu/pytesseract pattern to read action labels and edge guard labels (e.g. "yes"/"no").

### `backend/parser/`
Converts raw OCR text into structured class dictionaries. Handles visibility prefixes (`+`, `-`, `#`), attribute type annotations, method signatures, return types. Outputs plain dicts; the service layer promotes them to `backend/schemas/` types. Planned, not yet implemented: `activity_text_parser.py` for Milestone 9, a thinner sibling parser — no visibility/type-annotation grammar needed, just label normalization and guard-text classification.

### `backend/generator/`
Code generation engine. Accepts a validated `UmlDocument` from `backend/schemas/`, maps language-neutral types using a language map, and renders Jinja2 templates. One output file per class. Contains `language_maps/` and `registry.py`. Planned, not yet implemented (Milestone 9): a second template per language, `activity.j2`, rendering the structured control-flow IR (see `backend/services/activity_structuring.py`) instead of a class. `registry.py`/`LanguageConfig` need no changes — `config.template_dir` already resolves per language, `activity.j2` simply lives alongside the existing `class.j2`.

### `backend/generator/templates/`
Jinja2 template files organized by language. Adding a new language means adding a folder here plus a type mapping file — no other module changes.

### `backend/reverse/`
Language-specific AST parsers. Each sublanguage module (`python/`, `java/`, `javascript/`) exposes a single `parse(source: str) -> UmlDocument` function. They are completely independent of each other. `registry.py` maps language names to parser modules. Planned, not yet implemented: since building `UmlDocument` already requires walking each function/method's AST, the same walk has the information needed to additionally extract that function's control-flow graph (sequence, branches, loops) for the Activity Diagram feature — this would be a second, optional extraction path through the same parser module, not a separate module.

### `backend/mermaid/`
Accepts a `UmlDocument` and produces Mermaid `classDiagram` syntax. Pure transformation — no I/O, no HTTP, no schema validation. Planned, not yet implemented: also accepts a per-function control-flow representation (extracted by `backend/reverse/`) and produces Mermaid `flowchart`/activity syntax — a second, independent transformation in the same module, sharing no code path with the class-diagram renderer beyond the module boundary.

### `shared/schema/`
The canonical JSON Schema file (`uml_schema.json`) that serves as the ground truth for both frontend TypeScript types and backend Pydantic models.

### `tests/`
Mirror the `backend/` directory structure. Each module has a corresponding test file. Tests are unit tests unless otherwise noted.

---

## Coding Standards

### Python (Backend)

- Python 3.11+
- Type annotations on all function signatures and class attributes
- Pydantic v2 for all data models; no plain dicts crossing module boundaries
- Ruff for linting and formatting (replaces flake8 + black)
- Max line length: 100
- Imports ordered: stdlib → third-party → local, separated by blank lines
- No `import *`
- Module-level constants in `UPPER_SNAKE_CASE`
- No bare `except:` — always catch specific exception types

### JavaScript / React (Frontend)

- React 18+, functional components only — no class components
- TypeScript strict mode enabled
- ESLint + Prettier for linting and formatting
- Prefer named exports over default exports
- Co-locate component styles (CSS modules) with their component file
- No prop drilling beyond two levels — use context or a hook
- All canvas state must flow through `useDiagram` hook

### General

- No magic numbers — name constants
- No commented-out code in commits
- Functions do one thing; if a function needs a comment explaining what it does, split it
- Prefer composition over inheritance in both frontend components and backend service classes

---

## Naming Conventions

### Files and Folders

| Location | Convention | Example |
|---|---|---|
| Python modules | `snake_case.py` | `shape_detector.py` |
| React components | `PascalCase.tsx` | `UmlClassBox.tsx` |
| React hooks | `camelCase.ts` with `use` prefix | `useDiagram.ts` |
| Jinja2 templates | `snake_case.j2` | `class.j2` |
| Test files | `test_<module>.py` | `test_shape_detector.py` |

### Code

| Element | Convention |
|---|---|
| Python functions/methods | `snake_case` |
| Python classes | `PascalCase` |
| Python constants | `UPPER_SNAKE_CASE` |
| JS/TS functions | `camelCase` |
| JS/TS React components | `PascalCase` |
| JS/TS types and interfaces | `PascalCase` |
| JSON schema fields | `snake_case` |
| CSS class names | `kebab-case` |
| API endpoint paths | `kebab-case` |

### IDs

- Class IDs: `class_<integer>` (e.g., `class_1`, `class_12`)
- Relationship IDs: `rel_<integer>` (e.g., `rel_1`)
- IDs are assigned sequentially within a document; they are not globally unique across sessions

---

## API Conventions

All endpoints live under `/api`. All request and response bodies are JSON.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Create a user account (email + password) |
| `POST` | `/api/auth/login` | Authenticate; return a bearer token |
| `POST` | `/api/auth/logout` | Invalidate the current token |
| `GET` | `/api/auth/me` | Return the authenticated user's profile |
| `GET` | `/api/projects` | List the authenticated user's projects |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/projects/{id}` | Fetch a project including its Unified UML JSON document |
| `PUT` | `/api/projects/{id}` | Update project name and/or diagram document |
| `DELETE` | `/api/projects/{id}` | Delete a project |
| `POST` | `/api/image-to-json` | Run CV + OCR pipeline on uploaded image; return Unified UML JSON |
| `POST` | `/api/generate-code` | Accept Unified UML JSON + target language; return generated source files |
| `POST` | `/api/reverse` | Accept source file(s); return Unified UML JSON |
| `POST` | `/api/json-to-mermaid` | Accept Unified UML JSON; return Mermaid diagram text. Planned: accept a `diagram_type` of `class` (default) or `activity` to select which Mermaid output is rendered. |
| `GET` | `/api/languages` | Return list of supported target languages |
| `GET` | `/api/templates` | Return available code generation templates |
| `POST` | `/api/activity-image-to-json` | Planned (Milestone 9). Run CV + OCR pipeline on an uploaded activity-diagram image; return `ActivityDocument` |
| `POST` | `/api/generate-activity-code` | Planned (Milestone 9). Accept `ActivityDocument` + target language (+ optional `function_name`); return a standalone generated function with real control-flow structure |

### Request/Response Rules

- All request bodies are validated against the Pydantic models in `backend/models/requests.py`
- Controllers convert validated request models into `backend/schemas/` types before calling services
- On validation failure, return HTTP 422 with a structured error body
- On unexpected server error, return HTTP 500 with `{"error": "<message>"}` — never expose tracebacks to clients
- File uploads use `multipart/form-data`; all other requests use `application/json`
- Successful responses always include the Unified UML JSON where relevant, never intermediate representations
- Response bodies for code generation return a dict mapping filename to file content:
  ```json
  { "files": { "User.py": "...", "Order.py": "..." } }
  ```

### Authentication & Projects

- Every endpoint except `/api/auth/register` and `/api/auth/login` requires a valid bearer token (JWT), enforced via a dependency in `backend/api/dependencies/`
- Passwords are hashed with bcrypt; plaintext passwords never leave the auth service boundary
- Requests for a project the caller does not own return HTTP 404 (not 403) — do not leak project existence
- Each user owns many projects; a project belongs to exactly one user and holds exactly one Unified UML JSON document
- Project ownership is checked in `project_service`, not in controllers or routes

---

## Testing Expectations

### Coverage Targets

- `backend/schemas/`: 100% — the schema and validators are foundational, every path must be tested
- `backend/generator/`: 100% — code generation must be deterministic and fully verified
- `backend/services/`: unit tests for every service method; mock domain modules at the service boundary
- `backend/api/controllers/`: unit tests for HTTP error mapping; mock services
- `backend/api/routes/`: integration tests covering success and error paths for every endpoint
- `backend/cv/`, `backend/ocr/`: integration tests using fixture images; unit tests for helper functions
- `backend/parser/`: unit tests covering every visibility symbol, type annotation pattern, and method signature form
- `backend/reverse/`: unit tests using fixture source files for each supported language
- `backend/mermaid/`: unit tests for every relationship type
- `backend/services/auth_service.py`: unit tests for registration, login success/failure, hashing, and token validation — never store or log plaintext passwords in tests
- `backend/services/project_service.py`: unit tests for CRUD and ownership checks (accessing another user's project must 404); use an in-memory SQLite database

### Rules

- Each test module lives at `tests/<module_name>/test_<file>.py` mirroring `backend/`
- No mocking of the JSON schema models — tests must construct valid Pydantic objects
- Fixture files (images, source code) live in `tests/fixtures/`; they are committed to the repo
- Tests must not perform real network I/O or write to disk outside `tmp_path`
- A test that asserts a Jinja2 template output must assert the full rendered string, not just a substring, unless testing a single independent token (e.g., a class name)
- Use `pytest` — no `unittest.TestCase` classes

---

## Implementation Roadmap

The milestones below are ordered. Do not begin a milestone until the previous one's deliverables are complete and tested.

### Milestone 1 — Frontend UML Editor
- Infinite canvas with pan, zoom, grid, snap
- Generic shape library (Rectangle, Circle, Diamond, Line, Arrow)
- UML Class Box component with three editable compartments
- Relationship tools for all five types (Association, Aggregation, Composition, Inheritance, Dependency)
- Selection: single, multi, drag, resize, delete, duplicate
- Export canvas as PNG
- Serialize canvas state to Unified UML JSON

### Milestone 2 — Image Processing Pipeline
- OpenCV preprocessing (grayscale, threshold, denoise, edge, contour)
- Rectangle and shape detection
- OCR execution scoped to detected bounding boxes
- Relationship line detection and source/destination matching

### Milestone 3 — Unified UML JSON Layer
- Finalized, validated Pydantic schema (`backend/schemas/`)
- JSON Schema file in `shared/schema/`
- TypeScript types generated from or matching the schema
- Full test coverage of validation edge cases

### Milestone 4 — Code Generation
- Jinja2 templates for Python, Java, JavaScript
- Type mapping (language-neutral → language-specific)
- One output file per class
- `/api/generate-code` endpoint

### Milestone 5 — Reverse Engineering
- Python AST parser
- Java parser (JavaParser or equivalent)
- JavaScript parser (Babel/Acorn/Esprima)
- Relationship inference for all five relationship types
- `/api/reverse` endpoint

### Milestone 6 — Diagram Generation
- Mermaid generator from Unified UML JSON
- `/api/json-to-mermaid` endpoint
- Frontend Mermaid rendering and diagram preview panel
- Activity/control-flow diagram generation from parsed source code: extend each language's `backend/reverse/<language>/parser.py` to optionally extract a per-function/method control-flow graph (sequence, branches, loops) alongside the existing class-structure extraction, and extend `backend/mermaid/` with a second, independent transformation from that control-flow graph to Mermaid `flowchart`/activity syntax — an extension of the Reverse Engineering pipeline, not a new pipeline

### Milestone 7 — Full Integration
- End-to-end forward pipeline test: canvas → image → JSON → code
- End-to-end reverse pipeline test: source files → JSON → Mermaid → rendered diagram
- Cross-pipeline JSON consistency check

### Milestone 8 — Authentication & Projects
- User registration, login, logout with JWT bearer tokens and bcrypt password hashing
- `backend/db/` persistence layer (SQLAlchemy): `User` and `Project` models
- Project CRUD endpoints; each user owns many projects, each project holds one Unified UML JSON document
- Auth guard dependency protecting all non-auth endpoints
- Frontend pages: login, register, project dashboard; editor loads/saves the open project's diagram

### Milestone 9 — Activity Diagram Forward Pipeline

Parallel to the existing class-diagram forward pipeline, not a modification of it. Output is a **standalone generated function** (not spliced into any class from a separate class diagram). This milestone is a deliberate, scoped exception to Design Principle 7 below — see that principle for what "scoped" means here.

- **Schema** (`backend/schemas/activity.py`): `ActivityDocument` (`nodes: list[ActivityNode]`, `edges: list[ActivityEdge]`), `ActivityNode` (`id`, `type: ActivityNodeType`, `label`, `position`, `size`), `ActivityEdge` (`id`, `source`, `target`, `label` for guard text), `ActivityNodeType` enum (`start`, `end`, `action`, `decision`, `fork`, `join`). Validator checks referential integrity, exactly one `start`, at least one `end` — nothing about codegen-feasibility (that's the structuring algorithm's job, see below).
- **CV** (`backend/cv/activity_shape_detector.py`): classifies contours via circularity (start/end), 4-vertex-position pattern — corners vs. edge-midpoints — to distinguish action (rounded rect) from decision (diamond), and aspect ratio for fork/join bars. Reuses `preprocessor.py` unchanged.
- **OCR** (`backend/ocr/activity_extractor.py`): reuses `extractor.py`'s crop/pad/upscale/Otsu/pytesseract pattern for action labels and edge guard labels.
- **Edge orientation**: resolved by a DFS-from-the-unique-START heuristic over the undirected CV-detected line/shape adjacency, not by arrowhead detection — a back-edge is any edge whose target is an ancestor on the current DFS stack (standard compiler-theory back-edge definition). This is consistent with the existing class pipeline's own precedent of not detecting line direction/type from CV. A node unreachable from START, or a detected back-edge that violates the top-to-bottom drawing convention, raises `ValueError` rather than silently producing a wrong graph.
- **Structuring algorithm** (`backend/services/activity_structuring.py`): reconstructs `if`/`else` from a decision's two branches plus their nearest common reconvergence point (bounded forward search from each branch), and `while` loops from a DFS-detected back-edge into the decision acting as loop header. Out of scope for v1 — each case raises a clear `ValueError` (→ HTTP 422), never silently produces wrong code: any `fork`/`join` node, decisions with other than exactly 2 outgoing edges, irreducible loops (multiple entries), multiple back-edges into one header, multi-exit loops, or no findable convergence point.
- **Codegen** (`backend/services/activity_codegen_service.py` + `backend/generator/templates/*/activity.j2`): the structuring output (a tree of Action/If/While IR nodes) becomes a flat, recursively-nested template context, rendered by a recursive Jinja2 macro — mirrors the existing generator/template split (`codegen_service.py` / `class.j2`) exactly: all structural decisions resolved in Python, templates are presentation-only. Action bodies render as `# TODO: <label>` / `pass` (or the equivalent per language) — never fabricated logic. Decision conditions render as `if True:` / `if (true) {` with the diagram's label preserved only as a comment — inventing a boolean expression from OCR'd text would be exactly the kind of fabrication Principle 7 forbids. Loop placeholders default to `while False:` (not `while True:`) specifically so ungenerated code never infinite-loops by default.
- **API**: `POST /api/activity-image-to-json` (mirrors `image.py`/`image_controller.py`) and `POST /api/generate-activity-code` (mirrors `codegen.py`/`codegen_controller.py`; reuses the existing `CodeGenerationResponse` model as-is). New request/response models: `GenerateActivityCodeRequest`, `ActivityReverseResponse`.
- **Recommended build order** (de-risks the hardest part first): (1) schema, (2) structuring algorithm tested against hand-written `ActivityDocument` JSON fixtures — no CV/OCR involved yet, (3) codegen + templates against the same fixtures, (4) `/api/generate-activity-code` wired to hand-authored JSON to validate the API layer and demo the real value (structured code, not stubs) end-to-end, (5) CV shape detection in isolation against synthetic fixtures, (6) OCR extraction, (7) edge-orientation heuristic against adversarial synthetic fixtures (early loop-exit, nested if-in-loop), (8) full pipeline wiring + `/api/activity-image-to-json` + integration tests.
- **Diagrams already drawn** (design docs only — no code exists yet): `docs/diagrams/usecase_1_7_activity_code_generation.drawio`/`.puml` (use case: upload image, detect shapes, extract labels, generate code) and `docs/diagrams/activity_1_7_activity_code_generation.drawio`/`.puml` (activity diagram: the full upload → CV → OCR → parse → validate → structure → codegen → return flow, including both 422-error exit points). The forward-pipeline branch is also reflected in the two overall pipeline diagrams (`activity-overall.drawio` and `docs/diagrams/activity_diagram.drawio`, both gained a "Diagram type?" split mirroring the one already in their reverse column) and in `docs/diagrams/activity_forward_uml.drawio` (the sibling class-diagram forward pipeline, for comparison). `docs/diagrams/usecase_level1.drawio` and `docs/diagrams/er_diagram.drawio`/`.py` were updated to match (a 7th module bubble, and `ActivityNode`/`ActivityEdge` entities respectively).

---

## Development Workflow

### Starting a New Feature

1. Identify which milestone the feature belongs to — do not work ahead
2. Identify which module owns the feature (see Folder Responsibilities)
3. If the feature touches the Unified UML JSON schema, update `shared/schema/uml_schema.json` first and get it reviewed before any implementation
4. Write tests before or alongside implementation, not after

### Branching

- `main`: stable, passing CI only
- Feature branches: `feature/<milestone>-<short-description>` (e.g., `feature/m1-canvas-pan-zoom`)
- Fix branches: `fix/<short-description>`

### Before Submitting

- All tests pass: `pytest tests/`
- Linting passes: `ruff check backend/` and `eslint frontend/`
- No new type errors: `mypy backend/` and `tsc --noEmit` in `frontend/`
- No hardcoded values that belong in the schema or in constants

---

## Rules for Adding New Features

### Adding a New Target Language (Code Generation)

1. Add type mapping in `backend/generator/language_maps/<language>.py`
2. Add Jinja2 templates in `backend/generator/templates/<language>/class.j2`
3. Register the language in `backend/generator/registry.py`
4. Add unit tests in `tests/generator/test_<language>.py`
5. Update `/api/languages` to include the new language
6. No other module changes are required or permitted

### Adding a New Source Language (Reverse Engineering)

1. Add an AST parser module at `backend/reverse/<language>/parser.py`
2. The module must expose a single function: `parse(source: str) -> UmlDocument`
3. Add unit tests in `tests/reverse/test_<language>.py` using fixture files
4. Register the parser in `backend/reverse/registry.py`
5. Update `/api/reverse` to accept the new language specifier
6. No other module changes are required or permitted

### Adding a New Relationship Type

This is a schema change. It requires:
1. Update `shared/schema/uml_schema.json` — add to the `type` enum
2. Update `backend/schemas/uml.py` — add to the `RelationshipType` Pydantic enum
3. Update `frontend/` TypeScript types
4. Update all five relationship-aware modules: `backend/cv/`, `backend/parser/`, `backend/mermaid/`, `backend/generator/` (for each language), and `backend/reverse/` (for each language)
5. Update all corresponding tests

Schema changes are the most expensive change in this codebase. Avoid them.

### Adding a New API Endpoint

1. Add the route in the appropriate `backend/api/routes/<group>.py` file — URL pattern and HTTP method only
2. Add a controller function in `backend/api/controllers/<group>_controller.py` — parse request model, call one service method, return response model
3. Add request/response Pydantic models in `backend/models/requests.py` and `backend/models/responses.py`
4. Add or extend a service method in `backend/services/` — all domain logic lives here
5. Add integration test in `tests/api/routes/` and unit tests in `tests/api/controllers/`
6. Document the endpoint in this file under API Conventions

---

## Best Practices

### Pipeline Integrity

- Never let a module bypass the Unified UML JSON. A function that accepts a diagram image and returns Python code directly is an architectural violation, even if it is convenient.
- If you need data from a previous pipeline stage, accept the JSON, not the raw intermediate.

### State Management (Frontend)

- Canvas state (shapes, positions, selections) lives in `useDiagram`
- Do not store derived data — compute it from the canonical state
- When serializing to Unified UML JSON for the backend, call the serializer in `useDiagram`, not in individual components

### Template Design (Code Generation)

- Templates must not contain conditional logic beyond visibility and modifier rendering
- All structural decisions (inheritance, association, composition) are resolved in the generator before the template is called
- Templates must produce syntactically valid code for all valid inputs

### OCR Robustness

- Always run OCR on preprocessed (not raw) images
- Scope OCR to detected bounding boxes only — never run on the full image
- Treat OCR output as potentially noisy; the parser must be tolerant of common OCR errors (e.g., `l` vs `1`, `:` vs `;`)

### AST Parsing (Reverse Engineering)

- Parse only what the user selects — never traverse the entire filesystem
- Relationship inference is best-effort; emit what can be proven from the AST; do not guess
- When a language construct has no UML equivalent, discard it cleanly rather than approximating

---

## Design Principles

1. **The Unified UML JSON is the only contract.** No module knows what another module looks like internally. They communicate exclusively through validated JSON conforming to the shared schema.

2. **Pipelines are one-directional.** The forward pipeline only goes forward. The reverse pipeline only goes backward. They share the schema but do not share code paths or execution.

3. **Extensibility by addition, not modification.** Adding a new language must never require changing existing parsers, generators, or schema definitions.

4. **Each module is independently testable.** If a module requires another module to run its tests, the boundary between them is wrong.

5. **The backend is stateless per request.** No session state, no in-memory caches between requests — each API call is self-contained and authenticated by its bearer token. Durable state (users and projects) lives only in the `backend/db/` persistence layer; pipeline modules remain pure and stateless.

6. **The frontend serializes; the backend validates.** The frontend produces JSON; the backend validates it. The frontend never assumes its JSON is valid without a backend round-trip that includes schema validation.

7. **Generated code is a best-effort scaffold, not production code.** Templates produce compilable structure, not complete implementations. Method bodies are stubs. Do not attempt to generate method logic.

   **Scoped exception — Milestone 9 (Activity Diagram Forward Pipeline, planned):** this pipeline's entire purpose is generating real control-flow *structure* (`if`/`else`, `while`) from an activity diagram, which looks like "method logic" at a glance. The exception is narrow and does not relax this principle anywhere else: only the branching/looping *shape* mirrors the diagram; the content inside every action stays a placeholder (`# TODO: <label>` / `pass`), and every decision condition stays a literal placeholder (`if True:` / `while False:`) with the diagram's label preserved only as a comment — no boolean expression, no business logic is ever synthesized from OCR'd text. If a future change to this milestone starts inventing conditions or action bodies, that is a violation of this principle, not an extension of the exception.
