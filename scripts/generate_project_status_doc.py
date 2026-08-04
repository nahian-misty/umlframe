"""Generates PROJECT_STATUS.docx: a file-by-file map of the codebase plus
three end-to-end request-flow walkthroughs (auth, project load/save, and the
image-to-code forward pipeline).

Content reflects the code as of the time this was written (read directly from
backend/ and frontend/src/, not from CLAUDE.md's design-intent text) — re-read
the source before trusting any specific claim here after the code changes.
"""

from __future__ import annotations

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt


def add_bullets(doc, items: list[str], style: str = "List Bullet") -> None:
    for item in items:
        doc.add_paragraph(item, style=style)


def add_code_chain(doc, steps: list[str]) -> None:
    """Render an ordered call chain (route -> controller -> service -> ...).

    Deliberately plain Normal paragraphs with a manual "N. " prefix rather
    than the "List Number" style: that style's numbering is one continuous
    counter for the whole document in python-docx's default template, so
    three separate walkthroughs using it back-to-back would number 1-9,
    10-17, 18-26 instead of each restarting at 1. Section 7 below is the
    document's only other numbered list, so it's safe to use the real
    "List Number" style there without a restart conflict.
    """
    for i, step in enumerate(steps, start=1):
        doc.add_paragraph(f"{i}. {step}")


