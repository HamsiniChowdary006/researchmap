from __future__ import annotations

from pydantic import BaseModel, Field


class Extraction(BaseModel):
    problem: str = Field(description="Research problem addressed by the paper")
    method: str = Field(description="Core method or approach")
    key_results: str = Field(description="Important reported results")
    contribution: str = Field(description="Main contribution")
    limitations: str = Field(description="Limitations stated or evident in the paper")
    techniques_used: list[str] = Field(description="Named techniques, models, or datasets")


class LandscapeCluster(BaseModel):
    name: str
    description: str
    paper_indices: list[int]


class LandscapeRelationship(BaseModel):
    source_cluster: str
    target_cluster: str
    relationship: str


class Landscape(BaseModel):
    clusters: list[LandscapeCluster]
    relationships: list[LandscapeRelationship]
    tensions: list[str]
    open_problems: list[str]
