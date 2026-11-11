"""Engine + content tests.

The content tests matter as much as the algorithm tests: every 'expected order' quoted in
a quiz explanation is recomputed here, so a typo in course content fails CI.
"""

import pytest

from app.content.assessments import ASSESSMENTS
from app.content.course import ACTIVITIES, MODULES, MODULES_BY_SLUG, OBJECTIVES
from app.content.graphs import GRAPHS
from app.content.lessons import LESSONS
from app.engine.graph import Graph
from app.engine.replay import TraceAction, grade_trace
from app.engine.traversal import bfs_order, dfs_order, dfs_trace
from app.services.gamification import has_cycle, level_info
from app.services.grading import grade_item


def G(gid: str) -> Graph:
    return Graph.from_spec(GRAPHS[gid])


# --- traversal ------------------------------------------------------------------------------

@pytest.mark.parametrize(("gid", "start", "dfs", "bfs"), [
    ("tree", "A", "ABDECF", "ABCDEF"),
    ("loops", "A", "ABDFEC", "ABCDEF"),
    ("network", "A", "ABDGEFCH", "ABCDEFGH"),
    ("corridors", "A", "ABCDEFG", "ABFCEGD"),
    ("cycle", "A", "ABCDEFG", "ABFCEDG"),
    ("wide", "A", "ABEJFCGDHI", "ABCDEFGHIJ"),
    ("final-1", "A", "ABCDEFGH", "ABFCEGHD"),
    ("final-2", "C", "CABDFE", "CAEBDF"),
    ("intro-tree", "A", "ABDECFG", "ABCDEFG"),
    ("intro-corridor", "A", "ABCDEFG", "ABFCEGD"),
])
def test_orders(gid: str, start: str, dfs: str, bfs: str) -> None:
    assert "".join(dfs_order(G(gid), start)) == dfs
    assert "".join(bfs_order(G(gid), start)) == bfs


def test_dfs_trace_stack_mirrors_recursion() -> None:
    ev = dfs_trace(G("tree"), "A")
    assert [(e.kind, e.node) for e in ev][:5] == [
        ("visit", "A"), ("visit", "B"), ("visit", "D"), ("backtrack", "D"), ("visit", "E")]
    assert ev[-1].stack == ()  # traversal ends with an empty stack
    assert ev[3].stack == ("A", "B")


def test_directed_edges_are_one_way() -> None:
    g = G("anatomy-directed")
    assert "D" in g.neighbours("B") and "B" not in g.neighbours("D")


def test_has_cycle() -> None:
    assert not has_cycle(G("tree")) and not has_cycle(G("wide"))
    assert has_cycle(G("loops")) and has_cycle(G("cycle")) and has_cycle(G("labyrinth"))
    assert has_cycle(G("final-2"))  # B -> D -> F -> B


# --- replay grading ----------------------------------------------------------------------------

def visits(nodes: str) -> list[TraceAction]:
    return [TraceAction(kind="visit", node=n) for n in nodes]


def test_perfect_auto_trace_gets_three_stars() -> None:
    r = grade_trace(G("tree"), "A", visits("BDECF"), auto_backtrack=True)
    assert r.completed and r.stars == 3 and r.score == 1.0 and r.mistakes == 0


def test_mistakes_are_classified() -> None:
    acts = [*visits("C"),  # wrong_order (B comes first)
            *visits("B"), *visits("F"),  # not_adjacent from B
            *visits("A"),  # already visited
            *visits("DECF")]
    r = grade_trace(G("tree"), "A", acts, auto_backtrack=True)
    assert r.completed
    assert r.breakdown == {"wrong_order": 1, "not_adjacent": 1, "already_visited": 1}
    # 5 correct, 3 mistakes -> (5 - 0.75) / 5 = 0.85: completed without reveals -> 2 stars
    assert r.score == pytest.approx(0.85) and r.stars == 2


def test_manual_backtracking() -> None:
    bt = TraceAction(kind="backtrack")
    # corridors: A B C D | pop D, pop C | E | pop E, pop B | F G | pop G, pop F, pop A
    acts = [*visits("BCD"), bt, bt, *visits("E"), bt, bt, *visits("FG"), bt, bt, bt]
    r = grade_trace(G("corridors"), "A", acts, auto_backtrack=False)
    assert r.completed and r.stars == 3

    early = [*visits("B"), bt]  # B still has unvisited neighbours
    r2 = grade_trace(G("corridors"), "A", early, auto_backtrack=False)
    assert r2.breakdown == {"premature_backtrack": 1} and not r2.completed

    stuck = [*visits("BCD"), *visits("E")]  # at dead end D, tried to jump instead of popping
    r3 = grade_trace(G("corridors"), "A", stuck, auto_backtrack=False)
    assert r3.breakdown == {"should_backtrack": 1}