def build_doc() -> docx.Document:
    doc = docx.Document()

    doc.add_heading("UMLFrame — Project Status Guide", level=0)
    intro = doc.add_paragraph(
        "A plain-English map of the codebase: what each file does, how a request "
        "actually flows through the layers, what's finished, and what's still "
        "missing. Written by reading the code directly (not just the design "
        "docs) so it reflects what's actually there."
    )
    intro.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # ------------------------------------------------------------------
    # 1. What this project is
    # ------------------------------------------------------------------
    doc.add_heading("1. What this project is", level=1)
    doc.add_paragraph(
        "UMLFrame turns UML class diagrams into code, and turns code back into "
        "diagrams. Everything passes through one shared format called the "
        "Unified UML JSON — no part of the system talks to another part except "
        "through this JSON."
    )
    add_bullets(doc, [
        "Forward pipeline (done): draw a diagram → export as PNG → computer vision + OCR reads the image → Unified UML JSON → generate Python/Java/JS source code.",
        "Reverse pipeline (not built yet): paste in source code → parse it → Unified UML JSON → render as a Mermaid diagram.",
        "Multi-user platform (done): users register/log in, own multiple projects, each project stores one diagram.",
        "Future addition (not built yet): a second diagram type, Activity Diagrams (flowcharts with start/end/decision boxes), bidirectional the same way.",
    ])

    # ------------------------------------------------------------------
    # 2. Tech stack
    # ------------------------------------------------------------------
    doc.add_heading("2. Tech stack", level=1)

    doc.add_heading("Backend (Python 3.11+)", level=2)
    backend_libs = [
        ("Library", "What it's for"),
        ("FastAPI", "Web framework — all /api/* HTTP endpoints"),
        ("Uvicorn", "ASGI server that runs FastAPI"),
        ("Pydantic v2", "Every data model (UML schema, request/response bodies) — no raw dicts"),
        ("SQLAlchemy", "ORM — talks to the database"),
        ("SQLite", "The actual database (umlframe.db file on disk). Configurable via DATABASE_URL env var, defaults to SQLite — see backend/config.py"),
        ("PyJWT", "Issues/verifies login tokens (bearer auth)"),
        ("bcrypt", "Password hashing"),
        ("Jinja2", "Templates that render generated source code"),
        ("OpenCV (`cv2`) + NumPy", "Image preprocessing and shape detection for the image→diagram pipeline"),
        ("pytesseract", "OCR (reads text out of detected shapes) — wraps the Tesseract OCR engine"),
        ("pytest, httpx, ruff, mypy", "Testing, linting, type-checking"),
    ]
    t = doc.add_table(rows=1, cols=2)
    t.style = "Light Grid Accent 1"
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = backend_libs[0]
    for lib, purpose in backend_libs[1:]:
        row = t.add_row().cells
        row[0].text, row[1].text = lib, purpose

    doc.add_heading("Frontend", level=2)
    frontend_libs = [
        ("Library", "What it's for"),
        ("React 19 + react-dom", "UI framework"),
        ("TypeScript", "Type safety (strict mode)"),
        ("Vite", "Dev server / build tool"),
        ("react-router-dom", "Routing between pages (/, /login, /dashboard, /editor/:projectId, etc.)"),
        ("html-to-image", "Exports the canvas as a PNG"),
        ("lucide-react", "Icon set"),
        ("ESLint + Prettier", "Linting/formatting"),
    ]
    t2 = doc.add_table(rows=1, cols=2)
    t2.style = "Light Grid Accent 1"
    t2.rows[0].cells[0].text, t2.rows[0].cells[1].text = frontend_libs[0]
    for lib, purpose in frontend_libs[1:]:
        row = t2.add_row().cells
        row[0].text, row[1].text = lib, purpose

    doc.add_heading("Database", level=2)
    doc.add_paragraph(
        "SQLite, accessed through SQLAlchemy. Two tables: users and projects "
        "(backend/db/models.py). A Project row stores its diagram as a JSON "
        "*string* in a Text column (Project.document) — it is validated against "
        "the UmlDocument schema on every read (model_validate_json) and every "
        "write (model_dump_json), never stored as a native JSON/JSONB column. "
        "The ORM never sees a UmlDocument object directly; the controller layer "
        "converts on the way in and out (see 3.2 below)."
    )

    # ------------------------------------------------------------------
    # 3. How data flows through the system
    # ------------------------------------------------------------------
    doc.add_heading("3. How data flows through the system", level=1)
    doc.add_paragraph(
        "The file-by-file sections below (4 and 5) describe what each file "
        "contains. This section instead follows three concrete user actions "
        "end-to-end, hopping between frontend and backend files in the order "
        "they actually execute, so the layering makes sense as a whole rather "
        "than as a pile of separate files."
    )

    doc.add_heading("3.1 Register → log in → reach a protected page", level=2)
    add_code_chain(doc, [
        "User submits the form in frontend/src/pages/LoginPage.tsx (or SignupPage.tsx).",
        "The page calls login()/register() from frontend/src/context/AuthContext.tsx.",
        "AuthContext calls frontend/src/api/authApi.ts, which POSTs JSON to /api/auth/login or /api/auth/register via the shared apiFetch() wrapper in api/client.ts.",
        "backend/api/routes/auth.py receives the request, validates the body against RegisterRequest/LoginRequest (backend/models/requests.py — email format and an 8-char password minimum are enforced by Pydantic field_validators here), and calls auth_controller.",
        "backend/api/controllers/auth_controller.py calls exactly one service function (auth_service.register_user or authenticate_user), maps EmailAlreadyRegisteredError → HTTP 409 and InvalidCredentialsError → HTTP 401, and on success builds a TokenResponse.",
        "backend/services/auth_service.py does the actual work: bcrypt-hashes/verifies the password against the users table (via a plain SQLAlchemy Session, no ORM-level password logic), then create_access_token() signs a JWT (PyJWT, HS256) whose payload is just {sub: user_id, iat, exp} — no email, roles, or other claims are embedded.",
        "The TokenResponse (access_token + user id/email) comes back to authApi.ts, which AuthContext stores in React state and in localStorage under the key umlframe-token.",
        "Every subsequent AuthContext consumer (via useAuthContext()) sees isAuthenticated = token !== null && user !== null. frontend/src/components/routing/ProtectedRoute.tsx reads that flag and either renders its children or <Navigate to=\"/login\">.",
        "On every protected backend call afterward, the token travels as an Authorization: Bearer <token> header; backend/api/dependencies/auth.py's get_current_user dependency decodes it (auth_service.decode_access_token), loads the User row by the sub claim, and 401s the request if the token is missing, expired, or malformed.",
    ])
    doc.add_paragraph(
        "Note: /api/auth/logout does not invalidate the token server-side — the "
        "backend is stateless per request (Design Principle 5: no session "
        "state, no in-memory caches), so there is no token blacklist. The "
        "route exists only so the frontend has something to call before it "
        "discards the token from localStorage; the same JWT would still "
        "decode successfully against the backend until it naturally expires "
        "(60 minutes by default, ACCESS_TOKEN_EXPIRE_MINUTES in backend/config.py)."
    )

    doc.add_heading("3.2 Opening the dashboard, then loading/saving one project", level=2)
    add_code_chain(doc, [
        "frontend/src/pages/DashboardPage.tsx calls projectsApi.listProjects(token) on mount.",
        "GET /api/projects → backend/api/routes/projects.py → project_controller.list_projects(), which calls project_service.list_projects(db, user_id) — a query filtered to Project.owner_id == user_id and ordered by updated_at desc. Ownership is enforced entirely in project_service, never in the controller or route (per CLAUDE.md's rule).",
        "The controller converts each ORM Project row into a ProjectSummaryResponse via _to_summary(): it parses the stored document JSON string back into a UmlDocument (UmlDocument.model_validate_json) purely to compute class_count/relationship_count/class_boxes for the dashboard thumbnail — the full document is not sent at list time.",
        "Clicking a project card navigates to /editor/:projectId. frontend/src/pages/EditorPage.tsx then calls projectsApi.getProject(token, projectId), which this time returns the full ProjectResponse including the whole UmlDocument.",
        "EditorPage calls diagram.loadDocument(project.document) — this is the useDiagram() hook (frontend/src/hooks/useDiagram.ts), reached through the app-wide DiagramContext. loadDocument converts each wire UmlClass/Relationship into internal editor state via classFromWire() (frontend/src/components/uml/umlClassSerializer.ts), resets pan/zoom, clears selection, and reseeds the class_N/rel_N id counters from the loaded ids so newly created shapes never collide with existing ones.",
        "The Canvas (components/canvas/Canvas.tsx) renders purely from that state — UmlClassBox per class, RelationshipEdge per relationship — and every user edit (drag, resize, add attribute, etc.) goes through a useDiagram mutator, never touches the DOM/state directly.",
        "Clicking Save calls diagram.toDocument() (the exact inverse of loadDocument, via classToWire()) and PUTs it through projectsApi.updateProject → PUT /api/projects/{id} → project_controller.update_project → project_service.update_project, which re-serializes it with UmlDocument.model_dump_json() before writing the Text column. Renaming the project title (on blur) fires a separate PUT with only {name: ...}, document omitted.",
        "Every project route requires get_current_user, and project_service._get_owned_project() filters by owner_id == user_id; a project owned by someone else — or one that doesn't exist — raises ProjectNotFoundError, which project_controller maps to HTTP 404 either way. This is intentional (CLAUDE.md: 'don't leak project existence').",
    ])

    doc.add_heading("3.3 Forward pipeline in the UI: image → JSON → canvas → generated code", level=2)
    add_code_chain(doc, [
        "User opens the upload modal (frontend/src/components/toolbar/ImageUploadButton.tsx → ImageUploadModal.tsx) and picks a PNG/JPEG. If the canvas already has content, the modal requires a second confirming click before overwriting it.",
        "imageApi.imageToJson(file) builds a FormData body (multipart, no manual Content-Type header — the browser sets the boundary) and POSTs to /api/image-to-json.",
        "backend/api/routes/image.py accepts the UploadFile and hands it to image_controller, which checks the content-type is png/jpeg and the file isn't empty before calling image_service.image_to_document().",
        "backend/services/image_service.py runs the actual pipeline in sequence: preprocess() (backend/cv/preprocessor.py: decode bytes → grayscale → Gaussian blur → inverted binary threshold) → detect_shapes() (backend/cv/shape_detector.py) → extract_class_text() per box (backend/ocr/extractor.py) → parse_class_name/parse_attribute_line/parse_method_line (backend/parser/text_parser.py) → assembles Attribute/Method/UmlClass/Relationship objects → returns a validated UmlDocument.",
        "Shape detection is hole-based, not edge-based: it finds the black rectangular gaps between a class box's compartment dividers (cv2.findContours with RETR_CCOMP), groups holes that share left/right edges into one class box, and only then derives the outer box bounds and divider y-positions from that group. This is deliberately robust to relationship lines touching or crossing box borders.",
        "Relationship *type* is not detected from the image at all — every Hough-detected line that connects two class boxes becomes a plain RelationshipType.ASSOCIATION with 1..1 multiplicity in _build_relationships(). There is no arrowhead/diamond-head classification yet, so aggregation, composition, inheritance, and dependency lines all currently import as generic associations. (This is the concrete gap behind 'image processing is not perfect' — see the Gantt chart's M2 continuation segment.)",
        "OCR runs per compartment strip (name/attributes/methods), not on the whole image: each strip is cropped, padded with white, upscaled 4x with cubic interpolation, and Otsu-thresholded before pytesseract.image_to_string — this is what lets Tesseract read small class-diagram fonts reliably.",
        "text_parser.py then turns each raw OCR line into a name/type/visibility/default-value tuple, tolerating common OCR confusions (; → :, em/en-dash → -, middle-dot → .) and rejecting lines that don't look like a valid identifier rather than guessing.",
        "The resulting UmlDocument comes back through image_controller → ReverseResponse → imageApi.ts, and ImageUploadModal calls diagram.loadDocument(document) — the same function used when opening a saved project, so an image-derived diagram is indistinguishable from a hand-drawn one once it's on the canvas.",
        "From there the user can hit Generate Code in CodeGenPanel.tsx: it calls codegenApi.generateCode(diagram.toDocument(), language) → POST /api/generate-code → codegen_controller.generate() → codegen_service.generate_code().",
        "codegen_service builds one Jinja2 render context per class (mapped types via the language's registry.LanguageConfig, static vs. instance attributes split, per-class import lists computed from cross-references to other classes in the same document, inheritance resolved by scanning the document's own INHERITANCE relationships) and renders generator/templates/<lang>/class.j2 once per class — one output file per class, e.g. {ClassName}.py.",
        "The rendered files come back as a CodeGenerationResponse ({files: {filename: content}}) and CodeViewer.tsx displays them. Every method body in every template is a stub (`...`/`pass`/etc.) — no method logic is ever synthesized, per Design Principle 7.",
    ])
    doc.add_paragraph(
        "Note: neither /api/image-to-json nor /api/generate-code currently "
        "requires get_current_user — they're the only two non-auth, "
        "non-project endpoints that run without a bearer token, unlike what "
        "the 'every endpoint except register/login requires auth' rule in "
        "CLAUDE.md describes. Nothing about the request depends on which "
        "user is calling (there's no project/document being written), so it's "
        "a low-severity gap, but it's a real deviation from the stated rule "
        "worth closing before these are treated as fully production endpoints."
    )

    # ------------------------------------------------------------------
    # 4. File-by-file: Backend
    # ------------------------------------------------------------------
    doc.add_heading("4. File-by-file: Backend", level=1)

    doc.add_heading("Entry point & configuration", level=2)
    add_bullets(doc, [
        "backend/main.py — creates the FastAPI app with a lifespan hook that calls init_db() (creates SQLite tables if they don't exist yet) on startup, adds CORS middleware sourced from settings.cors_origins, and registers exactly four routers: auth, projects, codegen, image (in that order). reverse and mermaid routers do not exist yet, so importing them would fail.",
        "backend/config.py — a frozen dataclass Settings, instantiated once at import time as the module-level settings singleton. Every field reads from an environment variable with a hardcoded fallback: DATABASE_URL (sqlite:///./umlframe.db), JWT_SECRET_KEY (a dev default that must be overridden in real deployments), ACCESS_TOKEN_EXPIRE_MINUTES (60), CORS_ORIGINS (comma-split, defaults to http://localhost:3000).",
    ])

    doc.add_heading("Database & persistence (Milestone 8)", level=2)
    add_bullets(doc, [
        "backend/db/models.py — two SQLAlchemy 2.0-style Mapped models. User (id, email [unique/indexed], hashed_password, created_at) has a one-to-many relationship to Project with cascade=\"all, delete-orphan\" — deleting a user deletes their projects. Project (id, name, document [Text], owner_id [FK→users.id, indexed], created_at, updated_at [auto-updates via onupdate=]) stores its diagram as a raw JSON string, not a structured column.",
        "backend/db/session.py — builds the SQLAlchemy engine from settings.database_url (adding check_same_thread=False only for SQLite), a non-autoflush/non-autocommit SessionLocal factory, init_db() (Base.metadata.create_all), and the get_db() generator dependency that yields one Session per request and always closes it in a finally block.",
    ])

    doc.add_heading("Auth & Projects services (Milestone 8)", level=2)
    add_bullets(doc, [
        "backend/services/auth_service.py — four narrow custom exceptions (EmailAlreadyRegisteredError, InvalidCredentialsError, InvalidTokenError, UserNotFoundError), all subclasses of ValueError so a generic except ValueError in a controller still catches them. register_user() checks for an existing email before inserting; authenticate_user() looks up by email and bcrypt.checkpw()s the password; create_access_token()/decode_access_token() are the only two functions that touch PyJWT directly, keeping the JWT format an implementation detail of this one file.",
        "backend/services/project_service.py — every public function takes a user_id and internally calls the private _get_owned_project() helper, which is the single place that enforces ‘.filter(Project.id == project_id, Project.owner_id == user_id)’ — get/update/delete all funnel through it, so ownership can't accidentally be forgotten in one of the three. create_project() falls back to a shared EMPTY_DOCUMENT (an empty UmlDocument()) module constant when no initial document is supplied.",
        "backend/api/dependencies/auth.py — get_current_user is the sole auth guard in the codebase: an HTTPBearer security scheme extracts the token, auth_service decodes it and loads the user, and any ValueError from either step becomes a 401. Every route that depends on it gets auth for free; routes that don't include it (currently image.py and codegen.py — see 3.3) run unauthenticated.",
        "backend/api/routes/auth.py + api/controllers/auth_controller.py — /api/auth/register, /login, /logout, /me. The route file only wires HTTP verbs/paths to controller calls; all status-code mapping (409 for duplicate email, 401 for bad credentials, 422 for other ValueErrors, 500 as a last resort) lives in the controller.",
        "backend/api/routes/projects.py + api/controllers/project_controller.py — full CRUD at /api/projects and /api/projects/{id}. The controller's _to_summary()/_to_response() helpers are the only place a UmlDocument gets parsed back out of the stored JSON string for the HTTP layer.",
    ])

    doc.add_heading("Unified UML JSON schema (Milestone 3)", level=2)
    add_bullets(doc, [
        "backend/schemas/uml.py — the single source of truth for the shared schema: Visibility and RelationshipType (str, Enum subclasses so they serialize as plain strings), Parameter, Attribute, Method, Position, Size, UmlClass, Multiplicity, Relationship, and UmlDocument. Cross-field validation lives directly on UmlDocument as a @model_validator(mode=\"after\") — validate_relationship_references() — which checks every relationship's source/destination against the set of class ids in the same document. There is no separate validators.py file; CLAUDE.md's folder-responsibilities section describes one as planned, but the validator was implemented inline instead.",
    ])

    doc.add_heading("Image → JSON pipeline (Milestone 2)", level=2)
    add_bullets(doc, [
        "backend/cv/preprocessor.py — load_image() (cv2.imdecode, raises ValueError on undecodable bytes), to_grayscale(), to_binary() (3x3 Gaussian blur then an inverted binary threshold at 200 — this is why detected shapes are white-on-black internally even though the source image is normal black-on-white). preprocess() composes all three.",
        "backend/cv/shape_detector.py — detect_shapes() returns both ClassBox list and RelationshipLine list. Class boxes come from a hole-based approach (see 3.3): _find_compartment_holes() finds 4-vertex contour holes above a minimum size, _group_into_boxes() clusters holes sharing left/right edges within a 10px tolerance and keeps only groups of 2+ compartments, _build_class_box() derives the outer bounding box plus divider y-coordinates from the group. Lines come from cv2.HoughLinesP, filtered to exclude segments whose midpoint falls inside any detected box, then deduplicated by proximity.",
        "backend/ocr/extractor.py — extract_class_text() splits one ClassBox into up to three horizontal strips using its dividers_y (2 dividers → name/attrs/methods; 1 divider → name/attrs only; 0 → the whole box is treated as just a name). Each non-empty strip goes through _ocr_region(): crop → 12px white border pad → 4x cubic upscale → Otsu threshold → pytesseract with --oem 3 --psm 6 --dpi 300.",
        "backend/parser/text_parser.py — pure string→dataclass parsing, no I/O. parse_class_name() takes the first line that doesn't look like an attribute/method. parse_attribute_line()/parse_method_line() strip a leading +/-/#/~ visibility marker, split on : for type and = for default value (attributes) or on the outermost ( ) for parameters and a trailing : for return type (methods), and reject anything whose name isn't a valid identifier rather than emitting a guess. _OCR_FIXES normalizes a small set of common OCR confusions before any of that parsing happens.",
        "backend/services/image_service.py — the only module that sequences cv → ocr → parser → schemas into one image_to_document(bytes) -> UmlDocument call; see the full walkthrough in 3.3.",
        "backend/api/routes/image.py + api/controllers/image_controller.py — POST /api/image-to-json. The controller validates content-type and non-empty body before calling the service, and maps ValueError (bad/undecodable image) to 422 vs. any other exception to 500.",
    ])

    doc.add_heading("Code generation (Milestone 4)", level=2)
    add_bullets(doc, [
        "backend/generator/language_maps/{python,java,javascript}.py — each exposes TYPE_MAP (schema type → language type, e.g. String → str/String/string), VISIBILITY_PREFIX/VISIBILITY_KEYWORD (e.g. private → _ prefix in Python vs. a private keyword in Java), TEMPLATE_DIR, FILE_EXTENSION, and (Java only) STANDARD_IMPORTS for stdlib types that need an explicit import.",
        "backend/generator/registry.py — REGISTRY: dict[str, LanguageConfig] wires each language name to its language_map module's exports; SUPPORTED_LANGUAGES is just list(REGISTRY.keys()), so it can never drift out of sync with the registry itself.",
        "backend/generator/templates/{python,java,javascript}/class.j2 — one Jinja2 template per language rendering one class per file. All structural decisions (which attributes are static vs. instance, which imports are needed, who the parent class is) are resolved in Python before the template runs; the template itself only branches on those pre-computed flags/lists (e.g. the Python template's @staticmethod / @abstractmethod decorators, its `pass` fallback body when a class has no instance attributes). Method bodies are always a placeholder (`...` in Python) — never generated logic.",
        "backend/services/codegen_service.py — generate_code(document, language) validates the language against the registry, builds one Jinja2 Environment per call (trim_blocks/lstrip_blocks/keep_trailing_newline for clean output), and for each class in the document builds a template context via _build_template_context() (parent lookup by scanning the document's own INHERITANCE relationships, per-attribute/method context dataclasses with the mapped type and prefixed name already computed, cross-class and stdlib import lists) before rendering. Returns {filename: rendered_source}.",
        "backend/api/routes/codegen.py + api/controllers/codegen_controller.py — POST /api/generate-code, GET /api/languages, GET /api/templates. list_templates() just lists the .j2 filenames actually present in each language's template directory on disk, so it can't drift from what templates truly exist.",
    ])

    doc.add_heading("HTTP boundary models", level=2)
    add_bullets(doc, [
        "backend/models/requests.py — GenerateCodeRequest (language re-validated against SUPPORTED_LANGUAGES at the Pydantic level, in addition to codegen_service's own check), RegisterRequest (email must contain @ and a . after it; password must be 8+ chars — both enforced here, before the service layer even runs), LoginRequest, CreateProjectRequest, UpdateProjectRequest (both project fields optional, letting a PUT patch just the name or just the document). ReverseRequest and JsonToMermaidRequest are defined but unused, waiting on Milestones 5/6.",
        "backend/models/responses.py — CodeGenerationResponse, LanguageListResponse, TemplateListResponse, ReverseResponse (also currently doing double duty as the image-to-json response shape), MermaidResponse (unused), ErrorResponse, UserResponse, TokenResponse, ProjectResponse (full document), ProjectSummaryResponse + ClassBoxSummary (the lightweight dashboard-card shape, deliberately excluding the full document), ProjectListResponse.",
    ])

    doc.add_heading("Not built yet (empty directories)", level=2)
    add_bullets(doc, [
        "backend/reverse/ — should hold Python/Java/JavaScript AST parsers (parse(source) -> UmlDocument) and a registry.py. Currently empty.",
        "backend/mermaid/ — should turn a UmlDocument into Mermaid classDiagram text. Currently empty.",
        "No /api/reverse or /api/json-to-mermaid route exists in main.py yet.",
    ])

    # ------------------------------------------------------------------
    # 5. File-by-file: Frontend
    # ------------------------------------------------------------------
    doc.add_heading("5. File-by-file: Frontend", level=1)

    doc.add_heading("App shell, routing & auth state", level=2)
    add_bullets(doc, [
        "frontend/src/main.tsx — the actual composition root: wraps <App /> in BrowserRouter → AuthProvider → ToastProvider → DiagramProvider, in that order, so every page can call useAuthContext(), useToast(), and useDiagramContext() without prop drilling.",
        "frontend/src/App.tsx — the react-router-dom route table: / (HomePage), /login, /register are public; /dashboard and /editor/:projectId are wrapped in both ProtectedRoute and AppShell; any unmatched path redirects to /.",
        "frontend/src/context/AuthContext.tsx — owns the JWT (token), the current AuthUser, and an isLoading flag used only during the initial-mount session restore (it calls GET /api/auth/me with whatever token is in localStorage['umlframe-token'] before deciding whether the user is really still logged in — a stored token isn't trusted until the backend confirms it still decodes). login/register/logout all update localStorage and React state together so they can never drift apart.",
        "frontend/src/components/routing/ProtectedRoute.tsx — renders a loading placeholder while AuthContext's initial session restore is in flight, then either its children or <Navigate to=\"/login\"> (carrying the attempted location in router state so LoginPage can bounce back to it after a successful login).",
        "frontend/src/components/layout/AppShell.tsx + Header.tsx — the persistent chrome (top header + body slot) wrapped around the two authenticated pages only; HomePage/LoginPage/SignupPage render standalone without it.",
    ])

    doc.add_heading("Dashboard (project list)", level=2)
    add_bullets(doc, [
        "frontend/src/pages/DashboardPage.tsx — loads projectsApi.listProjects() once on mount; all search/sort (by last-updated or name) is a client-side useMemo over the already-fetched list, no server-side filtering. Creating a project immediately navigate()s into its editor rather than staying on the dashboard. Deleting asks for confirmation via a Modal before calling deleteProject() and removes the row from local state directly instead of re-fetching the whole list.",
        "frontend/src/components/dashboard/ProjectThumbnail.tsx — renders a miniature, non-interactive preview of a project's class boxes (from the class_boxes summary the backend computes) purely as small positioned rectangles — it does not reuse the real canvas renderer.",
    ])

    doc.add_heading("Editor: canvas, diagram state, and UML components (Milestone 1)", level=2)
    add_bullets(doc, [
        "frontend/src/pages/EditorPage.tsx — loads a project by :projectId param exactly once (a loadedProjectId ref guards against re-fetching on every diagram-state re-render, since useDiagram() returns a new object identity each render), and wires Save/rename to projectsApi.updateProject.",
        "frontend/src/context/DiagramContext.tsx — a thin app-wide provider around useDiagram(), so the canvas, the toolbar, and the editor page all read/write the exact same diagram state instance rather than each holding their own copy.",
        "frontend/src/hooks/useDiagram.ts — the canonical diagram state (classes, relationships, generic shapes) per CLAUDE.md's rule that all canvas state flows through this one hook. Composes useCanvas() (pan/zoom/tool/pending-relationship state) and useSelection() (multi-select set) into one combined return value. Owns toDocument()/loadDocument() — the only two functions that convert between editor state and the wire UmlDocument shape (via umlClassSerializer.ts) — plus id-sequence bookkeeping so class_N/rel_N ids stay monotonic and never collide after loading an existing document. duplicateSelected() deliberately computes new ids outside the setState updater function, because React 18 StrictMode double-invokes updaters in development and doing id generation inside one would double-increment the counters and silently duplicate entries.",
        "frontend/src/hooks/useCanvas.ts — pan/zoom (clamped to MIN_ZOOM/MAX_ZOOM), the active tool (select/pan/uml-class/shape-kind/relationship), snap-to-grid toggle, and the 'armed' source class id while a relationship is mid-creation.",
        "frontend/src/hooks/useSelection.ts — a Set-like list of {kind, id} refs (class/shape/relationship) supporting single-select, additive multi-select, and marquee-select.",
        "frontend/src/hooks/useKeyboardShortcuts.ts — wires Delete/Backspace → deleteSelected(), Ctrl/Cmd+D → duplicateSelected(), etc. at the document level.",
        "frontend/src/components/canvas/Canvas.tsx — the actual pointer-event surface. It is a bounded, finite page (CANVAS_WIDTH x CANVAS_HEIGHT), not an infinitely pannable one — clampPan() keeps the visible page from being panned entirely out of the viewport. A native (non-passive) wheel listener is added manually so ctrl/cmd+wheel zoom can call preventDefault() on the browser's own page-zoom gesture, which React's onWheel can't do since it's passive by default. Renders Grid, an SVG layer of RelationshipEdges, ShapeRenderers, UmlClassBoxes, a SelectionOverlay for the single selected item's resize handles, and a live marquee rectangle while drag-selecting.",
        "frontend/src/components/canvas/Grid.tsx, SelectionOverlay.tsx, ShapeRenderer.tsx — the generic (UML-agnostic) rendering layer: background grid, resize-handle chrome, and the five generic shapes (rectangle/circle/diamond/line/arrow) added via the shape toolbar. This layer has no knowledge of UML semantics, per CLAUDE.md's folder rule.",
        "frontend/src/components/uml/UmlClassBox.tsx (+ AttributeRow.tsx, MethodRow.tsx, ModifierChip.tsx) — the three-compartment class box with inline-editable name/attribute/method rows and modifier chips (static/final/abstract).",
        "frontend/src/components/uml/RelationshipEdge.tsx, RelationshipMarkerDefs.tsx, relationshipStyles.ts — draws all five relationship types as SVG paths between two class boxes' rects, with editable label and multiplicity text directly on the edge.",
        "frontend/src/components/uml/umlClassSerializer.ts — the only place that converts a UmlClassState (editor-internal, with synthetic per-row ids like class_3_attr_1 for React keys) to/from the wire UmlClass shape (attribute/method arrays with no per-item id, snake_case field names like default_value/return_type). Deliberately has no network access, matching the components/uml/ folder rule that it never talks to the backend directly.",
        "frontend/src/utils/{geometry,id,constants}.ts — rect/point math (clamp, snap-to-grid, rect intersection for marquee selection), sequential id generation (class_N/rel_N/shape_N, plus recovering the next sequence number from a loaded document's existing ids), and shared numeric constants (default sizes, zoom bounds, canvas dimensions).",
        "frontend/src/utils/pngExport.ts — exportCanvasAsPng() temporarily re-transforms the canvas content node to frame the full diagram bounds (not just whatever's currently in the viewport) at a fixed pixel ratio before calling html-to-image's toPng(), then restores the original transform in a finally block so the on-screen view is never visibly disturbed.",
    ])

    doc.add_heading("Toolbar: image upload, code generation, export", level=2)
    add_bullets(doc, [
        "frontend/src/components/toolbar/Toolbar.tsx — pure composition: ShapeToolPicker + RelationshipPicker on the left, ZoomControls + ImageUploadButton + ExportPngButton + CodeGenPanel on the right. No logic of its own.",
        "frontend/src/components/toolbar/ImageUploadButton.tsx / ImageUploadModal.tsx — the modal previews the chosen file locally (URL.createObjectURL) before upload, and if the canvas already has content it requires a second confirming click ('Replace & Load') rather than silently overwriting existing work.",
        "frontend/src/components/toolbar/CodeGenPanel.tsx + CodeViewer.tsx — fetches the supported-language list on mount (defaulting to python if available), disables the Generate button until at least one class exists, and shows generated files in a viewer modal.",
        "frontend/src/components/toolbar/{RelationshipPicker,ShapeToolPicker,ZoomControls,ExportPngButton}.tsx — thin controls that just call the corresponding useDiagram()/useCanvas() setters; none hold state of their own.",
    ])

    doc.add_heading("API client layer (frontend/src/api/)", level=2)
    add_bullets(doc, [
        "client.ts — apiFetch<T>(), the single fetch wrapper every other api/*.ts file goes through. Centralizes the base URL (VITE_API_BASE_URL env var, default http://localhost:8000) and error handling: a non-OK response is turned into an ApiError carrying the HTTP status and whatever detail/error message the backend body contained.",
        "authApi.ts, projectsApi.ts, imageApi.ts, codegenApi.ts — one file per backend route group, each translating between the wire (snake_case) shape and a camelCase TypeScript interface at the boundary (e.g. projectsApi's summaryFromWire()/projectFromWire()). No mermaidApi.ts/reverseApi.ts yet — there's nothing on the backend for them to call.",
    ])

    doc.add_heading("Not built yet", level=2)
    add_bullets(doc, [
        "No Mermaid rendering/preview panel (waiting on backend Milestone 6).",
        "No reverse-engineering UI (paste-code-in flow) (waiting on Milestone 5).",
        "No activity-diagram UI (waiting on Milestone 9).",
    ])

    # ------------------------------------------------------------------
    # 6. Status summary
    # ------------------------------------------------------------------
    doc.add_heading("6. Status summary", level=1)
    status_rows = [
        ("#", "Milestone", "Status"),
        ("1", "Frontend UML Editor", "✅ Mostly done"),
        ("2", "Image Processing Pipeline", "🟡 Done, but not perfect — relationship *type* detection isn't implemented (every line imports as a plain association) and OCR accuracy is still being refined"),
        ("3", "Unified UML JSON Schema", "✅ Done"),
        ("4", "Code Generation", "✅ Done"),
        ("5", "Reverse Engineering (code → JSON)", "❌ Not started"),
        ("6", "Diagram Generation (JSON → Mermaid)", "❌ Not started"),
        ("7", "Full Integration (end-to-end tests)", "🟡 Partial (forward pipeline only, scripts/e2e_demo.py)"),
        ("8", "Auth & Projects (multi-user)", "✅ Done"),
        ("9", "Activity Diagram forward pipeline (image → flowchart code)", "❌ Not started (design docs only)"),
    ]
    t3 = doc.add_table(rows=1, cols=3)
    t3.style = "Light Grid Accent 1"
    for i, val in enumerate(status_rows[0]):
        t3.rows[0].cells[i].text = val
    for row_vals in status_rows[1:]:
        row = t3.add_row().cells
        for i, val in enumerate(row_vals):
            row[i].text = val

    # ------------------------------------------------------------------
    # 7. What's left
    # ------------------------------------------------------------------
    doc.add_heading("7. What's left, in order", level=1)
    add_bullets(doc, [
        "Image processing accuracy (M2 follow-up) — teach shape_detector.py to classify arrowhead/diamond-head shape at each line endpoint so relationship type (not just existence) can be inferred, instead of always emitting association.",
        "Reverse Engineering (M5) — write a Python AST parser first (ast module, stdlib), get parse(source) -> UmlDocument working and tested, then do the same for Java and JavaScript. Wire up /api/reverse.",
        "Mermaid generation (M6) — turn a UmlDocument into Mermaid classDiagram text, add /api/json-to-mermaid, add a preview panel on the frontend. Later extension: also pull control-flow out of parsed functions and render it as a Mermaid flowchart (activity diagram from code).",
        "Full integration tests (M7) — once 5 and 6 exist, write an end-to-end reverse-pipeline test (source → JSON → Mermaid) to match the forward-pipeline one that already exists.",
        "Activity Diagram forward pipeline (M9) — the biggest remaining feature: upload a hand-drawn flowchart image, detect start/end/action/decision shapes, OCR the labels, reconstruct real if/while structure, and generate a standalone function (with the same 'never fabricate logic' scaffold rule as the class-diagram generator). Fully designed in CLAUDE.md but zero code written.",
    ], style="List Number")

    doc.add_paragraph(
        "This file is a snapshot as of the time it was generated. If milestones "
        "progress, re-check the actual directories (backend/reverse/, "
        "backend/mermaid/) and route files rather than trusting this doc "
        "blindly — code state is the source of truth."
    )

    return doc


if __name__ == "__main__":
    document = build_doc()
    for style_name in ("Normal", "List Bullet", "List Number"):
        document.styles[style_name].font.size = Pt(11)
    document.save("PROJECT_STATUS.docx")
