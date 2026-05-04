"""
router.py — LLM Router for AEGIS

Async LLM-powered bid justification and structured bid generation.

Priority chain:
    1. Groq (llama-3.1-8b-instant) — primary: FREE tier, ~10x faster than OpenAI
    2. Claude 3.5 Haiku (Anthropic) — secondary fallback
    3. Rule-based templates         — always works, no API key required

Get a free Groq API key at: https://console.groq.com

Singleton: ``from app.llm import llm_router``
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Groq models available (free tier) ────────────────────────────────────────
_GROQ_MODEL_FAST   = "llama-3.1-8b-instant"    # ~200ms, great for justifications
_GROQ_MODEL_SMART  = "llama-3.3-70b-versatile" # slower but smarter (structured bids)
_CLAUDE_MODEL      = "claude-3-5-haiku-20241022"

_SYSTEM_PROMPT = (
    "You are an autonomous AI agent managing critical city infrastructure during a disaster. "
    "Your role is to justify why your utility needs its requested power allocation. "
    "Be specific, urgent, and vary your reasoning based on the context. "
    "Mention specific equipment, patient counts, or operational details. "
    "Different scenarios require different justifications - be creative but realistic. "
    "One to two sentences maximum."
)

# ── Per-agent rule-based fallback templates ───────────────────────────────────
_FALLBACK_TEMPLATES: Dict[str, str] = {
    "HOSPITAL":     "{label} requires {demand:.1f} MW — {icu_patients} ICU patients depend on uninterrupted power (Urgency: {urgency:.1f}/10).",
    "POWER_GRID":   "{label} operating at {stability:.0f}% grid stability — load balancing critical to prevent cascade failure (Urgency: {urgency:.1f}/10).",
    "WATER_PLANT":  "{label} requires {demand:.1f} MW — pump deficit of {deficit:.0f} m³/h risks contamination (Urgency: {urgency:.1f}/10).",
    "FIRE_STATION": "{label} requires {demand:.1f} MW — {active_incidents} active incidents require full operational capacity (Urgency: {urgency:.1f}/10).",
    "TELECOM":      "{label} requires {demand:.1f} MW — {towers_online} comm towers must stay online for emergency coordination (Urgency: {urgency:.1f}/10).",
    "DEFAULT":      "{label} requires {demand:.1f} MW for critical operations (Urgency: {urgency:.1f}/10).",
}

# ── Optional SDK imports (won't crash if packages aren't installed) ───────────
try:
    from groq import AsyncGroq
    _GROQ_AVAILABLE = True
except ImportError:
    AsyncGroq = None            # type: ignore[assignment,misc]
    _GROQ_AVAILABLE = False
    logger.warning("groq package not installed — install with: pip install groq")

try:
    from anthropic import AsyncAnthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    AsyncAnthropic = None       # type: ignore[assignment,misc]
    _ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed — Claude fallback disabled")


class LLMRouter:
    """
    Async LLM router for AEGIS.

    Usage::

        justification = await llm_router.generate_justification("HOSPITAL", agent.get_status())
        bid_data      = await llm_router.generate_structured_bid(agent.get_status())

    Set GROQ_API_KEY in your .env file (free at https://console.groq.com).
    """

    def __init__(self) -> None:
        groq_key      = os.getenv("GROQ_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        self._groq: Optional[Any] = (
            AsyncGroq(api_key=groq_key)
            if _GROQ_AVAILABLE and groq_key
            else None
        )
        self._anthropic: Optional[Any] = (
            AsyncAnthropic(api_key=anthropic_key)
            if _ANTHROPIC_AVAILABLE and anthropic_key
            else None
        )

        # Startup log
        backends = []
        if self._groq:      backends.append(f"Groq ({_GROQ_MODEL_FAST})")
        if self._anthropic: backends.append(f"Anthropic ({_CLAUDE_MODEL})")
        if backends:
            logger.info("LLMRouter ready — backends: %s", ", ".join(backends))
        else:
            logger.warning(
                "LLMRouter: no API keys found — rule-based fallbacks only. "
                "Get a free Groq key at https://console.groq.com"
            )

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate_justification(
        self,
        agent_type: str,
        state:      Dict[str, Any],
        timeout:    float = 1.5,
    ) -> str:
        """
        Generate a 1-sentence justification for a power bid.

        Args:
            agent_type: e.g. ``"HOSPITAL"``, ``"WATER_PLANT"``
            state:      agent state dict (demand_mw, urgency_score, …)
            timeout:    max seconds to wait per LLM call

        Returns:
            Single justification sentence — Groq, Claude, or rule-based fallback.
        """
        prompt = self._build_prompt(agent_type, state)

        # 1 — Groq llama-3.1-8b-instant (primary, ~200ms)
        if self._groq:
            result = await self._groq_justification(prompt, timeout)
            if result:
                return result

        # 2 — Claude 3.5 Haiku (fallback)
        if self._anthropic:
            result = await self._anthropic_justification(prompt, timeout)
            if result:
                return result

        # 3 — Rule-based (always succeeds)
        return self._rule_based_justification(agent_type, state)

    async def generate_structured_bid(
        self,
        agent_state: Dict[str, Any],
        timeout:     float = 1.0,
    ) -> Dict[str, Any]:
        """
        Ask Groq to propose demand_mw and urgency_score from agent state.
        Falls back to rule-based values on timeout / parse error.

        Returns dict: demand_mw, urgency_score, justification, source.
        """
        if not self._groq:
            return self._rule_based_bid(agent_state)

        prompt = (
            f"You are {agent_state.get('agent_type', 'a utility')} AI. "
            f"State: {agent_state}. "
            "Output ONLY valid JSON: "
            '{"demand_mw": <float>, "urgency_score": <0-10 float>, "justification": "<1 urgent sentence>"}'
        )

        try:
            response = await asyncio.wait_for(
                self._groq.chat.completions.create(
                    model=_GROQ_MODEL_FAST,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=120,
                    temperature=0.1,
                ),
                timeout=timeout,
            )
            data = json.loads(response.choices[0].message.content)
            return {
                "demand_mw":     float(data.get("demand_mw", agent_state.get("current_demand", 1.0))),
                "urgency_score": max(0.0, min(10.0, float(data.get("urgency_score", 5.0)))),
                "justification": str(data.get("justification", "")).strip(),
                "source":        "groq",
            }
        except asyncio.TimeoutError:
            logger.warning("generate_structured_bid: Groq timeout — rule-based fallback")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("generate_structured_bid: parse error — %s", exc)
        except Exception as exc:
            logger.warning("generate_structured_bid: error — %s", exc)

        return self._rule_based_bid(agent_state)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_prompt(self, agent_type: str, state: Dict[str, Any]) -> str:
        demand  = state.get("current_demand", state.get("demand_mw", 0.0))
        urgency = state.get("urgency_score", 5.0)
        status  = state.get("state", "NORMAL")
        return (
            f"You are {agent_type} AI. "
            f"State: {status}. "
            f"Demand: {demand:.1f} MW. "
            f"Urgency: {urgency:.1f}/10. "
            f"Context: {state}. "
            "Write exactly 1 urgent sentence justifying this power allocation."
        )

    async def _groq_justification(self, prompt: str, timeout: float) -> Optional[str]:
        try:
            resp = await asyncio.wait_for(
                self._groq.chat.completions.create(
                    model=_GROQ_MODEL_FAST,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    max_tokens=80,
                    temperature=0.3,
                ),
                timeout=timeout,
            )
            return self._clean_sentence(resp.choices[0].message.content)
        except asyncio.TimeoutError:
            logger.debug("Groq justification timeout (%.1fs)", timeout)
        except Exception as exc:
            logger.debug("Groq justification error: %s", exc)
        return None

    async def _anthropic_justification(self, prompt: str, timeout: float) -> Optional[str]:
        try:
            resp = await asyncio.wait_for(
                self._anthropic.messages.create(
                    model=_CLAUDE_MODEL,
                    max_tokens=80,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                ),
                timeout=timeout,
            )
            return self._clean_sentence(resp.content[0].text)
        except asyncio.TimeoutError:
            logger.debug("Anthropic justification timeout (%.1fs)", timeout)
        except Exception as exc:
            logger.debug("Anthropic justification error: %s", exc)
        return None

    def _rule_based_justification(self, agent_type: str, state: Dict[str, Any]) -> str:
        template = _FALLBACK_TEMPLATES.get(agent_type, _FALLBACK_TEMPLATES["DEFAULT"])
        ctx = {
            "label":            agent_type.replace("_", " ").title(),
            "demand":           state.get("current_demand", state.get("demand_mw", 1.0)),
            "urgency":          state.get("urgency_score", 5.0),
            "icu_patients":     state.get("icu_patients", 50),
            "stability":        state.get("stability_pct", 100.0),
            "deficit":          state.get("pump_deficit_m3h", 0.0),
            "active_incidents": state.get("active_incidents", 0),
            "towers_online":    state.get("towers_online", 0),
        }
        try:
            return template.format(**ctx)
        except KeyError:
            return _FALLBACK_TEMPLATES["DEFAULT"].format(**ctx)

    def _rule_based_bid(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "demand_mw":     state.get("current_demand", 1.0),
            "urgency_score": state.get("urgency_score", 5.0),
            "justification": self._rule_based_justification(
                state.get("agent_type", "DEFAULT"), state
            ),
            "source": "rule_based",
        }

    @staticmethod
    def _clean_sentence(text: str) -> str:
        """Trim to a single complete sentence."""
        text  = text.strip()
        first = text.split(".")[0].strip()
        return first + "." if first else text


# ── Singleton export ──────────────────────────────────────────────────────────
llm_router = LLMRouter()
