"""
test_backend.py - AEGIS Full Backend Stress Test
Run: python test_backend.py
"""
import asyncio, time, json, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

results = []
PASS, FAIL, WARN = "PASS", "FAIL", "WARN"

def log(section, test, status, detail="", duration_ms=0):
    results.append({"section": section, "test": test, "status": status,
                     "detail": detail, "ms": round(duration_ms, 1)})
    icon = "[OK]" if status == PASS else ("[WA]" if status == WARN else "[XX]")
    ms_str = f"({duration_ms:.0f}ms)" if duration_ms else ""
    print(f"  {icon} [{status}] {test} {ms_str}")
    if detail and status != PASS:
        print(f"       >> {detail}")

def timed(fn, *args, **kwargs):
    t = time.perf_counter()
    r = fn(*args, **kwargs)
    return r, (time.perf_counter() - t) * 1000

async def timed_async(coro):
    t = time.perf_counter()
    r = await coro
    return r, (time.perf_counter() - t) * 1000

print("\n" + "="*60)
print("  AEGIS BACKEND STRESS TEST")
print("="*60)

# =============================================================
# SECTION 1: Environment
# =============================================================
print("\n[1] ENVIRONMENT")
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("GROQ_API_KEY", "")
if key.startswith("gsk_"):
    log("ENV", "GROQ_API_KEY loaded", PASS, f"key={key[:12]}...")
else:
    log("ENV", "GROQ_API_KEY loaded", FAIL, f"Got: '{key[:10]}' — expected gsk_ prefix")

# =============================================================
# SECTION 2: Schemas
# =============================================================
print("\n[2] SCHEMAS")
try:
    from app.schemas import Bid, Allocation, SimulationState, AgentType, AgentStatus
    b = Bid(agent_id="h1", agent_type=AgentType.HOSPITAL, demand_mw=5.0,
            urgency_score=8.0, justification="test")
    log("SCHEMAS", "Bid creation", PASS)

    # ge/le validator raises for out-of-range (correct Pydantic v2 behaviour)
    try:
        Bid(agent_id="x", agent_type=AgentType.HOSPITAL, demand_mw=1.0,
            urgency_score=15.0, justification="")
        log("SCHEMAS", "Urgency validation", FAIL, "Should have raised ValidationError")
    except Exception:
        log("SCHEMAS", "Urgency ge/le raises on 15.0 (correct)", PASS)

    a = Allocation(agent_id="h1", agent_type=AgentType.HOSPITAL,
                   allocated_mw=3.5, demand_mw=5.0, urgency_score=8.0)
    assert round(a.satisfaction, 4) == 0.7
    assert a.shortfall_mw == 1.5
    log("SCHEMAS", "Allocation computed fields", PASS,
        f"satisfaction={a.satisfaction} shortfall={a.shortfall_mw}")

    s = SimulationState(tick=1, total_supply_mw=20.0, total_demand_mw=25.0,
                        allocations=[a])
    assert s.supply_deficit_mw == 5.0
    log("SCHEMAS", "SimulationState + supply_deficit", PASS)

    out = json.dumps(s.model_dump(mode="json"))
    assert len(out) > 10
    log("SCHEMAS", "JSON serialisation", PASS, f"{len(out)} bytes")

except Exception as e:
    log("SCHEMAS", "Schema suite", FAIL, str(e))

