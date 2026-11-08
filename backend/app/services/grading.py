"""Item-level grading for quizzes.

Every grader returns a score in [0, 1], a correctness flag and structured *detail* that
the frontend turns into targeted feedback (which rows are wrong, where an order first
diverged, which rubric criteria were met...).
"""

import re
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


def graph_for(item: Item) -> Graph | None:
    return Graph.from_spec(GRAPHS[item.graph]) if item.graph else None


def expected_answer(item: Item) -> Any:
    """The answer in the same shape the client submits."""
    g = graph_for(item)
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


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower())


def grade_item(item: Item, answer: Any) -> ItemGrade:
    try:
        match item.type:
            case "mcq":
                return _grade_mcq(item, answer)
            case "graph_select":
                return _grade_select(item, answer)
            case "adjacency":
                return _grade_adjacency(item, answer)
            case "order":
                return _grade_order(item, answer)
            case "short_answer":
                return _grade_short(item, answer)
    except (TypeError, ValueError, AttributeError, KeyError):
        pass
    return ItemGrade(False, 0.0, "That answer couldn't be read – try again.")


def _grade_mcq(item: Item, answer: Any) -> ItemGrade:
    chosen = {int(a) for a in (answer if isinstance(answer, list) else [answer])}
    ok = chosen == set(item.answer)
    return ItemGrade(ok, 1.0 if ok else 0.0, "Correct!" if ok else item.hint)


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
        msg = item.hint
    return ItemGrade(ok, round(score, 3), msg, {"extra": sorted(extra), "missing_count": len(missing)})


def _grade_adjacency(item: Item, answer: Any) -> ItemGrade:
    expected: dict[str, list[str]] = expected_answer(item)
    wrong = [n for n, nbrs in expected.items() if sorted(set(answer.get(n, []))) != nbrs]
    score = (len(expected) - len(wrong)) / len(expected)
    ok = not wrong
    msg = "Perfect map!" if ok else f"{len(wrong)} row{'s' if len(wrong) != 1 else ''} still need fixing."
    return ItemGrade(ok, round(score, 3), msg, {"wrong_rows": wrong})


def _grade_order(item: Item, answer: Any) -> ItemGrade:
    expected: list[str] = expected_answer(item)
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
        g = graph_for(item)
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


def _grade_short(item: Item, answer: Any) -> ItemGrade:
    text = _norm_text(str(answer))
    assert item.rubric
    met = [c for c in item.rubric if any(k in text for k in c.any_of)]
    criteria = [{"id": c.id, "descriptor": c.descriptor, "met": c in met} for c in item.rubric]
    words = len(text.split())
    score = len(met) / len(item.rubric)
    ok = len(met) >= item.pass_criteria and words >= 8
    if words < 8:
        msg = "Say a little more – aim for at least one full sentence."
    elif len(met) == len(item.rubric):
        msg = "Distinction-level answer: you covered every criterion."
    elif ok:
        msg = f"Pass – you met {len(met)} of {len(item.rubric)} criteria. Can you cover the rest?"
    else:
        msg = f"You met {len(met)} of {len(item.rubric)} criteria; you need {item.pass_criteria} to pass."
    return ItemGrade(ok, round(score, 3), msg, {"criteria": criteria})


def public_item(item: Item) -> dict[str, Any]:
    """Item as sent to the browser - answers and rubric keywords stripped."""
    data = item.model_dump(exclude={"answer", "rubric", "model_answer", "explanation", "hint"})
    data["graph"] = GRAPHS[item.graph] if item.graph else None
    if item.rubric:
        # Criterion-referenced assessment: learners see the criteria, not the keywords.
        data["criteria"] = [c.descriptor for c in item.rubric]
    return data
