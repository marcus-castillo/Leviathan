"""Pydantic response models for the graph API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str  # node type: Case / Judge / Court / LegalTopic
    name: str | None = None
    attrs: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    rel: str


class GraphPayload(BaseModel):
    """Cytoscape-friendly node/edge lists."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    disclaimer: str


class CaseGraph(GraphPayload):
    focus: str
    influence: dict | None = None


class JudgeGraph(GraphPayload):
    judge_id: str
    influence: dict | None = None
    paths: list[list[str]] = Field(default_factory=list)


class ClusterResult(BaseModel):
    communities: dict
    statistical_grouping: dict
    disclaimer: str
