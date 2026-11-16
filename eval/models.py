"""Validated gold data, source snapshots, and prediction records."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ACTS = ("BNS", "BNSS", "BSA", "Constitution")
INTENTS = ("punishment", "definition", "procedure", "evidence", "rights")
Act = Literal["BNS", "BNSS", "BSA", "Constitution"]
Intent = Literal["punishment", "definition", "procedure", "evidence", "rights", "out_of_scope"]


class Provision(BaseModel):
    """An exact stored chunk ID and its source text, without vectors."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    chunk_id: str = Field(min_length=1)
    act: Act
    text: str = Field(min_length=1)


class GoldItem(BaseModel):
    """A draft becomes eligible for metrics only after explicit human review."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    intent: Intent
    act: Literal["BNS", "BNSS", "BSA", "Constitution", "MULTI", "OUT_OF_SCOPE"]
    expected_chunk_ids: list[str]
    acceptable_alternates: list[str] = Field(default_factory=list)
    answerable: bool
    notes: str = ""
    reviewed: bool = False

    @model_validator(mode="after")
    def validate_support(self) -> "GoldItem":
        """Reject missing support and out-of-scope records with invented sources."""
        if self.answerable != bool(self.expected_chunk_ids):
            raise ValueError("Answerable items need supporting IDs; unanswerable items must have none")
        if not self.answerable and self.acceptable_alternates:
            raise ValueError("Unanswerable items cannot have supporting alternates")
        for values in (self.expected_chunk_ids, self.acceptable_alternates):
            if len(values) != len(set(values)) or any(not value.strip() for value in values):
                raise ValueError("Supporting IDs must be unique and nonblank")
        if self.act == "MULTI" and len(self.expected_chunk_ids) < 2:
            raise ValueError("Multi-provision items require at least two supporting IDs")
        if (self.act == "OUT_OF_SCOPE") != (not self.answerable):
            raise ValueError("OUT_OF_SCOPE items must be unanswerable and vice versa")
        if (self.intent == "out_of_scope") != (not self.answerable):
            raise ValueError("Only unanswerable items use the out_of_scope intent")
        return self


class Draft(BaseModel):
    """Gemini may decline when sampled provisions cannot support a question."""

    question: str
    intent: Intent
    expected_chunk_ids: list[str]
    supported: bool
    notes: str


class Prediction(BaseModel):
    """Retrieved source IDs and an explicit refusal or evaluator confidence score."""

    id: str
    retrieved_chunk_ids: list[str]
    score: float = Field(ge=0, le=100, allow_inf_nan=False)
    refused: bool = False