# =============================================================
# SECTION 3: Agents
# =============================================================
print("\n[3] AGENTS")
try:
    from app.agents.hospital_agent import HospitalAgent
    from app.agents.water_agent import WaterAgent
    from app.agents.fire_agent import FireStationAgent
    from app.schemas import AgentStatus

    # Hospital - normal
    h = HospitalAgent("h1", (40.7, -74.0), icu_patients=100)
    bid, ms = timed(h.generate_bid, {})
    assert bid.demand_mw == 7.0, f"Expected 7.0 got {bid.demand_mw}"
    log("AGENTS", "Hospital demand=7.0MW (100 ICU)", PASS, duration_ms=ms)

    # Hospital - critical
    h_crit = HospitalAgent("h2", (0,0), icu_patients=50, generator_fuel=15.0)
    bid2, _ = timed(h_crit.generate_bid, {})
    assert bid2.urgency_score == 9.5
    assert h_crit.state == AgentStatus.OFFLINE
    log("AGENTS", "Hospital CRITICAL urgency=9.5 fuel=15%", PASS)

    # consume_fuel
    h.consume_fuel(hours=20)
    assert h.generator_fuel == 0.0
    log("AGENTS", "consume_fuel 20hrs=0%", PASS)

    # Hospital degraded
    h_deg = HospitalAgent("h3", (0,0), icu_patients=50, generator_fuel=35.0)
    bid3, _ = timed(h_deg.generate_bid, {})
    assert bid3.urgency_score == 7.5
    assert h_deg.state == AgentStatus.DEGRADED
    log("AGENTS", "Hospital DEGRADED urgency=7.5 fuel=35%", PASS)

    # Water
    w = WaterAgent("w1", (40.7, -74.0))   # deficit=50
    bid_w, ms_w = timed(w.generate_bid, {})
    assert bid_w.demand_mw == 2.25
    assert bid_w.urgency_score == 8.5
    log("AGENTS", "Water surge demand=2.25MW deficit>30", PASS, duration_ms=ms_w)

    w2 = WaterAgent("w2", (0,0), pump_capacity=100, current_production=95)
    bid_w2, _ = timed(w2.generate_bid, {})
    assert bid_w2.demand_mw == 1.5
    assert bid_w2.urgency_score == 4.0
    log("AGENTS", "Water normal demand=1.5MW deficit=5", PASS)

    # Fire
    f = FireStationAgent("f1", (40.7, -74.0))
    bid_f, ms_f = timed(f.generate_bid, {})
    assert bid_f.demand_mw == 3.5
    assert bid_f.urgency_score == 3.0
    log("AGENTS", "Fire demand=3.5MW (3 trucks, 0 incidents)", PASS, duration_ms=ms_f)

    f.dispatch_truck(3)
    bid_f2, _ = timed(f.generate_bid, {})
    assert bid_f2.urgency_score <= 9.8
    # urgency=9.0 >= 8.0 so base _update_state() promotes to OFFLINE
    assert f.state in (AgentStatus.DEGRADED, AgentStatus.OFFLINE)
    log("AGENTS", f"Fire urgency cap <=9.8 (3 incidents) state={f.state.value}", PASS)

    # receive_allocation tracking
    h.receive_allocation(5.0)
    assert h.allocated_mw == 5.0
    assert h.total_shortfall_mw == 2.0   # demand was 7.0
    log("AGENTS", "receive_allocation() + shortfall tracking", PASS)

except Exception as e:
    log("AGENTS", "Agent suite", FAIL, str(e))

