"""
base_agent.py — Abstract Base Class for all AEGIS Crisis Agents

Each agent represents a critical city utility (hospital, water plant, etc.)
and follows a perceive → think → act cycle:
    1. calculate_demand()  — how much power it needs this tick
    2. calculate_urgency() — how urgently it needs it (0–10)
    3. generate_bid()      — packages both into a Bid schema object

Concrete agent classes (hospital_agent.py, etc.) implement the two
abstract methods; everything else is inherited.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.schemas import AgentStatus, AgentType, Allocation, Bid

logger = logging.getLogger(__name__)


class CrisisAgent(ABC):
    """
    Abstract base for all AEGIS utility agents.

    Subclasses must implement:
        calculate_demand(city_graph)  → float  (MW needed)
        calculate_urgency(city_graph) → float  (0–10 urgency)
    """

    def __init__(
        self,
        agent_id:      str,
        agent_type:    AgentType,
        base_priority: int,
        location:      tuple = (0.0, 0.0),
    ) -> None:
        self.agent_id      = agent_id
        self.agent_type    = agent_type
        self.base_priority = base_priority
        self.location      = location

        # Runtime state — updated each tick
        self.current_demand: float      = 0.0
        self.urgency_score:  float      = 0.0
        self.allocated_mw:   float      = 0.0
        self.state:          AgentStatus = AgentStatus.ONLINE

        # History (last 100 ticks)
        self._bid_history:        List[Bid]   = []
        self._allocation_history: List[float] = []
        self.total_cycles:        int         = 0
        self.total_shortfall_mw:  float       = 0.0

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def calculate_demand(self, city_graph: Dict[str, Any]) -> float:
        """Return MW power demand for this negotiation tick."""
        pass

    @abstractmethod
    def calculate_urgency(self, city_graph: Dict[str, Any]) -> float:
        """Return urgency score 0–10 (10 = most critical)."""
        pass

    # ── Concrete methods ──────────────────────────────────────────────────────

    def generate_bid(
        self,
        city_graph:    Dict[str, Any],
        justification: str = "",
    ) -> Bid:
        """
        Run perceive-think-act and return a Bid schema object.

        Args:
            city_graph:    Current node state dict from CityGraph.
            justification: Pre-computed LLM justification string.
                           If empty, a rule-based fallback is used.

        Returns:
            Bid pydantic model ready for the Arbiter.
        """
        self.total_cycles += 1

        # PERCEIVE & THINK
        self.current_demand = round(self.calculate_demand(city_graph), 3)
        self.urgency_score  = max(0.0, min(10.0,
                                round(self.calculate_urgency(city_graph), 2)))

        # Update agent status from urgency
        self._update_state()

        # Fallback justification if LLM hasn't run yet
        if not justification:
            justification = self._rule_based_justification()

        bid = Bid(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            demand_mw=self.current_demand,
            urgency_score=self.urgency_score,
            justification=justification,
            timestamp=time.time(),
        )

        # Keep rolling history
        self._bid_history.append(bid)
        if len(self._bid_history) > 100:
            self._bid_history = self._bid_history[-100:]

        logger.debug(
            "[%s] bid=%.1f MW urgency=%.1f state=%s",
            self.agent_id, self.current_demand,
            self.urgency_score, self.state.value,
        )
        return bid

    def receive_allocation(self, allocated_mw: float) -> None:
        """
        Called by the Arbiter to inform this agent of its allocation.
        Updates allocated_mw and tracks cumulative shortfall.
        """
        self.allocated_mw = max(0.0, allocated_mw)
        shortfall = max(0.0, self.current_demand - self.allocated_mw)
        self.total_shortfall_mw += shortfall

        self._allocation_history.append(self.allocated_mw)
        if len(self._allocation_history) > 100:
            self._allocation_history = self._allocation_history[-100:]

        logger.debug(
            "[%s] allocated=%.1f MW (demand=%.1f, shortfall=%.1f)",
            self.agent_id, self.allocated_mw,
            self.current_demand, shortfall,
        )

    def get_status(self) -> Dict[str, Any]:
        """Return a serialisable status dict for WebSocket / API responses."""
        return {
            "agent_id":        self.agent_id,
            "agent_type":      self.agent_type.value,
            "state":           self.state.value,
            "urgency_score":   self.urgency_score,
            "current_demand":  self.current_demand,
            "allocated_mw":    self.allocated_mw,
            "location":        list(self.location),
            "total_cycles":    self.total_cycles,
            "total_shortfall_mw": round(self.total_shortfall_mw, 2),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _update_state(self) -> None:
        """Derive ONLINE / DEGRADED / OFFLINE from current urgency score."""
        if self.urgency_score >= 8.0:
            self.state = AgentStatus.OFFLINE       # critical — treat as near-offline
        elif self.urgency_score >= 5.0:
            self.state = AgentStatus.DEGRADED
        else:
            self.state = AgentStatus.ONLINE

    def _rule_based_justification(self) -> str:
        """Minimal fallback justification when LLM is unavailable."""
        return (
            f"{self.agent_type.value.replace('_', ' ').title()} requires "
            f"{self.current_demand:.1f} MW for critical operations "
            f"(Urgency: {self.urgency_score:.1f}/10)."
        )
