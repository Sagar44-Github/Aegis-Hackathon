"""
fire_agent.py — Fire Station Crisis Agent

Demand scales with active trucks deployed; urgency escalates
with the number of simultaneous active incidents.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.agents.base_agent import CrisisAgent
from app.schemas import AgentStatus, AgentType


class FireStationAgent(CrisisAgent):
    """
    Autonomous agent for a fire/emergency station.

    Demand formula:
        0.5 MW base + 1.0 MW per active truck deployed

    Urgency formula:
        3.0 base + 2.0 per active incident
        (capped at 9.8 to stay below hospital's life-support priority)
    """

    def __init__(
        self,
        agent_id:        str,
        location:        Tuple[float, float],
        active_trucks:   int = 3,
        active_incidents: int = 0,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.FIRE_STATION,
            base_priority=9,
            location=location,
        )
        self.active_trucks    = active_trucks
        self.active_incidents = active_incidents

    # ── Abstract implementations ──────────────────────────────────────────────

    def calculate_demand(self, city_graph: Dict[str, Any]) -> float:
        """
        Base station load + truck operational load.
            base  = 10.0 MW  (comms, lights, equipment, charging)
            trucks = 5.0 MW per active truck (high power for pumps, comms)
        """
        import random
        base = 10.0 + random.uniform(-2, 3)
        return round(base + (self.active_trucks * 5.0), 3)

    def calculate_urgency(self, city_graph: Dict[str, Any]) -> float:
        """
        Urgency driven by active incident count with randomness.
            0 incidents → 4.0  (ONLINE — standby)
            1 incident  → 6.5  (DEGRADED — responding)
            3 incidents → 9.5  (DEGRADED — overwhelmed)
        """
        import random
        random_factor = random.uniform(-0.5, 0.5)
        urgency = 4.0 + (self.active_incidents * 2.5) + random_factor
        urgency = min(9.8, urgency)

        if urgency >= 7.0:
            self.state = AgentStatus.DEGRADED
        else:
            self.state = AgentStatus.ONLINE

        return round(urgency, 2)

    # ── Fire-specific helpers ─────────────────────────────────────────────────

    def dispatch_truck(self, count: int = 1) -> None:
        """Deploy additional trucks to an incident."""
        import random
        self.active_trucks    = max(0, self.active_trucks + count)
        # Randomly add incidents to simulate dynamic emergency situations
        if random.random() > 0.7:
            self.active_incidents = max(0, self.active_incidents + random.randint(1, 2))

    def resolve_incident(self, count: int = 1) -> None:
        """Mark incidents as resolved, recall trucks."""
        self.active_incidents = max(0, self.active_incidents - count)
        self.active_trucks    = max(0, self.active_trucks - count)

    def _get_metadata(self) -> Dict[str, Any]:
        return {
            "state":            self.state.value,
            "active_trucks":    self.active_trucks,
            "active_incidents": self.active_incidents,
        }
