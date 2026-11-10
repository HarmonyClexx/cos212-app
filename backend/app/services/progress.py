"""Unlocking, module state, and adaptive revision recommendations."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.course import MODULES, MODULES_BY_SLUG, OBJECTIVES, OBJECTIVES_BY_ID
from app.core.config import settings
from app.models import ActivityProgress, Mastery, User

MASTERY_TARGET = 0.7
# Below this, practising again isn't enough: the learner is sent back to the lesson first.
RELEARN_BELOW = 0.4


def progress_map(db: Session, user: User) -> dict[str, ActivityProgress]:
    rows = db.scalars(select(ActivityProgress).where(ActivityProgress.user_id == user.id))
    return {r.activity_id: r for r in rows}


def mastery_map(db: Session, user: User) -> dict[int, Mastery]:
    return {m.objective: m for m in db.scalars(select(Mastery).where(Mastery.user_id == user.id))}


def module_states(prog: dict[str, ActivityProgress]) -> list[dict[str, Any]]:
    """Modules unlock in order; activities inside a module unlock in order (Gagne sequencing).

    Anything a learner has already started stays open, so adding content earlier in the course
    (as the intro course was) never locks anyone out of work in progress.
    """
    out = []
    prev_module_done = True
    for m in MODULES:
        unlocked = settings.unlock_all or prev_module_done or any(a.id in prog for a in m.activities)
        acts = []
        prev_done = True
        for a in m.activities:
            p = prog.get(a.id)
            done = bool(p and p.completed)
            acts.append({
                "id": a.id, "kind": a.kind, "title": a.title, "summary": a.summary, "xp": a.xp,
                "objective": a.objective,
                "completed": done, "best_stars": p.best_stars if p else 0,
                "xp_earned": p.xp_earned if p else 0, "attempts": p.attempts if p else 0,
                "unlocked": unlocked and (settings.unlock_all or prev_done or p is not None),
            })
            prev_done = done
        completed = all(a["completed"] for a in acts)
        out.append({
            "slug": m.slug, "order": m.order, "title": m.title, "tagline": m.tagline, "icon": m.icon,
            "objective": m.objective, "track": m.track, "lesson": m.lesson, "unlocked": unlocked,
            "completed": completed,
            "stars": sum(a["best_stars"] for a in acts if a["kind"] in ("trace", "quiz")),
            "max_stars": 3 * sum(1 for a in acts if a["kind"] in ("trace", "quiz")),
            "activities": acts,
        })
        prev_module_done = completed
    return out


def recommendations(states: list[dict[str, Any]], mastery: dict[int, Mastery]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for m in states:
        nxt = next((a for a in m["activities"] if a["unlocked"] and not a["completed"]), None)
        if nxt:
            recs.append({"type": "continue", "module": m["slug"], "activity_id": nxt["id"],
                         "title": nxt["title"], "reason": f"Up next in {m['title']}"})
            break

    weak = sorted((row for row in mastery.values() if row.value < MASTERY_TARGET), key=lambda r: r.value)
    by_id = {a["id"]: (m, a) for m in states for a in m["activities"]}
    for row in weak[:2]:
        obj = OBJECTIVES_BY_ID[row.objective]
        module = next(m for m in states if m["slug"] == obj.module)
        practice = [a for a in module["activities"] if a["kind"] in ("trace", "quiz") and a["completed"]]
        target = min(practice, key=lambda a: a["best_stars"]) if practice else module["activities"][0]
        home, advice = module, f"aim for {round(MASTERY_TARGET * 100)}%"
        lesson = MODULES_BY_SLUG[obj.module].lesson
        if row.value < RELEARN_BELOW and lesson in by_id and by_id[lesson][1]["unlocked"]:
            # Struggling badly: re-read the explanation before practising again.
            home, target = by_id[lesson]
            advice = "re-read the lesson, then practise again"
        recs.append({
            "type": "revise", "module": home["slug"], "activity_id": target["id"], "title": target["title"],
            "objective": row.objective,
            "reason": f"Mastery of “{obj.title}” is {round(row.value * 100)}% – {advice}",
        })
    return recs


def mastery_report(mastery: dict[int, Mastery]) -> list[dict[str, Any]]:
    return [
        {"objective": o.id, "title": o.title, "bloom": o.bloom, "verb": o.verb, "statement": o.statement,
         "module": o.module, "value": mastery[o.id].value if o.id in mastery else 0.0,
         "evidence": mastery[o.id].evidence if o.id in mastery else 0}
        for o in OBJECTIVES
    ]
