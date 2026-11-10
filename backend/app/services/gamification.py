"""XP, levels, streaks, badges and per-objective mastery.

Design notes (from the Design phase, 2.8):
* XP is only ever awarded for *improvement* - replaying for more stars earns the
  difference, so the leaderboard rewards learning rather than grinding.
* Mastery is a running average per objective that becomes an exponential moving
  average once there is enough evidence, so recent performance counts most.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.course import ACTIVITIES, MODULES
from app.content.graphs import GRAPHS
from app.content.schema import Activity
from app.engine.graph import Graph
from app.models import ActivityProgress, Attempt, Mastery, User, UserBadge

LEVEL_FLOORS = [0, 100, 250, 450, 700, 1000, 1350, 1750, 2200]
LEVEL_TITLES = [
    "Lost Wanderer", "Chalk Bearer", "Thread Spinner", "Path Tracer", "Backtrack Adept",
    "Labyrinth Scholar", "Graph Sage", "Ariadne's Heir", "Master of the Maze",
]


def level_info(xp: int) -> dict[str, Any]:
    lvl = max(i for i, floor in enumerate(LEVEL_FLOORS) if xp >= floor)
    floor = LEVEL_FLOORS[lvl]
    ceil = LEVEL_FLOORS[lvl + 1] if lvl + 1 < len(LEVEL_FLOORS) else None
    progress = 1.0 if ceil is None else (xp - floor) / (ceil - floor)
    return {"level": lvl + 1, "title": LEVEL_TITLES[lvl], "xp": xp, "floor": floor, "next": ceil,
            "progress": round(progress, 3)}


@dataclass(frozen=True)
class Badge:
    id: str
    name: str
    description: str
    icon: str


BADGES = [
    Badge("first-steps", "First Steps", "Complete your first activity.", "footprints"),
    Badge("well-read", "Ariadne's Pupil", "Finish all five lessons of the intro course.", "book"),
    Badge("thread-bearer", "Thread Bearer", "Find the Minotaur's lair in the Labyrinth.", "spool"),
    Badge("cartographer", "Cartographer", "Build an adjacency list perfectly on the first try.", "map"),
    Badge("deep-diver", "Deep Diver", "Earn 3 stars on a DFS trace.", "anchor"),
    Badge("cycle-breaker", "Cycle Breaker", "Finish a graph with a cycle without ever re-entering a visited vertex.",
          "repeat"),
    Badge("backtracker", "Master of the Thread", "Earn 3 stars on a challenge where you backtrack by hand.", "undo"),
    Badge("self-reliant", "Self-Reliant", "Complete 3 DFS challenges without a hint or a reveal.", "shield"),
    Badge("minotaur-slayer", "Minotaur Slayer", "Pass the final trial.", "sword"),
    Badge("flawless", "Flawless", "Score 100% on the final trial.", "crown"),
    Badge("on-fire", "On Fire", "Learn on 3 days in a row.", "flame"),
]
BADGES_BY_ID = {b.id: b for b in BADGES}


def has_cycle(g: Graph) -> bool:
    if g.directed:
        state: dict[str, int] = {}

        def visit(n: str) -> bool:
            state[n] = 1
            for m in g.neighbours(n):
                if state.get(m) == 1 or (m not in state and visit(m)):
                    return True
            state[n] = 2
            return False

        return any(n not in state and visit(n) for n in g.nodes)
    parent = {n: n for n in g.nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in g.edges:
        ru, rv = find(u), find(v)
        if ru == rv:
            return True
        parent[ru] = rv
    return False


def touch_streak(user: User, today: date | None = None) -> None:
    today = today or date.today()
    if user.last_active_on == today:
        return
    user.streak_days = user.streak_days + 1 if user.last_active_on == today - timedelta(days=1) else 1
    user.last_active_on = today


def update_mastery(db: Session, user: User, scores: dict[int, float]) -> None:
    for objective, score in scores.items():
        row = db.scalar(select(Mastery).where(Mastery.user_id == user.id, Mastery.objective == objective))
        if row is None:
            row = Mastery(user_id=user.id, objective=objective, value=0.0, evidence=0)
            db.add(row)
        alpha = max(0.35, 1 / (row.evidence + 1))
        row.value = round(row.value + alpha * (score - row.value), 4)
        row.evidence += 1


def stars_for_score(score: float, pass_mark: float = 0.4) -> int:
    if score >= 0.9:
        return 3
    if score >= 0.7:
        return 2
    return 1 if score >= pass_mark else 0


def _award_badges(db: Session, user: User, activity: Activity, result: dict[str, Any], stars: int,
                  completed: bool) -> list[str]:
    owned = set(db.scalars(select(UserBadge.badge_id).where(UserBadge.user_id == user.id)))
    earned: list[str] = []

    def grant(bid: str) -> None:
        if bid not in owned and bid not in earned:
            earned.append(bid)

    if completed:
        grant("first-steps")
    if activity.kind == "lesson" and completed:
        course = [a.id for a in ACTIVITIES[activity.id][0].activities]
        finished = set(db.scalars(select(ActivityProgress.activity_id).where(
            ActivityProgress.user_id == user.id, ActivityProgress.completed.is_(True),
            ActivityProgress.activity_id.in_(course))))
        if finished >= set(course):
            grant("well-read")
    if activity.kind == "maze" and completed:
        grant("thread-bearer")
    if activity.kind == "quiz" and activity.config.get("assessment") == "representation-check":
        if any(i.get("type") == "adjacency" and i.get("tries") == 1 and i.get("correct")
               for i in result.get("items", {}).values()):
            grant("cartographer")
    if activity.kind == "trace" and completed:
        auto = activity.config.get("auto_backtrack", True)
        if stars == 3:
            grant("deep-diver" if auto else "backtracker")
        g = Graph.from_spec(GRAPHS[activity.config["graph"]])
        if has_cycle(g) and result.get("breakdown", {}).get("already_visited", 0) == 0:
            grant("cycle-breaker")
        clean = db.scalars(
            select(Attempt.activity_id).where(Attempt.user_id == user.id, Attempt.kind == "trace").distinct()
            .where(Attempt.result["hints"].as_integer() == 0, Attempt.result["reveals"].as_integer() == 0,
                   Attempt.result["completed"].as_boolean().is_(True))
        )
        if len(set(clean) | ({activity.id} if result.get("hints") == 0 and result.get("reveals") == 0 else set())) >= 3:
            grant("self-reliant")
    if activity.id == "m6-final" and completed:
        grant("minotaur-slayer")
        if result.get("score", 0) >= 0.999:
            grant("flawless")
    if user.streak_days >= 3:
        grant("on-fire")

    for bid in earned:
        db.add(UserBadge(user_id=user.id, badge_id=bid))
    return earned


def record_result(
    db: Session,
    user: User,
    activity: Activity,
    *,
    kind: str,
    completed: bool,
    score: float,
    stars: int,
    payload: dict[str, Any],
    result: dict[str, Any],
    objective_scores: dict[int, float] | None = None,
    attempt: Attempt | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Persist one graded result and return the reward summary shown to the learner."""
    before = level_info(user.xp)

    prog = db.scalar(
        select(ActivityProgress).where(ActivityProgress.user_id == user.id,
                                       ActivityProgress.activity_id == activity.id)
    )
    if prog is None:
        prog = ActivityProgress(user_id=user.id, activity_id=activity.id, completed=False, best_stars=0,
                                best_score=0.0, xp_earned=0, attempts=0)
        db.add(prog)
    first_completion = completed and not prog.completed
    prev_best = prog.best_stars

    prog.attempts += 1
    potential = round(activity.xp * stars / 3) if completed else 0
    xp_gain = max(0, potential - prog.xp_earned)
    prog.xp_earned += xp_gain
    prog.completed = prog.completed or completed
    prog.best_stars = max(prog.best_stars, stars)
    prog.best_score = max(prog.best_score, score)
    user.xp += xp_gain

    touch_streak(user)
    if objective_scores:
        update_mastery(db, user, objective_scores)

    if attempt is None:
        attempt = Attempt(user_id=user.id, activity_id=activity.id, kind=kind)
        db.add(attempt)
    attempt.status = "closed"
    attempt.payload = payload
    attempt.result = result
    attempt.score = score
    attempt.stars = stars
    attempt.xp_awarded = xp_gain
    db.flush()

    new_badges = _award_badges(db, user, activity, result, stars, completed)
    if commit:
        db.commit()

    after = level_info(user.xp)
    return {
        "completed": completed,
        "first_completion": first_completion,
        "stars": stars,
        "best_stars": prog.best_stars,
        "improved": stars > prev_best,
        "score": score,
        "xp_gained": xp_gain,
        "xp_possible": activity.xp,
        "level": after,
        "level_up": after["level"] > before["level"],
        "streak_days": user.streak_days,
        "new_badges": [BADGES_BY_ID[b].__dict__ for b in new_badges],
        "next_activity": next_activity_id(activity.id),
    }


def next_activity_id(activity_id: str) -> str | None:
    ordered = [a.id for m in MODULES for a in m.activities]
    i = ordered.index(activity_id)
    return ordered[i + 1] if i + 1 < len(ordered) else None


def activity_module_slug(activity_id: str) -> str:
    return ACTIVITIES[activity_id][0].slug
