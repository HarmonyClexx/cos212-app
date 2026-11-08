"""End-to-end API tests on an in-memory SQLite database."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    def override() -> Iterator:
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(c: TestClient, name: str = "theseus") -> dict[str, str]:
    r = c.post("/api/auth/register", json={"username": name, "display_name": name.title(), "password": "labyrinth"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_auth_roundtrip(client: TestClient) -> None:
    register(client)
    assert client.post("/api/auth/register", json={"username": "Theseus", "display_name": "x",
                                                   "password": "labyrinth"}).status_code == 409
    assert client.post("/api/auth/login", json={"username": "theseus", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "THESEUS", "password": "labyrinth"}).status_code == 200
    assert client.get("/api/me").status_code == 401


def test_locking_and_maze(client: TestClient) -> None:
    h = register(client)
    mods = client.get("/api/modules", headers=h).json()
    assert mods[0]["unlocked"] and not mods[1]["unlocked"]
    assert client.get("/api/modules/anatomy", headers=h).status_code == 403

    bad = client.post("/api/activities/m0-maze/submit", headers=h, json={"data": {"path": ["A", "M"]}})
    assert bad.status_code == 422
    path = ["A", "B", "E", "H", "K", "M"]
    r = client.post("/api/activities/m0-maze/submit", headers=h, json={"data": {"path": path}}).json()
    assert r["reward"]["xp_gained"] == 50
    assert {b["id"] for b in r["reward"]["new_badges"]} == {"first-steps", "thread-bearer"}

    mods = client.get("/api/modules", headers=h).json()
    assert mods[1]["unlocked"]
    detail = client.get("/api/modules/anatomy", headers=h).json()
    assert detail["activities"][0]["config"]["graph"]["id"] == "anatomy"


def test_formative_quiz_flow_and_no_answer_leak(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "unlock_all", True)
    h = register(client)

    start = client.post("/api/activities/m1-quiz/attempts", headers=h).json()
    assert start["mode"] == "formative"
    assert all("answer" not in i and "explanation" not in i for i in start["items"])
    aid = start["attempt_id"]

    # a1: wrong twice, then right on the third try
    r = client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "a1", "answer": ["A"]}).json()
    assert not r["correct"] and r["tier"] == 1 and "hint" in r and "explanation" not in r
    r = client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "a1", "answer": ["B"]}).json()
    assert r["tier"] == 2 and "explanation" in r
    assert client.post(f"/api/attempts/{aid}/check", headers=h,
                       json={"item_id": "a1", "reveal": True}).status_code == 403
    r = client.post(f"/api/attempts/{aid}/check", headers=h,
                    json={"item_id": "a1", "answer": ["B", "C", "E"]}).json()
    assert r["correct"]

    early = client.post(f"/api/attempts/{aid}/finish", headers=h, json={})
    assert early.status_code == 409

    answers = {"a2": ["A-B", "A-C"], "a3": [0], "a4": [1], "a5": ["B", "C"], "a6": [2]}
    for iid, ans in answers.items():
        assert client.post(f"/api/attempts/{aid}/check", headers=h,
                           json={"item_id": iid, "answer": ans}).json()["correct"]
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={}).json()
    # 5 first-try (1.0) + one third-try (0.4) -> 5.4 / 6 = 0.9 -> 3 stars
    assert done["result"]["score"] == pytest.approx(0.9)
    assert done["reward"]["stars"] == 3
    m1 = next(m for m in done["mastery"] if m["objective"] == 1)
    assert m1["value"] == pytest.approx(0.9) and m1["evidence"] == 1


def test_trace_and_xp_is_not_farmable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "unlock_all", True)
    h = register(client)

    sloppy = [{"kind": "visit", "node": "C"}] + [{"kind": "visit", "node": n} for n in "BDECF"]
    r1 = client.post("/api/activities/m3-trace-1/submit", headers=h, json={"actions": sloppy}).json()
    assert r1["result"]["stars"] == 2 and r1["reward"]["xp_gained"] == round(80 * 2 / 3)

    perfect = [{"kind": "visit", "node": n} for n in "BDECF"]
    r2 = client.post("/api/activities/m3-trace-1/submit", headers=h, json={"actions": perfect}).json()
    assert r2["reward"]["xp_gained"] == 80 - round(80 * 2 / 3) and r2["reward"]["improved"]
    assert "deep-diver" in {b["id"] for b in r2["reward"]["new_badges"]}

    r3 = client.post("/api/activities/m3-trace-1/submit", headers=h, json={"actions": perfect}).json()
    assert r3["reward"]["xp_gained"] == 0


def test_summative_reports_per_objective(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "unlock_all", True)
    h = register(client)
    start = client.post("/api/activities/m6-final/attempts", headers=h).json()
    aid = start["attempt_id"]
    assert client.post(f"/api/attempts/{aid}/check", headers=h,
                       json={"item_id": "f1", "answer": ["C"]}).status_code == 403

    answers = {
        "f1": ["C", "F", "H"], "f2": [0],
        "f3": {"A": ["B", "C"], "B": ["A", "D", "E"], "C": ["A", "F"], "D": ["B"], "E": ["B"], "F": ["C"]},
        "f4": [0], "f5": list("ABCDEFGH"), "f6": list("CABDFE"), "f7": [0], "f8": [0], "f9": [0],
        "f10": "DFS uses a stack and goes deep down one branch before backtracking; BFS uses a queue and "
               "visits everything level by level.",
    }
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={"answers": answers}).json()
    assert done["result"]["passed"] and done["result"]["score"] == 1.0
    assert done["result"]["objectives"] == {str(i): 1.0 for i in range(1, 6)}
    assert {"minotaur-slayer", "flawless"} <= {b["id"] for b in done["reward"]["new_badges"]}

    me = client.get("/api/me", headers=h).json()
    assert me["level"]["xp"] == 300
    lb = client.get("/api/leaderboard", headers=h).json()
    assert lb["me"]["rank"] == 1 and lb["top"][0]["is_me"]
