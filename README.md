# Ariadne — learn depth-first search by playing it

A gamified, adaptive tutor that teaches **graphs and depth-first search (DFS)** to second-year CS
students with no prior data-structures background. Built for the COS750 project from the team's
ADDIE analysis and design documents.

> Theseus escaped the Labyrinth with a ball of thread and a stick of chalk.
> The thread is the **stack**. The chalk is the **visited set**. That is DFS.

| Layer | Stack |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 17 · PyJWT · bcrypt |
| Frontend | React 18 · TypeScript · Vite · TanStack Query · React Router (no UI/icon/animation libs: everything is hand-built SVG + CSS) |

---

## Quick start

**Prerequisites:** Docker, Python 3.12+, Node 20+.

```bash
# 1. Database (Postgres on localhost:5750)
docker compose up -d db

# 2. Backend (API on http://localhost:8750, docs at /api/docs)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env                     # then set ARIADNE_JWT_SECRET
.venv/bin/alembic upgrade head
.venv/bin/python -m scripts.seed_demo    # optional: 5 demo learners
.venv/bin/uvicorn app.main:app --port 8750 --reload

# 3. Frontend (http://localhost:5173, proxies /api to the backend)
cd frontend
npm install
npm run dev
```

**Everything in Docker instead:** `docker compose --profile full up --build`, then open http://localhost:4750.

**Demo accounts** (after seeding; password `labyrinth` for all): `ariadne` (course complete),
`icarus`, `daedalus`, `phaedra` (mid-course), `minos` (just started).

**Demo / marking mode:** set `ARIADNE_UNLOCK_ALL=true` in `backend/.env` to open every module immediately.

Ports use the course code to avoid clashing with other services: API **8750**, Postgres **5750**, Docker web **4750**.

---

## How the design document maps to the app

| ADDIE design element | Where it lives |
|---|---|
| **Problem-centred activation** (Merrill / Gagné 3): start from intuition, e.g. a maze | Module 0, *The Labyrinth*: fog-of-war maze with a thread and chalk; the map is then revealed as a graph and each tool is named |
| **Inform learners of objectives** (Gagné 2) | Every module header shows its objective, CS2023 skill level (Explain / Apply / Evaluate) and the outcome statement |
| **Frame 1:** canvas + inspector, click to reveal definitions | `InspectActivity`: click vertices/edges, toggle directed, discovery checklist |
| **Frame 2:** graph to adjacency list (drag and drop) | `RepresentActivity` (linked list / matrix / drawing) and the `adjacency` quiz item (drag *or* tap) |
| **Frame 3:** "Click the next node DFS will visit", call stack + visited panel | `TraceActivity` with auto-backtracking |
| **Frame 4:** dead end, "What action must DFS take?", learner pops the stack | `TraceActivity` in manual mode, with a **Backtrack (pop)** button on the stack |
| **Frame 4:** side-by-side DFS vs BFS replay | `CompareActivity`: synchronised race, stack vs queue |
| **Progressive scaffolding** (Design 2.6): hint, then explanation + visual cue, then worked step | Tier 1 / 2 / 3 feedback in traces (`engine/tracer.ts`) and quizzes (`/attempts/{id}/check`) |
| **Consistent tie-break** (alphabetical) | `engine/graph.py` and `engine/graph.ts` |
| **Working-memory constraint**: externalise the stack and visited list | Stack and visited panels are always on screen; the golden *thread* on the graph **is** the stack |
| **Formative assessment** (CAI / simulation / concept mapping) | Five formative quizzes with retries; item types: MCQ, tap-the-graph, adjacency builder, click-the-order, short answer |
| **Summative criterion-referenced test** | Module 6, *Face the Minotaur*: 10 items on *unseen* graphs, a per-objective report, pass mark 60% |
| **Short-answer rubric** (pass / differentiated descriptors) | Criteria are shown to the learner up front; pass = 2 of 4, distinction = 4 of 4 |
| **Adaptive system** recommending revision | Per-objective mastery (running average, then EMA) and "Revise: …" recommendations below 70% |
| **Flow** (Csíkszentmihályi): immediate feedback, balanced challenge | Instant per-click feedback, streak counter, difficulty ramp (tree → cycle → 8-node network) |
| **Malone & Lepper**: challenge, curiosity, fantasy, control | Stars, XP, levels, 10 badges, leaderboard · Theseus/Minotaur framing · learner drives every step |
| **Constructivism** | Learners *perform* the algorithm, so mistakes are diagnosed rather than just marked wrong |

