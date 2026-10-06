TYPE_MAP: dict[str, str] = {
    "String": "str",
    "int": "int",
    "Integer": "int",
    "long": "int",
    "Long": "int",
    "float": "float",
    "Float": "float",
    "double": "float",
    "Double": "float",
    "boolean": "bool",
    "bool": "bool",
    "Boolean": "bool",
    "void": "None",
    "Object": "object",
    "List": "list",
    "ArrayList": "list",
    "Map": "dict",
    "HashMap": "dict",
    "Set": "set",
    "HashSet": "set",
    "UUID": "UUID",
    "Date": "date",
    "DateTime": "datetime",
}

VISIBILITY_PREFIX: dict[str, str] = {
    "public": "",
    "protected": "_",
    "private": "__",
    "package": "_",
}

VISIBILITY_KEYWORD: dict[str, str] = {
    "public": "",
    "protected": "",
    "private": "",
    "package": "",
}

FILE_EXTENSION = ".py"
TEMPLATE_DIR = "python"

# Body printed for a method nobody has implemented (also used for abstract methods).
STUB_BODY_LINES: list[str] = ["..."]
