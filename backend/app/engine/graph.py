from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Graph:
    """Immutable graph with deterministic (alphabetical) neighbour ordering.

    The design doc (2.3.3) asks for "a consistent rule for choosing which neighbouring
    node to visit first, such as alphabetical order" - every traversal here follows it.
    """

    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]
    directed: bool = False
    _adj: dict[str, tuple[str, ...]] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        adj: dict[str, set[str]] = {n: set() for n in self.nodes}
        for u, v in self.edges:
            if u not in adj or v not in adj:
                raise ValueError(f"edge {u}-{v} references unknown node")
            adj[u].add(v)
            if not self.directed:
                adj[v].add(u)
        object.__setattr__(self, "_adj", {n: tuple(sorted(vs)) for n, vs in adj.items()})

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> "Graph":
        return cls(
            nodes=tuple(n["id"] for n in spec["nodes"]),
            edges=tuple((u, v) for u, v in spec["edges"]),
            directed=bool(spec.get("directed", False)),
        )

    def neighbours(self, node: str) -> tuple[str, ...]:
        return self._adj[node]

    def adjacency(self) -> dict[str, list[str]]:
        return {n: list(vs) for n, vs in self._adj.items()}

    def edge_id(self, u: str, v: str) -> str:
        if self.directed:
            return f"{u}->{v}"
        a, b = sorted((u, v))
        return f"{a}-{b}"

    def edge_ids(self) -> set[str]:
        return {self.edge_id(u, v) for u, v in self.edges}

    def degree(self, node: str) -> int:
        return len(self._adj[node])