### Mistakes are diagnosed, not just marked wrong

Every wrong click in a trace is classified as one of five misconceptions, and the feedback targets it:

| Mistake | Meaning |
|---|---|
| `wrong_order` | picked a neighbour, but not the alphabetically first unvisited one |
| `not_adjacent` | jumped to a vertex with no edge from the current one |
| `already_visited` | re-entered a visited vertex (the cycle trap) |
| `should_backtrack` | at a dead end, tried to move instead of popping |
| `premature_backtrack` | popped while unexplored neighbours remained |

The counts are stored per attempt (`attempts.result.breakdown`), ready for the ADDIE **Evaluate** phase.

---

## Architecture

```
backend/
  app/
    engine/        graph.py, traversal.py (DFS/BFS traces), replay.py (server-side trace grading)
    content/       graphs.py, course.py (modules + objectives), assessments.py (quiz banks)
    services/      grading.py (5 item types + rubric), gamification.py (XP, levels, badges,
                   streaks, mastery), progress.py (unlocking, recommendations)
    api/           auth.py, me.py (profile, leaderboard), course.py (content, submit, quiz attempts)
    models.py      users, activity_progress, attempts, mastery, user_badges
  alembic/         migrations
  scripts/         seed_demo.py (plays the course through the real API)
  tests/           engine + content integrity + end-to-end API tests
frontend/src/
  engine/          TypeScript twin of the backend engine + tracer state machine
  components/      GraphCanvas (SVG), Stack/Queue/Visited panels, RewardModal, TopBar, icons
  activities/      Maze, Inspect, Represent, Demo, Trace, Compare, Quiz (+ item types)
  pages/           Landing, Map, Module, Leaderboard, Profile
```

**Integrity by design**
- The browser runs a TypeScript copy of the DFS engine for instant feedback, but the **server
  re-grades everything**. Traces are sent as the raw click log (including wrong clicks, hints and
  reveals) and replayed against the canonical trace, so stars and XP can't be spoofed.
- Quiz answers never reach the browser before a learner has earned them. Each quiz is a
  server-side **attempt**, and the server, not the client, counts tries per item.
- XP is awarded only for **improvement** (stars × activity XP, minus what was already banked), so
  the leaderboard rewards learning, not grinding.

**Content is code.** Graphs, modules and quiz items live in `backend/app/content/`, are versioned
with the app, and are checked by tests. Every expected DFS/BFS order quoted in a question is
recomputed in `tests/test_engine.py`, so a typo in course content fails the build.

### Adding content
- **A graph:** add it with `_add(_g("my-graph", {"A": (x, y), ...}, "A-B B-C"))` in `content/graphs.py`
  (use `A>B` for directed edges; coordinates are in a 100 × 75 space).
- **A practice challenge:** add an `Activity(kind="trace", config={"graph": ..., "start": ..., "auto_backtrack": ...})` to a module in `content/course.py`.
- **A quiz question:** add an `Item(...)` to a bank in `content/assessments.py`. Adjacency and order
  answers are derived from the graph automatically.

### API (full interactive docs at `/api/docs`)

| Method | Path | |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | JWT auth |
| GET | `/api/me` | profile, level, badges, mastery, recommendations |
| GET | `/api/modules`, `/api/modules/{slug}` | course + per-learner state (locks, stars) |
| POST | `/api/activities/{id}/submit` | trace / maze / lesson completion → reward |
| POST | `/api/activities/{id}/attempts` | open a quiz attempt (sanitised items) |
| POST | `/api/attempts/{id}/check` | formative: grade one item, tiered feedback |
| POST | `/api/attempts/{id}/finish` | score, XP, badges, mastery, revision recommendations |
| GET | `/api/leaderboard` | top 20 + your rank |

---

## Tests

```bash
cd backend && .venv/bin/pytest          # 29 tests: engine, content integrity, API flows
cd frontend && npm run typecheck && npm run build
```
