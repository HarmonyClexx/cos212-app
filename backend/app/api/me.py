from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_user
from app.models import User, UserBadge
from app.services.gamification import BADGES, level_info
from app.services.progress import mastery_map, mastery_report, module_states, progress_map, recommendations

router = APIRouter(tags=["learner"])


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    states = module_states(progress_map(db, user))
    mastery = mastery_map(db, user)
    activities = [a for m in states for a in m["activities"]]
    earned = {b.badge_id: b.earned_at for b in db.scalars(select(UserBadge).where(UserBadge.user_id == user.id))}
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "level": level_info(user.xp),
        "streak_days": user.streak_days,
        "badges": [{**b.__dict__, "earned_at": earned.get(b.id)} for b in BADGES],
        "mastery": mastery_report(mastery),
        "recommendations": recommendations(states, mastery),
        "stats": {
            "completed": sum(a["completed"] for a in activities),
            "total": len(activities),
            "stars": sum(m["stars"] for m in states),
            "max_stars": sum(m["max_stars"] for m in states),
            "attempts": sum(a["attempts"] for a in activities),
        },
    }


@router.get("/leaderboard")
def leaderboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    badge_counts = dict(db.execute(select(UserBadge.user_id, func.count()).group_by(UserBadge.user_id)).all())
    top = db.scalars(select(User).order_by(User.xp.desc(), User.created_at).limit(20)).all()
    my_rank = db.scalar(select(func.count()).select_from(User).where(User.xp > user.xp)) + 1

    def row(u: User, rank: int) -> dict[str, Any]:
        lv = level_info(u.xp)
        return {"rank": rank, "display_name": u.display_name, "username": u.username, "xp": u.xp,
                "level": lv["level"], "title": lv["title"], "badges": badge_counts.get(u.id, 0),
                "streak_days": u.streak_days, "is_me": u.id == user.id}

    # Standard competition ranking (1, 2, 2, 4) so ties agree with `my_rank`.
    rows, rank, prev_xp = [], 0, None
    for i, u in enumerate(top):
        if u.xp != prev_xp:
            rank, prev_xp = i + 1, u.xp
        rows.append(row(u, rank))
    return {"top": rows, "me": row(user, my_rank)}
