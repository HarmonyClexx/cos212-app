"""Pinned quiz content and append-only response/support records, separate from scoring."""

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.assessments import ASSESSMENT_VERSIONS
from app.content.course import OBJECTIVES
from app.content.graphs import GRAPHS
from app.content.reserved_finals import FINAL_GRAPHS, FINAL_VARIANTS
from app.content.schema import Activity, Assessment, Item
from app.models import Attempt, User
from app.services.grading import ItemGrade, public_item

GRADING_VERSION = 1
KINDS = (
    "first_unassisted_practice", "first_assisted_practice", "repeat_practice",
    "history_unknown", "assisted_retry", "repeat_response", "final_fixed_set",
    "final_reserved_unassisted", "final_reserved_assisted", "final_repeat",
)


def content_supported(att: Attempt) -> bool:
    content = att.payload.get("content")
    if content is not None:
        return (content.get("grading_version") == GRADING_VERSION
                and content.get("bank_version") == att.payload.get("version"))
    return att.payload.get("version") in ASSESSMENT_VERSIONS


def pin_content(att: Attempt, activity: Activity) -> None:
    if att.payload.get("content") is not None:
        return
    version = att.payload["version"]
    assessment = ASSESSMENT_VERSIONS[version][att.payload.get("assessment_id", activity.config["assessment"])]
    catalogue = {**GRAPHS, **FINAL_GRAPHS}
    graphs = {i.graph: deepcopy(catalogue[i.graph]) for i in assessment.items if i.graph}
    versions = {}
    for item in assessment.items:
        # Fingerprints use public tasks only, never hashes of withheld answer keys.
        public = {"bank_version": version, "grading_version": GRADING_VERSION,
                  "assessment_id": assessment.id, "item": public_item(item, graphs)}
        versions[item.id] = hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()
    att.payload = {**att.payload, "content": {
        "bank_version": version, "grading_version": GRADING_VERSION,
        "assessment": assessment.model_dump(mode="json"), "graphs": graphs, "task_versions": versions,
    }}


def attempt_content(att: Attempt, activity: Activity) -> tuple[Assessment, dict[str, Any], dict[str, str]]:
    content = att.payload.get("content")
    if content is None:
        assessment = ASSESSMENT_VERSIONS[att.payload["version"]][att.payload.get("assessment_id", activity.config["assessment"])]
        return assessment, {**GRAPHS, **FINAL_GRAPHS}, {}
    return Assessment.model_validate(content["assessment"]), content["graphs"], content["task_versions"]


def initialise_evidence(repeated: bool) -> dict[str, Any]:
    return {"schema_version": 1, "from_revision": 0, "complete_from_start": True,
            "prior_exposure": "repeat" if repeated else "first_recorded_issuance",
            "responses": [], "assistance": [], "unanswered": []}


def _ledger(att: Attempt) -> dict[str, Any]:
    existing = att.payload.get("evidence")
    if existing is not None:
        return deepcopy(existing)
    # L1 recorded review requests, not the complete response/assistance history.
    support = [
        {**event, "action": "review_topic", "scope": "item", "source": "L1"}
        for event in att.payload.get("review_support", [])
    ]
    return {"schema_version": 1, "from_revision": att.payload.get("revision", 0) + 1,
            "complete_from_start": False, "prior_exposure": "unknown",
            "responses": [], "assistance": support, "unanswered": []}


def _event(att: Attempt, ledger: dict[str, Any], item: Item, request_id: str | None) -> dict[str, Any]:
    return {
        "item_id": item.id, "objective": item.objective,
        "task_version": att.payload["content"]["task_versions"][item.id],
        "bank_version": att.payload["version"], "grading_version": GRADING_VERSION,
        "sequence": len(ledger["responses"]) + len(ledger["assistance"]) + 1,
        "revision": att.payload.get("revision", 0) + 1, "request_id": request_id,
        "recorded_at": datetime.now(UTC).isoformat(),
    }


def record_assistance(att: Attempt, item: Item, action: str, request_id: str | None,
                      **metadata: Any) -> None:
    ledger = _ledger(att)
    ledger["assistance"].append({**_event(att, ledger, item, request_id),
                                  "action": action, "scope": "item", **metadata})
    att.payload = {**att.payload, "evidence": ledger}


def readable_answer(item: Item, answer: Any) -> bool:
    if item.type == "mcq":
        return isinstance(answer, list) and all(type(a) is int for a in answer)
    if item.type in ("order", "graph_select"):
        return isinstance(answer, list) and all(isinstance(a, str) for a in answer)
    if item.type == "adjacency":
        return isinstance(answer, dict) and all(
            isinstance(row, str) and isinstance(values, list) and all(isinstance(a, str) for a in values)
            for row, values in answer.items()
        )
    return False


