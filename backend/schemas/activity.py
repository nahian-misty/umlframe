from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, model_validator

from backend.schemas.uml import Position, Size


class ActivityNodeType(str, Enum):
    START = "start"
    END = "end"
    ACTION = "action"
    DECISION = "decision"
    FORK = "fork"
    JOIN = "join"


class ActivityNode(BaseModel):
    id: str
    type: ActivityNodeType
    label: str = ""
    position: Position
    size: Size


class ActivityEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""


class ActivityDocument(BaseModel):
    nodes: list[ActivityNode] = []
    edges: list[ActivityEdge] = []

    @model_validator(mode="after")
    def validate_structure(self) -> ActivityDocument:
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge '{edge.id}' references unknown source node '{edge.source}'")
            if edge.target not in node_ids:
                raise ValueError(f"Edge '{edge.id}' references unknown target node '{edge.target}'")

        starts = [n for n in self.nodes if n.type == ActivityNodeType.START]
        if len(starts) != 1:
            raise ValueError(f"ActivityDocument must have exactly one START node, found {len(starts)}")

        if not any(n.type == ActivityNodeType.END for n in self.nodes):
            raise ValueError("ActivityDocument must have at least one END node")

        return self
