from typing import Any, Literal

from pydantic import BaseModel, Field

ActivityKind = Literal["maze", "inspect", "represent", "demo", "trace", "compare", "quiz"]
ItemType = Literal["mcq", "graph_select", "adjacency", "order", "short_answer"]


class Objective(BaseModel):
    id: int
    title: str
    bloom: str  # CS2023 skill level
    verb: str
    statement: str
    module: str


class Criterion(BaseModel):
    """Criterion-referenced rubric line for short answers.

    A criterion is met when the answer contains at least one phrase from *any_of*.
    """

    id: str
    descriptor: str
    any_of: list[str]


class Item(BaseModel):
    id: str
    type: ItemType
    objective: int
    prompt: str
    graph: str | None = None
    options: list[str] | None = None
    multi: bool = False
    select: Literal["nodes", "edges"] | None = None
    algorithm: Literal["dfs", "bfs"] | None = None
    start: str | None = None
    answer: Any = None  # mcq -> list[int]; graph_select -> list[str]; others derived from graph
    rubric: list[Criterion] | None = None
    pass_criteria: int = 2
    model_answer: str | None = None
    hint: str  # tier-1 nudge after the first wrong attempt
    explanation: str  # tier-2 explanation / shown with the answer


class Assessment(BaseModel):
    id: str
    mode: Literal["formative", "summative"]
    items: list[Item]
    pass_mark: float = 0.6


class Activity(BaseModel):
    id: str
    kind: ActivityKind
    title: str
    summary: str
    objective: int | None = None
    xp: int
    config: dict[str, Any] = Field(default_factory=dict)


class Module(BaseModel):
    slug: str
    order: int
    title: str
    tagline: str
    story: str  # fantasy framing (Malone & Lepper)
    objective: int | None
    outcome: str  # "By the end you can..." (Gagne event 2: inform learners of objectives)
    icon: str
    activities: list[Activity]
