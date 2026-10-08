# Testing

The suite has 700+ tests and finishes in about a minute. Run it from the repo root:

```bash
pytest
ruff check backend/
mypy backend/
cd frontend && npm run typecheck && npm run lint
```

## Strategy

Because modules talk only through the Unified UML JSON (or `ActivityDocument`), each is tested alone, working from the inside out: schemas, then generators, parsers and structuring, then services, then routes, then integration.

| Area | Approach |
|---|---|
| `schemas`, `generator` | Full coverage; template tests assert the entire rendered string |
| `services` | Unit tests per method; domain modules mocked at the boundary |
| `api/controllers` | HTTP error mapping with mocked services |
| `api/routes` | Integration tests for success and error paths |
| `cv`, `ocr` | Fixture images in `tests/fixtures/` |
| `reverse` | Fixture source files per language |
| `auth`, `projects` | In-memory SQLite; accessing another user's project must 404 |
| `integration` | Image → JSON → code, source → JSON → Mermaid, and a codegen/reverse round trip |

## Rules

- Tests build real Pydantic objects; the schema models are never mocked.
- No network access, and nothing is written outside `tmp_path`.
- pytest functions only, no `unittest.TestCase`.
- OCR-dependent tests are skipped when Tesseract is missing.
