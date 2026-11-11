"""Course content, activity submission and quiz-attempt lifecycle.

Quiz attempts are server-side sessions:
    POST /activities/{id}/attempts      -> open an attempt, receive sanitised items
    POST /attempts/{aid}/hint           -> (formative only) ask for the next level of help
    POST /attempts/{aid}/check          -> (formative only) grade one item, tiered feedback
    POST /attempts/{aid}/finish         -> close, score, award XP / badges / mastery
so the number of tries and hints per item - which drive the scaffolding and the credit - are
recorded by the server, not trusted from the browser.
"""

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.assessments import ASSESSMENT_VERSION, ASSESSMENTS
from app.content.course import ACTIVITIES, MODULES_BY_SLUG, OBJECTIVES
from app.content.graphs import GRAPHS
from app.content.lessons import LESSONS, lesson_payload
from app.content.schema import Activity, Item, Module
from app.core.db import get_db
from app.core.security import get_current_user
from app.engine.graph import Graph
from app.engine.replay import HINT_COST, TraceAction, grade_trace
from app.models import Attempt, User
from app.services.gamification import record_result, stars_for_score
from app.services.grading import MAX_HINT_LEVEL, expected_answer, grade_item, hint_content, public_item
from app.services.progress import mastery_map, mastery_report, module_states, progress_map, recommendations

router = APIRouter(tags=["course"])

# Explore / watch activities: completion only, nothing to grade (lessons are graded on their checks).
EXPLORE_KINDS = {"inspect", "represent", "demo", "compare"}
INSPECT_CHECKLIST = {"vertex", "edge", "directed", "directed-edge", "degree"}
FORMATIVE_TRY_CREDIT = {1: 1.0, 2: 0.7, 3: 0.4}
# A hint (HINT_COST, shared with traces) is cheaper than a wrong guess (1.0 -> 0.7), so asking
# for help always beats guessing. Getting there yourself is worth at least MIN_CREDIT.
MIN_CREDIT = 0.2


# --- helpers ---------------------------------------------------------------------------------

def _resolve_config(activity: Activity) -> dict[str, Any]:
    cfg = dict(activity.config)
    for key in ("graph", "directed_graph"):
        if key in cfg:
            cfg[key] = GRAPHS[cfg[key]]
    if activity.kind == "quiz":
        a = ASSESSMENTS[cfg["assessment"]]
        cfg.update(mode=a.mode, item_count=len(a.items), pass_mark=a.pass_mark)
    if activity.kind == "lesson":
        cfg["lesson"] = lesson_payload(cfg["lesson"])
    return cfg


