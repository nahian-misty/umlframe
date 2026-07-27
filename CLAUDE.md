# UMLFrame — Claude Code Reference

## Project Overview

UMLFrame is a bidirectional UML ↔ Code Engineering platform. Users draw UML Class Diagrams visually, and the system either generates source code from those diagrams or reverse-engineers existing source code back into diagrams.

Two complete pipelines share a single intermediate representation — the Unified UML JSON:

**Forward Pipeline:** UML Canvas → Export Image → Computer Vision + OCR → Unified UML JSON → Source Code

**Reverse Pipeline:** Source Code → AST Parser → Unified UML JSON → Mermaid Generator → Rendered UML Diagram

The Unified UML JSON is the canonical representation for every subsystem. No subsystem communicates with another directly. Everything either produces or consumes this schema.

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
│   └── pages/                 # Top-level route pages
│
├── backend/                   # Python application
│   ├── api/
│   │   ├── routes/            # FastAPI APIRouter definitions — URL patterns only
│   │   │   ├── image.py       # /api/image-to-json
│   │   │   ├── codegen.py     # /api/generate-code, /api/languages, /api/templates
│   │   │   ├── reverse.py     # /api/reverse
│   │   │   └── mermaid.py     # /api/json-to-mermaid
│   │   ├── controllers/       # Request/response handling; calls services; no domain logic
│   │   │   ├── image_controller.py
│   │   │   ├── codegen_controller.py
│   │   │   ├── reverse_controller.py
│   │   │   └── mermaid_controller.py
│   │   └── dependencies/      # FastAPI dependency injection (shared across routes)
│   ├── models/                # Pydantic models for the HTTP boundary (requests + responses)
│   │   ├── requests.py        # ImageUploadRequest, GenerateCodeRequest, ReverseRequest, etc.
│   │   └── responses.py       # CodeGenerationResponse, MermaidResponse, etc.
│   ├── schemas/               # Unified UML JSON — Pydantic data models + validation rules
│   │   ├── uml.py             # UmlDocument, UmlClass, Attribute, Method, Relationship
│   │   └── validators.py      # Cross-field validation and business-rule constraints
│   ├── services/              # Business logic orchestration; owns pipeline sequencing
│   │   ├── image_service.py   # Sequences cv/ → ocr/ → parser/ → schemas/
│   │   ├── codegen_service.py # Sequences schemas/ → generator/
│   │   ├── reverse_service.py # Sequences reverse/ → schemas/
│   │   └── mermaid_service.py # Sequences schemas/ → mermaid/
│   ├── cv/                    # OpenCV image preprocessing + shape detection
│   ├── ocr/                   # OCR execution scoped to detected bounding boxes
│   ├── parser/                # OCR-text-to-structured-data parser
│   ├── generator/             # Code generation engine
│   │   ├── language_maps/     # Language-neutral → language-specific type mappings
│   │   │   ├── python.py
│   │   │   ├── java.py
│   │   │   └── javascript.py
│   │   ├── registry.py        # Maps language name → (language_map, template_dir)
│   │   └── templates/
│   │       ├── python/        # Jinja2 templates for Python output
│   │       ├── java/          # Jinja2 templates for Java output
│   │       └── javascript/    # Jinja2 templates for JavaScript output
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
Owns the Unified UML JSON as Pydantic models. `uml.py` defines `UmlDocument`, `UmlClass`, `Attribute`, `Method`, and `Relationship`. `validators.py` contains cross-field and business-rule validators (e.g., relationship source/destination must reference valid class IDs). Every module that works with UML data imports from here — never from `backend/models/`.

### `backend/services/`
One service per pipeline use case. Services orchestrate domain modules (cv, ocr, parser, generator, reverse, mermaid) in sequence and own the pipeline logic. Services accept and return `backend/schemas/` types, not HTTP models. Services have no knowledge of HTTP, request parsing, or response shaping.

### `backend/cv/`
OpenCV-based image processing: grayscale, threshold, denoise, edge enhancement, contour extraction, rectangle detection, arrow/diamond detection. Input: raw image bytes. Output: bounding boxes and shape descriptors. No HTTP, no schema imports.

### `backend/ocr/`
OCR execution and raw text extraction scoped to detected bounding boxes. Converts pixel regions to raw text strings. Does not parse or interpret the text. No HTTP, no schema imports.

### `backend/parser/`
Converts raw OCR text into structured class dictionaries. Handles visibility prefixes (`+`, `-`, `#`), attribute type annotations, method signatures, return types. Outputs plain dicts; the service layer promotes them to `backend/schemas/` types.

### `backend/generator/`
Code generation engine. Accepts a validated `UmlDocument` from `backend/schemas/`, maps language-neutral types using a language map, and renders Jinja2 templates. One output file per class. Contains `language_maps/` and `registry.py`.

### `backend/generator/templates/`
Jinja2 template files organized by language. Adding a new language means adding a folder here plus a type mapping file — no other module changes.

### `backend/reverse/`
Language-specific AST parsers. Each sublanguage module (`python/`, `java/`, `javascript/`) exposes a single `parse(source: str) -> UmlDocument` function. They are completely independent of each other. `registry.py` maps language names to parser modules.

### `backend/mermaid/`
Accepts a `UmlDocument` and produces Mermaid `classDiagram` syntax. Pure transformation — no I/O, no HTTP, no schema validation.

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
| `POST` | `/api/image-to-json` | Run CV + OCR pipeline on uploaded image; return Unified UML JSON |
| `POST` | `/api/generate-code` | Accept Unified UML JSON + target language; return generated source files |
| `POST` | `/api/reverse` | Accept source file(s); return Unified UML JSON |
| `POST` | `/api/json-to-mermaid` | Accept Unified UML JSON; return Mermaid diagram text |
| `GET` | `/api/languages` | Return list of supported target languages |
| `GET` | `/api/templates` | Return available code generation templates |

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

### Milestone 7 — Full Integration
- End-to-end forward pipeline test: canvas → image → JSON → code
- End-to-end reverse pipeline test: source files → JSON → Mermaid → rendered diagram
- Cross-pipeline JSON consistency check

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

5. **The backend is stateless.** No session state, no in-memory caches between requests. Each API call is self-contained. State persistence (if added later) is out of scope for the initial version.

6. **The frontend serializes; the backend validates.** The frontend produces JSON; the backend validates it. The frontend never assumes its JSON is valid without a backend round-trip that includes schema validation.

7. **Generated code is a best-effort scaffold, not production code.** Templates produce compilable structure, not complete implementations. Method bodies are stubs. Do not attempt to generate method logic.
