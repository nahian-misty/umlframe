# Unified UML JSON

The canonical representation for every subsystem. Defined in `backend/schemas/uml.py` and `shared/schema/uml_schema.json`.

```json
{
  "classes": [
    {
      "id": "class_1",
      "name": "User",
      "kind": "class",
      "attributes": [
        {"name": "email", "datatype": "String", "visibility": "private",
         "default_value": null, "static": false, "final": false}
      ],
      "methods": [
        {"name": "login", "visibility": "public", "parameters": [],
         "return_type": "void", "static": false, "abstract": false}
      ],
      "position": {"x": 100, "y": 200},
      "size": {"width": 160, "height": 120}
    }
  ],
  "relationships": [
    {"id": "rel_1", "source": "class_1", "destination": "class_2",
     "type": "association",
     "multiplicity": {"source": "1", "destination": "*"}, "label": ""}
  ]
}
```

## Class

| Field | Type | Notes |
|---|---|---|
| `id` | string | `class_N` |
| `name` | string | PascalCase |
| `kind` | enum | `class` (default), `abstract`, `interface` |
| `attributes` | Attribute[] | ordered |
| `methods` | Method[] | ordered |
| `position`, `size` | objects | canvas geometry |

`kind` is shown as `«abstract»` / `«interface»` in the editor, becomes a Mermaid annotation and picks the declaration keyword in generated code (Java `interface` / `abstract class`, Python `ABC`, JavaScript constructor guard).

## Attribute / Method

- Attribute: `name`, `datatype`, `visibility` (`public`, `private`, `protected`, `package`), `default_value`, `static`, `final`.
- Method: `name`, `visibility`, `parameters` (`{name, datatype}[]`), `return_type`, `static`, `abstract`.

## Relationship

`type` is one of `association`, `aggregation`, `composition`, `inheritance`, `dependency`. `source` and `destination` must reference existing class ids, which the validator enforces. An inheritance edge to an interface means `implements`.

## ActivityDocument

A sibling schema (`backend/schemas/activity.py`), not an extension.

- `nodes`: `id`, `type` (`start`, `end`, `action`, `decision`, `fork`, `join`), `label`, `position`, `size`.
- `edges`: `id`, `source`, `target`, `label` (guard text such as `yes` / `no`).
- Validation: edge references resolve, exactly one `start`, at least one `end`. Whether a graph can be turned into code is decided later by `activity_structuring.py`, not by the schema.
