"""End-to-end API tests on an in-memory SQLite database."""

import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app
from app.models import Attempt, User


@pytest.fixture
def client() -> Iterator[TestClient]:
    test_url = os.environ.get("ARIADNE_TEST_DATABASE_URL")
    if test_url:
        assert (make_url(test_url).database or "").startswith("ariadne_test_"), "Use a dedicated test database"
        engine = create_engine(test_url)
    else:
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
    Base.metadata.drop_all(engine)
    engine.dispose()


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
    # Level 2 is the idea in full plus a visual cue; the worked explanation waits for the answer.
    assert r["tier"] == 2 and r["focus"] == ["D"] and "explanation" not in r
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


def test_hints_on_request_are_levelled_and_cheap(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "unlock_all", True)
    h = register(client)
    start = client.post("/api/activities/m1-quiz/attempts", headers=h).json()
    assert all("hint" not in i and "hint2" not in i and "focus" not in i for i in start["items"])
    aid = start["attempt_id"]

    def ask(iid: str) -> dict:
        return client.post(f"/api/attempts/{aid}/hint", headers=h, json={"item_id": iid}).json()

    # a3, before any try: nudge first, then the full idea; asking again is free and repeats level 2.
    r = ask("a3")
    assert (r["level"], r["charged"], r["worth"]) == (1, True, 0.85) and r["hint"] and r["focus"] == []
    r = ask("a3")
    assert (r["level"], r["charged"], r["worth"]) == (2, True, 0.7)
    r = ask("a3")
    assert (r["level"], r["charged"], r["hints"], r["worth"]) == (2, False, 2, 0.7)

    # a1: one wrong try already showed level 1, so a hint jumps to level 2 with its visual cue.
    client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "a1", "answer": ["A"]})
    r = ask("a1")
    assert (r["level"], r["focus"], r["worth"]) == (2, ["D"], 0.55)

    answers = {"a1": ["B", "C", "E"], "a2": ["A-B", "A-C"], "a3": [0], "a4": [1], "a5": ["B", "C"], "a6": [2]}
    for iid, ans in answers.items():
        assert client.post(f"/api/attempts/{aid}/check", headers=h,
                           json={"item_id": iid, "answer": ans}).json()["correct"]
    assert client.post(f"/api/attempts/{aid}/hint", headers=h, json={"item_id": "a1"}).status_code == 409

    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={}).json()
    # a1: second try with one hint (0.7 - 0.15) · a3: first try with two hints (1.0 - 0.3) · four clean
    assert done["result"]["score"] == pytest.approx((0.55 + 0.7 + 4) / 6, abs=1e-3)
    assert {r["item_id"]: r["hints"] for r in done["result"]["review"]}["a3"] == 2

    final = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert client.post(f"/api/attempts/{final['attempt_id']}/hint", headers=h,
                       json={"item_id": "f1"}).status_code == 403


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
        "f10": [2],
    }
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={"answers": answers}).json()
    assert done["result"]["passed"] and done["result"]["score"] == 1.0
    assert done["result"]["objectives"] == {str(i): 1.0 for i in range(1, 6)}
    assert {"minotaur-slayer", "flawless"} <= {b["id"] for b in done["reward"]["new_badges"]}

    me = client.get("/api/me", headers=h).json()
    assert me["level"]["xp"] == 300
    lb = client.get("/api/leaderboard", headers=h).json()
    assert lb["me"]["rank"] == 1 and lb["top"][0]["is_me"]


@pytest.fixture
def unlocked(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings
    monkeypatch.setattr(settings, "unlock_all", True)


def test_account_resume_preserves_drafts_and_disclosed_support(client: TestClient, unlocked) -> None:
    h = register(client)
    aid = client.post("/api/activities/m1-quiz/attempts", headers=h).json()["attempt_id"]
    for _ in range(3):
        client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "a1", "answer": ["A"]})
    client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "a1", "reveal": True})
    client.post(f"/api/attempts/{aid}/hint", headers=h, json={"item_id": "a2"})
    client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "a2", "answer": ["A-B", "A-C"]})
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    draft = {"revision": state["revision"], "request_id": "save", "current_item": "a3",
             "answers": {**state["answers"], "a3": [0]}}
    assert client.put(f"/api/attempts/{aid}/draft", headers=h, json=draft).status_code == 200
    login = client.post("/api/auth/login", json={"username": "theseus", "password": "labyrinth"}).json()
    resumed = client.post("/api/activities/m1-quiz/attempts",
                          headers={"Authorization": f"Bearer {login['token']}"}).json()
    assert resumed["attempt_id"] == aid
    assert resumed["answers"]["a3"] == [0] and resumed["current_item"] == "a3"
    assert resumed["results"]["a1"]["tries"] == 3 and resumed["revealed"]["a1"]
    assert resumed["results"]["a2"]["correct"] and resumed["results"]["a2"]["hints"] == 1
    assert resumed["hints"]["a2"]["level"] == 1 and resumed["last"]["a2"] == "check"
    assert "answer" not in resumed["results"]["a2"] or resumed["results"]["a2"]["answer"] == ["A-B", "A-C"]
    assert all("answer" not in item for item in resumed["items"])


