"""
disasters.py — FastAPI Disaster Injection Router

Exposes HTTP endpoints to trigger disaster scenarios against the live
city_graph simulation. After injecting a disaster, the event is broadcast
via WebSocket to all connected frontend clients.

Routes:
    POST /api/disaster/{type}           — trigger a single disaster
    POST /api/disaster/scenario/{name}  — run a scripted scenario timeline
    GET  /api/disaster/status           — list available disaster types
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import random
import math

from app.simulation.disaster_generator import DisasterGenerator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Disasters"])


# ── Enums & Schemas ───────────────────────────────────────────────────────────

class DisasterType(str, Enum):
    earthquake   = "earthquake"
    cyber_attack = "cyber"
    flood        = "flood"
    aftershock   = "aftershock"


class EarthquakeParams(BaseModel):
    magnitude: float              = Field(default=7.0, ge=4.0, le=9.5,
                                          description="Richter scale magnitude")
    epicenter: Optional[List[float]] = Field(default=None,
                                             description="[lat, lon] of epicenter")
    rng_seed:  Optional[int]      = Field(default=None,
                                          description="Seed for reproducible simulations")


class CyberAttackParams(BaseModel):
    primary_target: str  = Field(default="POWER_GRID",
                                  description="Node type to target first")
    severity:       str  = Field(default="HIGH",
                                  description="LOW | MEDIUM | HIGH | CRITICAL",
                                  pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    rng_seed: Optional[int] = None


class FloodParams(BaseModel):
    water_level_m: float         = Field(default=1.5, ge=0.1,
                                          description="Flood water depth in metres")
    flood_zone: Optional[List[List[float]]] = Field(
        default=None,
        description="[[lat_min, lon_min], [lat_max, lon_max]] bounding box"
    )
    rng_seed: Optional[int] = None


class DisasterRequest(BaseModel):
    """Universal disaster request — only relevant fields used per type."""
    earthquake:   Optional[EarthquakeParams]  = None
    cyber_attack: Optional[CyberAttackParams] = None
    flood:        Optional[FloodParams]        = None


class LocationRequest(BaseModel):
    """User location for generating nearby agents."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class ApiControlRequest(BaseModel):
    """API call control request."""
    enabled: bool = Field(..., description="Whether to enable or disable API calls")


# ── Dependency: city_graph singleton ─────────────────────────────────────────

def get_city_graph() -> Dict[str, Any]:
    """
    FastAPI dependency that returns the live city_graph nodes dict.
    Imported lazily to avoid circular imports at module load time.
    """
    try:
        from app.simulation.city_graph import city_graph as _cg
        return _cg.nodes
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="City graph not initialised — start the simulation first.",
        )


def get_ws_manager():
    """Return the WebSocket connection manager (None-safe)."""
    try:
        from app.websocket.connection_manager import manager
        return manager
    except ImportError:
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/disaster/{dtype}",
    summary="Trigger a disaster event",
    response_description="The triggered disaster event details",
)
async def trigger_disaster(
    dtype:      DisasterType,
    body:       DisasterRequest   = DisasterRequest(),
    city_nodes: Dict[str, Any]   = Depends(get_city_graph),
    ws_manager                   = Depends(get_ws_manager),
) -> Dict[str, Any]:
    """
    Inject a disaster into the live simulation.

    - **earthquake** — radial damage from epicenter scaled by magnitude
    - **cyber**      — targeted attack on control systems
    - **flood**      — bounding-box zone flooding
    - **aftershock** — reduced-magnitude follow-up quake

    All parameters have sensible defaults so a bare POST with no body works.
    """
    event: Dict[str, Any]

    try:
        if dtype == DisasterType.earthquake or dtype == DisasterType.aftershock:
            params = body.earthquake or EarthquakeParams()
            epicenter: Optional[Tuple[float, float]] = (
                tuple(params.epicenter) if params.epicenter else None  # type: ignore[arg-type]
            )
            if dtype == DisasterType.aftershock:
                event = DisasterGenerator.inject_aftershock(
                    city_nodes,
                    original_magnitude=params.magnitude,
                    epicenter=epicenter or (40.7128, -74.0060),
                    rng_seed=params.rng_seed,
                )
            else:
                event = DisasterGenerator.inject_earthquake(
                    city_nodes,
                    magnitude=params.magnitude,
                    epicenter=epicenter or (40.7128, -74.0060),
                    rng_seed=params.rng_seed,
                )

        elif dtype == DisasterType.cyber_attack:
            params_c = body.cyber_attack or CyberAttackParams()
            event = DisasterGenerator.inject_cyber_attack(
                city_nodes,
                primary_target=params_c.primary_target,
                severity=params_c.severity,
                rng_seed=params_c.rng_seed,
            )

        elif dtype == DisasterType.flood:
            params_f = body.flood or FloodParams()
            flood_zone = None
            if params_f.flood_zone:
                flood_zone = (
                    tuple(params_f.flood_zone[0]),  # type: ignore[arg-type]
                    tuple(params_f.flood_zone[1]),  # type: ignore[arg-type]
                )
            event = DisasterGenerator.inject_flood(
                city_nodes,
                water_level_m=params_f.water_level_m,
                flood_zone=flood_zone or ((40.70, -74.02), (40.73, -73.98)),
                rng_seed=params_f.rng_seed,
            )

        else:
            # Enum validation makes this unreachable, but safety net
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown disaster type: {dtype}",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Disaster injection failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disaster injection error: {exc}",
        )

    # Broadcast to all WebSocket clients
    if ws_manager:
        try:
            await ws_manager.broadcast({
                "event_type": "disaster",
                "payload":    event,
            })
        except Exception as ws_exc:
            logger.warning("WebSocket broadcast failed: %s", ws_exc)

    logger.warning(
        "Disaster triggered via API: type=%s nodes_affected=%s",
        event.get("type"), event.get("affected_nodes", "?"),
    )

    return {
        "status":  "triggered",
        "event":   event,
    }


