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


def finish_lesson(c: TestClient, h: dict[str, str], activity_id: str) -> dict:
    from app.content.course import ACTIVITIES
    from app.content.lessons import LESSONS
    checks = LESSONS[ACTIVITIES[activity_id][1].config["lesson"]].checks()
    r = c.post(f"/api/activities/{activity_id}/submit", headers=h,
               json={"data": {"answers": {k.id: k.answer for k in checks}, "tries": {k.id: 1 for k in checks}}})
    assert r.status_code == 200, r.text
    return r.json()


INTRO = ["l1-graphs", "l2-representation", "l3-dfs", "l4-backtracking", "l5-bfs"]


def test_auth_roundtrip(client: TestClient) -> None:
    register(client)
    assert client.post("/api/auth/register", json={"username": "Theseus", "display_name": "x",
                                                   "password": "labyrinth"}).status_code == 409
    assert client.post("/api/auth/login", json={"username": "theseus", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "THESEUS", "password": "labyrinth"}).status_code == 200
    assert client.get("/api/me").status_code == 401


def test_leaderboard_badge_totals_match_profile(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import me as learner_api
    from app.services.gamification import Badge

    h = register(client)
    for earned in (0, 1):
        if earned:
            finish_lesson(client, h, "l1-graphs")
        profile = client.get("/api/me", headers=h).json()
        board = client.get("/api/leaderboard", headers=h).json()
        assert board["badge_total"] == len(profile["badges"])
        assert board["me"]["badges"] == sum(bool(b["earned_at"]) for b in profile["badges"]) == earned
        assert board["top"][0]["badges"] == earned

    original_total = board["badge_total"]
    monkeypatch.setattr(learner_api, "BADGES", [
        *learner_api.BADGES, Badge("test-badge", "Test Badge", "A newly available badge.", "star"),
    ])
    profile = client.get("/api/me", headers=h).json()
    board = client.get("/api/leaderboard", headers=h).json()
    assert board["badge_total"] == len(profile["badges"]) == original_total + 1
    assert board["me"]["badges"] == sum(bool(b["earned_at"]) for b in profile["badges"]) == 1


def test_locking_and_maze(client: TestClient) -> None:
    h = register(client)
    mods = client.get("/api/modules", headers=h).json()
    assert [m["slug"] for m in mods[:2]] == ["intro", "labyrinth"] and mods[0]["track"] == "course"
    assert mods[0]["unlocked"] and not mods[1]["unlocked"]
    assert client.get("/api/modules/labyrinth", headers=h).status_code == 403
    assert client.post("/api/activities/m0-maze/submit", headers=h,
                       json={"data": {"path": ["A", "B", "E", "H", "K", "M"]}}).status_code == 403

    for lesson in INTRO:
        finish_lesson(client, h, lesson)
    mods = client.get("/api/modules", headers=h).json()
    assert mods[0]["completed"] and mods[1]["unlocked"] and not mods[2]["unlocked"]
    assert client.get("/api/modules/anatomy", headers=h).status_code == 403

    bad = client.post("/api/activities/m0-maze/submit", headers=h, json={"data": {"path": ["A", "M"]}})
    assert bad.status_code == 422
    path = ["A", "B", "E", "H", "K", "M"]
    r = client.post("/api/activities/m0-maze/submit", headers=h, json={"data": {"path": path}}).json()
    assert r["reward"]["xp_gained"] == 50
    assert {b["id"] for b in r["reward"]["new_badges"]} == {"thread-bearer"}

    mods = client.get("/api/modules", headers=h).json()
    assert mods[2]["unlocked"]
    detail = client.get("/api/modules/anatomy", headers=h).json()
    assert detail["activities"][0]["config"]["graph"]["id"] == "anatomy"


def test_lessons_need_every_check_and_open_the_game(client: TestClient) -> None:
    h = register(client)
    intro = client.get("/api/modules/intro", headers=h).json()
    assert intro["track"] == "course" and [a["id"] for a in intro["activities"]] == INTRO
    lesson = intro["activities"][0]["config"]["lesson"]
    assert lesson["pages"][0]["figure"]["graphs"][0]["id"] == "intro-basic"  # graph ids are resolved
    assert client.get("/api/modules/anatomy", headers=h).status_code == 403

    # Lessons open in order, and only count once every check has been answered correctly.
    assert client.post("/api/activities/l2-representation/submit", headers=h, json={"data": {}}).status_code == 403
    checks = [p["check"] for p in lesson["pages"] if p["check"]]
    partial = {c["id"]: c["answer"] for c in checks[:-1]}
    wrong = {**partial, checks[-1]["id"]: (checks[-1]["answer"] + 1) % len(checks[-1]["options"])}
    for answers in (partial, wrong, {}):
        r = client.post("/api/activities/l1-graphs/submit", headers=h, json={"data": {"answers": answers}})
        assert r.status_code == 422

    first = finish_lesson(client, h, "l1-graphs")
    assert first["result"]["first_try"] == len(checks)
    assert {b["id"] for b in first["reward"]["new_badges"]} == {"first-steps"}
    assert first["reward"]["xp_gained"] == 20 and first["reward"]["next_activity"] == "l2-representation"
    assert finish_lesson(client, h, "l1-graphs")["reward"]["xp_gained"] == 0  # re-reading isn't farmable

    for lesson_id in INTRO[1:-1]:
        finish_lesson(client, h, lesson_id)
    last = finish_lesson(client, h, "l5-bfs")["reward"]
    assert "well-read" in {b["id"] for b in last["new_badges"]}
    assert last["next_activity"] == "m0-maze" and last["level"]["level"] == 2  # 5 x 20 XP

    me = client.get("/api/me", headers=h).json()
    assert me["recommendations"][0]["activity_id"] == "m0-maze"


def test_started_work_stays_open_when_content_is_added_before_it(
        client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A learner who started the game before the intro course existed keeps their place."""
    from app.core.config import settings
    h = register(client)
    monkeypatch.setattr(settings, "unlock_all", True)
    client.post("/api/activities/m0-maze/submit", headers=h, json={"data": {"path": ["A", "B", "E", "H", "K", "M"]}})
    client.post("/api/activities/m1-inspect/submit", headers=h,
                json={"data": {"discovered": ["vertex", "edge", "directed", "directed-edge", "degree"]}})
    monkeypatch.setattr(settings, "unlock_all", False)

    mods = {m["slug"]: m for m in client.get("/api/modules", headers=h).json()}
    assert mods["intro"]["unlocked"] and not mods["intro"]["completed"]
    assert mods["labyrinth"]["unlocked"] and mods["anatomy"]["unlocked"]
    assert [a["unlocked"] for a in mods["anatomy"]["activities"]] == [True, True]
    assert not mods["representation"]["unlocked"]


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

    from app.content.reserved_finals import FINAL_BANKS, FINAL_GRAPHS
    from app.services.grading import expected_answer
    answers = {i.id: expected_answer(i, FINAL_GRAPHS) for i in FINAL_BANKS["final-a"].items}
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


def test_representation_diagnostics_resume_and_preserve_reveal_gates(client: TestClient, unlocked) -> None:
    from app.content.graphs import GRAPHS
    from app.engine.graph import Graph

    h = register(client)
    start = client.post("/api/activities/m2-build/attempts", headers=h).json()
    assert all("option_feedback" not in i and "answer" not in i for i in start["items"])
    aid = start["attempt_id"]
    answer = {**Graph.from_spec(GRAPHS["build"]).adjacency(), "A": ["B", "C"]}
    row = client.post(f"/api/attempts/{aid}/check", headers=h,
                      json={"item_id": "r1", "answer": answer}).json()
    assert row["score"] == 0.8 and row["worth"] == 0.7 and row["tier"] == 1
    assert row["detail"]["row_feedback"]["A"]["missing_count"] == 1
    assert "answer" not in row and "explanation" not in row
    for tries in range(1, 4):
        response = client.post(f"/api/attempts/{aid}/check", headers=h,
                               json={"item_id": "r4", "answer": [2]}).json()
        assert response["tries"] == tries and response["tier"] == tries
        assert response["can_reveal"] == (tries == 3)
        assert "first 1" in response["detail"]["explanation"] and response["hint"]
        assert "answer" not in response and "explanation" not in response
        if tries == 1:
            resumed = client.post("/api/activities/m2-build/attempts", headers=h).json()
            assert resumed["attempt_id"] == aid
            assert resumed["results"]["r1"] == {k: v for k, v in row.items() if k not in {"revision", "evidence"}}
            assert resumed["results"]["r4"] == {k: v for k, v in response.items() if k not in {"revision", "evidence"}}
            assert client.post(f"/api/attempts/{aid}/check", headers=h,
                               json={"item_id": "r4", "reveal": True}).status_code == 403
    revealed = client.post(f"/api/attempts/{aid}/check", headers=h,
                           json={"item_id": "r4", "reveal": True}).json()
    assert revealed["answer"] == [0] and revealed["explanation"] and revealed["detail"] == {}
    for iid, correct in {
        "r1": Graph.from_spec(GRAPHS["build"]).adjacency(),
        "r2": Graph.from_spec(GRAPHS["build-directed"]).adjacency(), "r3": [0], "r5": [0],
    }.items():
        assert client.post(f"/api/attempts/{aid}/check", headers=h,
                           json={"item_id": iid, "answer": correct}).json()["correct"]
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={}).json()
    assert done["result"]["score"] == 0.74 and done["reward"]["stars"] == 2


def test_representation_final_feedback_is_withheld_until_submission(client: TestClient, unlocked) -> None:
    h = register(client)
    start = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert all("option_feedback" not in i and "answer" not in i for i in start["items"])
    aid = start["attempt_id"]
    for action in ("check", "hint"):
        assert client.post(f"/api/attempts/{aid}/{action}", headers=h,
                           json={"item_id": "f4", "answer": [2]}).status_code == 403
    assert client.put(f"/api/attempts/{aid}/draft", headers=h, json={
        "revision": 0, "request_id": "matrix-draft", "current_item": "f4", "answers": {"f4": [2]},
    }).status_code == 200
    resumed = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert resumed["results"] == {} and resumed["report"] is None
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={}).json()
    row = next(r for r in done["result"]["review"] if r["item_id"] == "f4")
    assert not row["correct"] and row["score"] == 0
    assert "every 1" in row["detail"]["explanation"] and row["answer"] == [0]
    closed = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert closed["report"]["result"]["review"] == done["result"]["review"]


def test_revision_review_is_owned_replayable_support_not_a_wrong_try(client: TestClient, unlocked) -> None:
    h = register(client)
    start = client.post("/api/activities/m2-build/attempts", headers=h).json()
    aid = start["attempt_id"]
    client.put(f"/api/attempts/{aid}/draft", headers=h, json={
        "revision": 0, "request_id": "select-matrix", "current_item": "r4", "answers": {"r4": [2]},
    })
    checked = client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "r4", "answer": [2]}).json()
    assert checked["review_topics"][0]["lesson"]["page_id"] == "matrix"
    body = {"revision": checked["revision"], "request_id": "read-matrix", "item_id": "r4",
            "topic_id": "matrix", "target": "lesson"}
    other = register(client, "another-learner")
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=other, json=body).status_code == 404
    response = client.post(f"/api/attempts/{aid}/review-topic", headers=h, json=body)
    assert response.status_code == 200
    assert response.json()["destination"]["page_id"] == "matrix"
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h, json=body).json() == response.json()
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h,
                       json={**body, "target": "practice"}).status_code == 409
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h,
                       json={**body, "request_id": "stale-review"}).status_code == 409
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert state["answers"] == {"r4": [2]} and state["current_item"] == "r4"
    assert state["results"]["r4"] == {k: v for k, v in checked.items() if k not in {"revision", "evidence"}}
    assert len(state["review_support"]) == 1 and state["review_support_from_revision"] == 0
    assert state["review_support"][0]["tries_before"] == 1
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h, json={
        **body, "revision": state["revision"], "request_id": "unknown-review", "topic_id": "storage",
    }).status_code == 422
    assert client.get(f"/api/attempts/{aid}", headers=h).json()["revision"] == state["revision"]
    right = client.post(f"/api/attempts/{aid}/check", headers=h, json={"item_id": "r4", "answer": [0]}).json()
    assert right["tries"] == 2 and right["hints"] == 0 and right["worth"] == 0.7


def test_revision_reviews_respect_activity_locks_and_final_secrecy(client: TestClient, unlocked, monkeypatch) -> None:
    from app.core.config import settings

    h = register(client)
    start = client.post("/api/activities/m2-build/attempts", headers=h).json()
    aid = start["attempt_id"]
    checked = client.post(f"/api/attempts/{aid}/check", headers=h,
                          json={"item_id": "r1", "answer": {"A": ["B"]}}).json()
    monkeypatch.setattr(settings, "unlock_all", False)
    body = {"revision": checked["revision"], "request_id": "locked-topic", "item_id": "r1",
            "topic_id": "adjacency-list", "target": "lesson"}
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h, json=body).status_code == 403
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert state["review_support"] == [] and state["revision"] == checked["revision"]
    topic = state["review_topics"]["r1"][0]
    assert not topic["lesson"]["unlocked"] and topic["fallback"]["unlocked"]
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h,
                       json={**body, "request_id": "available-lesson", "target": "fallback"}).status_code == 200
    monkeypatch.setattr(settings, "unlock_all", True)
    final = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert final["review_topics"] == {}
    assert client.post(f"/api/attempts/{final['attempt_id']}/review-topic", headers=h, json={
        "revision": 0, "request_id": "early-final-help", "item_id": "f4", "topic_id": "matrix", "target": "lesson",
    }).status_code == 403
    assert client.get(f"/api/attempts/{final['attempt_id']}", headers=h).json()["review_support"] == []


def test_revision_support_before_first_try_preserves_legacy_gaps(client: TestClient, unlocked) -> None:
    from app.content.graphs import GRAPHS
    from app.engine.graph import Graph

    h = register(client)
    start = client.post("/api/activities/m2-build/attempts", headers=h).json()
    aid = start["attempt_id"]
    database = app.dependency_overrides[get_db]()
    db = next(database)
    try:
        att = db.get(Attempt, aid)
        payload = dict(att.payload)
        payload.pop("review_support")
        payload.pop("review_support_from_revision")
        att.payload = payload
        db.commit()
    finally:
        database.close()
    assert client.get(f"/api/attempts/{aid}", headers=h).json()["review_support_from_revision"] is None
    body = {"revision": 0, "request_id": "pre-answer-review", "item_id": "r1",
            "topic_id": "objective-2", "target": "lesson"}
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h,
                       json={**body, "item_id": "r4"}).status_code == 422
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h, json=body).status_code == 200
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert state["results"] == {} and state["review_support_from_revision"] == 1
    assert state["review_support"][0]["tries_before"] == 0
    right = client.post(f"/api/attempts/{aid}/check", headers=h, json={
        "item_id": "r1", "answer": Graph.from_spec(GRAPHS["build"]).adjacency(),
    }).json()
    assert right["tries"] == 1 and right["hints"] == 0 and right["worth"] == 1
    assert client.post(f"/api/attempts/{aid}/review-topic", headers=h, json={
        **body, "revision": right["revision"], "request_id": "resolved-review",
    }).status_code == 409


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


def test_evidence_keeps_wrong_first_before_help_and_replayed_correct_retry(client, unlocked) -> None:
    h = register(client)
    start = client.post("/api/activities/m2-build/attempts", headers=h).json()
    aid = start["attempt_id"]
    assert start["evidence"]["complete_from_start"]
    wrong = client.post(f"/api/attempts/{aid}/check", headers=h, json={
        "item_id": "r3", "answer": [1], "revision": 0, "request_id": "wrong-first",
    }).json()
    row = next(r for r in wrong["evidence"]["items"] if r["item_id"] == "r3")
    first = row["first_response"]
    assert first["answer"] == [1] and not first["correct"] and first["score"] == 0
    assert first["kind"] == "first_unassisted_practice" and first["assistance_before"] == []
    assert first["sequence"] < row["assistance"][0]["sequence"]
    assert len(first["task_version"]) == 64 and not first["independent_final"]
    body = {"item_id": "r3", "answer": [0], "revision": wrong["revision"], "request_id": "right-retry"}
    right = client.post(f"/api/attempts/{aid}/check", headers=h, json=body).json()
    assert right["tries"] == 2 and right["worth"] == 0.7
    assert client.post(f"/api/attempts/{aid}/check", headers=h, json=body).json() == right
    restored = client.get(f"/api/attempts/{aid}", headers=h).json()
    row = next(r for r in restored["evidence"]["items"] if r["item_id"] == "r3")
    assert row["first_response"] == first and row["response_count"] == 2
    assert row["latest_response"]["correct"] and row["latest_response"]["kind"] == "assisted_retry"
    objective = client.get("/api/me", headers=h).json()["quiz_evidence"]["objectives"][1]
    assert objective["first_unassisted_practice"] == {"correct": 0, "total": 1}
    assert objective["assisted_retry"] == {"correct": 1, "total": 1}
    other = register(client, "evidence-other")
    assert client.get(f"/api/attempts/{aid}", headers=other).status_code == 404
    assert client.get("/api/me", headers=other).json()["quiz_evidence"]["objectives"][1]["assisted_retry"]["total"] == 0


def test_evidence_hint_first_and_repeat_issuance_remain_practice(client, unlocked) -> None:
    from app.content.assessments import ASSESSMENTS
    from app.services.grading import expected_answer

    h = register(client)
    aid = client.post("/api/activities/m1-quiz/attempts", headers=h).json()["attempt_id"]
    hint = client.post(f"/api/attempts/{aid}/hint", headers=h, json={
        "item_id": "a3", "revision": 0, "request_id": "hint-first",
    }).json()
    assert all(r["first_response"] is None for r in hint["evidence"]["items"])
    first = client.post(f"/api/attempts/{aid}/check", headers=h,
                        json={"item_id": "a3", "answer": [0]}).json()
    row = next(r for r in first["evidence"]["items"] if r["item_id"] == "a3")
    assert row["first_response"]["kind"] == "first_assisted_practice" and first["worth"] == 0.85
    for item in ASSESSMENTS["anatomy-check"].items:
        if item.id != "a3":
            client.post(f"/api/attempts/{aid}/check", headers=h,
                        json={"item_id": item.id, "answer": expected_answer(item)})
    client.post(f"/api/attempts/{aid}/finish", headers=h, json={})
    repeated = client.post("/api/activities/m1-quiz/attempts", headers=h, json={"new_attempt": True}).json()
    assert repeated["evidence"]["prior_exposure"] == "repeat"
    again = client.post(f"/api/attempts/{repeated['attempt_id']}/check", headers=h,
                        json={"item_id": "a3", "answer": [0]}).json()
    row = next(r for r in again["evidence"]["items"] if r["item_id"] == "a3")
    assert row["first_response"]["kind"] == "repeat_practice" and again["worth"] == 1


def test_evidence_pins_items_graphs_hints_and_resumes_published_version(client, unlocked, monkeypatch) -> None:
    from app.api import course
    from app.content.assessments import ASSESSMENTS
    from app.content.graphs import GRAPHS
    from app.engine.graph import Graph

    h = register(client)
    start = client.post("/api/activities/m2-build/attempts", headers=h).json()
    aid = start["attempt_id"]
    graph = start["items"][0]["graph"]
    original_hint = ASSESSMENTS["representation-check"].items[2].hint
    changed = ASSESSMENTS["representation-check"].model_copy(deep=True)
    changed.items[2].answer = [1]
    changed.items[2].hint = "A changed hint that must not replace the pinned one."
    monkeypatch.setitem(ASSESSMENTS, changed.id, changed)
    monkeypatch.setitem(GRAPHS, "build", {**graph, "edges": []})
    monkeypatch.setattr(course, "ASSESSMENT_VERSION", 3)
    resumed = client.post("/api/activities/m2-build/attempts", headers=h).json()
    assert resumed["attempt_id"] == aid and resumed["compatible"]
    assert resumed["items"] == start["items"] and resumed["assessment_version"] == 2
    hinted = client.post(f"/api/attempts/{aid}/hint", headers=h, json={"item_id": "r3"}).json()
    assert hinted["hint"] == original_hint
    assert client.post(f"/api/attempts/{aid}/check", headers=h,
                       json={"item_id": "r3", "answer": [0]}).json()["correct"]
    assert client.post(f"/api/attempts/{aid}/check", headers=h,
                       json={"item_id": "r1", "answer": Graph.from_spec(graph).adjacency()}).json()["correct"]
    assert all("answer" not in i and "hint" not in i and "option_feedback" not in i for i in resumed["items"])
    assert "content" not in resumed


def test_evidence_final_study_has_no_keys_and_blank_items_are_not_responses(client, unlocked) -> None:
    h = register(client)
    start = client.post("/api/activities/m6-final/attempts", headers=h).json()
    aid = start["attempt_id"]
    body = {"item_id": "f1", "activity_id": "l2-representation", "revision": 0, "request_id": "general-study"}
    studied = client.post(f"/api/attempts/{aid}/study", headers=h, json=body).json()
    assert client.post(f"/api/attempts/{aid}/study", headers=h, json=body).json() == studied
    assert all(r["first_response"] is None for r in studied["evidence"]["items"])
    assert all(len(r["assistance"]) == 1 and r["assistance"][0]["scope"] == "attempt"
               for r in studied["evidence"]["items"])
    restored = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert restored["results"] == {} and restored["review_topics"] == {}
    assert all("answer" not in item and "explanation" not in item for item in restored["items"])
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={
        "answers": {"f4": [0], "f3": {"A": []}, "f5": [], "f10": []},
        "revision": studied["revision"], "request_id": "final-submit",
    }).json()
    assert done["result"]["score"] == 0.1 and done["evidence"]["summary"]["unanswered_final_items"] == 9
    row = next(r for r in done["evidence"]["items"] if r["item_id"] == "f4")
    assert row["first_response"]["kind"] == "final_reserved_assisted" and row["first_response"]["correct"]
    assert not row["first_response"]["independent_final"] and len(row["first_response"]["assistance_before"]) == 1
    assert all(r["first_response"] is None for r in done["evidence"]["items"] if r["item_id"] != "f4")
    reopened = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert reopened["report"]["evidence"] == done["evidence"]


def test_evidence_failures_and_legacy_l1_records_do_not_fabricate_first_responses(client, unlocked) -> None:
    from app.content.graphs import GRAPHS
    from app.engine.graph import Graph

    h = register(client)
    aid = client.post("/api/activities/m2-build/attempts", headers=h).json()["attempt_id"]
    for body, status in [
        ({"item_id": "missing", "answer": [0]}, 404),
        ({"item_id": "r3", "answer": None}, 422),
        ({"item_id": "r3", "answer": [True]}, 422),
        ({"item_id": "r3", "answer": [0], "revision": 1}, 409),
    ]:
        assert client.post(f"/api/attempts/{aid}/check", headers=h, json=body).status_code == status
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert state["revision"] == 0 and state["results"] == {}
    assert all(r["response_count"] == 0 and r["assistance"] == [] for r in state["evidence"]["items"])
    body = {"item_id": "r1", "topic_id": "objective-2", "target": "lesson",
            "revision": 0, "request_id": "l1-review"}
    client.post(f"/api/attempts/{aid}/review-topic", headers=h, json=body)
    database = app.dependency_overrides[get_db]()
    db = next(database)
    try:
        att = db.get(Attempt, aid)
        att.payload = {k: v for k, v in att.payload.items() if k not in {"evidence", "content", "receipts"}}
        db.commit()
    finally:
        database.close()
    legacy = client.post("/api/activities/m2-build/attempts", headers=h).json()
    assert legacy["attempt_id"] == aid and not legacy["evidence"]["complete_from_start"]
    right = client.post(f"/api/attempts/{aid}/check", headers=h, json={
        "item_id": "r1", "answer": Graph.from_spec(GRAPHS["build"]).adjacency(),
    }).json()
    row = right["evidence"]["items"][0]
    assert row["first_response"]["kind"] == "history_unknown"
    assert row["first_response"]["assistance_before"][0]["source"] == "L1"
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert len(state["review_support"]) == 1 and state["review_support_from_revision"] == 0
    assert state["evidence"]["summary"]["unrecorded_attempts"] == 1


def test_evidence_study_respects_ownership_current_item_locks_and_stale_requests(client, unlocked, monkeypatch) -> None:
    from app.core.config import settings

    h = register(client)
    aid = client.post("/api/activities/m2-build/attempts", headers=h).json()["attempt_id"]
    body = {"item_id": "r1", "activity_id": "l2-representation", "revision": 0, "request_id": "study-once"}
    other = register(client, "study-other")
    assert client.post(f"/api/attempts/{aid}/study", headers=other, json=body).status_code == 404
    assert client.post(f"/api/attempts/{aid}/study", headers=h, json={**body, "item_id": "r3"}).status_code == 422
    monkeypatch.setattr(settings, "unlock_all", False)
    assert client.post(f"/api/attempts/{aid}/study", headers=h, json=body).status_code == 403
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert state["revision"] == 0 and all(r["assistance"] == [] for r in state["evidence"]["items"])
    monkeypatch.setattr(settings, "unlock_all", True)
    assert client.post(f"/api/attempts/{aid}/study", headers=h, json=body).status_code == 200
    assert client.post(f"/api/attempts/{aid}/study", headers=h,
                       json={**body, "request_id": "stale-study"}).status_code == 409
    assert client.post(f"/api/attempts/{aid}/study", headers=h,
                       json={**body, "activity_id": "m2-represent"}).status_code == 409
    state = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert state["results"] == {} and len(state["evidence"]["items"][0]["assistance"]) == 1
    checked = client.post(f"/api/attempts/{aid}/check", headers=h,
                          json={"item_id": "r3", "answer": [0]}).json()
    first = next(r for r in checked["evidence"]["items"] if r["item_id"] == "r3")["first_response"]
    assert first["kind"] == "first_assisted_practice" and first["assistance_before"][0]["scope"] == "attempt"
    assert checked["tries"] == 1 and checked["worth"] == 1


def test_evidence_closed_legacy_scores_remain_untouched_and_history_is_not_backfilled(client, unlocked) -> None:
    h = register(client)
    aid = client.post("/api/activities/m6-final/attempts", headers=h).json()["attempt_id"]
    client.post(f"/api/attempts/{aid}/finish", headers=h, json={"answers": {"f4": [0]}})
    database = app.dependency_overrides[get_db]()
    db = next(database)
    try:
        att = db.get(Attempt, aid)
        att.payload = {k: v for k, v in att.payload.items() if k not in {"evidence", "content", "receipts"}}
        original = {k: v for k, v in att.result.items() if k != "evidence_summary"}
        att.result = original
        db.commit()
        reopened = client.post("/api/activities/m6-final/attempts", headers=h).json()
        assert reopened["status"] == "closed" and reopened["report"]["result"]["score"] == 0.1
        assert reopened["evidence"]["schema_version"] is None
        assert all(r["first_response"] is None for r in reopened["evidence"]["items"])
        db.refresh(att)
        assert att.result == original and "evidence" not in att.payload
        profile = client.get("/api/me", headers=h).json()
        assert profile["quiz_evidence"]["unrecorded_attempts"] == 1
        assert all(r["final_fixed_set"]["total"] == 0 for r in profile["quiz_evidence"]["objectives"])
    finally:
        database.close()


def test_reserved_final_issuance_resume_exhaustion_and_explicit_repeat(client, unlocked) -> None:
    from app.content.reserved_finals import FINAL_BANKS, FINAL_GRAPHS
    from app.services.grading import expected_answer

    h = register(client)
    endpoint = "/api/activities/m6-final"
    available = client.get(f"{endpoint}/final-availability", headers=h).json()
    assert available["unused_versions"] == ["A", "B"] and not available["has_saved_attempt"]
    assert client.get(f"{endpoint}/final-availability", headers=h).json() == available
    first_id = None
    for variant in ("A", "B"):
        body = {"new_attempt": True, "request_id": f"start-{variant}"}
        start = client.post(f"{endpoint}/attempts", headers=h, json=body).json()
        aid = start["attempt_id"]
        if first_id is None:
            first_id = aid
        assert start["evidence"]["final_assignment"] == {
            "variant": variant, "purpose": "reserved", "unused_at_issuance": True,
        }
        assert start["assessment_version"] == 3
        resumed = client.post(f"{endpoint}/attempts", headers=h, json={**body, "request_id": f"other-{variant}"}).json()
        assert resumed["attempt_id"] == aid and resumed["items"] == start["items"]
        assert client.post(f"{endpoint}/attempts", headers=h,
                           json={**body, "repeat_practice": True}).status_code == 409
        bank = FINAL_BANKS[f"final-{variant.lower()}"]
        answers = {i.id: expected_answer(i, FINAL_GRAPHS) for i in bank.items}
        done_body = {"answers": answers, "revision": 0, "request_id": f"finish-{variant}"}
        done = client.post(f"/api/attempts/{aid}/finish", headers=h, json=done_body).json()
        assert done["result"]["score"] == 1 and done["reward"]["stars"] == 3
        assert all(r["first_response"]["independent_final"] and
                   r["first_response"]["kind"] == "final_reserved_unassisted" for r in done["evidence"]["items"])
        assert client.post(f"/api/attempts/{aid}/finish", headers=h, json=done_body).json() == done
        for request_id in (f"start-{variant}", f"other-{variant}"):
            acknowledged = client.post(f"{endpoint}/attempts", headers=h,
                                       json={**body, "request_id": request_id}).json()
            assert acknowledged["attempt_id"] == aid and acknowledged["status"] == "closed"
    exhausted = client.get(f"{endpoint}/final-availability", headers=h).json()
    assert exhausted["exhausted"] and exhausted["unused_versions"] == [] and exhausted["revision_topics"]
    denied = client.post(f"{endpoint}/attempts", headers=h, json={"new_attempt": True})
    assert denied.status_code == 409 and denied.json()["detail"]["code"] == "NO_UNUSED_FINAL"
    repeated = client.post(f"{endpoint}/attempts", headers=h, json={
        "new_attempt": True, "repeat_practice": True, "request_id": "repeat-start",
    }).json()
    assert repeated["evidence"]["final_assignment"] == {"variant": "A", "purpose": "repeat", "unused_at_issuance": False}
    done = client.post(f"/api/attempts/{repeated['attempt_id']}/finish", headers=h,
                       json={"answers": {"f4": [0]}}).json()
    first = done["evidence"]["items"][3]["first_response"]
    assert first["correct"] and not first["independent_final"] and first["kind"] == "final_repeat"
    again = client.get(f"/api/attempts/{first_id}", headers=h).json()
    assert again["evidence"]["final_assignment"]["variant"] == "A" and again["report"]["result"]["score"] == 1
    other = register(client, "unused-other")
    assert client.get(f"{endpoint}/final-availability", headers=other).json()["unused_versions"] == ["A", "B"]
    assert client.get(f"/api/attempts/{first_id}", headers=other).status_code == 404
    profile = client.get("/api/me", headers=h).json()["quiz_evidence"]["objectives"]
    assert all(r["final_reserved_unassisted"] == {"correct": 4, "total": 4} for r in profile)
    assert profile[1]["final_repeat"] == {"correct": 1, "total": 1}


def test_reserved_final_preserves_open_and_closed_legacy_bank(client, unlocked) -> None:
    h = register(client)
    database = app.dependency_overrides[get_db]()
    db = next(database)
    try:
        legacy = Attempt(user_id=client.get("/api/me", headers=h).json()["id"], activity_id="m6-final",
                         kind="quiz", status="open", result={}, payload={
                             "version": 2, "revision": 0, "items": {},
                             "draft": {"answers": {"f4": [2]}, "current_item": "f4", "reflections": {}},
                         })
        db.add(legacy)
        db.commit()
        aid = legacy.id
        resumed = client.post("/api/activities/m6-final/attempts", headers=h).json()
        assert resumed["attempt_id"] == aid and resumed["assessment_version"] == 2
        assert resumed["items"][2]["graph"]["id"] == "tree"
        assert resumed["answers"] == {"f4": [2]} and resumed["evidence"]["final_assignment"] is None
        closed = client.post(f"/api/attempts/{aid}/finish", headers=h, json={}).json()
        db.refresh(legacy)
        stored = legacy.result
        first = closed["evidence"]["items"][3]["first_response"]
        assert first["kind"] == "final_fixed_set" and not first["independent_final"]
        assert client.get("/api/activities/m6-final/final-availability", headers=h).json()["unused_versions"] == ["A", "B"]
        fresh = client.post("/api/activities/m6-final/attempts", headers=h, json={"new_attempt": True}).json()
        assert fresh["evidence"]["final_assignment"]["variant"] == "A"
        db.refresh(legacy)
        assert legacy.result == stored and legacy.payload["content"]["bank_version"] == 2
    finally:
        database.close()


def test_reserved_final_pin_survives_catalogue_changes_and_failed_requests(client, unlocked, monkeypatch) -> None:
    from app.content.assessments import ASSESSMENT_VERSIONS
    from app.content.reserved_finals import FINAL_BANKS, FINAL_GRAPHS

    h = register(client)
    start = client.post("/api/activities/m6-final/attempts", headers=h).json()
    aid = start["attempt_id"]
    changed = FINAL_BANKS["final-a"].model_copy(deep=True)
    changed.items[3].answer = [1]
    monkeypatch.setitem(ASSESSMENT_VERSIONS[3], "final-a", changed)
    graph = start["items"][4]["graph"]
    monkeypatch.setitem(FINAL_GRAPHS, graph["id"], {**graph, "edges": []})
    resumed = client.post("/api/activities/m6-final/attempts", headers=h).json()
    assert resumed["attempt_id"] == aid and resumed["items"] == start["items"]
    assert client.post(f"/api/attempts/{aid}/finish", headers=h,
                       json={"answers": {"f4": [True]}}).status_code == 422
    assert client.post(f"/api/attempts/{aid}/finish", headers=h,
                       json={"answers": {"f4": [0]}, "revision": 2}).status_code == 409
    restored = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert restored["revision"] == 0 and all(r["response_count"] == 0 for r in restored["evidence"]["items"])
    assert restored["final_availability"]["unused_versions"] == ["B"]
    assert client.put(f"/api/attempts/{aid}/draft", headers=h, json={
        "revision": 0, "request_id": "earlier-draft", "current_item": "f4", "answers": {"f4": [2]},
    }).status_code == 200
    done = client.post(f"/api/attempts/{aid}/finish", headers=h, json={"answers": {"f4": [0]}}).json()
    assert done["result"]["score"] == 0.1 and done["evidence"]["summary"]["unanswered_final_items"] == 9
    assert done["evidence"]["items"][3]["first_response"]["independent_final"]
    reopened = client.get(f"/api/attempts/{aid}", headers=h).json()
    assert reopened["answers"] == {"f4": [0]} and reopened["evidence"]["items"][3]["first_response"]["answer"] == [0]


def test_reserved_final_exhaustion_recommends_the_diagnosed_lesson_section(client, unlocked) -> None:
    h = register(client)
    for _ in range(2):
        start = client.post("/api/activities/m6-final/attempts", headers=h, json={"new_attempt": True}).json()
        client.post(f"/api/attempts/{start['attempt_id']}/finish", headers=h, json={"answers": {"f4": [2]}})
    available = client.get("/api/activities/m6-final/final-availability", headers=h).json()
    assert available["exhausted"]
    matrix = [t for t in available["revision_topics"] if t["specific"] and t["lesson"]["page_id"] == "matrix"]
    assert len(matrix) == 1
    saved = client.get("/api/me", headers=h).json()
    assert client.get("/api/activities/m6-final/final-availability", headers=h).json() == available
    assert client.get("/api/me", headers=h).json() == saved


@pytest.mark.skipif(not os.environ.get("ARIADNE_TEST_DATABASE_URL", "").startswith("postgresql"),
                    reason="Requires the explicitly configured isolated PostgreSQL database")
def test_reserved_final_postgres_concurrent_allocation_and_start_receipts(client, unlocked) -> None:
    from concurrent.futures import ThreadPoolExecutor

    h = register(client)
    endpoint = "/api/activities/m6-final/attempts"
    with ThreadPoolExecutor(max_workers=4) as pool:
        for variant in ("A", "B"):
            bodies = [{"new_attempt": True, "request_id": f"concurrent-{variant}-{n}"} for n in range(4)]
            starts = list(pool.map(lambda b: client.post(endpoint, headers=h, json=b).json(), bodies))
            aid = starts[0]["attempt_id"]
            assert {s["attempt_id"] for s in starts} == {aid}
            assert all(s["evidence"]["final_assignment"]["variant"] == variant for s in starts)
            finish = {"answers": {"f4": [0]}, "revision": 0, "request_id": f"finish-{variant}"}
            results = list(pool.map(lambda _, aid=aid, finish=finish: client.post(f"/api/attempts/{aid}/finish", headers=h,
                                                          json=finish).json(), range(4)))
            assert all(r == results[0] for r in results)
            retries = list(pool.map(lambda b: client.post(endpoint, headers=h, json=b).json(), bodies))
            assert all(s["attempt_id"] == aid and s["status"] == "closed" for s in retries)
    assert client.get("/api/activities/m6-final/final-availability", headers=h).json()["used_versions"] == ["A", "B"]
