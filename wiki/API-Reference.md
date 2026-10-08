# API Reference

All endpoints live under `/api`, with JSON bodies except file uploads (`multipart/form-data`). Every endpoint except register and login needs `Authorization: Bearer <token>`. Interactive docs are at `/docs` on a running backend.

## Errors

| Status | Meaning |
|---|---|
| 422 | Validation failed or the input cannot be processed (structured error body) |
| 401 | Missing or invalid token |
| 404 | Not found, or a project owned by someone else (existence is not leaked) |
| 500 | `{"error": "<message>"}`; tracebacks are never returned |

## Auth

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create an account (email, username, password) |
| POST | `/api/auth/login` | Return a bearer token |
| POST | `/api/auth/logout` | Invalidate the current token |
| GET | `/api/auth/me` | Current user profile |
| POST | `/api/auth/change-password` | `{current_password, new_password}`; invalidates older tokens and returns a fresh one |

## Projects

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/projects` | List own projects. Query: `search`, `sort` (`updated` or `name`), `limit` (1–100), `offset`, `project_type` (`uml` or `activity`) |
| POST | `/api/projects` | Create; `project_type` is fixed at creation |
| GET | `/api/projects/{id}` | Fetch with its diagram |
| PUT | `/api/projects/{id}` | Update name, diagram, activity document, `code_inputs` |
| DELETE | `/api/projects/{id}` | Delete |

## Class-diagram pipeline

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/image-to-json` | Image upload → Unified UML JSON |
| POST | `/api/generate-code` | Unified UML JSON + language → `{"files": {"User.py": "..."}}` |
| POST | `/api/reverse` | Source + language → Unified UML JSON; with `class_name` + `method_name` it also returns `control_flow` |
| POST | `/api/json-to-mermaid` | Mermaid text; `diagram_type` is `class` (default) or `activity` |
| GET | `/api/languages` | Supported target languages |
| GET | `/api/templates` | Available templates |

## Activity-diagram pipeline

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/activity-image-to-json` | Activity image → `ActivityDocument` |
| POST | `/api/generate-activity-code` | `ActivityDocument` + language (+ `function_name`) → standalone function |
| POST | `/api/reverse-control-flows` | Source + language → control flow of every method, with per-method errors |
| POST | `/api/activity-json-to-image` | `ActivityDocument` → re-importable PNG (`{image_base64}`) |

## Example

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"********"}' | jq -r .access_token)

curl -s -X POST localhost:8000/api/generate-code \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"document": {"classes": [], "relationships": []}, "language": "python"}'
```

Request and response field names are authoritative in `backend/models/requests.py` and `responses.py`.
