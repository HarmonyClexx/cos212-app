"""Item-level grading for quizzes.

Every grader returns a score in [0, 1], a correctness flag and structured *detail* that
the frontend turns into targeted feedback (which rows are wrong, where an order first
diverged, which rubric criteria were met...).
"""

from dataclasses import dataclass, field
from typing import Any

from app.content.graphs import GRAPHS
from app.content.schema import Item
from app.engine.graph import Graph
from app.engine.traversal import bfs_order, dfs_order


@dataclass
class ItemGrade:
    correct: bool
    score: float
    feedback: str
    detail: dict[str, Any] = field(default_factory=dict)


def graph_for(item: Item, graphs: dict[str, dict[str, Any]] | None = None) -> Graph | None:
    return Graph.from_spec((GRAPHS if graphs is None else graphs)[item.graph]) if item.graph else None


def expected_answer(item: Item, graphs: dict[str, dict[str, Any]] | None = None) -> Any:
    """The answer in the same shape the client submits."""
    g = graph_for(item, graphs)
    match item.type:
        case "adjacency":
            assert g
            return g.adjacency()
        case "order":
            assert g and item.start
            return (dfs_order if item.algorithm == "dfs" else bfs_order)(g, item.start)
        case "short_answer":
            return {"model_answer": item.model_answer}
        case _:
            return item.answer


def grade_item(item: Item, answer: Any, graphs: dict[str, dict[str, Any]] | None = None) -> ItemGrade:
    try:
        match item.type:
            case "mcq":
                return _grade_mcq(item, answer)
            case "graph_select":
                return _grade_select(item, answer)
            case "adjacency":
                return _grade_adjacency(item, answer, graphs)
            case "order":
                return _grade_order(item, answer, graphs)
    except (TypeError, ValueError, AttributeError, KeyError):
        pass
    return ItemGrade(False, 0.0, "That answer couldn't be read – try again.")


def _grade_mcq(item: Item, answer: Any) -> ItemGrade:
    if not isinstance(answer, list) or any(type(a) is not int for a in answer):
        raise ValueError("Choose an option")
    chosen = set(answer)
    ok = chosen == set(item.answer)
    detail = {}
    if not ok and not item.multi and len(chosen) == 1:
        diagnostic = item.option_feedback.get(next(iter(chosen)))
        if diagnostic:
            detail = {"concepts": [diagnostic.concept], "explanation": diagnostic.explanation}
    # The hint itself travels separately (see hint_content), so it is never shown twice.
    return ItemGrade(ok, 1.0 if ok else 0.0, "Correct!" if ok else "Not quite – have another look.", detail)


def _grade_select(item: Item, answer: Any) -> ItemGrade:
    chosen = {str(a) for a in answer}
    expected = set(item.answer)
    hits, extra, missing = chosen & expected, chosen - expected, expected - chosen
    score = max(0.0, (len(hits) - len(extra)) / len(expected))
    ok = not extra and not missing
    if ok:
        msg = "Correct!"
    elif extra and not missing:
        msg = f"You found them all, but also picked {len(extra)} that don't belong."
    elif missing and not extra:
        msg = f"Good so far – {len(missing)} more to find."
    else:
        verb = "is" if len(missing) == 1 else "are"
        msg = f"{len(extra)} of your picks don't belong, and {len(missing)} {verb} still missing."
    return ItemGrade(ok, round(score, 3), msg, {"extra": sorted(extra), "missing_count": len(missing)})


def _grade_adjacency(item: Item, answer: Any, graphs: dict[str, dict[str, Any]] | None = None) -> ItemGrade:
    g = graph_for(item, graphs)
    assert g
    expected: dict[str, list[str]] = expected_answer(item, graphs)
    chosen = {n: set(answer.get(n, [])) for n in expected}
    wrong = [n for n, nbrs in expected.items() if sorted(chosen[n]) != nbrs]
    score = (len(expected) - len(wrong)) / len(expected)
    ok = not wrong
    msg = "Perfect map!" if ok else f"{len(wrong)} row{'s' if len(wrong) != 1 else ''} still need fixing."
    detail: dict[str, Any] = {"wrong_rows": wrong}
    if not ok:
        rows = {}
        concepts = set()
        for n in wrong:
            missing, extra = set(expected[n]) - chosen[n], chosen[n] - set(expected[n])
            reverse_missing = sum(n in chosen[v] for v in missing) if not g.directed else 0
            incoming_only = sorted(extra & {v for v in expected if n in expected[v]}) if g.directed else []
            rows[n] = {"missing_count": len(missing), "extra": sorted(extra),
                       "reverse_missing_count": reverse_missing, "incoming_only": incoming_only}
            if missing:
                concepts.add("neighbour-omitted")
            if extra:
                concepts.add("non-neighbour-included")
            if reverse_missing:
                concepts.add("undirected-edge-one-way")
            if incoming_only:
                concepts.add("direction-ignored")
        detail.update(
            row_feedback=rows, concepts=sorted(concepts),
            explanation=(
                "Each row lists only vertices reached by arrows leaving that row's vertex. "
                "Incoming arrows belong in their starting vertex's row."
                if g.directed else
                "Each row lists directly connected vertices, not vertices reached through a longer path. "
                "An undirected edge must be recorded in both endpoint rows."
            ),
        )
    return ItemGrade(ok, round(score, 3), msg, detail)


def _grade_order(item: Item, answer: Any, graphs: dict[str, dict[str, Any]] | None = None) -> ItemGrade:
    expected: list[str] = expected_answer(item, graphs)
    got = [str(a) for a in answer]
    prefix = 0
    for e, a in zip(expected, got, strict=False):
        if e != a:
            break
        prefix += 1
    ok = got == expected
    score = prefix / len(expected)
    if ok:
        return ItemGrade(True, 1.0, "Exactly right!")
    detail: dict[str, Any] = {"correct_prefix": prefix}
    if prefix < len(got):
        g = graph_for(item, graphs)
        assert g and item.start
        other_alg = "bfs" if item.algorithm == "dfs" else "dfs"
        other = (bfs_order if other_alg == "bfs" else dfs_order)(g, item.start)
        if got[: prefix + 1] == other[: prefix + 1]:
            detail["looks_like"] = other_alg
            return ItemGrade(False, score, f"Your first {prefix} were right – then it started to look like "
                                           f"{other_alg.upper()} instead of {item.algorithm.upper()}.", detail)
        return ItemGrade(False, score, f"Your first {prefix} were right; vertex #{prefix + 1} is where it went wrong.",
                         detail)
    return ItemGrade(False, score, f"Right so far – but you stopped after {len(got)} of {len(expected)} vertices.",
                     detail)


def public_item(item: Item, graphs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Item as sent to the browser - answers and rubric keywords stripped."""
    data = item.model_dump(exclude={
        "answer", "rubric", "model_answer", "explanation", "hint", "hint2", "focus", "option_feedback",
    })
    data["graph"] = (GRAPHS if graphs is None else graphs)[item.graph] if item.graph else None
    if item.rubric:
        # Criterion-referenced assessment: learners see the criteria, not the keywords.
        data["criteria"] = [c.descriptor for c in item.rubric]
    return data


MAX_HINT_LEVEL = 2


def hint_content(item: Item, level: int) -> dict[str, Any]:
    """Scaffolding for *level* (Design 2.6): 1 = a nudge; 2 = the idea in full plus a visual cue."""
    if level <= 1:
        return {"hint": item.hint, "focus": []}
    return {"hint": item.hint2 or item.explanation, "focus": list(item.focus)}
