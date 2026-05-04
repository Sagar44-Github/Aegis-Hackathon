"""
calculator.py — AEGIS Metrics Calculator

Static methods for computing all key performance indicators defined in the
AEGIS technical specification:

    - Lives Saved            (hospital allocation satisfaction)
    - Economic Loss          (downtime cost in USD)
    - Cascading Failures     (graph-based failure propagation)
    - Jain's Fairness Index  (allocation equity across agents)
    - Service Continuity     (% essential services online)
    - System Health          (grid stability + continuity composite)
    - Negotiation Latency    (bid-to-allocation time tracking)

All methods are pure / side-effect-free and return typed dicts.
"""

from __future__ import annotations

import logging
import time
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Domain constants ──────────────────────────────────────────────────────────
# Calibrated against emergency management literature (hypothetical for hackathon)
LIVES_PER_MW_HOUR_FULL        = 0.10   # lives saved per MW·h when hospital fully satisfied
LIVES_PER_MW_HOUR_PARTIAL     = 0.02   # lives saved per MW·h when 50–80 % satisfied
ECONOMIC_LOSS_PER_MW_HOUR     = 5_000  # USD per MW·h of unmet demand
CASCADING_FAILURE_THRESHOLD   = 0.40   # node considered failed if load_ratio < 40 %

# Agent types considered "essential" for service continuity calculation
ESSENTIAL_AGENT_TYPES = {"HOSPITAL", "WATER_PLANT", "FIRE_STATION", "TELECOM"}


