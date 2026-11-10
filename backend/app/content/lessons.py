"""The intro course: five short lessons that *explain* before the game asks learners to *do*.

Design doc 2.2 sets out five steps per section: explanation, demonstration, practice,
assessment, feedback. The game modules cover the last four. These lessons are the
explanation step, one per learning section (2.3.1 to 2.3.5) and objective.

Each page pairs a short explanation with a figure the learner can poke at, and most end in a
check (retrieval practice). Every option of a check explains itself, so a wrong pick is
answered with *why*. Checks are ungraded: they only gate the next page.

The lessons use their own graphs (``intro-*`` in graphs.py), so they never give away a quiz
answer. Every fact a check depends on is recomputed in tests/test_engine.py.
"""

from typing import Any

from app.content.graphs import GRAPHS
from app.content.schema import Lesson, LessonCheck, LessonFigure, LessonPage

LESSONS: dict[str, Lesson] = {}


def _add(lesson: Lesson) -> None:
    LESSONS[lesson.id] = lesson


# --- 2.3.1 Introduction to graphs (Objective 1) -------------------------------------------------

_add(Lesson(
    id="graphs", objective=1, minutes=3, practice="anatomy",
    pages=[
        LessonPage(
            id="what", title="Things and the links between them",
            body="Lots of problems are really about **things** and the **links** between them:\n\n"
                 "- towns joined by roads\n"
                 "- people joined by friendships\n"
                 "- web pages joined by links\n"
                 "- rooms in a maze joined by corridors\n\n"
                 "A **graph** describes all of these in the same way. Its **vertices** (also called "
                 "*nodes*) are the things, drawn as circles. Its **edges** are the links, drawn as lines. "
                 "Each edge joins two vertices.\n\n"
                 "This graph has 6 vertices, A to F, and 6 edges. Where the circles sit on the page "
                 "doesn't matter. All that matters is *which* vertices are joined.",
            figure=LessonFigure(kind="graph", graphs=["intro-basic"],
                                captions=["6 vertices (circles) joined by 6 edges (lines)"]),
            check=LessonCheck(
                id="g-map",
                prompt="A road map is drawn as a graph. What are its vertices and its edges?",
                options=["Vertices are the towns; edges are the roads between them",
                         "Vertices are the roads; edges are the towns",
                         "Towns and roads are both vertices; the edges are the distances"],
                answer=0,
                why=["Right. The towns are the things, and a road links two of them, just as an edge "
                     "joins two vertices.",
                     "It's the other way round. An edge *joins* two things, and a road joins two towns.",
                     "A road is the link itself, so it's the edge. A distance would just be a label on "
                     "that edge."],
            ),
        ),
        LessonPage(
            id="degree", title="Neighbours and degree",
            body="Two vertices joined by an edge are **adjacent**: they are **neighbours**. "
                 "B's neighbours are A, C and D.\n\n"
                 "The **degree** of a vertex is the number of edges touching it, which is the same as "
                 "its number of neighbours. B has degree 3. E has degree 1, so it's a dead end: there's "
                 "only one way in or out.\n\n"
                 "Tap any vertex to see its neighbours and its degree.",
            figure=LessonFigure(kind="neighbours", graphs=["intro-basic"]),
            check=LessonCheck(
                id="g-degree", prompt="What is the degree of **D**?",
                options=["1", "2", "3", "4"], answer=2,
                why=["That's the degree of E or F, the two leaves hanging off D. Count every edge that "
                     "touches D itself.",
                     "Close. Look again: D is joined to B, E *and* F.",
                     "Right. Three edges touch D, going to B, E and F, so D has three neighbours.",
                     "D isn't joined to A or C. Count only the edges that touch D: to B, E and F."],
            ),
        ),
        LessonPage(
            id="directed", title="One-way streets: directed graphs",
            body="So far every edge has been a **two-way** street: if A is joined to B, you can go from "
                 "A to B *and* from B to A. That's an **undirected** graph. Friendships work like this.\n\n"
                 "In a **directed** graph each edge is an arrow that goes **one way only**, like "
                 "following someone online: you can follow them without them following you back. The "
                 "edge A → B lets you go from A to B, but not back again.\n\n"
                 "In a directed graph, a vertex's neighbours are the vertices its arrows point *to*.",
            figure=LessonFigure(kind="graph", graphs=["intro-basic", "intro-basic-directed"],
                                captions=["Undirected: every edge goes both ways",
                                          "Directed: follow the arrows"]),
            check=LessonCheck(
                id="g-directed",
                prompt="In the **directed** graph, where can you go from D in one step?",
                options=["B, E and F", "Only E", "B and F", "Nowhere: D is a dead end"], answer=1,
                why=["That's true in the undirected graph. In the directed one, check which way each "
                     "arrow points.",
                     "Right. Only the arrow D → E starts at D. The arrows from B and F point *into* D.",
                     "Those arrows point *into* D (B → D and F → D), and you can't travel an arrow "
                     "backwards.",
                     "Not quite: one arrow does leave D, the one to E."],
            ),
        ),
        LessonPage(
            id="cycles", title="Paths and cycles",
            body="A **path** is a route that follows edges from vertex to vertex, like A → B → D → E.\n\n"
                 "A **cycle** is a path that comes back to where it started without reusing an edge. "
                 "Here, A → B → C → A is a cycle.\n\n"
                 "Cycles matter for the rest of the course. Walk round one without keeping track of "
                 "where you've been, and you could go round forever. In the Labyrinth, chalk marks "
                 "solve that.",
            figure=LessonFigure(kind="graph", graphs=["intro-basic"], highlight=["A", "B", "C", "A-B", "B-C", "A-C"],
                                captions=["The cycle A → B → C → A"]),
            check=LessonCheck(
                id="g-cycle", prompt="Which of these is a **cycle** in the graph?",
                options=["A → B → D → E", "D → E → D", "B → D → F → B", "B → C → A → B"], answer=3,
                why=["That's a path, but it ends at E, not where it started. A cycle must come back to "
                     "its start.",
                     "That walks the same edge, D–E, there and back. A cycle can't reuse an edge.",
                     "There's no edge between F and B, so this route can't be walked at all.",
                     "Yes. B–C, C–A and A–B are all edges, and the route ends where it began. It's the "
                     "same triangle, just started from B."],
            ),
        ),
    ],
    recap=["A **graph** is a set of **vertices** (things) joined by **edges** (links).",
           "Joined vertices are **neighbours**. A vertex's **degree** is the number of edges touching it.",
           "**Undirected** edges go both ways. **Directed** edges (arrows) go one way only.",
           "A **cycle** is a path back to its start, so exploring a graph needs a memory of where you've been."],
))

