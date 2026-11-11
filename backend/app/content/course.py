"""The course: an intro course, then seven game modules that follow the team's ADDIE design.

The intro course (track "course") is the *explanation* step of design doc 2.2: five short
lessons, one per learning section 2.3.1-2.3.5 (see content/lessons.py). The game (track
"game") then puts each idea to work and assesses it.

Game module 0 is the problem-centred activation (Merrill / Gagne event 3): a maze that is
only afterwards revealed to be a graph. Modules 1-5 map one-to-one onto Objectives 1-5 and
storyboard Frames 1-4, and each links back to the lesson that teaches it. Module 6 is the
summative assessment.
"""

from app.content.schema import Activity, Module, Objective

OBJECTIVES: list[Objective] = [
    Objective(id=1, title="Foundational Graph Concepts", bloom="Explain", verb="Identify & describe",
              statement="Identify and describe vertices, edges, and directed vs undirected graphs.",
              module="anatomy"),
    Objective(id=2, title="Graph Representation", bloom="Explain", verb="Translate & illustrate",
              statement="Translate a visual graph into an adjacency list or adjacency matrix.",
              module="representation"),
    Objective(id=3, title="Depth-First Traversal", bloom="Apply", verb="Trace & execute",
              statement="Trace the exact order in which DFS visits the vertices of a graph.",
              module="dfs"),
    Objective(id=4, title="State & Backtracking", bloom="Apply / Analyse", verb="Track & record",
              statement="Track visited vertices and the stack, and recognise when DFS must backtrack.",
              module="backtracking"),
    Objective(id=5, title="DFS vs BFS", bloom="Evaluate", verb="Compare & contrast",
              statement="Compare how DFS and BFS explore a graph and explain why their orders differ.",
              module="dfs-vs-bfs"),
]

