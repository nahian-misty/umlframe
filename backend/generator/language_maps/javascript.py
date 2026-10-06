TYPE_MAP: dict[str, str] = {
    "String": "string",
    "str": "string",
    "int": "number",
    "Integer": "number",
    "long": "number",
    "float": "number",
    "double": "number",
    "boolean": "boolean",
    "bool": "boolean",
    "Boolean": "boolean",
    "void": "void",
    "Object": "Object",
    "List": "Array",
    "ArrayList": "Array",
    "Map": "Object",
    "HashMap": "Object",
    "Set": "Set",
    "UUID": "string",
    "Date": "Date",
    "DateTime": "Date",
}

VISIBILITY_KEYWORD: dict[str, str] = {
    "public": "",
    "protected": "",
    "private": "",
    "package": "",
}

VISIBILITY_PREFIX: dict[str, str] = {
    "public": "",
    "protected": "",
    "private": "#",
    "package": "",
}

FILE_EXTENSION = ".js"
TEMPLATE_DIR = "javascript"

# Body printed for a method nobody has implemented (also used for abstract methods).
STUB_BODY_LINES: list[str] = ["throw new Error('Not implemented');"]