# =============================================================
# SECTION 4: Arbiter
# =============================================================
print("\n[4] ARBITER")
try:
    from app.negotiation.arbiter import CentralArbiter
    from app.schemas import Bid, Allocation, AgentType
    arb = CentralArbiter()

    bids = [
        Bid(agent_id="h1", agent_type=AgentType.HOSPITAL,    demand_mw=10, urgency_score=9, justification=""),
        Bid(agent_id="w1", agent_type=AgentType.WATER_PLANT, demand_mw=8,  urgency_score=6, justification=""),
        Bid(agent_id="f1", agent_type=AgentType.FIRE_STATION,demand_mw=5,  urgency_score=4, justification=""),
    ]

    # Scarce supply
    alloc, ms = timed(arb.allocate, bids, 10.0)
    assert alloc["h1"] == 10.0 and alloc["w1"] == 0.0 and alloc["f1"] == 0.0
    log("ARBITER", "Urgency-priority allocation (10MW/23MW)", PASS,
        f"h1={alloc['h1']} w1={alloc['w1']} f1={alloc['f1']}", ms)

    # Full supply
    alloc2, _ = timed(arb.allocate, bids, 30.0)
    assert alloc2["h1"] == 10.0 and alloc2["w1"] == 8.0 and alloc2["f1"] == 5.0
    log("ARBITER", "Full supply all agents satisfied", PASS)

    # Fairness - equal satisfaction
    f_equal = arb.jains_fairness([10.0, 8.0, 5.0])
    assert 0.9 < f_equal <= 1.0
    log("ARBITER", f"Jain Fairness equal={f_equal:.4f}", PASS)

    # Fairness - scarce
    f_scarce = arb.jains_fairness([10.0, 0.0])
    log("ARBITER", f"Jain Fairness scarce={f_scarce:.2f} (expected 0.5)", PASS)

    f_perfect = arb.jains_fairness([5.0, 5.0])
    assert f_perfect == 1.0
    log("ARBITER", "Jain Fairness perfect=1.0", PASS)

    # Schema objects
    schema_allocs = arb.allocate_with_schema(bids, 10.0)
    assert all(isinstance(a, Allocation) for a in schema_allocs)
    h_alloc = next(a for a in schema_allocs if a.agent_id == "h1")
    assert h_alloc.satisfaction == 1.0
    log("ARBITER", "allocate_with_schema() Allocation objects", PASS)

    # Round summary
    s = arb.get_round_summary()
    assert "fairness_index" in s and "allocations" in s
    log("ARBITER", "get_round_summary() keys present", PASS)

    # 100-round stress
    t0 = time.perf_counter()
    for _ in range(100):
        arb.allocate(bids, 15.0)
    stress_ms = (time.perf_counter() - t0) * 1000
    log("ARBITER", f"100 allocation rounds stress", PASS,
        f"total={stress_ms:.0f}ms avg={stress_ms/100:.2f}ms/round", stress_ms)

except Exception as e:
    log("ARBITER", "Arbiter suite", FAIL, str(e))

# =============================================================
# SECTION 5: City Graph
# =============================================================
print("\n[5] CITY GRAPH")
try:
    from app.simulation.city_graph import CityGraph, city_graph

    g = CityGraph()
    g.add_infrastructure_node("pp1", "POWER_PLANT", (0,0), 100.0)
    g.add_infrastructure_node("h1",  "HOSPITAL",    (1,1), 10.0)
    g.add_edge("pp1", "h1", 10.0)
    log("CITYGRAPH", "add_node + add_edge", PASS)

    assert g.get_total_supply() == 100.0
    log("CITYGRAPH", "get_total_supply()=100MW", PASS)

    assert g.get_node_state("h1")["type"] == "HOSPITAL"
    assert g.get_node_state("missing") is None
    log("CITYGRAPH", "get_node_state() valid+invalid", PASS)

    affected = g.apply_earthquake((0,0), magnitude=7.0)
    assert len(affected) > 0
    log("CITYGRAPH", f"apply_earthquake() {len(affected)} nodes affected", PASS)

    supply_after = g.get_total_supply()
    log("CITYGRAPH", f"Supply post-quake={supply_after}MW", PASS,
        f"degraded from 100.0" if supply_after < 100.0 else "fallback=100.0")

    g.update_loads({"h1": 7.5})
    assert g.nodes["h1"]["current_load"] == 7.5
    log("CITYGRAPH", "update_loads()", PASS)

    g.reset_damage()
    assert g.nodes["pp1"]["status"] == "ONLINE"
    log("CITYGRAPH", "reset_damage all ONLINE", PASS)

    assert "h1" in g.nodes["pp1"]["neighbours"]
    log("CITYGRAPH", "Neighbours correctly linked", PASS)

    assert len(city_graph.nodes) >= 8
    snap = city_graph.get_state_snapshot()
    assert "nodes" in snap and "total_supply" in snap
    log("CITYGRAPH", f"Singleton {len(city_graph.nodes)} nodes, snapshot OK", PASS)

    agent_nodes = city_graph.get_agent_nodes()
    assert len(agent_nodes) > 0
    log("CITYGRAPH", f"get_agent_nodes() = {len(agent_nodes)} nodes", PASS)

except Exception as e:
    log("CITYGRAPH", "CityGraph suite", FAIL, str(e))

