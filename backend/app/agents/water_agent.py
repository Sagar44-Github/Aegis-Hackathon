"""
water_agent.py — Water Treatment Plant Crisis Agent

Demand scales with pump deficit; urgency spikes when production
falls significantly below capacity (contamination risk).
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.agents.base_agent import CrisisAgent
from app.schemas import AgentStatus, AgentType


class WaterAgent(CrisisAgent):
    """
    Autonomous agent for a water treatment plant.

    Urgency tiers (based on production deficit = capacity - current_production):
        deficit > 30 m³/h → 8.5  (DEGRADED — contamination risk)
        deficit > 10 m³/h → 6.5  (DEGRADED — pumps struggling)
        deficit ≤ 10 m³/h → 4.0  (ONLINE — normal operations)

    Demand surges 1.5× when deficit > 20 m³/h (catch-up pumping needed).
    """

    def __init__(
        self,
        agent_id:          str,
        location:          Tuple[float, float],
        pump_capacity:     float = 100.0,   # m³/hour max
        current_production: float = 50.0,   # m³/hour current
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.WATER_PLANT,
            base_priority=8,
            location=location,
        )
        self.pump_capacity      = pump_capacity
        self.current_production = current_production

    # ── Abstract implementations ──────────────────────────────────────────────

    def calculate_demand(self, city_graph: Dict[str, Any]) -> float:
        """
        Base pump load + surge power when production deficit is high.
            normal : 1.5 MW
            deficit > 20 m³/h : 2.25 MW (1.5× surge to catch up)
        """
        base    = 1.5
        deficit = self.pump_capacity - self.current_production
        return round(base * 1.5 if deficit > 20 else base, 3)

    def calculate_urgency(self, city_graph: Dict[str, Any]) -> float:
        """Urgency driven by water production deficit."""
        deficit = self.pump_capacity - self.current_production

        if deficit > 30:
            self.state = AgentStatus.DEGRADED
            return 8.5
        elif deficit > 10:
            self.state = AgentStatus.DEGRADED
            return 6.5
        else:
            self.state = AgentStatus.ONLINE
            return 4.0

    # ── Water-specific helpers ────────────────────────────────────────────────

    def apply_flood_damage(self, damage_pct: float = 40.0) -> None:
        """Flood reduces pump production capacity."""
        self.current_production = max(
            0.0, self.current_production * (1 - damage_pct / 100)
        )

    def restore_production(self, amount_m3h: float = 10.0) -> None:
        """Gradually restore production after repairs."""
        self.current_production = min(
            self.pump_capacity,
            self.current_production + amount_m3h,
        )

    @property
    def deficit(self) -> float:
        return round(self.pump_capacity - self.current_production, 2)

    def _get_metadata(self) -> Dict[str, Any]:
        return {
            "state":              self.state.value,
            "pump_capacity":      self.pump_capacity,
            "current_production": self.current_production,
            "pump_deficit_m3h":   self.deficit,
        }