def test_reveals_cap_stars() -> None:
    acts = [TraceAction(kind="hint"), TraceAction(kind="reveal"), *visits("DECF")]
    r = grade_trace(G("tree"), "A", acts, auto_backtrack=True)
    assert r.completed and r.reveals == 1 and r.hints == 1 and r.stars == 1


def test_incomplete_trace_scores_zero() -> None:
    r = grade_trace(G("tree"), "A", visits("BD"), auto_backtrack=True)
    assert not r.completed and r.stars == 0 and r.score == 0


# --- content integrity -------------------------------------------------------------------------

def test_every_activity_references_real_content() -> None:
    for _module, act in ACTIVITIES.values():
        for key in ("graph", "directed_graph"):
            if key in act.config:
                assert act.config[key] in GRAPHS, act.id
        if act.kind == "quiz":
            assert act.config["assessment"] in ASSESSMENTS, act.id
        if act.kind == "lesson":
            assert act.config["lesson"] in LESSONS, act.id
        if "start" in act.config:
            assert act.config["start"] in G(act.config["graph"]).nodes


def test_every_objective_is_assessed_in_the_final() -> None:
    final_objectives = {i.objective for i in ASSESSMENTS["final"].items}
    assert final_objectives == {o.id for o in OBJECTIVES}


def test_quiz_answers_are_right() -> None:
    for a in ASSESSMENTS.values():
        for item in a.items:
            if item.graph:
                assert item.graph in GRAPHS
            if item.type == "mcq":
                assert item.options and all(0 <= i < len(item.options) for i in item.answer)
            if item.type == "graph_select":
                g = G(item.graph)
                universe = set(g.nodes) if item.select == "nodes" else g.edge_ids()
                assert set(item.answer) <= universe, item.id


def test_select_items_match_graph_facts() -> None:
    assert sorted(G("anatomy").neighbours("D")) == ["B", "C", "E"]
    assert sorted(G("final-1").neighbours("E")) == ["C", "F", "H"]
    assert list(G("anatomy-directed").neighbours("A")) == ["B", "C"]


def test_formative_items_have_full_scaffolding() -> None:
    """Every practice question offers both hint levels, and its visual cue rings real vertices."""
    for a in ASSESSMENTS.values():
        for item in a.items:
            if a.mode == "formative":
                assert item.hint and item.hint2, item.id
            if item.focus:
                assert item.graph and set(item.focus) <= set(G(item.graph).nodes), item.id
            for c in item.rubric or []:
                assert c.nudge, c.id


def test_module_order_is_contiguous() -> None:
    for track in ("course", "game"):
        orders = [m.order for m in MODULES if m.track == track]
        assert orders == list(range(len(orders))), track
    # The intro course comes before the game it prepares learners for.
    assert [m.track for m in MODULES] == sorted((m.track for m in MODULES), key=["course", "game"].index)


# --- intro course ------------------------------------------------------------------------------

def test_lessons_are_well_formed() -> None:
    check_ids: list[str] = []
    for lesson in LESSONS.values():
        assert lesson.checks(), lesson.id
        assert lesson.practice in MODULES_BY_SLUG, lesson.id
        for page in lesson.pages:
            fig = page.figure
            if fig:
                assert all(g in GRAPHS for g in fig.graphs), page.id
                needs = {"graph": 1, "neighbours": 1, "representation": 1, "trace": 1, "orders": 1}
                assert len(fig.graphs) >= needs.get(fig.kind, 0), page.id
                if fig.kind in ("trace", "orders"):
                    assert fig.start in G(fig.graphs[0]).nodes, page.id
                for gid in fig.graphs:
                    universe = set(G(gid).nodes) | G(gid).edge_ids()
                    assert set(fig.highlight) <= universe, (page.id, gid)
            if page.check:
                c = page.check
                assert 0 <= c.answer < len(c.options) and len(c.why) == len(c.options), c.id
                assert len(set(c.options)) == len(c.options), c.id
                check_ids.append(c.id)
    assert len(check_ids) == len(set(check_ids))


