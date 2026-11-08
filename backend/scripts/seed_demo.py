"""Seed demo learners by *playing the course through the real API*.

Every XP point, star, badge and mastery value is earned through the same endpoints a
browser uses, so the seeded data is exactly what real learners would produce.

    cd backend && .venv/bin/python -m scripts.seed_demo          # password for all: labyrinth
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore", message="Using `httpx`")

import random
import sys

from fastapi.testclient import TestClient

from app.content.assessments import ASSESSMENTS
from app.content.course import MODULES
from app.content.graphs import GRAPHS
from app.engine.graph import Graph
from app.engine.traversal import dfs_trace
from app.main import app
from app.services.grading import expected_answer

PASSWORD = "labyrinth"
LEARNERS = [
    # username, display name, fraction of activities to complete, skill (0..1)
    ("ariadne", "Ariadne", 1.0, 1.0),
    ("icarus", "Icarus", 1.0, 0.75),
    ("daedalus", "Daedalus", 0.8, 0.9),
    ("phaedra", "Phaedra", 0.55, 0.6),
    ("minos", "King Minos", 0.3, 0.5),
]


def perfect_trace(graph_id: str, start: str, auto: bool) -> list[dict]:
    events = dfs_trace(Graph.from_spec(GRAPHS[graph_id]), start)[1:]
    return [{"kind": "visit", "node": e.node} if e.kind == "visit" else {"kind": "backtrack"}
            for e in events if not (auto and e.kind == "backtrack")]


def sloppy(actions: list[dict], skill: float, rng: random.Random) -> list[dict]:
    out: list[dict] = []
    for a in actions:
        if rng.random() > skill:
            out.append({"kind": "hint"} if rng.random() < 0.5 else {"kind": "visit", "node": "A"})
        out.append(a)
    return out


def play(c: TestClient, h: dict, activity, skill: float, rng: random.Random) -> None:
    cfg = activity.config
    if activity.kind == "maze":
        r = c.post(f"/api/activities/{activity.id}/submit", headers=h,
                   json={"data": {"path": ["A", "B", "E", "H", "K", "M"]}})
    elif activity.kind in ("inspect", "represent", "demo", "compare"):
        data = {"discovered": ["vertex", "edge", "directed", "directed-edge", "degree"]}
        r = c.post(f"/api/activities/{activity.id}/submit", headers=h, json={"data": data})
    elif activity.kind == "trace":
        acts = sloppy(perfect_trace(cfg["graph"], cfg["start"], cfg.get("auto_backtrack", True)), skill, rng)
        r = c.post(f"/api/activities/{activity.id}/submit", headers=h, json={"actions": acts})
    else:  # quiz
        a = ASSESSMENTS[cfg["assessment"]]
        aid = c.post(f"/api/activities/{activity.id}/attempts", headers=h).json()["attempt_id"]
        if a.mode == "formative":
            for item in a.items:
                if rng.random() > skill:  # one wrong try first
                    c.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": item.id, "answer": []})
                ans = expected_answer(item)
                if item.type == "short_answer":
                    ans = ("DFS uses a stack and dives deep down one branch before backtracking, "
                           "while BFS uses a queue and explores level by level.")
                c.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": item.id, "answer": ans})
            r = c.post(f"/api/attempts/{aid}/finish", headers=h, json={})
        else:
            answers = {}
            for item in a.items:
                ans = expected_answer(item)
                if item.type == "short_answer":
                    ans = "DFS uses a stack to go deep and backtrack; BFS uses a queue to go level by level."
                answers[item.id] = ans if rng.random() < skill + 0.1 else None
            r = c.post(f"/api/attempts/{aid}/finish", headers=h, json={"answers": answers})
    r.raise_for_status()


def main() -> None:
    rng = random.Random(750)
    activities = [a for m in MODULES for a in m.activities]
    with TestClient(app) as c:
        for username, name, frac, skill in LEARNERS:
            r = c.post("/api/auth/register", json={"username": username, "display_name": name, "password": PASSWORD})
            if r.status_code == 409:
                print(f"  {username}: already exists, skipping")
                continue
            r.raise_for_status()
            h = {"Authorization": f"Bearer {r.json()['token']}"}
            for activity in activities[: round(len(activities) * frac)]:
                play(c, h, activity, skill, rng)
            me = c.get("/api/me", headers=h).json()
            print(f"  {username:<9} level {me['level']['level']} · {me['level']['xp']:>4} XP · "
                  f"{sum(1 for b in me['badges'] if b['earned_at'])} badges · "
                  f"{me['stats']['completed']}/{me['stats']['total']} done")
    print(f"Done. Sign in as any of them with password '{PASSWORD}'.")


if __name__ == "__main__":
    sys.exit(main())