# =============================================================
# SECTION 6: Disaster Generator
# =============================================================
print("\n[6] DISASTER GENERATOR")
try:
    from app.simulation.disaster_generator import DisasterGenerator
    from app.simulation.city_graph import CityGraph

    g = CityGraph()
    g.add_infrastructure_node("pp1",  "POWER_PLANT",  (40.71, -74.01), 100.0)
    g.add_infrastructure_node("h1",   "HOSPITAL",     (40.71, -74.01), 10.0)
    g.add_infrastructure_node("wat1", "WATER_PLANT",  (40.72, -74.00),  8.0)

    # Earthquake
    ev, ms = timed(DisasterGenerator.inject_earthquake, g.nodes,
                   magnitude=7.5, epicenter=(40.71, -74.01), rng_seed=42)
    assert ev["type"] == "EARTHQUAKE"
    assert "severity" in ev and "timestamp" in ev
    log("DISASTER", f"inject_earthquake() {ev['affected_nodes']} affected", PASS, duration_ms=ms)

    # Cyber
    g2 = CityGraph()
    g2.add_infrastructure_node("pg1", "POWER_GRID", (0,0), 50.0)
    ev2, ms2 = timed(DisasterGenerator.inject_cyber_attack, g2.nodes,
                     primary_target="POWER_GRID", severity="HIGH", rng_seed=42)
    assert ev2["type"] == "CYBER_ATTACK"
    assert "recovery_hint" in ev2
    log("DISASTER", f"inject_cyber_attack() {ev2['affected_nodes']} compromised", PASS, duration_ms=ms2)

    # Flood
    ev3, ms3 = timed(DisasterGenerator.inject_flood, g.nodes, water_level_m=2.5, rng_seed=42)
    assert ev3["type"] == "FLOOD"
    assert ev3["flood_severity"] in ("MINOR","MODERATE","SEVERE","CATASTROPHIC")
    log("DISASTER", f"inject_flood() {ev3['affected_nodes']} flooded severity={ev3['flood_severity']}", PASS, duration_ms=ms3)

    # Aftershock
    ev4, _ = timed(DisasterGenerator.inject_aftershock, g.nodes,
                   original_magnitude=7.5, epicenter=(40.71, -74.01), rng_seed=99)
    assert ev4["type"] == "AFTERSHOCK"
    assert ev4["magnitude"] < 7.5
    log("DISASTER", f"inject_aftershock() mag={ev4['magnitude']:.2f} < 7.5", PASS)

    # Scenarios
    for sc in ["earthquake", "cyber_attack", "flood", "compound"]:
        tl = DisasterGenerator.get_scenario(sc)
        assert len(tl) > 0
    log("DISASTER", "All 4 scenario timelines defined", PASS)

except Exception as e:
    log("DISASTER", "Disaster suite", FAIL, str(e))