@router.post(
    "/disaster/scenario/{name}",
    summary="Load a scripted disaster scenario timeline",
)
async def load_scenario(name: str) -> Dict[str, Any]:
    """
    Return a scripted event timeline for a named disaster scenario.

    Available scenarios: ``earthquake``, ``cyber_attack``, ``flood``, ``compound``

    The SimulationEngine feeds these events into its loop based on ``delay_s``.
    """
    timeline = DisasterGenerator.get_scenario(name)
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown scenario '{name}'. "
                   f"Available: earthquake, cyber_attack, flood, compound",
        )
    return {
        "scenario": name,
        "steps":    len(timeline),
        "timeline": timeline,
    }


@router.get(
    "/disaster/status",
    summary="List available disaster types and scenarios",
)
async def disaster_status() -> Dict[str, Any]:
    """Returns all injectable disaster types and scripted scenario names."""
    return {
        "disaster_types": [d.value for d in DisasterType],
        "scenarios":      ["earthquake", "cyber_attack", "flood", "compound"],
        "parameters": {
            "earthquake":   EarthquakeParams.model_json_schema(),
            "cyber_attack": CyberAttackParams.model_json_schema(),
            "flood":        FloodParams.model_json_schema(),
        },
    }


@router.post("/set-api-calls")
async def set_api_calls(request: ApiControlRequest) -> Dict[str, Any]:
    """
    Enable or disable API calls to prevent hitting rate limits.
    When disabled, the system will use rule-based justifications instead of LLM calls.
    """
    try:
        from app.llm.router import llm_router
        
        # Store the API control state in the LLM router
        llm_router.set_api_calls_enabled(request.enabled)
        
        logger.info(f"API calls {'ENABLED' if request.enabled else 'DISABLED'} via frontend control")
        
        return {
            "status": "success",
            "api_calls_enabled": request.enabled,
            "message": f"API calls {'enabled' if request.enabled else 'disabled'} - {'using AI justifications' if request.enabled else 'using rule-based justifications'}"
        }
    except Exception as exc:
        logger.exception("Failed to set API calls: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set API calls: {exc}"
        )


@router.post("/set-location")
async def set_user_location(location: LocationRequest) -> Dict[str, Any]:
    """
    Receive user location and regenerate agents around that location.
    Generates random infrastructure nodes within 10km of user's position.
    """
    try:
        from app.simulation.city_graph import city_graph as _cg
        from app.main import agents, arbiter
        from app.agents.hospital_agent import HospitalAgent
        from app.agents.water_agent import WaterAgent
        from app.agents.fire_agent import FireStationAgent
        
        # Clear existing nodes and agents
        _cg.clear()
        agents.clear()
        
        # Generate power plant at user location (supply source)
        _cg.add_infrastructure_node("pp_main", "POWER_PLANT", (location.latitude, location.longitude), 100.0)
        
        # Generate random agents within ~10km radius
        num_agents = random.randint(5, 10)
        agent_types = ["HOSPITAL", "WATER_PLANT", "FIRE_STATION", "TELECOM"]
        
        for i in range(num_agents):
            # Random offset within ~0.1 degrees (~10km)
            lat_offset = random.uniform(-0.1, 0.1)
            lng_offset = random.uniform(-0.1, 0.1)
            agent_lat = location.latitude + lat_offset
            agent_lng = location.longitude + lng_offset
            
            agent_type = random.choice(agent_types)
            node_id = f"{agent_type.lower()}_{i}"
            capacity = random.uniform(5, 20)
            
            _cg.add_infrastructure_node(node_id, agent_type, (agent_lat, agent_lng), capacity)
            
            # Connect to power plant
            _cg.add_edge("pp_main", node_id, capacity=random.uniform(5, 15))
            
            # Create agent
            if agent_type == "HOSPITAL":
                agents.append(HospitalAgent(node_id, (agent_lat, agent_lng), icu_patients=random.randint(20, 100)))
            elif agent_type == "WATER_PLANT":
                agents.append(WaterAgent(node_id, (agent_lat, agent_lng)))
            elif agent_type == "FIRE_STATION":
                agents.append(FireStationAgent(node_id, (agent_lat, agent_lng)))
        
        logger.info(f"Regenerated {num_agents} agents around user location ({location.latitude}, {location.longitude})")
        
        return {
            "status": "success",
            "agents_generated": num_agents,
            "user_location": {"lat": location.latitude, "lng": location.longitude},
            "nodes": list(_cg.nodes.keys())
        }
    except Exception as exc:
        logger.exception("Failed to set location: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set location: {exc}"
        )
