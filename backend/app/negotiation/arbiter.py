"""
arbiter.py — Central Arbiter for AEGIS Negotiation

Implements urgency-weighted auction allocation:
    1. Sort bids by urgency_score (descending)
    2. Allocate min(demand, remaining_supply) top-down
    3. Track history for fairness and metrics

Optionally applies a minimum_guarantee_mw so no agent gets
completely starved (configurable per deployment).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import AgentType, Allocation, Bid

logger = logging.getLogger(__name__)


class CentralArbiter:
    """
    Urgency-weighted power auction arbiter.

    Usage::

        arb = CentralArbiter(total_supply=20.0)
        allocations_dict = arb.allocate(bids, total_supply=15.0)
        summary          = arb.get_round_summary()
    """

    def __init__(
        self,
        minimum_guarantee_mw: float = 0.0,   # MW floor guaranteed to every agent
    ) -> None:
        self.minimum_guarantee_mw = minimum_guarantee_mw

        # Full history: list of round dicts
        self._round_history: List[Dict[str, Any]] = []
        # Flat list of per-allocation rows (for fairness / metrics)
        self._allocation_log: List[Dict[str, Any]] = []

    # ── Core allocation ───────────────────────────────────────────────────────

    def allocate(
        self,
        bids:         List[Bid],
        total_supply: float,
    ) -> Dict[str, float]:
        """
        Urgency-weighted auction: allocates power top-down by urgency score.

        Args:
            bids:         List of Bid pydantic objects from all agents.
            total_supply: Total available MW this round.

        Returns:
            Dict mapping agent_id → allocated_mw (float).
            Every agent in bids is present, even if allocated 0.
        """
        if not bids:
            return {}

        total_supply = max(0.0, total_supply)

        # 1 — Sort by urgency descending (highest urgency served first)
        sorted_bids = sorted(bids, key=lambda b: b.urgency_score, reverse=True)

        # 2 — Reserve minimum guarantee for every agent first
        n_agents   = len(sorted_bids)
        guaranteed = min(
            self.minimum_guarantee_mw,
            total_supply / n_agents if n_agents else 0.0,
        )
        reserved       = guaranteed * n_agents
        remaining      = max(0.0, total_supply - reserved)

        allocations: Dict[str, float] = {}

        # 3 — Top-down urgency allocation on remaining supply
        for bid in sorted_bids:
            if remaining <= 0:
                allocations[bid.agent_id] = round(guaranteed, 3)
            else:
                extra = min(bid.demand_mw - guaranteed, remaining)
                extra = max(0.0, extra)
                alloc = guaranteed + extra
                allocations[bid.agent_id] = round(alloc, 3)
                remaining -= extra

        # 4 — Log this round
        round_record = self._build_round_record(
            sorted_bids, allocations, total_supply
        )
        self._round_history.append(round_record)

        for bid in sorted_bids:
            allocated = allocations[bid.agent_id]
            is_fully_satisfied = allocated >= bid.demand_mw
            decision = "ACCEPTED" if is_fully_satisfied else "PARTIALLY_ACCEPTED" if allocated > 0 else "DENIED"
            
            # Generate reasoning for the decision
            if is_fully_satisfied:
                reason = f"Fully satisfied - high urgency ({bid.urgency_score}/10) and sufficient supply available"
            elif allocated > 0:
                reason = f"Partially satisfied - allocated {allocated:.1f} MW of {bid.demand_mw:.1f} MW demand due to supply constraints. Urgency: {bid.urgency_score}/10"
            else:
                reason = f"Denied - insufficient supply. Demand: {bid.demand_mw:.1f} MW, urgency: {bid.urgency_score}/10, other agents had higher priority"
            
            self._allocation_log.append({
                "tick":      len(self._round_history),
                "agent_id":  bid.agent_id,
                "agent_type": bid.agent_type.value,
                "urgency":   bid.urgency_score,
                "demand":    bid.demand_mw,
                "allocated": allocated,
                "decision":  decision,
                "reason":    reason,
                "justification": bid.justification,
            })

        logger.info(
            "Arbiter round %d | supply=%.1f MW | agents=%d | "
            "total_allocated=%.1f MW | fairness=%.3f",
            len(self._round_history),
            total_supply,
            n_agents,
            sum(allocations.values()),
            self.jains_fairness(list(allocations.values())),
        )

        return allocations

    def allocate_with_schema(
        self,
        bids:         List[Bid],
        total_supply: float,
    ) -> List[Allocation]:
        """
        Same as allocate() but returns List[Allocation] schema objects
        (richer — includes satisfaction, shortfall, urgency_score).
        """
        raw = self.allocate(bids, total_supply)

        # Build a lookup for bid metadata
        bid_map = {b.agent_id: b for b in bids}

        results: List[Allocation] = []
        for agent_id, allocated_mw in raw.items():
            bid = bid_map[agent_id]
            results.append(Allocation(
                agent_id=agent_id,
                agent_type=bid.agent_type,
                allocated_mw=allocated_mw,
                demand_mw=bid.demand_mw,
                urgency_score=bid.urgency_score,
            ))
        return results

    # ── Metrics ───────────────────────────────────────────────────────────────

    def jains_fairness(self, allocations: List[float]) -> float:
        """
        Jain's Fairness Index: F = (Σxᵢ)² / (n · Σxᵢ²)

        Range: 1/n (worst) → 1.0 (perfectly fair).
        Returns 1.0 if allocations list is empty or all zeros.
        """
        if not allocations:
            return 1.0
        n      = len(allocations)
        sum_x  = sum(allocations)
        sum_x2 = sum(x * x for x in allocations)
        return round((sum_x * sum_x) / (n * sum_x2), 4) if sum_x2 > 0 else 1.0

    def get_round_summary(self) -> Dict[str, Any]:
        """Return the most recent round's summary dict for WebSocket broadcast."""
        if not self._round_history:
            return {}
        return self._round_history[-1]

    def get_history(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Return the last N round summaries."""
        return self._round_history[-last_n:]

    def get_fairness_trend(self, last_n: int = 10) -> List[float]:
        """Return fairness index values for the last N rounds."""
        return [r.get("fairness_index", 1.0) for r in self._round_history[-last_n:]]

    def reset(self) -> None:
        """Clear all history (e.g. when starting a new scenario)."""
        self._round_history.clear()
        self._allocation_log.clear()
        logger.info("Arbiter history reset")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_round_record(
        self,
        sorted_bids:  List[Bid],
        allocations:  Dict[str, float],
        total_supply: float,
    ) -> Dict[str, Any]:
        alloc_values     = list(allocations.values())
        total_demand     = sum(b.demand_mw for b in sorted_bids)
        total_allocated  = sum(alloc_values)

        return {
            "tick":             len(self._round_history) + 1,
            "timestamp":        time.time(),
            "total_supply_mw":  round(total_supply, 2),
            "total_demand_mw":  round(total_demand, 2),
            "total_allocated":  round(total_allocated, 2),
            "supply_deficit":   round(max(0.0, total_demand - total_supply), 2),
            "fairness_index":   self.jains_fairness(alloc_values),
            "allocations": [
                {
                    "agent_id":    b.agent_id,
                    "agent_type":  b.agent_type.value,
                    "urgency":     b.urgency_score,
                    "demand":      b.demand_mw,
                    "allocated":   allocations[b.agent_id],
                    "satisfaction": round(
                        allocations[b.agent_id] / b.demand_mw
                        if b.demand_mw > 0 else 1.0, 3
                    ),
                }
                for b in sorted_bids
            ],
        }