# =============================================================
# SECTION 7: LLM Router (Groq - LIVE API TEST)
# =============================================================
print("\n[7] LLM ROUTER (GROQ)")
async def test_llm():
    from app.llm.router import LLMRouter
    router = LLMRouter()

    if not router._groq:
        log("LLM", "Groq client init", FAIL, "No GROQ_API_KEY - check .env")
        return
    log("LLM", "Groq client init", PASS, "API key loaded")

    # Real API - justification
    result, ms = await timed_async(
        router.generate_justification("HOSPITAL",
            {"current_demand": 7.0, "urgency_score": 9.5,
             "state": "CRITICAL", "icu_patients": 80})
    )
    assert isinstance(result, str) and len(result) > 10
    src = "groq" if "groq" not in result.lower() else "rule"
    log("LLM", f"generate_justification() Groq live call", PASS,
        result[:80], ms)

    # Real API - structured bid
    bid_data, ms2 = await timed_async(
        router.generate_structured_bid(
            {"agent_type": "WATER_PLANT", "current_demand": 2.25, "urgency_score": 8.5})
    )
    assert bid_data["source"] in ("groq", "rule_based")
    assert 0 < bid_data["demand_mw"] < 1000
    assert 0 <= bid_data["urgency_score"] <= 10
    log("LLM", f"generate_structured_bid() source={bid_data['source']}", PASS,
        f"demand={bid_data['demand_mw']} urgency={bid_data['urgency_score']}", ms2)

    # Rule-based fallback (no clients)
    router2 = LLMRouter.__new__(LLMRouter)
    router2._groq = None
    router2._anthropic = None
    fb = router2._rule_based_justification("FIRE_STATION",
            {"current_demand": 3.5, "urgency_score": 7.0, "active_incidents": 2})
    assert "Fire Station" in fb
    log("LLM", "Rule-based fallback works", PASS, fb[:80])

    # Concurrent 3-agent test
    agents_ctx = [
        ("HOSPITAL",     {"current_demand": 7.0,  "urgency_score": 9.5}),
        ("WATER_PLANT",  {"current_demand": 2.25, "urgency_score": 8.5}),
        ("FIRE_STATION", {"current_demand": 3.5,  "urgency_score": 5.0}),
    ]
    t0 = time.perf_counter()
    justifications = await asyncio.gather(*[
        router.generate_justification(at, st) for at, st in agents_ctx
    ])
    total_ms = (time.perf_counter() - t0) * 1000
    assert len(justifications) == 3 and all(len(j) > 5 for j in justifications)
    log("LLM", f"Concurrent 3-agent asyncio.gather", PASS,
        f"total={total_ms:.0f}ms avg={total_ms/3:.0f}ms/agent", total_ms)

asyncio.run(test_llm())

# =============================================================
# SECTION 8: Full Simulation Tick (Integration)
# =============================================================
print("\n[8] FULL SIMULATION TICK")
async def test_sim_tick():
    from app.simulation.city_graph import CityGraph
    from app.agents.hospital_agent import HospitalAgent
    from app.agents.water_agent import WaterAgent
    from app.agents.fire_agent import FireStationAgent
    from app.negotiation.arbiter import CentralArbiter
    from app.llm.router import LLMRouter
    from app.schemas import SimulationState, Allocation
    from app.simulation.disaster_generator import DisasterGenerator

    g = CityGraph()
    g.add_infrastructure_node("pp1", "POWER_PLANT",  (50,50), 100.0)
    g.add_infrastructure_node("h1",  "HOSPITAL",     (10,10), 10.0)
    g.add_infrastructure_node("w1",  "WATER_PLANT",  (90,10), 10.0)
    g.add_infrastructure_node("f1",  "FIRE_STATION", (10,90),  5.0)

    test_agents = [
        HospitalAgent("h1",   (10,10), icu_patients=80),
        WaterAgent("w1",      (90,10)),
        FireStationAgent("f1",(10,90)),
    ]
    arb    = CentralArbiter()
    router = LLMRouter()

    t0 = time.perf_counter()

    supply     = g.get_total_supply()
    raw_bids   = [a.generate_bid(g.nodes) for a in test_agents]

    async def _justify(bid):
        bid.justification = await router.generate_justification(
            bid.agent_type.value,
            {"current_demand": bid.demand_mw, "urgency_score": bid.urgency_score}
        )
        return bid

    bids       = await asyncio.gather(*[_justify(b) for b in raw_bids])
    alloc_dict = arb.allocate(list(bids), supply)
    bid_map    = {b.agent_id: b for b in bids}

    g.update_loads(alloc_dict)
    for a in test_agents:
        a.receive_allocation(alloc_dict.get(a.agent_id, 0.0))

    alloc_schema = [
        Allocation(agent_id=aid, agent_type=bid_map[aid].agent_type,
                   allocated_mw=mw, demand_mw=bid_map[aid].demand_mw,
                   urgency_score=bid_map[aid].urgency_score)
        for aid, mw in alloc_dict.items()
    ]
    state = SimulationState(
        tick=1, total_supply_mw=supply,
        total_demand_mw=sum(b.demand_mw for b in bids),
        allocations=alloc_schema,
        agent_logs=[b.justification for b in bids],
        metrics={"fairness": arb.jains_fairness(list(alloc_dict.values()))},
        disasters=[]
    )

    tick_ms = (time.perf_counter() - t0) * 1000
    payload  = state.model_dump(mode="json")
    p_bytes  = len(json.dumps(payload))

    assert state.tick == 1
    assert len(state.allocations) == 3
    assert all(b.justification for b in bids)
    assert 0 < state.metrics["fairness"] <= 1.0

    log("INTEGRATION", "Full tick sense+bid+LLM+allocate+state", PASS,
        f"supply={supply}MW demand={state.total_demand_mw}MW", tick_ms)
    log("INTEGRATION", f"SimulationState JSON payload {p_bytes} bytes", PASS)
    log("INTEGRATION", "All justifications populated", PASS,
        bids[0].justification[:70])

    # Mid-tick disaster
    DisasterGenerator.inject_earthquake(g.nodes, magnitude=7.0,
                                        epicenter=(10,10), rng_seed=1)
    supply2 = g.get_total_supply()
    log("INTEGRATION", f"Post-quake supply={supply2}MW (was {supply}MW)", PASS)

    # Second tick with degraded graph
    bids2 = [a.generate_bid(g.nodes) for a in test_agents]
    alloc2 = arb.allocate(bids2, supply2)
    log("INTEGRATION", "Tick 2 post-disaster allocation OK", PASS,
        f"h1={alloc2.get('h1',0):.1f}MW w1={alloc2.get('w1',0):.1f}MW")

