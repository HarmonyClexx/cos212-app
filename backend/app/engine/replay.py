"""Server-side grading of an interactive DFS trace.

The client streams the learner's raw action log (every click, including wrong ones,
plus hint requests and "show me" reveals). We replay it against the canonical trace,
so XP, stars and mastery can never be spoofed by a modified client.

Mistakes are classified so analytics (and badges) can tell *why* a learner went wrong -
which maps directly onto the misconceptions identified in the Analysis phase.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from app.engine.graph import Graph
from app.engine.traversal import Event, dfs_trace

MistakeKind = Literal[
    "wrong_order",  # picked an unvisited neighbour, but not the alphabetically-first one
    "not_adjacent",  # jumped to a node with no edge from the current node
    "already_visited",  # tried to re-enter a visited node (the cycle trap)
    "should_backtrack",  # dead end reached, learner tried to move instead of popping
    "premature_backtrack",  # popped while unexplored neighbours remained
]


# Score deductions, in units of one step. A hint is cheaper than a mistake, so asking beats guessing.
MISTAKE_COST = 0.25
HINT_COST = 0.15


class TraceAction(BaseModel):
    kind: Literal["visit", "backtrack", "hint", "reveal"]
    node: str | None = None


@dataclass
class TraceResult:
    completed: bool
    total_steps: int
    correct_steps: int
    mistakes: int
    hints: int
    reveals: int
    breakdown: dict[str, int] = field(default_factory=dict)
    score: float = 0.0
    stars: int = 0


def classify(g: Graph, expected: Event, prev: Event, action: TraceAction) -> MistakeKind:
    current = prev.stack[-1]
    if action.kind == "backtrack":
        return "premature_backtrack"
    node = action.node or ""
    if expected.kind == "backtrack":
        return "should_backtrack"
    if node in prev.visited:
        return "already_visited"
    if node not in g.neighbours(current):
        return "not_adjacent"
    return "wrong_order"


def is_correct(expected: Event, action: TraceAction) -> bool:
    if action.kind == "backtrack":
        return expected.kind == "backtrack"
    return expected.kind == "visit" and action.node == expected.node


def grade_trace(g: Graph, start: str, actions: list[TraceAction], auto_backtrack: bool) -> TraceResult:
    events = dfs_trace(g, start)
    # Steps the learner is responsible for. The initial visit(start) is given.
    required = [i for i, e in enumerate(events) if i > 0 and not (auto_backtrack and e.kind == "backtrack")]

    pos = 0  # index into `required`
    correct = mistakes = hints = reveals = 0
    breakdown: Counter[str] = Counter()

    for action in actions:
        if pos >= len(required):
            break
        if action.kind == "hint":
            hints += 1
            continue
        idx = required[pos]
        expected = events[idx]
        # State the learner is looking at. In auto-backtrack mode this already includes
        # any automatic pops that precede the step, because those are events too.
        prev = events[idx - 1]
        if action.kind == "reveal":
            reveals += 1
            pos += 1
            continue
        if is_correct(expected, action):
            correct += 1
            pos += 1
        else:
            mistakes += 1
            breakdown[classify(g, expected, prev, action)] += 1

    total = len(required)
    completed = pos >= total
    raw = (correct - MISTAKE_COST * mistakes - HINT_COST * hints) / total if total else 1.0
    score = round(max(0.0, min(1.0, raw)), 3) if completed else 0.0

    if not completed:
        stars = 0
    elif mistakes == 0 and hints == 0 and reveals == 0:
        stars = 3
    elif reveals == 0 and score >= 0.7:
        stars = 2
    else:
        stars = 1

    return TraceResult(
        completed=completed,
        total_steps=total,
        correct_steps=correct,
        mistakes=mistakes,
        hints=hints,
        reveals=reveals,
        breakdown=dict(breakdown),
        score=score,
        stars=stars,
    )
