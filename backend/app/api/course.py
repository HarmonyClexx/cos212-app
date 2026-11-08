"""Course content, activity submission and quiz-attempt lifecycle.

Quiz attempts are server-side sessions:
    POST /activities/{id}/attempts      -> open an attempt, receive sanitised items
    POST /attempts/{aid}/check          -> (formative only) grade one item, tiered feedback
    POST /attempts/{aid}/finish         -> close, score, award XP / badges / mastery
so the number of tries per item - which drives the scaffolding - is recorded by the
server, not trusted from the browser.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.content.assessments import ASSESSMENTS
from app.content.course import ACTIVITIES, MODULES_BY_SLUG, OBJECTIVES
from app.content.graphs import GRAPHS
from app.content.schema import Activity, Module
from app.core.db import get_db
from app.core.security import get_current_user
from app.engine.graph import Graph
from app.engine.replay import TraceAction, grade_trace
from app.models import Attempt, User
from app.services.gamification import record_result, stars_for_score
from app.services.grading import expected_answer, grade_item, public_item
from app.services.progress import mastery_map, mastery_report, module_states, progress_map, recommendations

router = APIRouter(tags=["course"])

LESSON_KINDS = {"inspect", "represent", "demo", "compare"}
INSPECT_CHECKLIST = {"vertex", "edge", "directed", "directed-edge", "degree"}
FORMATIVE_TRY_CREDIT = {1: 1.0, 2: 0.7, 3: 0.4}


# --- helpers ---------------------------------------------------------------------------------

def _resolve_config(activity: Activity) -> dict[str, Any]:
    cfg = dict(activity.config)
    for key in ("graph", "directed_graph"):
        if key in cfg:
            cfg[key] = GRAPHS[cfg[key]]
    if activity.kind == "quiz":
        a = ASSESSMENTS[cfg["assessment"]]
        cfg.update(mode=a.mode, item_count=len(a.items), pass_mark=a.pass_mark)
    return cfg


def _module_payload(m: Module) -> dict[str, Any]:
    return {
        "slug": m.slug, "order": m.order, "title": m.title, "tagline": m.tagline, "story": m.story,
        "objective": m.objective, "outcome": m.outcome, "icon": m.icon,
        "activities": [{**a.model_dump(), "config": _resolve_config(a)} for a in m.activities],
    }


def _get_activity(activity_id: str, user: User, db: Session) -> tuple[Module, Activity]:
    if activity_id not in ACTIVITIES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown activity")
    module, activity = ACTIVITIES[activity_id]
    states = module_states(progress_map(db, user))
    state = next(a for m in states for a in m["activities"] if a["id"] == activity_id)
    if not state["unlocked"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Finish the earlier activities first")
    return module, activity


# --- content -----------------------------------------------------------------------------------

@router.get("/objectives")
def objectives() -> list[dict[str, Any]]:
    return [o.model_dump() for o in OBJECTIVES]


@router.get("/modules")
def list_modules(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return module_states(progress_map(db, user))


@router.get("/modules/{slug}")
def get_module(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    m = MODULES_BY_SLUG.get(slug)
    if m is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown module")
    state = next(s for s in module_states(progress_map(db, user)) if s["slug"] == slug)
    if not state["unlocked"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This module is still locked")
    payload = _module_payload(m)
    by_id = {a["id"]: a for a in state["activities"]}
    for a in payload["activities"]:
        a["state"] = by_id[a["id"]]
    return payload


# --- non-quiz activities -------------------------------------------------------------------

class SubmitIn(BaseModel):
    actions: list[TraceAction] | None = None
    data: dict[str, Any] | None = None


@router.post("/activities/{activity_id}/submit")
def submit(activity_id: str, body: SubmitIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict[str, Any]:
    _, activity = _get_activity(activity_id, user, db)
    cfg = activity.config
    data = body.data or {}

    if activity.kind == "trace":
        if body.actions is None:
            raise HTTPException(422, "actions required")
        g = Graph.from_spec(GRAPHS[cfg["graph"]])
        r = grade_trace(g, cfg["start"], body.actions, auto_backtrack=cfg.get("auto_backtrack", True))
        result = r.__dict__
        reward = record_result(
            db, user, activity, kind="trace", completed=r.completed, score=r.score, stars=r.stars,
            payload={"actions": [a.model_dump() for a in body.actions]}, result=result,
            objective_scores={activity.objective: r.score} if r.completed and activity.objective else None,
        )
        return {"result": result, "reward": reward}

    if activity.kind == "maze":
        g = Graph.from_spec(GRAPHS[cfg["graph"]])
        path = [str(p) for p in data.get("path", [])]
        valid = (len(path) >= 2 and path[0] == cfg["start"] and path[-1] == cfg["goal"]
                 and all(b in g.neighbours(a) for a, b in zip(path, path[1:], strict=False)))
        if not valid:
            raise HTTPException(422, "That path doesn't reach the lair")
        result = {"moves": len(path) - 1, "rooms_visited": len(set(path))}
        reward = record_result(db, user, activity, kind="maze", completed=True, score=1.0, stars=3,
                               payload={"path": path}, result=result)
        return {"result": result, "reward": reward}

    if activity.kind in LESSON_KINDS:
        if activity.kind == "inspect" and not INSPECT_CHECKLIST <= set(data.get("discovered", [])):
            raise HTTPException(422, "Finish the discovery checklist first")
        reward = record_result(db, user, activity, kind="lesson", completed=True, score=1.0, stars=3,
                               payload=data, result={})
        return {"result": {}, "reward": reward}

    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quizzes are submitted through attempts")


# --- quiz attempts ------------------------------------------------------------------------------

class CheckIn(BaseModel):
    item_id: str
    answer: Any = None
    reveal: bool = False


class FinishIn(BaseModel):
    answers: dict[str, Any] | None = None


def _open_attempt(aid: int, user: User, db: Session) -> tuple[Attempt, Activity]:
    att = db.get(Attempt, aid)
    if att is None or att.user_id != user.id or att.kind != "quiz":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown attempt")
    if att.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is already finished")
    return att, ACTIVITIES[att.activity_id][1]


@router.post("/activities/{activity_id}/attempts", status_code=status.HTTP_201_CREATED)
def start_attempt(activity_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict[str, Any]:
    _, activity = _get_activity(activity_id, user, db)
    if activity.kind != "quiz":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a quiz")
    assessment = ASSESSMENTS[activity.config["assessment"]]
    att = Attempt(user_id=user.id, activity_id=activity.id, kind="quiz", status="open",
                  payload={"items": {}}, result={})
    db.add(att)
    db.commit()
    return {"attempt_id": att.id, "mode": assessment.mode, "pass_mark": assessment.pass_mark,
            "items": [public_item(i) for i in assessment.items]}


@router.post("/attempts/{aid}/check")
def check_item(aid: int, body: CheckIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict[str, Any]:
    att, activity = _open_attempt(aid, user, db)
    assessment = ASSESSMENTS[activity.config["assessment"]]
    if assessment.mode != "formative":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No feedback during the final trial")
    item = next((i for i in assessment.items if i.id == body.item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown item")

    items = dict(att.payload.get("items", {}))
    st = dict(items.get(item.id, {"tries": 0, "correct": False, "revealed": False, "type": item.type}))
    if st["correct"] or st["revealed"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "Item already resolved")

    if body.reveal:
        if st["tries"] < 3:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Have three goes before asking for the answer")
        st["revealed"] = True
        grade = None
    else:
        grade = grade_item(item, body.answer)
        st["tries"] += 1
        st["correct"] = grade.correct
        st["last_score"] = grade.score
    items[item.id] = st
    att.payload = {**att.payload, "items": items}
    db.commit()

    # Progressive scaffolding (Design 2.6): hint -> explanation -> worked answer.
    tier = 0 if grade and grade.correct else min(st["tries"], 3)
    resp: dict[str, Any] = {
        "item_id": item.id, "tries": st["tries"], "correct": bool(grade and grade.correct),
        "score": grade.score if grade else 0.0, "feedback": grade.feedback if grade else "Here's the worked answer.",
        "detail": grade.detail if grade else {}, "tier": tier, "can_reveal": not st["correct"] and st["tries"] >= 3,
    }
    if tier >= 1:
        resp["hint"] = item.hint
    if tier >= 2 or (grade and grade.correct) or body.reveal:
        resp["explanation"] = item.explanation
    if body.reveal or (grade and grade.correct):
        resp["answer"] = expected_answer(item)
    return resp


@router.post("/attempts/{aid}/finish")
def finish_attempt(aid: int, body: FinishIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> dict[str, Any]:
    att, activity = _open_attempt(aid, user, db)
    assessment = ASSESSMENTS[activity.config["assessment"]]
    per_objective: dict[int, list[float]] = {}
    review: list[dict[str, Any]] = []

    if assessment.mode == "formative":
        state = att.payload.get("items", {})
        for item in assessment.items:
            st = state.get(item.id, {})
            credit = 0.0 if st.get("revealed") or not st.get("correct") else FORMATIVE_TRY_CREDIT.get(st["tries"], 0.2)
            per_objective.setdefault(item.objective, []).append(credit)
            review.append({"item_id": item.id, "objective": item.objective, "score": credit,
                           "tries": st.get("tries", 0), "correct": bool(st.get("correct")),
                           "revealed": bool(st.get("revealed"))})
        unresolved = [r for r in review if not r["correct"] and not r["revealed"]]
        if unresolved:
            raise HTTPException(status.HTTP_409_CONFLICT, f"{len(unresolved)} question(s) still unanswered")
        score = sum(r["score"] for r in review) / len(review)
        completed = True
        stars = max(1, stars_for_score(score))
        result: dict[str, Any] = {"score": round(score, 3), "items": state, "review": review}
    else:
        answers = body.answers or {}
        for item in assessment.items:
            g = grade_item(item, answers.get(item.id))
            per_objective.setdefault(item.objective, []).append(g.score)
            review.append({"item_id": item.id, "objective": item.objective, "score": g.score, "correct": g.correct,
                           "feedback": g.feedback, "detail": g.detail, "explanation": item.explanation,
                           "answer": expected_answer(item), "your_answer": answers.get(item.id)})
        score = sum(r["score"] for r in review) / len(review)
        completed = score >= assessment.pass_mark
        stars = stars_for_score(score, assessment.pass_mark) if completed else 0
        result = {"score": round(score, 3), "passed": completed, "review": review}

    objective_scores = {o: sum(v) / len(v) for o, v in per_objective.items()}
    result["objectives"] = {str(o): round(s, 3) for o, s in objective_scores.items()}
    reward = record_result(db, user, activity, kind="quiz", completed=completed, score=round(score, 3), stars=stars,
                           payload=att.payload | {"answers": body.answers or {}}, result=result,
                           objective_scores=objective_scores, attempt=att)
    mastery = mastery_map(db, user)
    return {
        "result": result,
        "reward": reward,
        "mastery": mastery_report(mastery),
        "recommendations": recommendations(module_states(progress_map(db, user)), mastery),
    }