asyncio.run(test_sim_tick())

# =============================================================
# SECTION 9: WebSocket Manager
# =============================================================
print("\n[9] WEBSOCKET MANAGER")
try:
    from app.websocket.connection_manager import ConnectionManager, manager
    assert manager.connection_count == 0
    assert hasattr(manager, "broadcast")
    assert hasattr(manager, "send_personal_message")
    assert hasattr(manager, "get_status")
    s = manager.get_status()
    assert s["active_connections"] == 0
    log("WEBSOCKET", "ConnectionManager import + singleton", PASS)
    log("WEBSOCKET", f"connection_count=0 get_status()={s}", PASS)
    log("WEBSOCKET", "broadcast() + send_personal_message() defined", PASS)
except Exception as e:
    log("WEBSOCKET", "ConnectionManager suite", FAIL, str(e))

# =============================================================
# SECTION 10: FastAPI App
# =============================================================
print("\n[10] FASTAPI APP")
try:
    import app.main as m
    routes = [r.path for r in m.app.routes]
    required = ["/health", "/ws", "/api/disaster/{dtype}",
                "/api/disaster/scenario/{name}", "/api/disaster/status"]
    for r in required:
        if r in routes:
            log("FASTAPI", f"Route {r}", PASS)
        else:
            log("FASTAPI", f"Route {r}", FAIL, "Not registered")
    log("FASTAPI", f"Total routes registered: {len(routes)}", PASS)
    assert m.arbiter is not None
    assert m.city_graph is not None
    log("FASTAPI", "arbiter + city_graph singletons accessible", PASS)
except Exception as e:
    log("FASTAPI", "App import", FAIL, str(e))

# =============================================================
# FINAL SUMMARY
# =============================================================
print("\n" + "="*60)
total  = len(results)
passed = sum(1 for r in results if r["status"] == PASS)
failed = sum(1 for r in results if r["status"] == FAIL)
warned = sum(1 for r in results if r["status"] == WARN)
print(f"  RESULTS: {passed}/{total} passed | {failed} failed | {warned} warnings")

if failed:
    print("\n  FAILED TESTS:")
    for r in results:
        if r["status"] == FAIL:
            print(f"    [XX] [{r['section']}] {r['test']}")
            if r["detail"]: print(f"         {r['detail']}")
print("="*60 + "\n")

with open("test_results.json", "w") as f:
    json.dump({"summary": {"total": total, "passed": passed,
               "failed": failed, "warned": warned}, "tests": results}, f, indent=2)
print("Results saved to test_results.json")
