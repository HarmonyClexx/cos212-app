"""Canonical DFS / BFS traces.

A *trace* is the list of atomic events a learner must reproduce. The frontend has a
TypeScript twin of this module for instant feedback; the server copy is authoritative
for grading.
"""

from dataclasses import dataclass
from typing import Literal

from app.engine.graph import Graph

EventKind = Literal["visit", "backtrack"]


@dataclass(frozen=True)
class Event:
    kind: EventKind
    node: str  # visit: the node entered. backtrack: the node popped.
    stack: tuple[str, ...]  # stack *after* the event
    visited: frozenset[str]  # visited set *after* the event


def dfs_trace(g: Graph, start: str) -> list[Event]:
    """Iterative DFS that mirrors the recursive call stack exactly.

    At each step look at the top of the stack: visit its first unvisited neighbour
    (alphabetical), or pop it if it is a dead end.
    """
    visited: set[str] = {start}
    stack: list[str] = [start]
    events = [Event("visit", start, tuple(stack), frozenset(visited))]
    while stack:
        top = stack[-1]
        nxt = next((n for n in g.neighbours(top) if n not in visited), None)
        if nxt is None:
            stack.pop()
            events.append(Event("backtrack", top, tuple(stack), frozenset(visited)))
        else:
            visited.add(nxt)
            stack.append(nxt)
            events.append(Event("visit", nxt, tuple(stack), frozenset(visited)))
    return events


def dfs_order(g: Graph, start: str) -> list[str]:
    return [e.node for e in dfs_trace(g, start) if e.kind == "visit"]


def bfs_order(g: Graph, start: str) -> list[str]:
    order, seen, queue = [start], {start}, [start]
    while queue:
        cur = queue.pop(0)
        for n in g.neighbours(cur):
            if n not in seen:
                seen.add(n)
                order.append(n)
                queue.append(n)
    return order