# --- 2.3.2 Graph representation (Objective 2) ----------------------------------------------------

_add(Lesson(
    id="representation", objective=2, minutes=3, practice="representation",
    pages=[
        LessonPage(
            id="why", title="A computer can't see the picture",
            body="The drawing is for people. A program needs the graph as **data**, and all it really "
                 "has to know is *who is next to whom*.\n\n"
                 "There are two standard ways to write that down:\n\n"
                 "- an **adjacency list**: for every vertex, a list of its neighbours\n"
                 "- an **adjacency matrix**: a grid of 0s and 1s, with one row and one column per vertex\n\n"
                 "Both describe exactly the same graph. They just suit different jobs.",
            figure=LessonFigure(kind="graph", graphs=["intro-rep"], captions=["The graph we'll write down"]),
            check=LessonCheck(
                id="r-data", prompt="What does a program need to store about a graph?",
                options=["Where each circle is drawn on the screen", "Which vertices are joined to which",
                         "The colour of each vertex"], answer=1,
                why=["Positions only matter for drawing. Move the circles around and it's still the "
                     "same graph.",
                     "Right. A graph is just its vertices and the connections between them.",
                     "Colours are decoration. The graph is the same in any colour."],
            ),
        ),
        LessonPage(
            id="list", title="The adjacency list",
            body="An **adjacency list** gives each vertex a row listing its neighbours. Hover over (or "
                 "tap) a vertex or a row to match them up.\n\n"
                 "Two things to notice:\n\n"
                 "- In an undirected graph each edge appears **twice**: the edge A–B puts B in A's row "
                 "*and* A in B's row.\n"
                 "- Every row is in **alphabetical order**, which is also the order DFS will try "
                 "neighbours in.",
            figure=LessonFigure(kind="representation", graphs=["intro-rep"], views=["list"]),
            check=LessonCheck(
                id="r-list", prompt="Which vertices are in **B**'s row?",
                options=["A, C, D", "A, C", "C, D", "A, B, C, D"], answer=0,
                why=["Right. B is joined to A, C and D.",
                     "You've missed one. Follow every line out of B: there's one to D as well.",
                     "Don't forget A. The edge A–B counts for B's row too, because an undirected edge "
                     "appears in both rows.",
                     "A vertex isn't its own neighbour unless an edge loops back to it. B's row is A, C, D."],
            ),
        ),
        LessonPage(
            id="matrix", title="The adjacency matrix",
            body="An **adjacency matrix** is a grid with a row and a column for every vertex. The cell "
                 "in row *u*, column *v* holds **1** if there's an edge from *u* to *v*, and **0** if "
                 "there isn't.\n\n"
                 "- **Undirected:** each edge sets *two* cells, (u, v) and (v, u). The grid is a mirror "
                 "image across its diagonal: it's **symmetric**.\n"
                 "- **Directed:** the arrow u → v sets only the cell in row *u*, column *v*.\n\n"
                 "Switch between the two versions and compare the grids.",
            figure=LessonFigure(kind="representation", graphs=["intro-rep", "intro-rep-directed"], views=["matrix"]),
            check=LessonCheck(
                id="r-matrix",
                prompt="Switch to **Directed**. Row D is all zeros, yet two arrows touch D. Why?",
                options=["Both arrows end at D, and a row records only the arrows that start there",
                         "D isn't part of the directed graph",
                         "It's a mistake: the matrix should be symmetric",
                         "A 0 means the edge goes both ways"], answer=0,
                why=["Exactly. B → D and E → D show up in column D (rows B and E), not in row D.",
                     "D is still a vertex: it has a row and a column. It just has no arrows leaving it.",
                     "Only undirected matrices are symmetric. Arrows go one way, so the mirror image breaks.",
                     "A 0 means there's no edge from that row's vertex to that column's vertex."],
            ),
        ),
        LessonPage(
            id="choose", title="Which one should you use?",
            body="Both work. They make different jobs fast.\n\n"
                 "- An **adjacency list** stores only the edges that exist. Listing a vertex's neighbours "
                 "is quick, and DFS and BFS do exactly that at every step.\n"
                 "- An **adjacency matrix** always has n × n cells, even when most of them are 0. In "
                 "return, *is there an edge from u to v?* takes a single lookup.\n\n"
                 "Most real graphs are **sparse**: each vertex has only a few neighbours compared with "
                 "the size of the whole graph. That's why lists are the usual choice.",
            check=LessonCheck(
                id="r-choose",
                prompt="A social network has 1 000 000 people, each with about 200 friends. Which "
                       "representation needs far less memory?",
                options=["Adjacency list", "Adjacency matrix", "They need about the same"], answer=0,
                why=["Right. The lists hold about 1 000 000 × 200 = 200 million entries. A matrix would "
                     "need 1 000 000 × 1 000 000 = a million million cells, almost all of them 0.",
                     "A matrix needs a cell for every *possible* pair of people: a million million cells, "
                     "nearly all 0. The lists store only the 200 million or so entries that exist.",
                     "They're wildly different. A matrix stores every possible pair; a list stores only "
                     "the pairs that exist."],
            ),
        ),
    ],
    recap=["A program stores a graph as **who is next to whom**, not as a picture.",
           "**Adjacency list:** each vertex has a row of its neighbours, in alphabetical order. An "
           "undirected edge appears in both rows.",
           "**Adjacency matrix:** a 1 in row *u*, column *v* means an edge from u to v. Undirected graphs "
           "give a symmetric matrix.",
           "Lists suit sparse graphs and fast neighbour loops. A matrix answers *is there an edge?* instantly."],
))