def has_answer(answer: Any) -> bool:
    if isinstance(answer, dict):
        return any(bool(values) for values in answer.values())
    return bool(answer)


def record_response(att: Attempt, item: Item, answer: Any, grade: ItemGrade,
                    request_id: str | None, mode: str) -> None:
    ledger = _ledger(att)
    previous = [r for r in ledger["responses"] if r["item_id"] == item.id]
    assistance = [a for a in ledger["assistance"] if a.get("scope") == "attempt" or a["item_id"] == item.id]
    if previous:
        kind = "assisted_retry" if assistance else "repeat_response"
    elif mode == "summative":
        assignment = att.payload.get("final_assignment", {})
        reserved = (FINAL_VARIANTS.get(assignment.get("variant")) ==
                    att.payload["content"]["assessment"]["id"])
        if reserved and assignment.get("purpose") == "repeat":
            kind = "final_repeat"
        elif reserved and assignment.get("unused_at_issuance"):
            kind = ("history_unknown" if not ledger["complete_from_start"] else
                    "final_reserved_assisted" if assistance else "final_reserved_unassisted")
        else:
            kind = "final_fixed_set"
    elif not ledger["complete_from_start"]:
        kind = "history_unknown"
    elif ledger["prior_exposure"] == "repeat":
        kind = "repeat_practice"
    else:
        kind = "first_assisted_practice" if assistance else "first_unassisted_practice"
    response = {
        **_event(att, ledger, item, request_id), "mode": mode, "kind": kind,
        "answer": deepcopy(answer), "correct": grade.correct, "score": grade.score,
        "detail": deepcopy(grade.detail),
        "reflection": att.payload.get("draft", {}).get("reflections", {}).get(item.id),
        "assistance_before": deepcopy(assistance), "independent_final": kind == "final_reserved_unassisted",
        "final_variant": att.payload.get("final_assignment", {}).get("variant"),
        "prior_exposure": ledger["prior_exposure"],
    }
    ledger["responses"].append(response)
    att.payload = {**att.payload, "evidence": ledger}


def mark_unanswered(att: Attempt, items: list[Item], answers: dict[str, Any]) -> None:
    ledger = _ledger(att)
    ledger["unanswered"] = [i.id for i in items if not has_answer(answers.get(i.id))]
    att.payload = {**att.payload, "evidence": ledger}


def _summary(ledgers: list[dict[str, Any] | None]) -> dict[str, Any]:
    rows = {o.id: {"objective": o.id, **{kind: {"correct": 0, "total": 0} for kind in KINDS}} for o in OBJECTIVES}
    missing = 0
    unanswered = 0
    for ledger in ledgers:
        if not ledger or not ledger["complete_from_start"]:
            missing += 1
        if not ledger:
            continue
        unanswered += len(ledger.get("unanswered", []))
        for response in ledger["responses"]:
            bucket = rows[response["objective"]][response["kind"]]
            bucket["total"] += 1
            bucket["correct"] += int(response["correct"])
    return {"objectives": list(rows.values()), "unrecorded_attempts": missing, "unanswered_final_items": unanswered}


def evidence_report(att: Attempt, items: list[Item]) -> dict[str, Any]:
    ledger = att.payload.get("evidence")
    content = att.payload.get("content", {})
    rows = []
    for item in items:
        responses = [r for r in (ledger or {}).get("responses", []) if r["item_id"] == item.id]
        assistance = [a for a in (ledger or {}).get("assistance", [])
                      if a.get("scope") == "attempt" or a["item_id"] == item.id]
        if ledger is None:
            assistance = [{**a, "action": "review_topic", "scope": "item", "source": "L1"}
                          for a in att.payload.get("review_support", []) if a["item_id"] == item.id]
        rows.append({"item_id": item.id, "task_version": content.get("task_versions", {}).get(item.id),
                     "first_response": responses[0] if responses else None,
                     "latest_response": responses[-1] if responses else None,
                     "response_count": len(responses), "assistance": assistance,
                     "unanswered": item.id in (ledger or {}).get("unanswered", [])})
    return {"schema_version": (ledger or {}).get("schema_version"),
            "final_assignment": att.payload.get("final_assignment"),
            "from_revision": (ledger or {}).get("from_revision"),
            "complete_from_start": bool(ledger and ledger["complete_from_start"]),
            "prior_exposure": (ledger or {}).get("prior_exposure", "unknown"),
            "items": rows, "summary": _summary([ledger])}


def learner_evidence(db: Session, user: User) -> dict[str, Any]:
    payloads = db.scalars(select(Attempt.payload).where(Attempt.user_id == user.id, Attempt.kind == "quiz"))
    return _summary([payload.get("evidence") for payload in payloads])
