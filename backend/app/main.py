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
        pp_main    — 100 MW power plant (supply source)
        hosp_main  — Hospital (80 ICU patients)
        water_main — Water treatment plant
        fire_main  — Fire station (3 trucks, 0 incidents)
    """
    # Supply source
    city_graph.add_infrastructure_node("pp_main",    "POWER_PLANT",  (50, 50), 100.0)
    # Consumer nodes
    city_graph.add_infrastructure_node("hosp_main",  "HOSPITAL",     (10, 10), 10.0)
    city_graph.add_infrastructure_node("water_main", "WATER_PLANT",  (90, 10), 10.0)
    city_graph.add_infrastructure_node("fire_main",  "FIRE_STATION", (10, 90),  5.0)

    # Power line connections
    city_graph.add_edge("pp_main", "hosp_main",  capacity=10.0)
    city_graph.add_edge("pp_main", "water_main", capacity=10.0)
    city_graph.add_edge("pp_main", "fire_main",  capacity=5.0)

    # Agents (one per consumer node, IDs match node IDs)
    agents.append(HospitalAgent("hosp_main",  (10, 10), icu_patients=80))
    agents.append(WaterAgent(   "water_main", (90, 10)))
    agents.append(FireStationAgent("fire_main", (10, 90)))

    logger.info(
        "City setup complete — supply: %.0f MW | agents: %d",
        city_graph.get_total_supply(), len(agents),
    )


# ── Simulation Loop ───────────────────────────────────────────────────────────

async def simulation_loop() -> None:
    """
    Core async background loop — runs every 2 seconds.

    Each tick:
        1. Sense   — read supply + node states from city_graph
        2. Bid     — each agent generates a raw bid
        3. Justify — LLM justifications fetched concurrently (asyncio.gather)
        4. Allocate— arbiter distributes supply by urgency
        5. Update  — city_graph loads updated
        6. Metrics — fairness index + utilisation calculated
        7. Broadcast— SimulationState pushed to all WebSocket clients
    """
    global tick_counter

    while True:
        await asyncio.sleep(2.0)
        tick_counter += 1

        try:
            # 1 — Sense
            total_supply = city_graph.get_total_supply()
            graph_state  = city_graph.nodes

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
            utilisation   = sum(alloc_values) / total_supply if total_supply > 0 else 0.0

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
                if agent_id in bid_map
            ]

            state = SimulationState(
                tick=tick_counter,
                timestamp=time.time(),
                total_supply_mw=total_supply,
                total_demand_mw=total_demand,
                allocations=allocations_schema,
                agent_logs=[b.justification for b in bids],
                metrics={
                    "fairness_index": fairness,
                    "utilisation":    round(utilisation, 3),
                    "supply_mw":      total_supply,
                    "demand_mw":      round(total_demand, 2),
                },
                disasters=[],
            )

            # Broadcast to all WebSocket clients
            await manager.broadcast(state.model_dump(mode="json"))

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
    logger.info(
        "AEGIS simulation started — LLM backend: %s",
        "OpenAI" if llm_router._openai else "rule-based fallback",
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
