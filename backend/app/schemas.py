"""
schemas.py — AEGIS Pydantic Data Models

Single source of truth for all data structures shared across agents,
negotiation, websocket, and API layers.

Note: placed at app/schemas.py for easy import during hackathon.
      (app/schemas/__init__.py can re-export from here later.)
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


# ── Enums ─────────────────────────────────────────────────────────────────────

class AgentType(str, Enum):
    HOSPITAL     = "HOSPITAL"
    WATER_PLANT  = "WATER_PLANT"
    FIRE_STATION = "FIRE_STATION"
    POWER_GRID   = "POWER_GRID"
    TELECOM      = "TELECOM"


class AgentStatus(str, Enum):
    ONLINE   = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE  = "OFFLINE"


class DisasterType(str, Enum):
    EARTHQUAKE   = "EARTHQUAKE"
    CYBER_ATTACK = "CYBER_ATTACK"
    FLOOD        = "FLOOD"
    AFTERSHOCK   = "AFTERSHOCK"


class Severity(str, Enum):
    LOW          = "LOW"
    MODERATE     = "MODERATE"
    HIGH         = "HIGH"
    CRITICAL     = "CRITICAL"
    CATASTROPHIC = "CATASTROPHIC"


# ── Core models ───────────────────────────────────────────────────────────────

class Bid(BaseModel):
    """Power allocation bid submitted by an agent to the Arbiter."""

    agent_id:      str
    agent_type:    AgentType
    demand_mw:     float       = Field(gt=0, description="MW requested")
    urgency_score: float       = Field(ge=0.0, le=10.0, description="0–10 urgency")
    justification: str         = Field(default="", description="LLM or rule-based reason")
    timestamp:     float       = Field(default_factory=time.time)
    metadata:      Dict[str, Any] = Field(default_factory=dict)

    @field_validator("urgency_score")
    @classmethod
    def clamp_urgency(cls, v: float) -> float:
        return max(0.0, min(10.0, v))

    @field_validator("demand_mw")
    @classmethod
    def round_demand(cls, v: float) -> float:
        return round(v, 3)

    model_config = {"json_encoders": {float: lambda v: round(v, 4)}}


class Allocation(BaseModel):
    """Result of one negotiation round for a single agent."""

    agent_id:     str
    agent_type:   AgentType
    allocated_mw: float = Field(ge=0.0)
    demand_mw:    float = Field(ge=0.0)
    urgency_score: float = Field(ge=0.0, le=10.0, default=5.0)

    @computed_field                         # type: ignore[misc]
    @property
    def satisfaction(self) -> float:
        """Fraction of demand met (0.0–1.0). 1.0 if no demand."""
        if self.demand_mw <= 0:
            return 1.0
        return round(min(1.0, self.allocated_mw / self.demand_mw), 4)

    @computed_field                         # type: ignore[misc]
    @property
    def shortfall_mw(self) -> float:
        """Unmet demand in MW."""
        return round(max(0.0, self.demand_mw - self.allocated_mw), 3)

    model_config = {"json_encoders": {float: lambda v: round(v, 4)}}


class DisasterEvent(BaseModel):
    """A disaster event injected into the simulation."""

    type:          str
    severity:      str                    = "UNKNOWN"
    description:   str                    = ""
    affected_nodes: int                   = 0
    timestamp:     float                  = Field(default_factory=time.time)
    metadata:      Dict[str, Any]         = Field(default_factory=dict)


class SimulationState(BaseModel):
    """Full snapshot of the simulation at one tick — sent via WebSocket."""

    tick:            int
    timestamp:       float                = Field(default_factory=time.time)
    total_supply_mw: float
    total_demand_mw: float
    allocations:     List[Allocation]     = Field(default_factory=list)
    agent_logs:      List[str]            = Field(default_factory=list)
    metrics:         Dict[str, float]     = Field(default_factory=dict)
    disasters:       List[str]            = Field(default_factory=list)
    disaster_events: List[DisasterEvent]  = Field(default_factory=list)

    @computed_field                       # type: ignore[misc]
    @property
    def supply_deficit_mw(self) -> float:
        """How much demand exceeds supply (0 if supply is sufficient)."""
        return round(max(0.0, self.total_demand_mw - self.total_supply_mw), 2)

    @computed_field                       # type: ignore[misc]
    @property
    def overall_satisfaction(self) -> float:
        """Mean satisfaction across all allocations."""
        if not self.allocations:
            return 1.0
        return round(
            sum(a.satisfaction for a in self.allocations) / len(self.allocations), 4
        )

    model_config = {
        "json_encoders": {float: lambda v: round(v, 4)},
        "populate_by_name": True,
    }


class AgentStateSnapshot(BaseModel):
    """Lightweight status snapshot for a single agent (used in API responses)."""

    agent_id:        str
    agent_type:      AgentType
    status:          AgentStatus = AgentStatus.ONLINE
    urgency_score:   float       = Field(ge=0.0, le=10.0, default=0.0)
    current_demand:  float       = 0.0
    allocated_mw:    float       = 0.0
    location:        List[float] = Field(default_factory=lambda: [0.0, 0.0])
    total_shortfall: float       = 0.0


# ── WebSocket message envelope ────────────────────────────────────────────────

class WSMessage(BaseModel):
    """Envelope for all WebSocket broadcasts."""

    event_type: str                   # "state" | "bids" | "disaster" | "metrics"
    payload:    Any
    timestamp:  float = Field(default_factory=time.time)


if __name__ == "__main__":
    # Quick smoke test
    bid = Bid(
        agent_id="hospital-1",
        agent_type=AgentType.HOSPITAL,
        demand_mw=4.5,
        urgency_score=8.5,
        justification="ICU requires uninterrupted power.",
    )
    alloc = Allocation(
        agent_id="hospital-1",
        agent_type=AgentType.HOSPITAL,
        allocated_mw=3.5,
        demand_mw=4.5,
        urgency_score=8.5,
    )
    state = SimulationState(
        tick=1,
        total_supply_mw=20.0,
        total_demand_mw=25.0,
        allocations=[alloc],
        agent_logs=["Hospital bid accepted at 3.5 MW"],
        metrics={"fairness_index": 0.87},
        disasters=["EARTHQUAKE M7.5"],
    )
    print("Schemas OK")
    print(f"  Bid:         {bid.agent_id} → {bid.demand_mw} MW @ urgency {bid.urgency_score}")
    print(f"  Allocation:  satisfaction={alloc.satisfaction}, shortfall={alloc.shortfall_mw} MW")
    print(f"  State:       tick={state.tick}, deficit={state.supply_deficit_mw} MW, "
          f"overall_satisfaction={state.overall_satisfaction}")
