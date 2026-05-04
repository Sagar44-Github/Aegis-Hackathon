"""
city_graph.py — AEGIS City Infrastructure Graph

Models the city as a NetworkX graph where nodes are infrastructure
facilities and edges represent physical connections (power lines, pipes).

Node schema::

    {
        "id":           str,
        "type":         str,          # AgentType value e.g. "HOSPITAL"
        "location":     (lat, lon),
        "capacity":     float,        # MW (original / max)
        "current_load": float,        # MW currently allocated
        "status":       str,          # ONLINE | DEGRADED | OFFLINE
        "max_output":   float,        # current effective max (degrades on damage)
        "neighbours":   List[str],    # adjacent node IDs (for cascade detection)
    }

Exports a pre-initialised ``city_graph`` singleton used by the API router.
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

logger = logging.getLogger(__name__)

# Node type constants (match AgentType enum values)
POWER_GRID   = "POWER_GRID"
HOSPITAL     = "HOSPITAL"
WATER_PLANT  = "WATER_PLANT"
FIRE_STATION = "FIRE_STATION"
TELECOM      = "TELECOM"
POWER_PLANT  = "POWER_PLANT"   # supply source (not a bidding agent)

_AGENT_TYPES = {HOSPITAL, WATER_PLANT, FIRE_STATION, TELECOM, POWER_GRID}
_SUPPLY_TYPES = {POWER_PLANT, POWER_GRID}


class CityGraph:
    """
    Graph-based city infrastructure model.

    Usage::

        g = CityGraph()
        g.add_infrastructure_node('h1', 'HOSPITAL', (40.71, -74.01), capacity=10.0)
        g.add_edge('pp1', 'h1', capacity=10.0)
        supply = g.get_total_supply()
        g.apply_earthquake((40.71, -74.01), magnitude=7.0)
    """

    def __init__(self) -> None:
        self.graph: nx.Graph         = nx.Graph()
        self.nodes: Dict[str, Dict[str, Any]] = {}

    # ── Node management ───────────────────────────────────────────────────────

    def add_infrastructure_node(
        self,
        node_id:  str,
        node_type: str,
        location: Tuple[float, float],
        capacity: float,
    ) -> None:
        """
        Register an infrastructure node in both the NetworkX graph and nodes dict.

        Args:
            node_id:   Unique identifier (e.g. 'hospital-1').
            node_type: One of HOSPITAL, WATER_PLANT, FIRE_STATION,
                       TELECOM, POWER_GRID, POWER_PLANT.
            location:  (lat, lon) geographic coordinates.
            capacity:  Max MW capacity (for supply nodes) or MW demand ceiling.
        """
        node_type = node_type.upper()

        self.graph.add_node(node_id, type=node_type, location=location)
        self.nodes[node_id] = {
            "id":           node_id,
            "type":         node_type,
            "location":     location,
            "capacity":     capacity,
            "max_output":   capacity,      # degrades on damage
            "current_load": 0.0,
            "status":       "ONLINE",
            "neighbours":   [],
        }
        logger.debug("Added node %s (%s) cap=%.1f MW", node_id, node_type, capacity)

    def add_edge(
        self,
        from_node: str,
        to_node:   str,
        capacity:  float = 0.0,
    ) -> None:
        """Add a connection between two infrastructure nodes."""
        if from_node not in self.nodes or to_node not in self.nodes:
            logger.warning("add_edge: one or both nodes not found (%s, %s)", from_node, to_node)
            return
        self.graph.add_edge(from_node, to_node, capacity=capacity)
        # Maintain neighbour lists for cascade detection
        self.nodes[from_node]["neighbours"].append(to_node)
        self.nodes[to_node]["neighbours"].append(from_node)

    def get_node_state(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Return node properties dict or None if not found."""
        return self.nodes.get(node_id)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and clean up neighbour references."""
        if node_id not in self.nodes:
            return
        for nb in self.nodes[node_id].get("neighbours", []):
            if nb in self.nodes:
                self.nodes[nb]["neighbours"] = [
                    n for n in self.nodes[nb]["neighbours"] if n != node_id
                ]
        self.graph.remove_node(node_id)
        del self.nodes[node_id]

    # ── State queries ─────────────────────────────────────────────────────────

    def get_agent_nodes(self) -> Dict[str, Dict[str, Any]]:
        """Return only bidding-agent nodes (excludes pure supply sources)."""
        return {k: v for k, v in self.nodes.items() if v["type"] in _AGENT_TYPES}

    def get_total_supply(self) -> float:
        """
        Sum effective output of all supply nodes (POWER_PLANT / POWER_GRID).
        ONLINE → full max_output; DEGRADED → 30% output; OFFLINE → 0.
        Falls back to 100.0 MW if no supply nodes are defined.
        """
        supply = 0.0
        for node in self.nodes.values():
            if node["type"] in _SUPPLY_TYPES:
                status = node["status"]
                if status == "ONLINE":
                    supply += node["max_output"]
                elif status == "DEGRADED":
                    supply += node["max_output"] * 0.3

        return round(supply, 2) if supply > 0 else 100.0

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Return a serialisable snapshot for WebSocket broadcast."""
        return {
            "nodes":        list(self.nodes.values()),
            "edges":        [
                {"from": u, "to": v, "capacity": d.get("capacity", 0)}
                for u, v, d in self.graph.edges(data=True)
            ],
            "total_supply": self.get_total_supply(),
            "online_count": sum(1 for n in self.nodes.values() if n["status"] == "ONLINE"),
            "degraded_count": sum(1 for n in self.nodes.values() if n["status"] == "DEGRADED"),
            "offline_count": sum(1 for n in self.nodes.values() if n["status"] == "OFFLINE"),
        }

    # ── Damage methods ────────────────────────────────────────────────────────

    def apply_damage(
        self,
        node_id:    str,
        severity:   float,              # 0.0 – 1.0
        rng:        Optional[random.Random] = None,
    ) -> str:
        """
        Apply direct damage to a single node.

        Severity thresholds:
            > 0.7 → OFFLINE   + max_output = 0
            > 0.3 → DEGRADED  + max_output reduced proportionally
            ≤ 0.3 → capacity reduction only (status unchanged)

        Returns new status string.
        """
        if node_id not in self.nodes:
            return "NOT_FOUND"
        rng  = rng or random.Random()
        node = self.nodes[node_id]

        if severity > 0.7:
            node["status"]     = "OFFLINE"
            node["max_output"] = 0.0
        elif severity > 0.3:
            node["status"]     = "DEGRADED"
            node["max_output"] = node["capacity"] * rng.uniform(0.2, 0.6)
        else:
            # Minor — reduce capacity without status change
            node["max_output"] = node["capacity"] * rng.uniform(0.7, 0.9)

        return node["status"]

    def apply_earthquake(
        self,
        epicenter:  Tuple[float, float],
        magnitude:  float,
        rng_seed:   Optional[int] = None,
    ) -> List[str]:
        """
        Apply earthquake damage to all nodes within radius.
        Delegates individual damage to apply_damage().

        Returns list of affected node_ids.
        """
        rng    = random.Random(rng_seed)
        radius = magnitude * 5.0
        affected: List[str] = []

        for node_id, node in self.nodes.items():
            dist = math.hypot(
                node["location"][0] - epicenter[0],
                node["location"][1] - epicenter[1],
            )
            if dist >= radius:
                continue

            damage_prob = 1.0 - (dist / radius)
            # Also reduce max_output proportionally
            node["capacity"]  = node["capacity"]   # keep original for reference
            new_status = self.apply_damage(node_id, severity=damage_prob, rng=rng)
            affected.append(node_id)
            logger.debug(
                "Earthquake hit %s: dist=%.2f prob=%.2f → %s",
                node_id, dist, damage_prob, new_status,
            )

        logger.warning(
            "apply_earthquake: epicenter=%s mag=%.1f → %d nodes affected",
            epicenter, magnitude, len(affected),
        )
        return affected

    def update_loads(self, allocations: Dict[str, float]) -> None:
        """Update current_load on nodes from arbiter allocation results."""
        for node_id, load in allocations.items():
            if node_id in self.nodes:
                self.nodes[node_id]["current_load"] = round(load, 3)

    def reset_damage(self) -> None:
        """Restore all nodes to ONLINE with full capacity (new scenario)."""
        for node in self.nodes.values():
            node["status"]     = "ONLINE"
            node["max_output"] = node["capacity"]
            node["current_load"] = 0.0
        logger.info("CityGraph: all nodes restored to ONLINE")

    def clear(self) -> None:
        """Clear all nodes and edges from the graph."""
        self.graph.clear()
        self.nodes.clear()
        logger.info("CityGraph: cleared all nodes and edges")