# --- 2.3.3 Depth-first search (Objective 3) ------------------------------------------------------

_add(Lesson(
    id="dfs", objective=3, minutes=4, practice="dfs",
    pages=[
        LessonPage(
            id="traversal", title="Exploring a whole graph",
            body="A **traversal** visits every vertex you can reach from a start vertex, **exactly once**. "
                 "It's how a program finds the way out of a maze, checks whether a network is connected, "
                 "or crawls every page of a website.\n\n"
                 "**Depth-first search (DFS)** explores like someone in a maze holding a thread:\n\n"
                 "1. Keep walking down new corridors, as deep as you can go.\n"
                 "2. At a dead end, wind the thread back to the last junction that still has an "
                 "unexplored corridor.\n"
                 "3. Carry on from there.\n\n"
                 "To find its way back, DFS needs a memory. That memory is a **stack**.",
            figure=LessonFigure(kind="graph", graphs=["intro-tree"], highlight=["A"],
                                captions=["We'll explore this graph from A"]),
        ),
        LessonPage(
            id="stack", title="Stacks: last in, first out",
            body="A **stack** works like a pile of plates. You can only touch the **top**:\n\n"
                 "- **push** puts a new item on top\n"
                 "- **pop** takes the top item off\n\n"
                 "So the last item in is always the first one out: **LIFO**, last in, first out. Try it "
                 "with the stack here.\n\n"
                 "DFS pushes each vertex as it walks *in*, and pops it as it walks back *out*. The stack "
                 "always holds the way home, like Theseus's thread.",
            figure=LessonFigure(kind="stack"),
            check=LessonCheck(
                id="d-stack", prompt="You push A, push B, push C, then pop once. What's on top now?",
                options=["A", "B", "C", "Nothing: the stack is empty"], answer=1,
                why=["A is at the bottom, because it went in first. Only C has been popped so far.",
                     "Right. The pop removed C, the last one in, so B is on top.",
                     "C was on top, but the pop took it off: the last one in is the first one out.",
                     "Only one pop happened. Three items went in and one came out."],
            ),
        ),
        LessonPage(
            id="rule", title="The DFS rule",
            body="Here is DFS in five steps. Each **visited** vertex gets a chalk mark, so it's never "
                 "entered twice.\n\n"
                 "1. Push the start vertex and mark it visited.\n"
                 "2. Look at the vertex on **top of the stack**.\n"
                 "3. If it has an **unvisited** neighbour, take the **alphabetically first** one, mark it "
                 "visited and push it. *(Go deeper.)*\n"
                 "4. If it has none, it's a dead end: **pop** it. *(Go back.)*\n"
                 "5. Repeat from step 2 until the stack is empty.\n\n"
                 "Why alphabetical? A real program uses whatever order its adjacency list happens to be "
                 "in. We always take the alphabetically first one so everyone gets the same answer.\n\n"
                 "In code, each call of `dfs` waits on the **call stack** until all its neighbours are "
                 "done. That's why the game's stack shows `dfs(A)`, `dfs(B)`, and so on.",
            code="dfs(v):\n"
                 "    mark v as visited\n"
                 "    for each neighbour w of v, in alphabetical order:\n"
                 "        if w is not visited:\n"
                 "            dfs(w)\n"
                 "    # every neighbour is done: return (pop)",
            check=LessonCheck(
                id="d-rule",
                prompt="DFS is at a vertex whose neighbours are C, E and F. C is already visited. "
                       "Which vertex does DFS visit next?",
                options=["C", "E", "F", "None: it backtracks"], answer=1,
                why=["C is visited (it has a chalk mark), so DFS never enters it again.",
                     "Right. E is the alphabetically first neighbour that's still unvisited.",
                     "F is unvisited too, but E comes first alphabetically.",
                     "DFS backtracks only when *no* neighbour is unvisited. E and F still are."],
            ),
        ),
        LessonPage(
            id="watch", title="Watch it run",
            body="Step through DFS on this tree, starting from A. Keep an eye on three things at once:\n\n"
                 "- the **golden thread**: the stack, drawn on the graph\n"
                 "- the **stack**: a push when DFS goes deeper, a pop at each dead end\n"
                 "- the **visited** list: the order in which DFS reached each vertex\n\n"
                 "Before you press next, predict what DFS will do.",
            figure=LessonFigure(kind="trace", graphs=["intro-tree"], start="A", algorithm="dfs"),
            check=LessonCheck(
                id="d-next", prompt="After A, B and D, which vertex does DFS visit next?",
                options=["C", "E", "F", "A"], answer=1,
                why=["C is A's neighbour, but DFS isn't back at A yet. After the dead end at D it pops "
                     "back to B, and B still has an unvisited neighbour.",
                     "Right. D is a dead end, so DFS pops back to B, whose next unvisited neighbour is E. "
                     "Depth first: B's branch is finished before C's begins.",
                     "F hangs off C, and DFS hasn't reached C yet. It finishes B's branch first.",
                     "A is already visited, and DFS never visits a vertex twice."],
            ),
        ),
    ],
    recap=["A **traversal** visits every reachable vertex exactly once.",
           "A **stack** is last in, first out: **push** onto the top, **pop** off the top.",
           "**The DFS rule:** from the top of the stack, visit the alphabetically first unvisited "
           "neighbour. At a dead end, pop.",
           "On this tree, DFS from A visits **A, B, D, E, C, F, G**: it finishes one branch before "
           "starting the next."],
))

