"""
hospital_agent.py — Hospital Crisis Agent

Represents a hospital's autonomous power negotiation agent.
Demand scales with ICU patient load; urgency spikes when backup
generator fuel drops below critical thresholds.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from app.agents.base_agent import CrisisAgent
from app.schemas import AgentStatus, AgentType


class HospitalAgent(CrisisAgent):
    """
    Autonomous agent for a hospital utility.

    Urgency tiers:
        fuel < 20%  → 9.5  (CRITICAL — life support at risk)
        fuel < 50%  → 7.5  (DEGRADED — generator struggling)
        fuel >= 50% → 5.0 + patient_factor  (NORMAL operations)
    """

    def __init__(
        self,
        agent_id:     str,
        location:     Tuple[float, float],
        icu_patients: int   = 50,
        generator_fuel: float = 100.0,
    ) -> None:
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.HOSPITAL,
            base_priority=10,          # highest priority agent
            location=location,
        )
        self.icu_patients:    int   = icu_patients
        self.generator_fuel:  float = generator_fuel   # percent 0–100

    # ── Abstract implementations ──────────────────────────────────────────────

    def calculate_demand(self, city_graph: Dict[str, Any]) -> float:
        """
        Base hospital load + ICU patient load.
            base  = 2.0 MW  (lights, HVAC, general equipment)
            ICU   = 0.05 MW per patient (50 kW each)
        """
        base_load = 2.0
        icu_load  = self.icu_patients * 0.05
        return base_load + icu_load

    def calculate_urgency(self, city_graph: Dict[str, Any]) -> float:
        """
        Urgency driven by generator fuel level and patient count.
        Fuel < 20% → life-support risk → urgency 9.5 (CRITICAL).
        """
        if self.generator_fuel < 20:
            self.state = AgentStatus.OFFLINE          # near-critical treated as offline
            return 9.5
        elif self.generator_fuel < 50:
            self.state = AgentStatus.DEGRADED
            return 7.5
        else:
            self.state = AgentStatus.ONLINE
            patient_factor = self.icu_patients / 100  # 0.5 for 50 patients, 1.0 for 100
            return min(9.0, 5.0 + patient_factor)

    # ── Hospital-specific methods ─────────────────────────────────────────────

    def consume_fuel(self, hours: float = 1.0) -> None:
        """
        Simulate generator fuel consumption.
        Burn rate: 5% per hour at full load.
        """
        if self.generator_fuel > 0:
            self.generator_fuel = max(0.0, self.generator_fuel - (5.0 * hours))

    def refuel(self, amount_pct: float = 30.0) -> None:
        """Emergency refuelling — caps at 100%."""
        self.generator_fuel = min(100.0, self.generator_fuel + amount_pct)

    def surge_patients(self, additional: int) -> None:
        """Add disaster-surge patients (increases demand and urgency)."""
        self.icu_patients = max(0, self.icu_patients + additional)

    def _get_metadata(self) -> Dict[str, Any]:
        """Attach hospital-specific fields to the bid metadata."""
        return {
            "state":          self.state.value,
            "icu_patients":   self.icu_patients,
            "generator_fuel": round(self.generator_fuel, 1),
        }
