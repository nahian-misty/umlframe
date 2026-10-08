# Extending UMLFrame

Extension is by addition. These steps should not require editing existing parsers, generators or the schema.

## Add a target language (code generation)

1. Type map in `backend/generator/language_maps/<language>.py`.
2. Templates in `backend/generator/templates/<language>/` (`class.j2`, and `activity.j2` for activity output).
3. Register it in `backend/generator/registry.py`.
4. Tests in `tests/generator/test_<language>.py`.
5. `/api/languages` picks it up from the registry.

## Add a source language (reverse engineering)

1. `backend/reverse/<language>/parser.py` exposing `parse(source) -> UmlDocument` and optionally `extract_control_flow(source, class_name, method_name) -> ActivityDocument`.
2. Register it in `backend/reverse/registry.py`.
3. Tests in `tests/reverse/` using fixture sources.

## Add an API endpoint

1. Route in `backend/api/routes/<group>.py`: URL and method only.
2. Controller in `backend/api/controllers/`: parse the request model, call one service method, map exceptions.
3. Request and response models in `backend/models/`.
4. Service logic in `backend/services/`.
5. Route integration test and controller unit test.

## Add a relationship type

This is a schema change, so avoid it. It touches `uml_schema.json`, `RelationshipType`, the frontend types, and the cv, parser, mermaid, generator (per language) and reverse (per language) modules, plus their tests.

## Conventions

- Python 3.11+, type hints everywhere, Ruff with line length 100, `snake_case.py` modules.
- React functional components, TypeScript strict, `PascalCase.tsx` components, `useX.ts` hooks.
- IDs are `class_<n>` and `rel_<n>`; JSON fields are `snake_case`; API paths are `kebab-case`.
- Branches: `feature/<milestone>-<description>`, `fix/<description>`, `docs/<description>`.