# ── Default city singleton ────────────────────────────────────────────────────
# Pre-initialised with a representative city layout.
# Imported by app/api/disasters.py and app/simulation/event_loop.py.

def _build_default_city() -> CityGraph:
    g = CityGraph()

    # Supply nodes
    g.add_infrastructure_node("pp1", POWER_PLANT,  (40.700, -74.020), capacity=60.0)
    g.add_infrastructure_node("pp2", POWER_PLANT,  (40.750, -73.980), capacity=40.0)

    # Demand / agent nodes
    g.add_infrastructure_node("hospital-1",  HOSPITAL,     (40.712, -74.006), capacity=10.0)
    g.add_infrastructure_node("hospital-2",  HOSPITAL,     (40.740, -73.990), capacity=10.0)
    g.add_infrastructure_node("water-1",     WATER_PLANT,  (40.705, -74.015), capacity=8.0)
    g.add_infrastructure_node("fire-1",      FIRE_STATION, (40.720, -74.000), capacity=5.0)
    g.add_infrastructure_node("fire-2",      FIRE_STATION, (40.745, -73.985), capacity=5.0)
    g.add_infrastructure_node("telecom-1",   TELECOM,      (40.715, -74.010), capacity=4.0)

    # Power line connections
    g.add_edge("pp1", "hospital-1", capacity=10.0)
    g.add_edge("pp1", "water-1",    capacity=8.0)
    g.add_edge("pp1", "fire-1",     capacity=5.0)
    g.add_edge("pp1", "telecom-1",  capacity=4.0)
    g.add_edge("pp2", "hospital-2", capacity=10.0)
    g.add_edge("pp2", "fire-2",     capacity=5.0)

    return g


city_graph = _build_default_city()