def test_every_objective_has_a_lesson_and_its_module_links_back() -> None:
    lesson_activity = {a.config["lesson"]: a for m in MODULES if m.track == "course" for a in m.activities}
    assert {LESSONS[k].objective for k in lesson_activity} == {o.id for o in OBJECTIVES}
    for key, act in lesson_activity.items():
        assert act.objective == LESSONS[key].objective
        assert MODULES_BY_SLUG[LESSONS[key].practice].lesson == act.id, key
    for m in MODULES:
        if m.track == "game" and m.objective:
            assert m.lesson and ACTIVITIES[m.lesson][1].kind == "lesson", m.slug


def test_lesson_checks_match_graph_facts() -> None:
    """Every graph fact a lesson check (or its explanation) relies on, recomputed."""
    basic, directed = G("intro-basic"), G("intro-basic-directed")
    assert len(basic.nodes) == 6 and len(basic.edge_ids()) == 6
    assert basic.adjacency()["B"] == ["A", "C", "D"] and basic.degree("B") == 3
    assert basic.degree("D") == 3 and basic.degree("E") == basic.degree("F") == 1
    assert list(directed.neighbours("D")) == ["E"]
    assert {u for u in directed.nodes if "D" in directed.neighbours(u)} == {"B", "F"}
    assert {"A-B", "B-C", "A-C"} <= basic.edge_ids() and "B-F" not in basic.edge_ids()

    rep_u, rep_d = G("intro-rep"), G("intro-rep-directed")
    assert rep_u.adjacency()["B"] == ["A", "C", "D"]
    assert rep_d.adjacency()["D"] == [] and {"B->D", "E->D"} <= rep_d.edge_ids()

    assert list(G("intro-tree").neighbours("B")) == ["A", "D", "E"]

    corridor = G("intro-corridor")
    events = dfs_trace(corridor, "A")
    kinds = [(e.kind, e.node) for e in events]
    d = kinds.index(("backtrack", "D"))
    assert kinds[d + 1] == ("backtrack", "C") and kinds[d + 2] == ("visit", "E")  # the double pop
    at_f = next(e for e in events if e.kind == "visit" and e.node == "F")
    assert at_f.visited == set("ABCDEF") and list(corridor.neighbours("F")) == ["A", "E", "G"]
    at_g = next(e for e in events if e.kind == "visit" and e.node == "G")
    assert at_g.stack == tuple("ABEFG")
    assert {"A-B", "B-E", "E-F", "A-F", "F-G"} <= corridor.edge_ids()  # the loop, and A-F-G is shorter


# --- item grading -----------------------------------------------------------------------------

def _item(aid: str, iid: str):
    return next(i for i in ASSESSMENTS[aid].items if i.id == iid)


def test_grade_adjacency_and_order() -> None:
    adj = _item("representation-check", "r1")
    perfect = G("build").adjacency()
    assert grade_item(adj, perfect).correct
    wrong = {**perfect, "A": ["B"]}
    g = grade_item(adj, wrong)
    assert not g.correct and g.detail["wrong_rows"] == ["A"]

    order = _item("final", "f5")
    assert grade_item(order, list("ABCDEFGH")).correct
    bfs_like = grade_item(order, list("ABF"))
    assert not bfs_like.correct and bfs_like.detail.get("looks_like") == "bfs"


@pytest.mark.parametrize(("bank", "iid", "right", "swapped"), [
    ("compare-check", "c5", [1], [0]), ("final", "f10", [2], [1]),
])
def test_comparison_reasons_reject_swapped_concepts(bank, iid, right, swapped) -> None:
    item = _item(bank, iid)
    assert grade_item(item, right).correct
    assert grade_item(item, right).score == 1
    assert not grade_item(item, swapped).correct
    assert grade_item(item, swapped).score == 0
    reversed_prose = "DFS uses a queue while BFS uses a stack; DFS goes level by level and BFS goes deep."
    assert not grade_item(item, reversed_prose).correct
    assert not grade_item(item, str(right[0])).correct


def test_level_curve() -> None:
    assert level_info(0)["level"] == 1
    assert level_info(100)["level"] == 2
    assert level_info(10_000)["next"] is None


def test_weak_mastery_sends_the_learner_back_to_the_lesson() -> None:
    from types import SimpleNamespace as Row

    from app.services.progress import module_states, recommendations
    mastery = {1: Row(objective=1, value=0.2), 2: Row(objective=2, value=0.5)}
    revise = {r["objective"]: r for r in recommendations(module_states({}), mastery) if r["type"] == "revise"}
    assert (revise[1]["module"], revise[1]["activity_id"]) == ("intro", "l1-graphs")  # struggling: re-learn
    assert revise[2]["module"] == "representation"  # developing: practise again