def _module_payload(m: Module) -> dict[str, Any]:
    return {
        "slug": m.slug, "order": m.order, "title": m.title, "tagline": m.tagline, "story": m.story,
        "objective": m.objective, "outcome": m.outcome, "icon": m.icon, "track": m.track, "lesson": m.lesson,
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

    if activity.kind == "lesson":
        # Checks are ungraded, but a lesson only counts once every one of them has been answered.
        checks = LESSONS[cfg["lesson"]].checks()
        answers = data.get("answers") or {}
        if not isinstance(answers, dict) or any(answers.get(c.id) != c.answer for c in checks):
            raise HTTPException(422, "Answer every check in the lesson first")
        raw_tries = data.get("tries") if isinstance(data.get("tries"), dict) else {}
        tries = {c.id: max(1, min(int(t), len(c.options))) for c in checks
                 if isinstance(t := raw_tries.get(c.id), int) and not isinstance(t, bool)}
        # Tries per check are kept for the Evaluate phase: which ideas needed a second look.
        result = {"checks": len(checks), "first_try": sum(1 for t in tries.values() if t == 1), "tries": tries}
        reward = record_result(db, user, activity, kind="lesson", completed=True, score=1.0, stars=3,
                               payload={"answers": {c.id: c.answer for c in checks}, "tries": tries},
                               result=result)
        return {"result": result, "reward": reward}

    if activity.kind in EXPLORE_KINDS:
        if activity.kind == "inspect" and not INSPECT_CHECKLIST <= set(data.get("discovered", [])):
            raise HTTPException(422, "Finish the discovery checklist first")
        reward = record_result(db, user, activity, kind="lesson", completed=True, score=1.0, stars=3,
                               payload=data, result={})
        return {"result": {}, "reward": reward}

    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quizzes are submitted through attempts")


# --- quiz attempts ------------------------------------------------------------------------------

class OperationIn(BaseModel):
    request_id: str | None = Field(default=None, min_length=1, max_length=64)
    revision: int | None = Field(default=None, ge=0)


class CheckIn(OperationIn):
    item_id: str
    answer: Any = None
    reveal: bool = False


class HintIn(OperationIn):
    item_id: str


def _credit_if_correct(tries: int, hints: int) -> float:
    return round(max(MIN_CREDIT, FORMATIVE_TRY_CREDIT.get(tries, MIN_CREDIT) - HINT_COST * hints), 3)


def _help_level(st: dict[str, Any]) -> int:
    """Scaffolding already shown for an unresolved item: wrong tries and hint requests both count."""
    return min(3, max(st["tries"], st["hint_level"]))


def _formative_item(att: Attempt, activity: Activity, item_id: str) -> tuple[Item, dict[str, Any]]:
    assessment = ASSESSMENTS[activity.config["assessment"]]
    if assessment.mode != "formative":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No feedback during the final trial")
    item = next((i for i in assessment.items if i.id == item_id), None)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown item")
    st = {"tries": 0, "correct": False, "revealed": False, "hints": 0, "hint_level": 0, "type": item.type,
          **att.payload.get("items", {}).get(item.id, {})}
    if st["correct"] or st["revealed"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "Item already resolved")
    return item, st


def _save_item(att: Attempt, item: Item, st: dict[str, Any], db: Session) -> None:
    att.payload = {**att.payload, "items": {**att.payload.get("items", {}), item.id: st}}


class FinishIn(OperationIn):
    answers: dict[str, Any] | None = None


def _lock_learner(user: User, db: Session) -> None:
    # Serialise quiz starts and mutations across tabs/workers, including reward updates.
    db.execute(
        select(User).where(User.id == user.id).with_for_update().execution_options(populate_existing=True)
    ).scalar_one()


def _owned_attempt(aid: int, user: User, db: Session) -> tuple[Attempt, Activity]:
    att = db.get(Attempt, aid)
    if att is None or att.user_id != user.id or att.kind != "quiz":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown attempt")
    return att, ACTIVITIES[att.activity_id][1]


def _require_open(att: Attempt) -> None:
    if att.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is already finished")
    if att.payload.get("version") != ASSESSMENT_VERSION:
        raise HTTPException(status.HTTP_409_CONFLICT, "The quiz format changed. Reopen this activity to continue.")


def _replay(att: Attempt, body: OperationIn, kind: str) -> dict[str, Any] | None:
    receipt = att.payload.get("receipts", {}).get(body.request_id)
    if receipt:
        if receipt["fingerprint"] != _fingerprint(body, kind):
            raise HTTPException(409, "This request ID was already used for a different action")
        return receipt["response"]
    _require_open(att)
    if body.revision is not None and body.revision != att.payload.get("revision", 0):
        raise HTTPException(409, "This quiz changed in another tab. Reload its saved state before continuing.")
    return None


def _fingerprint(body: OperationIn, kind: str) -> str:
    return hashlib.sha256(json.dumps([kind, body.model_dump()], sort_keys=True).encode()).hexdigest()


def _commit_operation(att: Attempt, body: OperationIn, kind: str, response: dict[str, Any],
                      db: Session) -> dict[str, Any]:
    revision = att.payload.get("revision", 0) + 1
    response = {**response, "revision": revision}
    receipts = dict(att.payload.get("receipts", {}))
    if body.request_id:
        receipts[body.request_id] = {"fingerprint": _fingerprint(body, kind), "response": response}
    att.payload = {**att.payload, "revision": revision, "receipts": receipts}
    db.commit()
    return response


def _report(att: Attempt, user: User, db: Session) -> dict[str, Any]:
    return {
        "revision": att.payload.get("revision", 0),
        "result": att.result,
        "mastery": mastery_report(mastery_map(db, user)),
        "recommendations": recommendations(module_states(progress_map(db, user)), mastery_map(db, user)),
    }


def _attempt_payload(att: Attempt, activity: Activity, user: User, db: Session) -> dict[str, Any]:
    assessment = ASSESSMENTS[activity.config["assessment"]]
    compatible = att.payload.get("version") == ASSESSMENT_VERSION
    state = att.payload.get("items", {}) if compatible else {}
    draft = att.payload.get("draft", {}) if compatible else {}
    return {
        "attempt_id": att.id, "status": att.status, "revision": att.payload.get("revision", 0),
        "user_id": user.id, "last_draft_request": att.payload.get("last_draft_request"),
        "mode": assessment.mode, "pass_mark": assessment.pass_mark,
        "items": [public_item(i) for i in assessment.items],
        "answers": draft.get("answers", {}), "reflections": draft.get("reflections", {}),
        "current_item": draft.get("current_item", assessment.items[0].id),
        "results": {iid: st["response"] for iid, st in state.items() if "response" in st},
        "hints": {iid: st["hint_response"] for iid, st in state.items() if "hint_response" in st},
        "revealed": {iid: st.get("revealed", False) for iid, st in state.items()},
        "last": {iid: st.get("last", "check") for iid, st in state.items()},
        "compatible": compatible,
        "report": _report(att, user, db) if att.status == "closed" else None,
    }


class StartIn(BaseModel):
    new_attempt: bool = False


class DraftIn(OperationIn):
    revision: int = Field(ge=0)
    answers: dict[str, Any]
    reflections: dict[str, str] = Field(default_factory=dict)
    current_item: str


@router.post("/activities/{activity_id}/attempts", status_code=status.HTTP_201_CREATED)
def start_attempt(activity_id: str, body: StartIn | None = None, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> dict[str, Any]:
    _lock_learner(user, db)
    _, activity = _get_activity(activity_id, user, db)
    if activity.kind != "quiz":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a quiz")
    attempts = list(db.scalars(select(Attempt).where(
        Attempt.user_id == user.id, Attempt.activity_id == activity.id, Attempt.kind == "quiz"
    ).order_by(Attempt.id.desc())))
    active = next((a for a in attempts if a.status == "open"
                   and a.payload.get("version") == ASSESSMENT_VERSION), None)
    superseded = False
    for old in attempts:
        if old.status == "open" and old is not active:
            old.status = "superseded"
            superseded = True
    if active:
        db.commit()
        return _attempt_payload(active, activity, user, db)
    closed = next((a for a in attempts if a.status == "closed"), None)
    if closed and not (body and body.new_attempt):
        db.commit()
        return _attempt_payload(closed, activity, user, db)
    att = Attempt(user_id=user.id, activity_id=activity.id, kind="quiz", status="open", result={},
                  payload={"items": {}, "version": ASSESSMENT_VERSION, "revision": 0, "draft": {}})
    db.add(att)
    db.commit()
    response = _attempt_payload(att, activity, user, db)
    if superseded:
        response["notice"] = "An older unfinished quiz could not be resumed. Its record was kept; this is a new attempt."
    return response


@router.get("/attempts/{aid}")
def get_attempt(aid: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> dict[str, Any]:
    att, activity = _owned_attempt(aid, user, db)
    return _attempt_payload(att, activity, user, db)


@router.put("/attempts/{aid}/draft")
def save_draft(aid: int, body: DraftIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict[str, Any]:
    _lock_learner(user, db)
    att, activity = _owned_attempt(aid, user, db)
    if cached := _replay(att, body, "draft"):
        return cached
    items = {i.id: i for i in ASSESSMENTS[activity.config["assessment"]].items}
    if body.current_item not in items or not body.answers.keys() <= items.keys():
        raise HTTPException(422, "Unknown question in draft")
    if any(iid not in items or not items[iid].reflection_prompt or len(text) > 1200
           for iid, text in body.reflections.items()):
        raise HTTPException(422, "Invalid optional reflection")
    previous = att.payload.get("draft", {}).get("answers", {})
    for iid, st in att.payload.get("items", {}).items():
        if (st.get("correct") or st.get("revealed")) and body.answers.get(iid) != previous.get(iid):
            raise HTTPException(409, "A resolved answer cannot be changed")
    att.payload = {**att.payload, "last_draft_request": body.request_id, "draft": {
        "answers": body.answers, "reflections": body.reflections, "current_item": body.current_item,
    }}
    return _commit_operation(att, body, "draft", {}, db)


@router.post("/attempts/{aid}/hint")
def hint(aid: int, body: HintIn, user: User = Depends(get_current_user),
         db: Session = Depends(get_db)) -> dict[str, Any]:
    """Next level of help, before or between tries. Only help the learner hasn't seen is charged."""
    _lock_learner(user, db)
    att, activity = _owned_attempt(aid, user, db)
    if cached := _replay(att, body, "hint"):
        return cached
    item, st = _formative_item(att, activity, body.item_id)
    seen = min(MAX_HINT_LEVEL, _help_level(st))
    charged = seen < MAX_HINT_LEVEL
    level = min(MAX_HINT_LEVEL, seen + 1)
    if charged:
        st["hints"] += 1
        st["hint_level"] = level
        _save_item(att, item, st, db)
    response = {"item_id": item.id, "level": level, "max_level": MAX_HINT_LEVEL, "charged": charged,
                "hints": st["hints"], "worth": _credit_if_correct(st["tries"] + 1, st["hints"]),
                **hint_content(item, level)}
    st.update(hint_response=response, last="hint")
    _save_item(att, item, st, db)
    return _commit_operation(att, body, "hint", response, db)


@router.post("/attempts/{aid}/check")
def check_item(aid: int, body: CheckIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> dict[str, Any]:
    _lock_learner(user, db)
    att, activity = _owned_attempt(aid, user, db)
    if cached := _replay(att, body, "check"):
        return cached
    item, st = _formative_item(att, activity, body.item_id)

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
        draft = att.payload.get("draft", {})
        att.payload = {**att.payload, "draft": {
            **draft, "answers": {**draft.get("answers", {}), item.id: body.answer},
        }}
    _save_item(att, item, st, db)

    # Progressive scaffolding (Design 2.6): nudge -> the idea in full + visual cue -> worked answer.
    correct = bool(grade and grade.correct)
    tier = 0 if correct else _help_level(st)
    resp: dict[str, Any] = {
        "item_id": item.id, "tries": st["tries"], "hints": st["hints"], "correct": correct,
        "score": grade.score if grade else 0.0, "feedback": grade.feedback if grade else "Here's the worked answer.",
        "detail": grade.detail if grade else {}, "tier": tier, "can_reveal": not st["correct"] and st["tries"] >= 3,
        "worth": 0.0 if body.reveal else _credit_if_correct(st["tries"] if correct else st["tries"] + 1, st["hints"]),
    }
    if tier >= 1 and not body.reveal:
        resp |= hint_content(item, min(tier, MAX_HINT_LEVEL))
    if correct or body.reveal:
        resp["explanation"] = item.explanation
        resp["answer"] = expected_answer(item)
    st.update(response=resp, last="check")
    _save_item(att, item, st, db)
    return _commit_operation(att, body, "check", resp, db)


@router.post("/attempts/{aid}/finish")
def finish_attempt(aid: int, body: FinishIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> dict[str, Any]:
    _lock_learner(user, db)
    att, activity = _owned_attempt(aid, user, db)
    if cached := _replay(att, body, "finish"):
        return cached
    assessment = ASSESSMENTS[activity.config["assessment"]]
    per_objective: dict[int, list[float]] = {}
    review: list[dict[str, Any]] = []

    if assessment.mode == "formative":
        state = att.payload.get("items", {})
        for item in assessment.items:
            st = state.get(item.id, {})
            ok = st.get("correct") and not st.get("revealed")
            credit = _credit_if_correct(st["tries"], st.get("hints", 0)) if ok else 0.0
            per_objective.setdefault(item.objective, []).append(credit)
            review.append({"item_id": item.id, "objective": item.objective, "score": credit,
                           "tries": st.get("tries", 0), "hints": st.get("hints", 0), "correct": bool(st.get("correct")),
                           "revealed": bool(st.get("revealed"))})
        unresolved = [r for r in review if not r["correct"] and not r["revealed"]]
        if unresolved:
            raise HTTPException(status.HTTP_409_CONFLICT, f"{len(unresolved)} question(s) still unanswered")
        score = sum(r["score"] for r in review) / len(review)
        completed = True
        stars = max(1, stars_for_score(score))
        result: dict[str, Any] = {"score": round(score, 3), "items": state, "review": review}
    else:
        answers = body.answers if body.answers is not None else att.payload.get("draft", {}).get("answers", {})
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
                           payload=att.payload | {"answers": body.answers if body.answers is not None
                                                  else att.payload.get("draft", {}).get("answers", {})}, result=result,
                           objective_scores=objective_scores, attempt=att, commit=False)
    mastery = mastery_map(db, user)
    response = {
        "result": result,
        "reward": reward,
        "mastery": mastery_report(mastery),
        "recommendations": recommendations(module_states(progress_map(db, user)), mastery),
    }
    return _commit_operation(att, body, "finish", response, db)
