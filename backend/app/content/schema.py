from typing import Any, Literal

from pydantic import BaseModel, Field

ActivityKind = Literal["lesson", "maze", "inspect", "represent", "demo", "trace", "compare", "quiz"]
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
    nudge: str = ""  # question shown while the criterion is unmet: points at the gap, never the wording


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
    reflection_prompt: str | None = None
    # Progressive scaffolding (Design 2.6). Each level is reached by asking for a hint or by a
    # wrong try, whichever comes first; the worked answer itself needs three tries.
    hint: str  # level 1: a short nudge
    hint2: str | None = None  # level 2: the idea explained in full - still not the answer
    focus: list[str] = Field(default_factory=list)  # level 2 visual cue: vertices to ring on the graph
    explanation: str  # worked explanation, shown with the answer (once correct or revealed)


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
    order: int  # position within its track
    title: str
    tagline: str
    story: str  # fantasy framing (Malone & Lepper)
    objective: int | None
    outcome: str  # "By the end you can..." (Gagne event 2: inform learners of objectives)
    icon: str
    activities: list[Activity]
    # "course" = the intro course (explanation first); "game" = the Labyrinth that puts it to work.
    track: Literal["course", "game"] = "game"
    lesson: str | None = None  # intro-course activity that teaches this module's ideas


# --- intro course ------------------------------------------------------------------------------

class LessonCheck(BaseModel):
    """A retrieval-practice question inside a lesson. Ungraded: it gates the next page, nothing else.

    Every option carries its own explanation, so a wrong pick is answered with *why* it is wrong.
    """

    id: str
    prompt: str
    options: list[str]
    answer: int
    why: list[str]


class LessonFigure(BaseModel):
    kind: Literal["graph", "neighbours", "representation", "stack", "queue", "trace", "orders"]
    graphs: list[str] = Field(default_factory=list)  # graph ids; "graph" shows them side by side
    captions: list[str] = Field(default_factory=list)
    highlight: list[str] = Field(default_factory=list)  # vertex ids and edge ids ("A-B") to emphasise
    start: str | None = None
    algorithm: Literal["dfs", "bfs"] = "dfs"
    views: list[Literal["list", "matrix"]] = Field(default_factory=lambda: ["list", "matrix"])


class LessonPage(BaseModel):
    id: str
    title: str
    body: str  # paragraphs; "- " bullets; "1. " steps; **bold**, *italic*, `code`
    code: str | None = None  # pseudocode
    figure: LessonFigure | None = None
    check: LessonCheck | None = None


class Lesson(BaseModel):
    id: str
    objective: int | None
    minutes: int
    pages: list[LessonPage]
    recap: list[str]  # "In a nutshell" (Gagne event 9: enhance retention)
    practice: str  # slug of the game module that puts this lesson to work

    def checks(self) -> list[LessonCheck]:
        return [p.check for p in self.pages if p.check]
