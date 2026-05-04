// frontend/src/components/AgentLog.jsx
import { clsx } from 'clsx';
import { Terminal, Brain, Zap, AlertTriangle, Activity, Cloud } from 'lucide-react';

// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_ITEMS = 200; // Increased to show more history

// ─── Urgency color coding ─────────────────────────────────────────────────────
function getUrgencyColor(urgency) {
  if (urgency >= 8) return { color: 'text-red-400', bg: 'bg-red-900/20', border: 'border-red-500' };
  if (urgency >= 5) return { color: 'text-yellow-400', bg: 'bg-yellow-900/20', border: 'border-yellow-500' };
  return { color: 'text-green-400', bg: 'bg-green-900/20', border: 'border-green-500' };
}

// ─── Agent type icons ─────────────────────────────────────────────────────────
const AGENT_ICONS = {
  HOSPITAL: { icon: Activity, color: 'text-pink-400' },
  WATER_PLANT: { icon: Cloud, color: 'text-blue-400' },
  FIRE_STATION: { icon: AlertTriangle, color: 'text-orange-400' },
  POWER_PLANT: { icon: Zap, color: 'text-yellow-400' },
  DEFAULT: { icon: Brain, color: 'text-purple-400' },
};

// ─── Timestamp helper ─────────────────────────────────────────────────────────
function formatTs(timestamp) {
  try {
    const d = timestamp != null ? new Date(timestamp) : new Date();
    return isNaN(d.getTime()) ? new Date().toLocaleTimeString() : d.toLocaleTimeString();
  } catch {
    return new Date().toLocaleTimeString();
  }
}

// ─── Single log row ───────────────────────────────────────────────────────────
function LogRow({ entry, index }) {
  const isNewest = index === 0;
  
  // Handle both old string format and new object format
  const agentId = entry.agent_id ?? 'Unknown';
  const agentType = entry.agent_type ?? 'DEFAULT';
  const demand = entry.demand_mw ?? 0;
  const urgency = entry.urgency_score ?? 0;
  const justification = entry.justification ?? (typeof entry === 'string' ? entry : '');
  const timestamp = entry.timestamp ?? null;
  
  const urgencyStyle = getUrgencyColor(urgency);
  const agentIcon = AGENT_ICONS[agentType] || AGENT_ICONS.DEFAULT;
  const AgentIcon = agentIcon.icon;

  return (
    <div
      className={clsx(
        'px-3 py-3 rounded-lg border-l-4 text-gray-300',
        'flex flex-col gap-2',
        urgencyStyle.bg,
        urgencyStyle.border,
        isNewest && 'ring-1 ring-white/10'
      )}
    >
      {/* Header row with agent info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Agent icon */}
          <AgentIcon className={clsx('w-4 h-4', agentIcon.color)} />
          
          {/* Agent ID */}
          <span className="font-semibold text-sm text-white">
            {agentId}
          </span>
          
          {/* Agent type badge */}
          <span className="text-xs text-gray-500 capitalize bg-gray-900/50 px-2 py-0.5 rounded">
            {agentType.replace('_', ' ')}
          </span>
        </div>
        
        {/* Timestamp */}
        <span className="font-mono text-xs text-gray-500">
          {formatTs(timestamp)}
        </span>
      </div>

      {/* Metrics row */}
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Demand:</span>
          <span className="font-mono text-white font-semibold">
            {demand.toFixed(1)} MW
          </span>
        </div>
        
        <div className="flex items-center gap-1">
          <span className="text-gray-500">Urgency:</span>
          <span className={clsx('font-mono font-bold', urgencyStyle.color)}>
            {urgency.toFixed(1)}/10
          </span>
        </div>
        
        {/* API call badge */}
        <span className="flex items-center gap-1 text-xs text-purple-400 bg-purple-900/30 px-2 py-0.5 rounded ml-auto">
          <Brain className="w-3 h-3" />
          LLM API
        </span>
      </div>

      {/* Justification message */}
      <div className="text-sm leading-relaxed text-gray-300 pl-1 border-l-2 border-gray-700">
        "{justification}"
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function AgentLog({ logs = [] }) {
  const visible = [...logs].reverse().slice(0, MAX_ITEMS);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 flex flex-col h-[500px]">

      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-gray-400">
          <Terminal className="w-4 h-4" />
          <span className="font-mono text-sm tracking-wide font-semibold">AGENT NEGOTIATION LOG</span>
        </div>
        {logs.length > 0 && (
          <span className="font-mono text-xs text-gray-500 tabular-nums">
            Showing {visible.length} of {logs.length} logs
          </span>
        )}
      </div>

      {/* Scrollable log list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {visible.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-500">
            <Brain className="w-10 h-10 mb-3 opacity-50" />
            <p className="font-mono text-sm">Waiting for agent bids with LLM reasoning…</p>
          </div>
        ) : (
          visible.map((entry, i) => (
            <LogRow
              key={entry.agent_id ? `${entry.agent_id}-${entry.timestamp}` : i}
              entry={entry}
              index={i}
            />
          ))
        )}
      </div>

    </div>
  );
}
