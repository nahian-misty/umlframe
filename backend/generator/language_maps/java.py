TYPE_MAP: dict[str, str] = {
    "String": "String",
    "str": "String",
    "int": "int",
    "Integer": "Integer",
    "long": "long",
    "Long": "Long",
    "float": "float",
    "Float": "Float",
    "double": "double",
    "Double": "Double",
    "bool": "boolean",
    "Boolean": "Boolean",
    "void": "void",
    "Object": "Object",
    "List": "List<Object>",
    "ArrayList": "ArrayList<Object>",
    "Map": "Map<Object, Object>",
    "HashMap": "HashMap<Object, Object>",
    "Set": "Set<Object>",
    "HashSet": "HashSet<Object>",
    "UUID": "UUID",
    "Date": "Date",
    "DateTime": "LocalDateTime",
}

STANDARD_IMPORTS: dict[str, str] = {
    "List<Object>": "java.util.List",
    "ArrayList<Object>": "java.util.ArrayList",
    "Map<Object, Object>": "java.util.Map",
    "HashMap<Object, Object>": "java.util.HashMap",
    "Set<Object>": "java.util.Set",
    "HashSet<Object>": "java.util.HashSet",
    "UUID": "java.util.UUID",
    "Date": "java.util.Date",
    "LocalDateTime": "java.time.LocalDateTime",
}

VISIBILITY_KEYWORD: dict[str, str] = {
    "public": "public",
    "protected": "protected",
    "private": "private",
    "package": "",
}

VISIBILITY_PREFIX: dict[str, str] = {
    "public": "",
    "protected": "",
    "private": "",
    "package": "",
}

FILE_EXTENSION = ".java"
TEMPLATE_DIR = "java"
