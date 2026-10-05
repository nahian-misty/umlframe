from typing import Literal

from pydantic import BaseModel, Field

ProjectType = Literal["uml", "activity"]
DEFAULT_PROJECT_TYPE: ProjectType = "uml"

MAX_SOURCE_LENGTH = 200_000
MAX_FIELD_LENGTH = 255


class CodeToUmlInput(BaseModel):
    language: str = Field(default="python", max_length=MAX_FIELD_LENGTH)
    source: str = Field(default="", max_length=MAX_SOURCE_LENGTH)


class CodeToActivityInput(BaseModel):
    language: str = Field(default="python", max_length=MAX_FIELD_LENGTH)
    class_name: str = Field(default="", max_length=MAX_FIELD_LENGTH)
    method_name: str = Field(default="", max_length=MAX_FIELD_LENGTH)
    source: str = Field(default="", max_length=MAX_SOURCE_LENGTH)


class CodeInputs(BaseModel):
    """Source text the user pasted into the two code-input tabs, kept so a project reopens
    with its code as well as its diagram. Workspace state, not part of the Unified UML JSON."""

    code_to_uml: CodeToUmlInput = Field(default_factory=CodeToUmlInput)
    code_to_activity: CodeToActivityInput = Field(default_factory=CodeToActivityInput)
