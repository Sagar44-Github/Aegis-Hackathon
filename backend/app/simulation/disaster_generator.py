"""
disaster_generator.py — AEGIS Disaster Injection Engine

Simulates three crisis scenarios by mutating city_graph node states in-place
and returning a structured event dict consumed by the SimulationEngine and
broadcast via WebSocket to the frontend.

Scenarios:
    - Earthquake   : radial damage from epicenter, magnitude-scaled
    - Cyber Attack : targeted / cascading supply collapse
    - Flood        : zone-based progressive infrastructure loss
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Node status constants ─────────────────────────────────────────────────────
STATUS_ONLINE   = "ONLINE"
STATUS_DEGRADED = "DEGRADED"
STATUS_OFFLINE  = "OFFLINE"

# ── Vulnerability weights per node type ──────────────────────────────────────
# Higher = more likely to be damaged
_EARTHQUAKE_VULNERABILITY: Dict[str, float] = {
    "HOSPITAL":     0.3,   # reinforced structures
    "POWER_PLANT":  0.6,
    "POWER_GRID":   0.6,
    "WATER_PLANT":  0.5,
    "FIRE_STATION": 0.4,
    "TELECOM":      0.7,   # towers susceptible to shaking
    "SUBSTATION":   0.8,
    "DEFAULT":      0.5,
}

_FLOOD_VULNERABILITY: Dict[str, float] = {
    "HOSPITAL":     0.2,   # usually elevated
    "POWER_PLANT":  0.7,
    "POWER_GRID":   0.5,
    "WATER_PLANT":  0.9,   # ground-level, pumps flood first
    "FIRE_STATION": 0.4,
    "TELECOM":      0.3,
    "SUBSTATION":   0.8,
    "DEFAULT":      0.5,
}

_CYBER_TARGETS: Dict[str, float] = {
    "POWER_GRID":  0.95,   # primary target
    "SUBSTATION":  0.90,
    "TELECOM":     0.75,
    "WATER_PLANT": 0.60,
    "HOSPITAL":    0.40,
    "FIRE_STATION": 0.30,
    "DEFAULT":     0.20,
}


class DisasterGenerator:
    """
    Stateless disaster injection engine.

    Each static method:
        1. Mutates affected city_graph nodes in-place (status, capacity).
        2. Returns a structured event dict for logging / WebSocket broadcast.

    city_graph node format expected::

        {
          "node_id": {
            "type":         str,           # e.g. "HOSPITAL"
            "status":       str,           # ONLINE | DEGRADED | OFFLINE
            "capacity":     float,         # MW capacity
            "current_load": float,         # MW currently allocated
            "location":     (lat, lon),    # tuple of floats
          }
        }
    """

    # ── Earthquake ────────────────────────────────────────────────────────────

    @staticmethod
    def inject_earthquake(
        city_graph: Dict[str, Dict[str, Any]],
        magnitude: float = 7.0,
        epicenter: Tuple[float, float] = (40.7128, -74.0060),
        rng_seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Simulate an earthquake centred at *epicenter* with Richter *magnitude*.

        Damage radius scales exponentially with magnitude:
            radius_km = 10^(0.5 * magnitude - 1.5)   (simplified attenuation)

        Within radius, each node has a damage probability that:
            - Increases as distance → 0
            - Is weighted by node-type structural vulnerability
            - Degrades ONLINE → DEGRADED or DEGRADED → OFFLINE
            - Reduces capacity proportionally

        Args:
            city_graph:  Mutable dict of node_id → node_props.
            magnitude:   Richter scale magnitude (5.0 – 9.0).
            epicenter:   (lat, lon) of earthquake centre.
            rng_seed:    Optional seed for reproducible simulations.

        Returns:
            Event dict with type, magnitude, epicenter, affected_nodes, timestamp.
        """
        rng = random.Random(rng_seed)
        magnitude = max(4.0, min(9.5, magnitude))

        # Damage radius in "coordinate units" (approx degrees for simplicity)
        damage_radius = 10 ** (0.5 * magnitude - 1.5)

        affected: List[Dict[str, Any]] = []

        for node_id, props in city_graph.items():
            loc = props.get("location", (0.0, 0.0))
            dist = DisasterGenerator._euclidean_distance(epicenter, loc)

            if dist > damage_radius:
                continue  # Outside blast zone

            # Proximity factor: 1.0 at epicenter → 0 at edge
            proximity = 1.0 - (dist / damage_radius)

            node_type   = props.get("type", "DEFAULT")
            vuln        = _EARTHQUAKE_VULNERABILITY.get(node_type, 0.5)
            damage_prob = proximity * vuln * (magnitude / 9.5)

            roll = rng.random()
            old_status = props.get("status", STATUS_ONLINE)

            if roll < damage_prob * 0.6:
                # Severe hit
                if old_status == STATUS_ONLINE:
                    props["status"] = STATUS_DEGRADED
                    props["capacity"] = props.get("capacity", 100.0) * rng.uniform(0.4, 0.7)
                elif old_status == STATUS_DEGRADED:
                    props["status"] = STATUS_OFFLINE
                    props["capacity"] = 0.0

            elif roll < damage_prob:
                # Minor damage — capacity reduction only
                props["capacity"] = props.get("capacity", 100.0) * rng.uniform(0.7, 0.9)

            new_status = props.get("status", STATUS_ONLINE)
            if new_status != old_status or roll < damage_prob:
                affected.append({
                    "node_id":       node_id,
                    "node_type":     node_type,
                    "old_status":    old_status,
                    "new_status":    new_status,
                    "distance_from_epicenter": round(dist, 4),
                    "damage_probability": round(damage_prob, 3),
                })

        event = {
            "type":          "EARTHQUAKE",
            "magnitude":     magnitude,
            "epicenter":     list(epicenter),
            "damage_radius": round(damage_radius, 3),
            "affected_nodes": len(affected),
            "affected":      affected,
            "description":   (
                f"M{magnitude:.1f} earthquake struck near {epicenter}. "
                f"{len(affected)} infrastructure node(s) affected within "
                f"{damage_radius:.1f} km radius."
            ),
            "timestamp":     time.time(),
            "severity":      DisasterGenerator._magnitude_to_severity(magnitude),
        }

        logger.warning(
            "EARTHQUAKE M%.1f @ %s — %d nodes affected",
            magnitude, epicenter, len(affected)
        )
        return event

    # ── Cyber Attack ──────────────────────────────────────────────────────────

    @staticmethod
    def inject_cyber_attack(
        city_graph: Dict[str, Dict[str, Any]],
        primary_target: str = "POWER_GRID",
        severity: str = "HIGH",
        rng_seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Simulate a cyber attack (e.g. ransomware on grid control systems).

        The attack:
            - Immediately degrades / offline the primary_target type nodes.
            - Cascades to dependent node types with decreasing probability.
            - Reduces capacity without physical damage (can be restored faster).

        Args:
            city_graph:      Mutable dict of node_id → node_props.
            primary_target:  Node type to hit first (default: POWER_GRID).
            severity:        "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
            rng_seed:        Optional seed for reproducibility.

        Returns:
            Event dict with attack details and affected nodes.
        """
        rng = random.Random(rng_seed)

        severity_multipliers = {"LOW": 0.3, "MEDIUM": 0.55, "HIGH": 0.80, "CRITICAL": 1.0}
        sev_mult = severity_multipliers.get(severity, 0.8)

        affected: List[Dict[str, Any]] = []

        for node_id, props in city_graph.items():
            node_type   = props.get("type", "DEFAULT")
            base_prob   = _CYBER_TARGETS.get(node_type, _CYBER_TARGETS["DEFAULT"])
            attack_prob = base_prob * sev_mult

            # Primary target always takes maximum impact
            if node_type == primary_target:
                attack_prob = min(1.0, attack_prob * 1.4)

            roll       = rng.random()
            old_status = props.get("status", STATUS_ONLINE)

            if roll < attack_prob:
                # Cyber attacks degrade control systems — capacity drops
                cap_loss = rng.uniform(0.3, 0.7) * sev_mult

                if roll < attack_prob * 0.4:
                    props["status"]   = STATUS_OFFLINE
                    props["capacity"] = max(0.0, props.get("capacity", 100.0) * (1 - cap_loss))
                    props["cyber_compromised"] = True
                else:
                    props["status"]   = STATUS_DEGRADED
                    props["capacity"] = props.get("capacity", 100.0) * rng.uniform(0.5, 0.8)
                    props["cyber_compromised"] = True

                affected.append({
                    "node_id":           node_id,
                    "node_type":         node_type,
                    "old_status":        old_status,
                    "new_status":        props["status"],
                    "capacity_remaining": round(props["capacity"], 2),
                    "attack_probability": round(attack_prob, 3),
                    "is_primary_target": node_type == primary_target,
                })

        event = {
            "type":            "CYBER_ATTACK",
            "primary_target":  primary_target,
            "severity":        severity,
            "affected_nodes":  len(affected),
            "affected":        affected,
            "description": (
                f"{severity} cyber attack on {primary_target.replace('_', ' ')} "
                f"control systems — {len(affected)} nodes compromised. "
                "Manual override may be required."
            ),
            "timestamp":       time.time(),
            "recovery_hint":   "Isolate compromised nodes and restore from backup.",
        }

        logger.warning(
            "CYBER ATTACK (%s) targeting %s — %d nodes compromised",
            severity, primary_target, len(affected)
        )
        return event

    # ── Flood ─────────────────────────────────────────────────────────────────

    @staticmethod
    def inject_flood(
        city_graph: Dict[str, Dict[str, Any]],
        flood_zone: Tuple[Tuple[float, float], Tuple[float, float]] = (
            (40.70, -74.02), (40.73, -73.98)
        ),
        water_level_m: float = 1.5,
        rng_seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Simulate a flood within a bounding-box zone.

        Water level determines damage severity:
            < 0.5m  → minor degradation (some nodes)
            0.5–2m  → moderate (ground-floor equipment at risk)
            > 2m    → severe (pumps, substations likely offline)

        Nodes outside the flood_zone bounding box are unaffected.

        Args:
            city_graph:    Mutable dict of node_id → node_props.
            flood_zone:    ((lat_min, lon_min), (lat_max, lon_max)) bounding box.
            water_level_m: Flood water depth in metres.
            rng_seed:      Optional seed for reproducibility.

        Returns:
            Event dict with flood zone, water level, and affected nodes.
        """
        rng = random.Random(rng_seed)
        water_level_m = max(0.1, water_level_m)

        (lat_min, lon_min), (lat_max, lon_max) = flood_zone

        # Severity multiplier from water level
        if water_level_m < 0.5:
            water_mult = 0.25
            flood_severity = "MINOR"
        elif water_level_m < 2.0:
            water_mult = 0.60
            flood_severity = "MODERATE"
        elif water_level_m < 4.0:
            water_mult = 0.85
            flood_severity = "SEVERE"
        else:
            water_mult = 1.0
            flood_severity = "CATASTROPHIC"

        affected: List[Dict[str, Any]] = []

        for node_id, props in city_graph.items():
            loc = props.get("location", (0.0, 0.0))
            lat, lon = loc[0], loc[1]

            # Check if node is within flood zone
            if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                continue

            node_type    = props.get("type", "DEFAULT")
            vuln         = _FLOOD_VULNERABILITY.get(node_type, 0.5)
            damage_prob  = vuln * water_mult
            old_status   = props.get("status", STATUS_ONLINE)

            roll = rng.random()

            if roll < damage_prob * 0.5:
                props["status"]   = STATUS_OFFLINE
                props["capacity"] = 0.0
                props["flood_damaged"] = True
            elif roll < damage_prob:
                props["status"]   = STATUS_DEGRADED
                props["capacity"] = props.get("capacity", 100.0) * rng.uniform(0.3, 0.6)
                props["flood_damaged"] = True
            elif roll < damage_prob * 1.3:
                # Capacity reduction without status change
                props["capacity"] = props.get("capacity", 100.0) * rng.uniform(0.7, 0.9)

            new_status = props.get("status", STATUS_ONLINE)
            if new_status != old_status or roll < damage_prob * 1.3:
                affected.append({
                    "node_id":       node_id,
                    "node_type":     node_type,
                    "old_status":    old_status,
                    "new_status":    new_status,
                    "capacity_remaining": round(props.get("capacity", 0.0), 2),
                    "in_flood_zone": True,
                    "damage_probability": round(damage_prob, 3),
                })

        event = {
            "type":          "FLOOD",
            "flood_zone":    [list(flood_zone[0]), list(flood_zone[1])],
            "water_level_m": water_level_m,
            "flood_severity": flood_severity,
            "affected_nodes": len(affected),
            "affected":      affected,
            "description": (
                f"{flood_severity} flood with {water_level_m:.1f}m water level "
                f"in zone {flood_zone}. "
                f"{len(affected)} infrastructure node(s) affected."
            ),
            "timestamp":     time.time(),
            "recovery_hint": "Pump stations and drainage must be restored before power.",
        }

        logger.warning(
            "FLOOD (%s, %.1fm) in zone %s — %d nodes affected",
            flood_severity, water_level_m, flood_zone, len(affected)
        )
        return event

    # ── Aftershock (bonus) ────────────────────────────────────────────────────

    @staticmethod
    def inject_aftershock(
        city_graph: Dict[str, Dict[str, Any]],
        original_magnitude: float,
        epicenter: Tuple[float, float],
        rng_seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate an aftershock (magnitude = original − 1.0 to 1.5).
        Delegates to inject_earthquake with reduced magnitude.
        """
        aftershock_mag = max(4.0, original_magnitude - random.uniform(1.0, 1.5))
        event = DisasterGenerator.inject_earthquake(
            city_graph, aftershock_mag, epicenter, rng_seed
        )
        event["type"]        = "AFTERSHOCK"
        event["description"] = event["description"].replace("earthquake", "aftershock")
        return event

    # ── Helper utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _euclidean_distance(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> float:
        """Euclidean distance between two (lat, lon) points (approx for small areas)."""
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    @staticmethod
    def _magnitude_to_severity(magnitude: float) -> str:
        if magnitude >= 8.0:
            return "CATASTROPHIC"
        elif magnitude >= 7.0:
            return "SEVERE"
        elif magnitude >= 6.0:
            return "MODERATE"
        elif magnitude >= 5.0:
            return "MINOR"
        else:
            return "MICRO"

    @staticmethod
    def get_scenario(name: str) -> List[Dict[str, Any]]:
        """
        Return a scripted event timeline for common demo scenarios.

        Usage::

            events = DisasterGenerator.get_scenario("earthquake")
            # Feed into SimulationEngine.load_scenario(events)

        Returns list of dicts with keys: delay_s, method, kwargs.
        """
        scenarios: Dict[str, List[Dict[str, Any]]] = {
            "earthquake": [
                {"delay_s": 0,   "method": "inject_earthquake",
                 "kwargs": {"magnitude": 7.5, "epicenter": (40.712, -74.006)}},
                {"delay_s": 300, "method": "inject_aftershock",
                 "kwargs": {"original_magnitude": 7.5, "epicenter": (40.715, -74.010)}},
                {"delay_s": 900, "method": "inject_earthquake",
                 "kwargs": {"magnitude": 5.8, "epicenter": (40.720, -74.000)}},
            ],
            "cyber_attack": [
                {"delay_s": 0,   "method": "inject_cyber_attack",
                 "kwargs": {"primary_target": "POWER_GRID", "severity": "HIGH"}},
                {"delay_s": 120, "method": "inject_cyber_attack",
                 "kwargs": {"primary_target": "TELECOM",    "severity": "MEDIUM"}},
            ],
            "flood": [
                {"delay_s": 0,   "method": "inject_flood",
                 "kwargs": {"water_level_m": 0.8,
                            "flood_zone": ((40.70, -74.02), (40.73, -73.98))}},
                {"delay_s": 600, "method": "inject_flood",
                 "kwargs": {"water_level_m": 2.5,
                            "flood_zone": ((40.70, -74.02), (40.73, -73.98))}},
            ],
            "compound": [
                {"delay_s": 0,   "method": "inject_earthquake",
                 "kwargs": {"magnitude": 6.8, "epicenter": (40.712, -74.006)}},
                {"delay_s": 180, "method": "inject_cyber_attack",
                 "kwargs": {"primary_target": "POWER_GRID", "severity": "HIGH"}},
                {"delay_s": 360, "method": "inject_flood",
                 "kwargs": {"water_level_m": 1.5,
                            "flood_zone": ((40.70, -74.02), (40.73, -73.98))}},
            ],
        }
        return scenarios.get(name, [])