def test_final_draft_and_reflection_do_not_reveal_or_change_grades(client: TestClient, unlocked) -> None:
    h = register(client)
    start = client.post("/api/activities/m6-final/attempts", headers=h).json()
    aid = start["attempt_id"]
    body = {"revision": 0, "request_id": "draft", "answers": {"f10": [1]}, "current_item": "f10",
            "reflections": {"f10": "DFS uses a stack and goes deep; BFS uses a queue and goes level by level."}}
    assert client.put(f"/api/attempts/{aid}/draft", headers=h, json=body).status_code == 200
    resumed = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert resumed["attempt_id"] == aid and resumed["answers"] == body["answers"]
    assert resumed["reflections"] == body["reflections"]
    assert resumed["results"] == {} and resumed["hints"] == {} and resumed["report"] is None
    assert all("answer" not in i and "explanation" not in i for i in resumed["items"])
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={}).json()
    row = next(r for r in done["result"]["review"] if r["item_id"] == "f10")
    assert not row["correct"] and row["score"] == 0


def test_request_retries_are_idempotent_and_stale_saves_cannot_erase_checks(client: TestClient, unlocked) -> None:
    h = register(client)
    aid = client.post("/api/activities/m1-quiz/attempts", headers=h).json()["attempt_id"]
    hint = {"item_id": "a1", "revision": 0, "request_id": "hint-once"}
    first = client.post(f"/api/attempts/{aid}/hint", headers=h, json=hint).json()
    assert client.post(f"/api/attempts/{aid}/hint", headers=h, json=hint).json() == first
    assert first["hints"] == 1
    check = {"item_id": "a1", "answer": ["B", "C", "E"], "revision": first["revision"], "request_id": "check-once"}
    result = client.post(f"/api/attempts/{aid}/check", headers=h, json=check).json()
    assert result["tries"] == 1 and result["correct"]
    assert client.post(f"/api/attempts/{aid}/check", headers=h, json=check).json() == result
    assert client.post(f"/api/attempts/{aid}/check", headers=h,
                       json={**check, "answer": ["A"]}).status_code == 409
    stale = {"revision": 0, "answers": {"a1": ["A"]}, "current_item": "a1", "request_id": "stale"}
    assert client.put(f"/api/attempts/{aid}/draft", headers=h, json=stale).status_code == 409
    assert client.put(f"/api/attempts/{aid}/draft", headers=h,
                      json={**stale, "revision": result["revision"]}).status_code == 409
    restored = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert restored["results"]["a1"]["correct"] and restored["answers"]["a1"] == check["answer"]


def test_only_owner_can_read_or_mutate_a_quiz(client: TestClient, unlocked) -> None:
    h = register(client)
    aid = client.post("/api/activities/m1-quiz/attempts", headers=h).json()["attempt_id"]
    other = register(client, "other")
    assert client.get(f"/api/attempts/{aid}", headers=other).status_code == 404
    assert client.put(f"/api/attempts/{aid}/draft", headers=other,
                      json={"revision": 0, "answers": {}, "current_item": "a1"}).status_code == 404
    for endpoint, body in [("hint", {"item_id": "a1"}), ("check", {"item_id": "a1", "answer": []}), ("finish", {})]:
        assert client.post(f"/api/attempts/{aid}/{endpoint}", headers=other, json=body).status_code == 404


def test_finish_retry_does_not_repeat_rewards_and_retakes_are_explicit(client: TestClient, unlocked) -> None:
    h = register(client)
    aid = client.post("/api/activities/m6-final/attempts", headers=h).json()["attempt_id"]
    # Contradictory reflection cannot spoil a correctly selected reason.
    draft = {"revision": 0, "request_id": "draft", "answers": {"f10": [2]}, "current_item": "f10",
             "reflections": {"f10": "DFS uses a queue while BFS uses a stack; DFS goes level by level and BFS goes deep."}}
    client.put(f"/api/attempts/{aid}/draft", headers=h, json=draft)
    body = {"revision": 1, "request_id": "finish-once"}
    first = client.post(f"/api/attempts/{aid}/finish", headers=h, json=body).json()
    assert first["result"]["review"][-1]["correct"]
    me = client.get("/api/me", headers=h).json()
    assert client.post(f"/api/attempts/{aid}/finish", headers=h, json=body).json() == first
    assert client.get("/api/me", headers=h).json() == me
    closed = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert closed["attempt_id"] == aid and closed["status"] == "closed"
    assert closed["report"]["result"] == first["result"]
    assert closed["reflections"] == draft["reflections"]
    new = client.post("/api/activities/m6-final/attempts", headers=h, json={"new_attempt": True}).json()
    assert new["attempt_id"] != aid and new["status"] == "open"
    assert client.post("/api/activities/m6-final/attempts", headers=h,
                       json={"new_attempt": True}).json()["attempt_id"] == new["attempt_id"]