# --- 2.3.4 Visited nodes and backtracking (Objective 4) ------------------------------------------

_add(Lesson(
    id="backtracking", objective=4, minutes=3, practice="backtracking",
    pages=[
        LessonPage(
            id="deadends", title="Dead ends",
            body="A vertex is a **dead end** for DFS when it has **no unvisited neighbours**. Either it "
                 "has no other neighbours at all, or every one of them already has a chalk mark.\n\n"
                 "At a dead end DFS **backtracks**: it pops the dead end off the stack. The vertex "
                 "underneath, the one DFS came from, is back on top, and DFS checks *it* for unvisited "
                 "neighbours.\n\n"
                 "Sometimes one pop isn't enough. Here D is a dead end, and once D is popped, C is a dead "
                 "end too. DFS pops twice before it can branch from B to E. Step through and watch.",
            figure=LessonFigure(kind="trace", graphs=["intro-corridor"], start="A", algorithm="dfs"),
            check=LessonCheck(
                id="b-pop",
                prompt="The stack is [A, B, C, D], with the top on the right. D's only neighbour, C, is "
                       "already visited. What does DFS do next?",
                options=["Visit C again", "Pop D, so C is on top again",
                         "Jump straight to E, the next unvisited vertex", "Stop: the search is over"],
                answer=1,
                why=["C is visited. Walking back into it is exactly the loop the chalk marks prevent.",
                     "Right. D is a dead end, so pop it and look at C again. C turns out to be a dead "
                     "end too, so DFS pops again.",
                     "DFS can only move along edges, and there's no edge from D to E. It has to wind back "
                     "first.",
                     "The search stops only when the stack is empty, and A, B and C are still on it."],
            ),
        ),
        LessonPage(
            id="visited", title="Why chalk marks matter",
            body="This graph has a loop: A → B → E → F → A. Picture DFS without a visited set. At F it "
                 "would see its neighbour A, walk into A, then B, then E, then F again, round and round "
                 "forever.\n\n"
                 "The **visited set** (the chalk marks) is DFS's memory. Before pushing a neighbour, DFS "
                 "checks that it isn't already visited. A visited vertex is **never pushed again**, even "
                 "when it's right next door and even when it comes first alphabetically.",
            figure=LessonFigure(kind="graph", graphs=["intro-corridor"],
                                highlight=["A", "B", "E", "F", "A-B", "B-E", "E-F", "A-F"],
                                captions=["The loop A → B → E → F → A"]),
            check=LessonCheck(
                id="b-visited",
                prompt="DFS has visited A, B, C, D, E and F. It's now at F, whose neighbours are A, E "
                       "and G. Which vertex comes next?",
                options=["A, because it's alphabetically first", "E", "G", "None: backtrack"], answer=2,
                why=["Alphabetical order only chooses between *unvisited* neighbours. A is visited, so "
                     "it's skipped.",
                     "E is visited: DFS has just come from there.",
                     "Right. G is the only unvisited neighbour, so DFS visits it.",
                     "There's still an unvisited neighbour, G, so DFS goes deeper instead of popping."],
            ),
        ),
        LessonPage(
            id="thread", title="The stack is the way home",
            body="At any moment, the stack spells out the exact route from the start vertex to where "
                 "DFS is now. In the maze, it's the thread.\n\n"
                 "That's not the same as the **visited** list. When DFS reaches G here, it has visited "
                 "A, B, C, D, E, F and G, but the stack is only [A, B, E, F, G]. C and D were visited, "
                 "then popped on the way back from their dead end.\n\n"
                 "DFS is **finished** when the stack is empty. By then the start vertex itself has been "
                 "popped, and every vertex reachable from it has been visited.",
            figure=LessonFigure(kind="graph", graphs=["intro-corridor"],
                                highlight=["A", "B", "E", "F", "G", "A-B", "B-E", "E-F", "F-G"],
                                captions=["When DFS reaches G, the stack is [A, B, E, F, G]"]),
            check=LessonCheck(
                id="b-thread",
                prompt="When DFS reaches G, the stack is [A, B, E, F, G]. What does it tell you?",
                options=["Every vertex DFS has visited so far",
                         "The route from A to G that DFS is on; popping walks back along it",
                         "The vertices DFS still has to visit",
                         "The shortest path from A to G"], answer=1,
                why=["Not quite. C and D were visited too, but they were popped on the way back from "
                     "their dead end. The visited list and the stack are different things.",
                     "Exactly. The stack is the thread: the path from the start to where DFS is now.",
                     "Everything on the stack is already visited, because DFS pushes a vertex at the "
                     "moment it visits it.",
                     "DFS doesn't look for shortest paths: A → F → G is shorter. The stack is just the "
                     "route DFS happened to take."],
            ),
        ),
    ],
    recap=["A **dead end** has no unvisited neighbours. DFS **pops** it and carries on from the vertex "
           "below.",
           "Several dead ends in a row mean several pops in a row.",
           "The **visited set** stops DFS going round a cycle forever: visited vertices are never pushed "
           "again.",
           "The **stack** is the path from the start to the current vertex. DFS ends when the stack is empty."],
))

