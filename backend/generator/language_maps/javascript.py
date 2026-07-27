TYPE_MAP: dict[str, str] = {
    "String": "string",
    "str": "string",
    "int": "number",
    "Integer": "number",
    "long": "number",
    "float": "number",
    "double": "number",
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
