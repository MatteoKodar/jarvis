from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Claim(Strict):
    text: str = Field(max_length=1200)
    kind: Literal["FAKTA", "ANTAGANDE", "TESTRESULTAT"]
    source_ids: list[str] = Field(default_factory=list, max_length=5)

class Candidate(Strict):
    title: str = Field(max_length=150)
    problem: str = Field(max_length=1500)
    audience: str = Field(max_length=500)
    solution: str = Field(max_length=1500)
    competitors: str = Field(max_length=1000)
    distribution: str = Field(max_length=1000)
    payment_signals: str = Field(max_length=1000)
    costs: str = Field(max_length=1000)
    risks: str = Field(max_length=1000)
    questions: str = Field(max_length=1000)
    willingness: int = Field(ge=0, le=5)
    reach: int = Field(ge=0, le=5)
    test_cost: int = Field(ge=0, le=5)
    automation: int = Field(ge=0, le=5)
    advantage: int = Field(ge=0, le=5)
    evidence: Literal["Saknas", "Svagt", "Måttligt", "Starkt"]

class AgentResult(Strict):
    summary: str = Field(max_length=10000)
    rationale: str = Field(max_length=2000)
    proposed_agent: Literal["researcher", "analyst", "strategist", "developer", "designer", "marketer", "sales", "finance", "critic"] = "researcher"
    next_action: str = Field(default="Granska befintligt underlag", max_length=2000)
    risks: str = Field(default="Underlag behöver verifieras.", max_length=2000)
    alternatives: str = Field(default="Avstå eller avgränsa uppdraget.", max_length=2000)
    claims: list[Claim] = Field(default_factory=list, max_length=12)
    candidates: list[Candidate] = Field(default_factory=list, max_length=5)
    blocked: bool = False