# --- 2.3.5 Comparing DFS and BFS (Objective 5) ---------------------------------------------------

_add(Lesson(
    id="dfs-vs-bfs", objective=5, minutes=3, practice="dfs-vs-bfs",
    pages=[
        LessonPage(
            id="queue", title="Queues: first in, first out",
            body="A **queue** is a line at a shop. Newcomers join at the **back** (*enqueue*), and the "
                 "person at the **front** is served next (*dequeue*).\n\n"
                 "So the first item in is the first one out: **FIFO**, first in, first out. It's the "
                 "opposite of a stack. Try it.",
            figure=LessonFigure(kind="queue"),
            check=LessonCheck(
                id="q-fifo",
                prompt="You enqueue A, then B, then C, then dequeue once. Which letter leaves?",
                options=["A", "B", "C"], answer=0,
                why=["Right. A joined first, so A is served first. A stack would have given you C.",
                     "B is next in line, but A is still ahead of it.",
                     "That's what a stack would do: last in, first out. A queue serves whoever has "
                     "waited longest."],
            ),
        ),
        LessonPage(
            id="bfs", title="Breadth-first search",
            body="**Breadth-first search (BFS)** explores in widening rings: first the start, then all of "
                 "its neighbours, then all of *their* neighbours, level by level.\n\n"
                 "It's the same idea as DFS with the stack swapped for a **queue**:\n\n"
                 "1. Mark the start visited and enqueue it.\n"
                 "2. Dequeue the vertex at the **front**.\n"
                 "3. Mark each of its unvisited neighbours visited and enqueue them, in alphabetical order.\n"
                 "4. Repeat from step 2 until the queue is empty.\n\n"
                 "Step through BFS on the tree you watched DFS explore.",
            code="bfs(start):\n"
                 "    mark start as visited; enqueue start\n"
                 "    while the queue is not empty:\n"
                 "        v = dequeue()\n"
                 "        for each neighbour w of v, in alphabetical order:\n"
                 "            if w is not visited:\n"
                 "                mark w as visited; enqueue w",
            figure=LessonFigure(kind="trace", graphs=["intro-tree"], start="A", algorithm="bfs"),
            check=LessonCheck(
                id="q-next",
                prompt="BFS has visited A, B and C, and the queue is [B, C]. Which vertex does it take "
                       "out next?",
                options=["B: it's at the front of the queue", "C: it went in last", "D: go deeper"],
                answer=0,
                why=["Right. B has waited longest, so BFS dequeues it next and discovers B's neighbours, "
                     "D and E.",
                     "Taking the newest item is what a stack does. A queue takes the oldest, which is B.",
                     "BFS never jumps ahead. D is only discovered once B comes off the queue."],
            ),
        ),
        LessonPage(
            id="compare", title="Same graph, different order",
            body="Here's the same tree explored both ways from A. The numbers give the visiting order.\n\n"
                 "- **DFS** (stack) always takes the **newest** vertex it knows about, so it dives to the "
                 "bottom of one branch before trying another.\n"
                 "- **BFS** (queue) always takes the **oldest**, so it finishes each level before going "
                 "deeper.\n\n"
                 "That difference has a useful consequence: BFS reaches vertices in order of distance "
                 "from the start, so it finds the route with the **fewest edges**. DFS suits exploring "
                 "a maze, and problems that need backtracking.",
            figure=LessonFigure(kind="orders", graphs=["intro-tree"], start="A"),
            check=LessonCheck(
                id="q-why", prompt="Why does DFS go deep while BFS goes wide?",
                options=["DFS takes its next vertex from a stack (newest first); BFS from a queue (oldest first)",
                         "DFS ignores the alphabetical rule",
                         "Only BFS keeps a visited set",
                         "DFS only works on trees"], answer=0,
                why=["Exactly. Swap the stack for a queue and depth-first becomes breadth-first.",
                     "Both use the same alphabetical tie-break. The difference is which vertex they take "
                     "next.",
                     "Both need a visited set, or a cycle would trap them.",
                     "DFS works on any graph. You've already seen it handle a cycle."],
            ),
        ),
    ],
    recap=["A **queue** is first in, first out: enqueue at the back, dequeue from the front.",
           "**BFS** is DFS's idea with a queue instead of a stack, so it explores level by level.",
           "On this tree, DFS visits **A, B, D, E, C, F, G** and BFS visits **A, B, C, D, E, F, G**.",
           "BFS finds routes with the fewest edges. DFS dives deep and backtracks."],
))


# --- payload -----------------------------------------------------------------------------------

def lesson_payload(lesson_id: str) -> dict[str, Any]:
    """The lesson as the browser sees it, with graph ids resolved to full graphs.

    Check answers are included on purpose: checks are ungraded retrieval practice that only gate
    the next page. The server still confirms every check was answered before completing a lesson.
    """
    data = LESSONS[lesson_id].model_dump()
    for page in data["pages"]:
        fig = page.get("figure")
        if fig:
            fig["graphs"] = [GRAPHS[g] for g in fig["graphs"]]
    return data
