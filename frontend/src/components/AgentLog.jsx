// frontend/src/components/AgentLog.jsx
import { clsx } from 'clsx';
import { Terminal, Brain, AlertCircle, Zap } from 'lucide-react';

// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_ITEMS = 50;

// ─── Severity detection based on urgency score ────────────────────────────────
function getSeverity(entry) {
  if (typeof entry === 'string') {
    if (/critical|imminent|failure/i.test(entry)) return 'critical';
    if (/high|urgent|generator/i.test(entry))     return 'high';
    return 'normal';
  }
  const urgency = entry.urgency_score ?? 5;
  if (urgency >= 8) return 'critical';
  if (urgency >= 6) return 'high';
  return 'normal';
}

const SEVERITY = {
  critical: {
    row:   'border-l-2 border-red-500 bg-red-900/20',
    badge: 'text-red-400',
    dot:   'bg-red-500',
  },
  high: {
    row:   'border-l-2 border-yellow-500 bg-yellow-900/20',
    badge: 'text-yellow-400',
    dot:   'bg-yellow-400',
  },
  normal: {
    row:   'border-l-2 border-green-500 bg-green-900/10',
    badge: 'text-green-400',
    dot:   'bg-green-400',
  },
};

// ─── Agent type colors ────────────────────────────────────────────────────────
const AGENT_COLORS = {
  HOSPITAL:     'text-red-400',
  WATER_PLANT:  'text-cyan-400',
  FIRE_STATION: 'text-orange-400',
  POWER_PLANT:  'text-blue-400',
  POWER_GRID:   'text-purple-400',
};

// ─── Timestamp helper ─────────────────────────────────────────────────────────
function formatTs(entry) {
  const raw = typeof entry === 'object' ? (entry.timestamp ?? entry.ts ?? null) : null;
  try {
    const d = raw != null ? new Date(raw * 1000) : new Date();
    return isNaN(d.getTime()) ? new Date().toLocaleTimeString() : d.toLocaleTimeString();
  } catch {
    return new Date().toLocaleTimeString();
  }
}

// ─── Build display message from structured entry ──────────────────────────────
function buildMessage(entry) {
  if (typeof entry === 'string') return entry;
  if (entry.message) return entry.message;

  const agentId   = entry.agent_id   ?? 'Unknown';
  const agentType = entry.agent_type ?? 'UNKNOWN';
  const demand    = entry.demand_mw  ?? 0;
  const urgency   = entry.urgency_score ?? 0;

  return `${agentId} (${agentType.replace('_', ' ')}) — Demand: ${demand.toFixed(1)} MW | Urgency: ${urgency.toFixed(1)}/10`;
}

// ─── Single log row ───────────────────────────────────────────────────────────
function LogRow({ entry, index }) {
  const message  = buildMessage(entry);
  const severity = getSeverity(entry);
  const s        = SEVERITY[severity];
  const isNewest = index === 0;

  const agentType    = typeof entry === 'object' ? entry.agent_type : null;
  const justification = typeof entry === 'object' ? entry.justification : null;
  const hasLLM       = justification && justification.length > 10;
  const tick         = typeof entry === 'object' ? entry.tick : null;

  return (
    <div
      className={clsx(
        'px-3 py-2 rounded-r text-gray-300',
        'flex flex-col gap-1',
        s.row,
      )}
    >
      {/* Header row with timestamp and type indicator */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Live pulse dot (only newest) */}
        <span className="shrink-0">
          <span
            className={clsx('block w-1.5 h-1.5 rounded-full', s.dot, isNewest && 'animate-pulse')}
          />
        </span>
        
        {/* Timestamp */}
        <span className="font-mono text-xs text-gray-500 select-none">
          [{formatTs(entry)}]
        </span>

        {/* Tick badge */}
        {tick != null && (
          <span className="text-[10px] text-gray-600 font-mono">
            T{tick}
          </span>
        )}

        {/* Agent type badge */}
        {agentType && (
          <span className={clsx(
            'text-[10px] font-semibold px-1.5 py-0.5 rounded bg-gray-800',
            AGENT_COLORS[agentType] ?? 'text-gray-400'
          )}>
            {agentType.replace('_', ' ')}
          </span>
        )}
        
        {/* LLM indicator */}
        {hasLLM && (
          <span className="flex items-center gap-1 text-xs text-purple-400 bg-purple-900/30 px-1.5 py-0.5 rounded">
            <Brain className="w-3 h-3" />
            LLM
          </span>
        )}
        
        {/* Severity badge */}
        {severity !== 'normal' && (
          <span className={clsx('text-xs font-medium', s.badge, 'capitalize')}>
            {severity}
          </span>
        )}
      </div>

      {/* Agent bid summary */}
      <div className={clsx(
        'text-sm leading-relaxed pl-4 font-medium',
        severity !== 'normal' ? s.badge : 'text-gray-200'
      )}>
        {typeof entry === 'object' ? (entry.agent_id ?? 'Unknown Agent') : message}
        {typeof entry === 'object' && (
          <span className="ml-2 text-xs text-gray-400 font-normal">
            — {(entry.demand_mw ?? 0).toFixed(1)} MW demand, urgency {(entry.urgency_score ?? 0).toFixed(1)}/10
          </span>
        )}
      </div>

      {/* LLM Justification (the actual reasoning) */}
      {hasLLM && (
        <div className="pl-4 mt-1 text-xs text-gray-400 leading-relaxed bg-gray-900/40 rounded p-2 border-l-2 border-purple-500/30 italic">
          "{justification}"
        </div>
      )}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
/**
 * AgentLog
 * @param {{ logs: Array<string | { agent_id: string, agent_type: string, demand_mw: number, urgency_score: number, justification: string, timestamp: number, tick: number }> }} props
 */
export default function AgentLog({ logs = [] }) {
  const visible = [...logs].reverse().slice(0, MAX_ITEMS);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 flex flex-col h-96">

      {/* Header — terminal aesthetic */}
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-gray-400">
          <Terminal className="w-4 h-4" />
          <span className="font-mono text-sm tracking-wide font-semibold">AGENT NEGOTIATION LOG</span>
        </div>
        {logs.length > 0 && (
          <span className="font-mono text-[10px] text-gray-600 tabular-nums">
            {Math.min(logs.length, MAX_ITEMS)}/{logs.length}
          </span>
        )}
      </div>

      {/* Scrollable log list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {visible.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <Brain className="w-8 h-8 mb-2 opacity-50" />
            <p className="font-mono text-xs">Waiting for agent bids with LLM reasoning…</p>
          </div>
        ) : (
          visible.map((entry, i) => (
            <LogRow
              key={typeof entry === 'object' ? (entry.id ?? `${entry.agent_id}-${entry.tick}-${i}`) : i}
              entry={entry}
              index={i}
            />
          ))
        )}
      </div>

    </div>
  );
}