MODULES: list[Module] = [
    Module(
        slug="intro", order=0, icon="book", objective=None, track="course",
        title="Intro course",
        tagline="Learn the ideas first. Then play them.",
        story="Before Theseus stepped into the Labyrinth, Ariadne explained how it works. Five short lessons, "
              "about three minutes each: read, try the examples, answer the quick checks.",
        outcome="Know the ideas the game uses: graphs, adjacency lists and matrices, stacks, DFS, backtracking, "
                "queues and BFS.",
        activities=[
            Activity(id="l1-graphs", kind="lesson", xp=20, objective=1, title="What is a graph?",
                     summary="Vertices, edges, neighbours, direction and cycles: the words the whole course uses.",
                     config={"lesson": "graphs"}),
            Activity(id="l2-representation", kind="lesson", xp=20, objective=2, title="Writing a graph down",
                     summary="Adjacency lists and adjacency matrices: how a program stores a graph.",
                     config={"lesson": "representation"}),
            Activity(id="l3-dfs", kind="lesson", xp=20, objective=3, title="Depth-first search",
                     summary="Stacks, the DFS rule, and a complete run you can step through.",
                     config={"lesson": "dfs"}),
            Activity(id="l4-backtracking", kind="lesson", xp=20, objective=4, title="Dead ends & backtracking",
                     summary="Why DFS pops, why it needs chalk marks, and what the stack is telling you.",
                     config={"lesson": "backtracking"}),
            Activity(id="l5-bfs", kind="lesson", xp=20, objective=5, title="DFS vs BFS",
                     summary="Queues, breadth-first search, and why the two explore in different orders.",
                     config={"lesson": "dfs-vs-bfs"}),
        ],
    ),
    Module(
        slug="labyrinth", order=0, icon="door", objective=None,
        title="The Labyrinth",
        tagline="Find the lair. Don't get lost.",
        story="King Minos has locked you in the Labyrinth. Ariadne slipped you a ball of golden thread "
              "and a stick of chalk. Somewhere in the dark is the Minotaur's lair…",
        outcome="Explore a maze using only what you can see from each room, and discover a strategy that never gets lost.",
        activities=[
            Activity(id="m0-maze", kind="maze", xp=50, title="Into the dark",
                     summary="Explore room by room. Your thread follows you; your chalk marks where you've been.",
                     config={"graph": "labyrinth", "start": "A", "goal": "M"}),
        ],
    ),
    Module(
        slug="anatomy", order=1, icon="nodes", objective=1,
        lesson="l1-graphs",
        title="Anatomy of a Graph",
        tagline="Rooms are vertices. Corridors are edges.",
        story="Ariadne unrolls a map of the Labyrinth. It isn't a drawing of walls – it's a graph.",
        outcome="Identify vertices and edges, tell directed from undirected graphs, and read a vertex's degree.",
        activities=[
            Activity(id="m1-inspect", kind="inspect", xp=30, objective=1, title="Inspect the map",
                     summary="Click vertices and edges to reveal what they are. Complete the discovery checklist.",
                     config={"graph": "anatomy", "directed_graph": "anatomy-directed"}),
            Activity(id="m1-quiz", kind="quiz", xp=60, objective=1, title="Name that part",
                     summary="Six quick questions. Stuck? Ask for a hint – and you can always try again.",
                     config={"assessment": "anatomy-check"}),
        ],
    ),
    Module(
        slug="representation", order=2, icon="table", objective=2,
        lesson="l2-representation",
        title="Mapping the Maze",
        tagline="How a computer remembers who is next to whom.",
        story="A computer can't see a drawing. To explore the Labyrinth it needs the map written down as data.",
        outcome="Translate a drawn graph into an adjacency list and an adjacency matrix, and read them back.",
        activities=[
            Activity(id="m2-represent", kind="represent", xp=30, objective=2, title="Three views, one graph",
                     summary="Hover anything – the drawing, the list and the matrix light up together.",
                     config={"graph": "rep", "directed_graph": "rep-directed"}),
            Activity(id="m2-build", kind="quiz", xp=70, objective=2, title="Cartographer",
                     summary="Build adjacency lists yourself, then decode a matrix.",
                     config={"assessment": "representation-check"}),
        ],
    ),
    Module(
        slug="dfs", order=3, icon="dive", objective=3,
        lesson="l3-dfs",
        title="Into the Depths",
        tagline="Go as deep as you can. Then go back.",
        story="Theseus's rule was simple: always take the first unexplored corridor, and only turn back at a dead end.",
        outcome="Trace the exact order in which depth-first search visits every vertex.",
        activities=[
            Activity(id="m3-demo", kind="demo", xp=20, objective=3, title="Watch Ariadne's rule",
                     summary="Step through DFS on a small tree. Watch the stack, the chalk marks and the thread.",
                     config={"graph": "tree", "start": "A", "focus": "traversal"}),
            Activity(id="m3-trace-1", kind="trace", xp=80, objective=3, title="Warm-up: the tree",
                     summary="Click the next vertex DFS will visit. Backtracking happens automatically.",
                     config={"graph": "tree", "start": "A", "auto_backtrack": True, "difficulty": 1}),
            Activity(id="m3-trace-2", kind="trace", xp=100, objective=3, title="Branches & loops",
                     summary="A cycle appears. Visited vertices are off-limits.",
                     config={"graph": "loops", "start": "A", "auto_backtrack": True, "difficulty": 2}),
            Activity(id="m3-trace-3", kind="trace", xp=120, objective=3, title="The deep network",
                     summary="Eight vertices, several dead ends. Keep your nerve.",
                     config={"graph": "network", "start": "A", "auto_backtrack": True, "difficulty": 3}),
        ],
    ),
    Module(
        slug="backtracking", order=4, icon="undo", objective=4,
        lesson="l4-backtracking",
        title="Dead Ends & the Thread",
        tagline="You hold the thread now.",
        story="At a dead end Theseus winds the thread back to the last junction with an unexplored corridor. "
              "That thread is the stack.",
        outcome="Track visited vertices and the stack, and decide yourself when DFS must backtrack.",
        activities=[
            Activity(id="m4-demo", kind="demo", xp=20, objective=4, title="Why we wind the thread",
                     summary="Watch DFS meet a long dead-end corridor and pop its way back out.",
                     config={"graph": "corridors", "start": "A", "focus": "backtracking"}),
            Activity(id="m4-trace-1", kind="trace", xp=100, objective=4, title="Corridors",
                     summary="Now you push AND pop. Click a vertex to go deeper, or Backtrack at a dead end.",
                     config={"graph": "corridors", "start": "A", "auto_backtrack": False, "difficulty": 2}),
            Activity(id="m4-trace-2", kind="trace", xp=140, objective=4, title="The cyclic labyrinth",
                     summary="A ring of rooms. Every wrong turn leads back to somewhere you've been.",
                     config={"graph": "cycle", "start": "A", "auto_backtrack": False, "difficulty": 3}),
            Activity(id="m4-quiz", kind="quiz", xp=60, objective=4, title="Read the stack",
                     summary="What's on the stack, and why? Four questions.",
                     config={"assessment": "backtracking-check"}),
        ],
    ),
    Module(
        slug="dfs-vs-bfs", order=5, icon="split", objective=5,
        lesson="l5-bfs",
        title="Deep vs Wide",
        tagline="Two explorers, one labyrinth.",
        story="Theseus dives deep with his thread. His rival sends scouts out in widening rings. Who is right?",
        outcome="Compare DFS and BFS and explain why one goes deep while the other goes wide.",
        activities=[
            Activity(id="m5-compare", kind="compare", xp=40, objective=5, title="The race",
                     summary="Watch DFS and BFS explore the same graph side by side.",
                     config={"graph": "wide", "start": "A", "goal": "J"}),
            Activity(id="m5-quiz", kind="quiz", xp=80, objective=5, title="Deep or wide?",
                     summary="Spot the orders, name the structures, explain the difference.",
                     config={"assessment": "compare-check"}),
        ],
    ),
    Module(
        slug="minotaur", order=6, icon="crown", objective=None,
        title="Face the Minotaur",
        tagline="The final trial. No hints in the dark.",
        story="Everything you've learned, on graphs you've never seen. Pass, and the Labyrinth is yours.",
        outcome="Show mastery of all five objectives on unseen graphs.",
        activities=[
            Activity(id="m6-final", kind="quiz", xp=300, title="The final trial",
                     summary="Ten questions across all five objectives. Results show your mastery per objective.",
                     config={"assessment": "final"}),
        ],
    ),
]

MODULES_BY_SLUG = {m.slug: m for m in MODULES}
ACTIVITIES = {a.id: (m, a) for m in MODULES for a in m.activities}
OBJECTIVES_BY_ID = {o.id: o for o in OBJECTIVES}