def test_legacy_attempts_are_preserved_without_reusing_old_grades(client: TestClient, unlocked) -> None:
    h = register(client)
    dependency = app.dependency_overrides[get_db]()
    db = next(dependency)
    try:
        user = db.scalar(select(User).where(User.username == "theseus"))
        legacy = Attempt(user_id=user.id, activity_id="m5-quiz", kind="quiz", status="open",
                         payload={"items": {"c5": {"correct": True, "tries": 1}}}, result={})
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id
        fresh = client.post("/api/activities/m5-quiz/attempts", headers=h).json()
        assert fresh["attempt_id"] != legacy_id and fresh["results"] == {} and fresh["notice"]
        db.refresh(legacy)
        assert legacy.status == "superseded" and legacy.payload["items"]["c5"]["correct"]
    finally:
        dependency.close()


@pytest.mark.skipif(not os.environ.get("ARIADNE_TEST_DATABASE_URL"), reason="Requires isolated PostgreSQL")
def test_postgres_concurrent_starts_saves_hints_and_finish(client: TestClient, unlocked, monkeypatch) -> None:
    h = register(client)
    with ThreadPoolExecutor(max_workers=4) as pool:
        starts = list(pool.map(lambda _: client.post("/api/activities/m1-quiz/attempts", headers=h).json(), range(4)))
        aid = starts[0]["attempt_id"]
        assert {s["attempt_id"] for s in starts} == {aid}
        saves = list(pool.map(lambda i: client.put(f"/api/attempts/{aid}/draft", headers=h, json={
            "revision": 0, "request_id": f"save-{i}", "answers": {"a1": ["A"]}, "current_item": "a1",
        }).status_code, range(4)))
        assert sorted(saves) == [200, 409, 409, 409]
        hint = {"revision": 1, "request_id": "hint-once", "item_id": "a1"}
        hints = list(pool.map(lambda _: client.post(f"/api/attempts/{aid}/hint", headers=h, json=hint).json(), range(4)))
        assert all(r == hints[0] for r in hints) and hints[0]["hints"] == 1
        final = client.post("/api/activities/m6-final/attempts", headers=h).json()["attempt_id"]
        body = {"revision": 0, "request_id": "finish-once", "answers": {"f10": [2]}}
        finishes = list(pool.map(lambda _: client.post(f"/api/attempts/{final}/finish", headers=h, json=body).json(), range(4)))
        assert all(r == finishes[0] for r in finishes)
        assert next(m for m in client.get("/api/me", headers=h).json()["mastery"] if m["objective"] == 5)["evidence"] == 1

        from app.api import course
        from app.content.assessments import ASSESSMENTS
        from app.content.course import ACTIVITIES
        from app.services.grading import expected_answer

        ready = []
        for activity_id in ["m1-quiz", "m5-quiz"]:
            opened = client.post(f"/api/activities/{activity_id}/attempts", headers=h).json()
            bank = ASSESSMENTS[ACTIVITIES[activity_id][1].config["assessment"]]
            for item in bank.items:
                checked = client.post(f"/api/attempts/{opened['attempt_id']}/check", headers=h,
                                      json={"item_id": item.id, "answer": expected_answer(item)})
                assert checked.json()["correct"]
            ready.append(opened["attempt_id"])
        original_lock = course._lock_learner
        barrier = Barrier(2)

        def lock_after_both_users_loaded(user, db):
            barrier.wait(timeout=10)
            original_lock(user, db)

        monkeypatch.setattr(course, "_lock_learner", lock_after_both_users_loaded)
        rewards = list(pool.map(lambda a: client.post(f"/api/attempts/{a}/finish", headers=h, json={}).json(), ready))
        assert all(r["reward"]["xp_gained"] > 0 for r in rewards)
        expected_xp = sum(ACTIVITIES[a][1].xp for a in ["m1-quiz", "m5-quiz"])
        assert client.get("/api/me", headers=h).json()["level"]["xp"] == expected_xp
