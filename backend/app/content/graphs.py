"""Hand-laid graphs used across the course.

Coordinates live in a 100 x 75 design space; the frontend scales them to fit.
Each graph was chosen to teach something specific - the comment says what.
"""

from typing import Any


def _g(gid: str, nodes: dict[str, tuple[float, float]], edges: str, directed: bool = False) -> dict[str, Any]:
    sep = ">" if directed else "-"
    pairs = [tuple(e.split(sep)) for e in edges.split()]
    return {
        "id": gid,
        "directed": directed,
        "nodes": [{"id": n, "x": x, "y": y} for n, (x, y) in nodes.items()],
        "edges": [list(p) for p in pairs],
    }


GRAPHS: dict[str, dict[str, Any]] = {}


def _add(g: dict[str, Any]) -> None:
    GRAPHS[g["id"]] = g


# --- Module 0: the labyrinth (fog-of-war exploration) -------------------------------------
# Rooms laid out on a grid so it *feels* like a maze. Has dead ends (D, J, L) and a loop
# (A-B-E-H-G-F-A) so learners discover on their own why chalk marks matter.
_add(_g("labyrinth", {
    "A": (8, 66), "B": (8, 38), "C": (8, 10), "D": (31, 10),
    "E": (31, 38), "F": (31, 66), "G": (54, 66), "H": (54, 38),
    "I": (54, 10), "J": (77, 10), "K": (77, 38), "L": (77, 66), "M": (96, 38),
}, "A-B B-C C-D B-E E-H H-I I-J A-F F-G G-H H-K K-L K-M"))

# --- Module 1: anatomy ------------------------------------------------------------------
_ANATOMY_POS = {"A": (12, 38), "B": (38, 12), "C": (38, 64), "D": (64, 38), "E": (90, 38)}
_add(_g("anatomy", _ANATOMY_POS, "A-B A-C B-D C-D D-E"))
_add(_g("anatomy-directed", _ANATOMY_POS, "A>B A>C B>D C>D D>E", directed=True))

# --- Module 2: representation -----------------------------------------------------------
_REP_POS = {"A": (12, 14), "B": (50, 10), "C": (88, 20), "D": (22, 60), "E": (66, 60)}
_add(_g("rep", _REP_POS, "A-B A-D B-C B-E D-E"))
_add(_g("rep-directed", _REP_POS, "A>B A>D B>C E>B D>E", directed=True))

_BUILD_POS = {"A": (12, 20), "B": (50, 12), "C": (88, 24), "D": (28, 62), "E": (72, 60)}
_add(_g("build", _BUILD_POS, "A-B A-D B-C B-D C-E D-E"))
_add(_g("build-directed", _BUILD_POS, "A>B B>C C>E E>D D>A B>D", directed=True))

# --- Module 3: DFS traversal (easy -> hard) ---------------------------------------------
# A plain tree: no cycles, so the only new idea is "go deep first".
_add(_g("tree", {
    "A": (50, 8), "B": (28, 34), "C": (72, 34), "D": (14, 64), "E": (42, 64), "F": (72, 64),
}, "A-B A-C B-D B-E C-F"))

# A cycle appears: from F the learner is tempted back towards visited nodes.
_add(_g("loops", {
    "A": (10, 38), "B": (34, 12), "C": (34, 64), "D": (62, 12), "E": (62, 64), "F": (90, 38),
}, "A-B A-C B-D B-E C-E D-F E-F"))

# Eight nodes, several backtracks, and C only reachable late through F.
_add(_g("network", {
    "A": (8, 38), "B": (28, 12), "C": (28, 64), "D": (52, 10), "E": (52, 38),
    "F": (52, 66), "G": (76, 22), "H": (94, 52),
}, "A-B A-C B-D B-E C-F D-G E-F E-G G-H F-H"))

# --- Module 4: backtracking -------------------------------------------------------------
# A long dead-end corridor (C-D) forces a double pop before the learner can branch to E.
_add(_g("corridors", {
    "A": (8, 40), "B": (30, 18), "C": (55, 8), "D": (82, 8), "E": (58, 36),
    "F": (30, 64), "G": (60, 66),
}, "A-B B-C C-D B-E A-F F-G"))

# A hexagonal loop with a chord and a pendant: the "cyclic labyrinth".
_add(_g("cycle", {
    "A": (10, 38), "B": (32, 10), "C": (64, 10), "D": (88, 38), "E": (64, 66),
    "F": (32, 66), "G": (96, 70),
}, "A-B B-C C-D D-E E-F F-A C-E D-G"))

# --- Module 5: DFS vs BFS ---------------------------------------------------------------
# Wide-and-deep tree where the two orders differ dramatically.
_add(_g("wide", {
    "A": (50, 6), "B": (18, 28), "C": (50, 28), "D": (82, 28), "E": (8, 50),
    "F": (28, 50), "G": (50, 50), "H": (72, 50), "I": (92, 50), "J": (8, 72),
}, "A-B A-C A-D B-E B-F C-G D-H D-I E-J"))

# --- Module 6: final assessment (unseen graphs, to test transfer) -----------------------
_add(_g("final-1", {
    "A": (10, 18), "B": (38, 8), "C": (68, 12), "D": (92, 36), "E": (66, 42),
    "F": (34, 44), "G": (12, 66), "H": (50, 70),
}, "A-B A-F B-C B-F C-D C-E E-F F-G F-H E-H"))

_add(_g("final-2", {
    "A": (16, 12), "B": (54, 8), "C": (8, 56), "D": (54, 40), "E": (34, 70), "F": (88, 40),
}, "C>A C>E A>B B>D D>F E>D E>F F>B", directed=True))