class MetricsCalculator:
    """
    Pure-static metrics engine for AEGIS simulation evaluation.

    All methods accept plain Python dicts / lists so they are decoupled
    from ORM or agent class hierarchies — easy to test and serialise.
    """

    # ── Lives Saved ───────────────────────────────────────────────────────────

    @staticmethod
    def calculate_lives_saved(
        hospital_allocation_history: List[float],
        hospital_demand_history: List[float],
        icu_patients: int = 50,
    ) -> Dict[str, Any]:
        """
        Estimate lives saved based on hospital power satisfaction over time.

        Satisfaction tiers (per tick):
            ≥ 0.8  → full care possible      → +0.10 lives / MW·h
            ≥ 0.5  → degraded care           → +0.02 lives / MW·h
            < 0.5  → critical failure        →  0    lives saved (mortality spike)

        Args:
            hospital_allocation_history: MW allocated to hospital each tick.
            hospital_demand_history:     MW demanded by hospital each tick.
            icu_patients:                Number of ICU patients (scales impact).

        Returns:
            Dict with lives_saved, critical_ticks, avg_satisfaction, detail.
        """
        if not hospital_allocation_history or not hospital_demand_history:
            return {
                "lives_saved": 0.0,
                "critical_ticks": 0,
                "avg_satisfaction": 0.0,
                "detail": "No history available",
            }

        lives_saved   = 0.0
        critical_ticks = 0
        satisfactions  = []

        for alloc, demand in zip(hospital_allocation_history, hospital_demand_history):
            if demand <= 0:
                satisfactions.append(1.0)
                continue

            sat = min(1.0, alloc / demand)
            satisfactions.append(sat)

            if sat >= 0.8:
                # Full care — lives saved proportional to allocation & patients
                lives_saved += LIVES_PER_MW_HOUR_FULL * alloc * (icu_patients / 50)
            elif sat >= 0.5:
                # Degraded care — partial contribution
                lives_saved += LIVES_PER_MW_HOUR_PARTIAL * alloc * (icu_patients / 50)
            else:
                critical_ticks += 1  # Mortality spike — no credit

        avg_sat = mean(satisfactions) if satisfactions else 0.0

        return {
            "lives_saved":     round(lives_saved, 2),
            "critical_ticks":  critical_ticks,
            "avg_satisfaction": round(avg_sat, 3),
            "total_ticks":     len(satisfactions),
            "detail": (
                f"Hospital averaged {avg_sat:.0%} power satisfaction over "
                f"{len(satisfactions)} ticks — {critical_ticks} critical failure ticks."
            ),
        }

    # ── Economic Loss ─────────────────────────────────────────────────────────

    @staticmethod
    def calculate_economic_loss(
        downtime_mw_hours: float,
        agent_type: str = "DEFAULT",
        sector_multipliers: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Estimate economic loss from unmet power demand.

        Args:
            downtime_mw_hours:   Total MW·h of unserved energy.
            agent_type:          Used to apply sector-specific cost multipliers.
            sector_multipliers:  Override default per-sector multipliers.

        Returns:
            Dict with total_loss_usd, loss_per_mwh, agent_type, severity.
        """
        _default_multipliers: Dict[str, float] = {
            "HOSPITAL":     3.0,   # Life-critical → highest cost
            "WATER_PLANT":  2.5,   # Public health risk
            "FIRE_STATION": 2.0,   # Emergency response degradation
            "TELECOM":      1.8,   # Communication disruption
            "POWER_GRID":   1.5,   # Systemic impact
            "DEFAULT":      1.0,
        }
        multipliers = sector_multipliers or _default_multipliers
        multiplier  = multipliers.get(agent_type, multipliers["DEFAULT"])

        loss_usd = downtime_mw_hours * ECONOMIC_LOSS_PER_MW_HOUR * multiplier

        if loss_usd < 100_000:
            severity = "LOW"
        elif loss_usd < 1_000_000:
            severity = "MODERATE"
        elif loss_usd < 10_000_000:
            severity = "HIGH"
        else:
            severity = "CATASTROPHIC"

        return {
            "total_loss_usd":   round(loss_usd, 2),
            "loss_per_mwh":     round(ECONOMIC_LOSS_PER_MW_HOUR * multiplier, 2),
            "downtime_mw_hours": round(downtime_mw_hours, 3),
            "agent_type":       agent_type,
            "sector_multiplier": multiplier,
            "severity":         severity,
        }

    # ── Cascading Failures ────────────────────────────────────────────────────

    @staticmethod
    def calculate_cascading_failures(
        graph_state: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Detect and quantify cascading failure propagation in the city graph.

        A node is "failed" when its load_ratio (allocated / capacity) drops
        below CASCADING_FAILURE_THRESHOLD.  Cascading is detected when a
        failed node's neighbours also show degraded status.

        Args:
            graph_state: Dict of node_id → node_properties.
                         Expected keys per node:
                             capacity (float), current_load (float),
                             status (str), type (str),
                             neighbours (List[str])  ← optional

        Returns:
            Dict with failure_count, cascading_pairs, affected_types,
            cascade_risk_score, detail.
        """
        if not graph_state:
            return {
                "failure_count":     0,
                "cascading_pairs":   0,
                "affected_types":    [],
                "cascade_risk_score": 0.0,
                "detail":            "Empty graph state",
            }

        failed_nodes:    List[str]          = []
        degraded_nodes:  List[str]          = []
        cascading_pairs: List[Tuple[str, str]] = []
        affected_types:  List[str]          = []

        for node_id, props in graph_state.items():
            capacity = props.get("capacity", 1.0)
            load     = props.get("current_load", 0.0)
            status   = props.get("status", "ONLINE")

            load_ratio = load / capacity if capacity > 0 else 0.0

            if status == "OFFLINE" or load_ratio < CASCADING_FAILURE_THRESHOLD:
                failed_nodes.append(node_id)
                node_type = props.get("type", "UNKNOWN")
                if node_type not in affected_types:
                    affected_types.append(node_type)
            elif load_ratio < 0.7:
                degraded_nodes.append(node_id)

        # Detect cascading: failed node whose neighbour is also failed/degraded
        for node_id in failed_nodes:
            props     = graph_state[node_id]
            neighbours = props.get("neighbours", [])
            for nb_id in neighbours:
                if nb_id in failed_nodes or nb_id in degraded_nodes:
                    pair = tuple(sorted([node_id, nb_id]))
                    if pair not in cascading_pairs:   # type: ignore[operator]
                        cascading_pairs.append(pair)  # type: ignore[arg-type]

        total_nodes        = len(graph_state)
        failure_rate       = len(failed_nodes) / total_nodes if total_nodes else 0.0
        cascade_risk_score = min(1.0, failure_rate * 1.5 + len(cascading_pairs) * 0.1)

        return {
            "failure_count":      len(failed_nodes),
            "degraded_count":     len(degraded_nodes),
            "cascading_pairs":    len(cascading_pairs),
            "affected_types":     affected_types,
            "cascade_risk_score": round(cascade_risk_score, 3),
            "failure_rate":       round(failure_rate, 3),
            "failed_nodes":       failed_nodes,
            "detail": (
                f"{len(failed_nodes)} nodes failed, {len(degraded_nodes)} degraded, "
                f"{len(cascading_pairs)} cascading pair(s) detected."
            ),
        }

    # ── Jain's Fairness Index ─────────────────────────────────────────────────

    @staticmethod
    def calculate_fairness_index(allocations: List[float]) -> Dict[str, Any]:
        """
        Compute Jain's Fairness Index: F = (Σxᵢ)² / (n · Σxᵢ²)

        1.0 = perfectly fair, 1/n = maximally unfair.

        Args:
            allocations: List of MW allocated to each agent this round.

        Returns:
            Dict with fairness_index, interpretation, n_agents.
        """
        n = len(allocations)
        if n == 0:
            return {"fairness_index": 1.0, "interpretation": "N/A — no agents", "n_agents": 0}

        sum_x  = sum(allocations)
        sum_x2 = sum(x ** 2 for x in allocations)

        index = (sum_x ** 2) / (n * sum_x2) if sum_x2 > 0 else 1.0
        index = round(min(1.0, index), 4)

        if index >= 0.9:
            interpretation = "Excellent — highly equitable distribution"
        elif index >= 0.75:
            interpretation = "Good — acceptable fairness"
        elif index >= 0.5:
            interpretation = "Fair — some agents underserved"
        else:
            interpretation = "Poor — significant allocation inequality"

        return {
            "fairness_index":  index,
            "interpretation":  interpretation,
            "n_agents":        n,
            "total_allocated": round(sum_x, 2),
        }

    # ── Service Continuity ────────────────────────────────────────────────────

    @staticmethod
    def calculate_service_continuity(
        agent_statuses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Compute Service Continuity Index = online essential services / total essential services.

        Args:
            agent_statuses: List of dicts with keys ``agent_type`` and ``state``.
                            state ∈ {NORMAL, DEGRADED, CRITICAL, OFFLINE}.

        Returns:
            Dict with service_continuity, essential_online, essential_total, breakdown.
        """
        essential = [a for a in agent_statuses if a.get("agent_type") in ESSENTIAL_AGENT_TYPES]
        total     = len(essential)

        if total == 0:
            return {
                "service_continuity": 1.0,
                "essential_online":   0,
                "essential_total":    0,
                "breakdown":          {},
            }

        online    = sum(1 for a in essential if a.get("state") in ("NORMAL", "DEGRADED"))
        continuity = round(online / total, 3)

        breakdown = {}
        for a in essential:
            t = a.get("agent_type", "UNKNOWN")
            breakdown[t] = a.get("state", "UNKNOWN")

        return {
            "service_continuity": continuity,
            "essential_online":   online,
            "essential_total":    total,
            "breakdown":          breakdown,
        }

    # ── System Health (composite) ─────────────────────────────────────────────

    @staticmethod
    def calculate_system_health(
        agent_statuses: List[Dict[str, Any]],
        supply_history: List[float],
        allocation_history: List[float],
        demand_history: List[float],
    ) -> Dict[str, Any]:
        """
        Composite system health snapshot combining grid stability and service continuity.

        Args:
            agent_statuses:     Latest agent state dicts.
            supply_history:     Available MW supply per tick.
            allocation_history: Total MW allocated per tick.
            demand_history:     Total MW demanded per tick.

        Returns:
            Dict with grid_stability, service_continuity, demand_satisfaction,
            supply_margin, overall_health_score.
        """
        # Grid stability — current supply vs recent peak demand
        grid_stability = 1.0
        if supply_history and demand_history:
            current_supply = supply_history[-1]
            peak_demand    = max(demand_history[-10:]) if demand_history else 1.0
            grid_stability = round(min(1.0, current_supply / max(peak_demand, 1.0)), 3)

        # Service continuity from essential agents
        continuity_result = MetricsCalculator.calculate_service_continuity(agent_statuses)
        service_cont      = continuity_result["service_continuity"]

        # Demand satisfaction — how much of total demand was met
        demand_satisfaction = 1.0
        if allocation_history and demand_history:
            recent_alloc  = allocation_history[-1] if allocation_history else 0
            recent_demand = demand_history[-1]      if demand_history     else 1
            demand_satisfaction = round(
                min(1.0, recent_alloc / max(recent_demand, 1.0)), 3
            )

        # Supply margin — buffer above current demand
        supply_margin = 0.0
        if supply_history and demand_history:
            supply_margin = round(
                max(0.0, supply_history[-1] - demand_history[-1]), 2
            )

        # Composite overall health (weighted)
        overall = round(
            0.4 * grid_stability +
            0.35 * service_cont  +
            0.25 * demand_satisfaction,
            3
        )

        return {
            "grid_stability":       grid_stability,
            "service_continuity":   service_cont,
            "demand_satisfaction":  demand_satisfaction,
            "supply_margin_mw":     supply_margin,
            "overall_health_score": overall,
            "status": (
                "STABLE"   if overall >= 0.8 else
                "DEGRADED" if overall >= 0.5 else
                "CRITICAL"
            ),
        }

    # ── Negotiation Latency ───────────────────────────────────────────────────

    @staticmethod
    def calculate_negotiation_latency(
        latency_samples_ms: List[float],
    ) -> Dict[str, Any]:
        """
        Summarise bid-to-allocation negotiation latency statistics.

        Args:
            latency_samples_ms: List of cycle latencies in milliseconds.

        Returns:
            Dict with avg_ms, p95_ms, max_ms, min_ms, meets_sla.
        """
        if not latency_samples_ms:
            return {
                "avg_ms": 0.0, "p95_ms": 0.0,
                "max_ms": 0.0, "min_ms": 0.0,
                "meets_sla": True, "samples": 0,
            }

        sorted_samples = sorted(latency_samples_ms)
        n              = len(sorted_samples)
        p95_idx        = max(0, int(n * 0.95) - 1)

        avg_ms = round(mean(sorted_samples), 2)
        p95_ms = round(sorted_samples[p95_idx], 2)
        max_ms = round(sorted_samples[-1], 2)
        min_ms = round(sorted_samples[0], 2)

        # SLA: p95 < 2000 ms (as per AEGIS spec)
        meets_sla = p95_ms < 2_000.0

        return {
            "avg_ms":    avg_ms,
            "p95_ms":    p95_ms,
            "max_ms":    max_ms,
            "min_ms":    min_ms,
            "meets_sla": meets_sla,
            "samples":   n,
        }
