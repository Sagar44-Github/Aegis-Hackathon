"""
main.py — AEGIS FastAPI Application Entry Point

Wires together:
    - City graph + agent setup (lifespan)
    - Simulation loop (async background task, 2s tick)
    - WebSocket endpoint /ws  (real-time state broadcast)
    - Disaster injection router /api/disaster/...
    - Health endpoint /health

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── Schemas ───────────────────────────────────────────────────────────────────
from app.schemas import Allocation, AgentType, SimulationState

# ── Singletons (import — do NOT re-instantiate) ───────────────────────────────
from app.simulation.city_graph import city_graph          # pre-built default city
from app.websocket.connection_manager import manager      # ws connection manager
from app.llm.router import llm_router                     # LLM justification router

# ── Negotiation ───────────────────────────────────────────────────────────────
from app.negotiation.arbiter import CentralArbiter

# ── Agents ───────────────────────────────────────────────────────────────────
from app.agents.hospital_agent import HospitalAgent
from app.agents.water_agent import WaterAgent
from app.agents.fire_agent import FireStationAgent

# ── API Routers ───────────────────────────────────────────────────────────────
from app.api.disasters import router as disasters_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Simulation globals ────────────────────────────────────────────────────────
arbiter:      CentralArbiter = CentralArbiter()
agents:       List[Any]      = []
tick_counter: int            = 0


# ── City + Agent Setup ────────────────────────────────────────────────────────

def setup_city() -> None:
    """
    Extend the default city_graph singleton with simulation-specific nodes
    and instantiate one agent per consumer node.

    Adds:
        pp_main    — 80 MW power plant (supply source) - REDUCED to create scarcity
        hosp_main  — Hospital (80 ICU patients)
        water_main — Water treatment plant
        fire_main  — Fire station (3 trucks, 0 incidents)
    """
    import random
    
    # Supply source - REDUCED from 100 to 80 MW to create scarcity
    supply_capacity = 80.0 + random.uniform(-10, 5)  # Variable supply 70-85 MW
    # Using realistic San Francisco Bay Area coordinates
    city_graph.add_infrastructure_node("pp_main",    "POWER_PLANT",  (37.78, -122.42), supply_capacity)
    
    # Consumer nodes - all within San Francisco area
    city_graph.add_infrastructure_node("hosp_main",  "HOSPITAL",     (37.77, -122.41), 10.0)
    city_graph.add_infrastructure_node("water_main", "WATER_PLANT",  (37.76, -122.43), 10.0)
    city_graph.add_infrastructure_node("fire_main",  "FIRE_STATION", (37.79, -122.40),  5.0)

    # Power line connections
    city_graph.add_edge("pp_main", "hosp_main",  capacity=10.0)
    city_graph.add_edge("pp_main", "water_main", capacity=10.0)
    city_graph.add_edge("pp_main", "fire_main",  capacity=5.0)

    # Agents (one per consumer node, IDs match node IDs)
    # Initialize with varied states for dynamic behavior
    # Agent coordinates must match node coordinates
    agents.append(HospitalAgent("hosp_main",  (37.77, -122.41), icu_patients=random.randint(60, 120), generator_fuel=random.uniform(30, 100)))
    agents.append(WaterAgent(   "water_main", (37.76, -122.43), pump_capacity=100.0, current_production=random.uniform(40, 90)))
    agents.append(FireStationAgent("fire_main", (37.79, -122.40), active_trucks=random.randint(2, 5), active_incidents=random.randint(0, 2)))

    logger.info(
        "City setup complete — supply: %.0f MW | agents: %d",
        city_graph.get_total_supply(), len(agents),
    )


# ── Simulation Loop ───────────────────────────────────────────────────────────

# Global accumulator for agent logs across ticks
_accumulated_agent_logs: List[Dict[str, Any]] = []

async def simulation_loop() -> None:
    """
    Core async background loop — runs every 2 seconds.

    Each tick:
        1. Sense   — read supply + node states from city_graph
        2. Dynamic Events — randomly change agent states to create variety
        3. Bid     — each agent generates a raw bid
        4. Justify — LLM justifications fetched concurrently (asyncio.gather)
        5. Allocate— arbiter distributes supply by urgency
        6. Update  — city_graph loads updated
        7. Metrics — fairness index + utilisation calculated
        8. Broadcast— SimulationState pushed to all WebSocket clients
    """
    global tick_counter, _accumulated_agent_logs
    import random

    while True:
        await asyncio.sleep(2.0)
        tick_counter += 1

        try:
            # 1 — Sense
            total_supply = city_graph.get_total_supply()
            graph_state  = city_graph.nodes
            
            # 2 — Dynamic Events: randomly change agent states every 5 ticks
            if tick_counter % 5 == 0:
                for agent in agents:
                    if hasattr(agent, 'icu_patients'):  # Hospital
                        # Randomly change patient count
                        if random.random() > 0.7:
                            change = random.randint(-10, 15)
                            agent.icu_patients = max(20, min(150, agent.icu_patients + change))
                        # Randomly consume fuel
                        agent.consume_fuel(hours=0.5)
                        # Randomly refuel if low
                        if agent.generator_fuel < 30 and random.random() > 0.5:
                            agent.refuel(random.uniform(20, 40))
                    elif hasattr(agent, 'current_production'):  # Water
                        # Randomly change production
                        if random.random() > 0.6:
                            change = random.uniform(-15, 10)
                            agent.current_production = max(20, min(100, agent.current_production + change))
                    elif hasattr(agent, 'active_incidents'):  # Fire
                        # Randomly add/resolve incidents
                        if random.random() > 0.7:
                            if random.random() > 0.5:
                                agent.dispatch_truck(random.randint(1, 2))
                            else:
                                agent.resolve_incident(random.randint(1, 2))
                
                # Randomly vary supply slightly
                if random.random() > 0.8:
                    supply_change = random.uniform(-5, 3)
                    current_supply = city_graph.nodes.get("pp_main", {}).get("capacity", 80)
                    new_supply = max(50, min(100, current_supply + supply_change))
                    city_graph.nodes["pp_main"]["capacity"] = new_supply
                    city_graph.nodes["pp_main"]["max_output"] = new_supply

            # 2 — Raw bids (synchronous, fast)
            raw_bids = [agent.generate_bid(graph_state) for agent in agents]

            # 3 — LLM justifications (concurrent, 1.5s timeout each, fallback safe)
            async def _justify(bid):
                bid.justification = await llm_router.generate_justification(
                    agent_type=bid.agent_type.value,
                    state={"demand_mw": bid.demand_mw,
                           "urgency_score": bid.urgency_score},
                )
                return bid

            bids = await asyncio.gather(*[_justify(b) for b in raw_bids])

            # 4 — Allocate
            allocations_dict = arbiter.allocate(list(bids), total_supply)

            # Notify each agent of its allocation
            bid_map = {b.agent_id: b for b in bids}
            for agent in agents:
                agent.receive_allocation(
                    allocations_dict.get(agent.agent_id, 0.0)
                )

            # 5 — Update graph loads
            city_graph.update_loads(allocations_dict)

            # 6 — Metrics
            alloc_values  = list(allocations_dict.values())
            total_demand  = sum(b.demand_mw for b in bids)
            fairness      = arbiter.jains_fairness(alloc_values)
            # Utilization: fraction (0-1) of supply that is actually allocated
            utilisation   = (sum(alloc_values) / total_supply) if total_supply > 0 else 0.0

            # 7 — Build SimulationState schema
            allocations_schema = [
                Allocation(
                    agent_id=agent_id,
                    agent_type=bid_map[agent_id].agent_type,
                    allocated_mw=alloc_mw,
                    demand_mw=bid_map[agent_id].demand_mw,
                    urgency_score=bid_map[agent_id].urgency_score,
                )
                for agent_id, alloc_mw in allocations_dict.items()
            ]

            # Build current tick's agent logs
            current_tick_logs = [
                {
                    "agent_id": b.agent_id,
                    "agent_type": b.agent_type.value,
                    "demand_mw": b.demand_mw,
                    "urgency_score": b.urgency_score,
                    "justification": b.justification,
                    "timestamp": time.time(),
                    "tick": tick_counter,
                }
                for b in bids
            ]
            
            # Accumulate logs (keep last 500)
            _accumulated_agent_logs.extend(current_tick_logs)
            if len(_accumulated_agent_logs) > 500:
                _accumulated_agent_logs = _accumulated_agent_logs[-500:]

            state = SimulationState(
                tick=tick_counter,
                timestamp=time.time(),
                total_supply_mw=total_supply,
                total_demand_mw=total_demand,
                allocations=allocations_schema,
                agent_logs=_accumulated_agent_logs,  # Send accumulated history
                metrics={
                    "fairness_index": fairness,
                    "utilization":    round(utilisation, 3),
                    "total_supply_mw": total_supply,
                    "total_demand_mw": round(total_demand, 2),
                    "active_agents":  len(agents),
                },
                disasters=[],
            )
            
            # Add nodes data to state for frontend
            state_dict = state.model_dump(mode="json")
            state_dict["nodes"] = city_graph.nodes
            
            # Add allocation decisions with reasons
            state_dict["allocation_decisions"] = arbiter._allocation_log[-len(agents):] if len(arbiter._allocation_log) >= len(agents) else arbiter._allocation_log

            # Broadcast to all WebSocket clients
            await manager.broadcast(state_dict)

            logger.debug(
                "Tick %d | supply=%.0f MW | demand=%.1f MW | fairness=%.2f | clients=%d",
                tick_counter, total_supply, total_demand,
                fairness, manager.connection_count,
            )

        except Exception as exc:
            logger.exception("simulation_loop error at tick %d: %s", tick_counter, exc)


# ── App Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: build city, launch simulation loop. Shutdown: log."""
    setup_city()
    task = asyncio.create_task(simulation_loop())
    backend = "Groq" if llm_router._groq else ("Anthropic" if llm_router._anthropic else "rule-based fallback")
    logger.info(
        "AEGIS simulation started — LLM backend: %s",
        backend,
    )
    yield
    task.cancel()
    logger.info("AEGIS simulation stopped")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AEGIS — Autonomous Emergency Grid Intelligence System",
    description=(
        "Real-time multi-agent negotiation for crisis resource allocation. "
        "Agents representing city utilities bid for power during disaster scenarios."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(disasters_router)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health() -> Dict[str, Any]:
    return {
        "status":      "AEGIS ONLINE",
        "tick":        tick_counter,
        "agents":      len(agents),
        "supply_mw":   city_graph.get_total_supply(),
        "ws_clients":  manager.connection_count,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Real-time WebSocket endpoint.
    Clients receive SimulationState JSON every 2 seconds automatically.
    Keep-alive: any message from the client is accepted and ignored.
    """
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()   # keep-alive / ignore client messages
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
        manager.disconnect(websocket)


# ── Dev runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
