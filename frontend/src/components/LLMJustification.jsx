// frontend/src/components/LLMJustification.jsx
import { clsx } from 'clsx';
import { Brain, MessageSquare, Clock, Zap, AlertTriangle, Activity, ChevronDown } from 'lucide-react';
import { useState } from 'react';

// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_ITEMS = 5; // Reduced from 20 to 5 for compact display

// ─── Agent type icons and colors ────────────────────────────────────────────────
const AGENT_INFO = {
  HOSPITAL: {
    icon: AlertTriangle,
    color: 'text-red-400',
    bg: 'bg-red-900/20',
    border: 'border-red-500/30',
    name: 'Hospital'
  },
  WATER_PLANT: {
    icon: Zap,
    color: 'text-cyan-400',
    bg: 'bg-cyan-900/20',
    border: 'border-cyan-500/30',
    name: 'Water Plant'
  },
  FIRE_STATION: {
    icon: Activity,
    color: 'text-orange-400',
    bg: 'bg-orange-900/20',
    border: 'border-orange-500/30',
    name: 'Fire Station'
  },
  POWER_PLANT: {
    icon: Zap,
    color: 'text-blue-400',
    bg: 'bg-blue-900/20',
    border: 'border-blue-500/30',
    name: 'Power Plant'
  },
};

// ─── Urgency level helpers ─────────────────────────────────────────────────────
function getUrgencyLevel(urgency) {
  if (urgency >= 8) return { level: 'CRITICAL', color: 'text-red-400', bg: 'bg-red-900/30' };
  if (urgency >= 6) return { level: 'HIGH', color: 'text-yellow-400', bg: 'bg-yellow-900/30' };
  if (urgency >= 4) return { level: 'MEDIUM', color: 'text-blue-400', bg: 'bg-blue-900/30' };
  return { level: 'LOW', color: 'text-green-400', bg: 'bg-green-900/30' };
}

// ─── Format timestamp ───────────────────────────────────────────────────────────
function formatTimestamp(timestamp) {
  try {
    const d = new Date(timestamp * 1000);
    return isNaN(d.getTime()) ? 'Unknown' : d.toLocaleTimeString();
  } catch {
    return 'Unknown';
  }
}

// ─── Single justification card ───────────────────────────────────────────────────
function JustificationCard({ log, index }) {
  const agentInfo = AGENT_INFO[log.agent_type] || AGENT_INFO.POWER_PLANT;
  const AgentIcon = agentInfo.icon;
  const urgencyInfo = getUrgencyLevel(log.urgency_score);
  const hasJustification = log.justification && log.justification.length > 10;
  const isNewest = index === 0;

  return (
    <div className={clsx(
      'relative bg-gray-800/50 rounded-lg border border-gray-700 p-4 transition-all duration-300',
      agentInfo.border,
      agentInfo.bg,
      isNewest && 'ring-2 ring-purple-500/30 shadow-lg shadow-purple-500/10',
      'hover:border-gray-600 hover:shadow-md'
    )}>
      {/* Live indicator for newest entry */}
      {isNewest && (
        <div className="absolute -top-2 -right-2">
          <div className="flex items-center gap-1 bg-purple-600 text-white text-xs px-2 py-1 rounded-full animate-pulse">
            <div className="w-1.5 h-1.5 bg-white rounded-full animate-ping" />
            LIVE
          </div>
        </div>
      )}

      {/* Header with agent info */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={clsx('p-2 rounded-lg bg-gray-900', agentInfo.color)}>
            <AgentIcon className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-white">{log.agent_id}</span>
              <span className={clsx('text-xs px-2 py-1 rounded bg-gray-900', agentInfo.color)}>
                {agentInfo.name}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Clock className="w-3 h-3 text-gray-500" />
              <span className="text-xs text-gray-400 font-mono">
                {formatTimestamp(log.timestamp)}
              </span>
              {log.tick && (
                <span className="text-xs text-gray-500 font-mono">
                  • Tick {log.tick}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Urgency badge */}
        <div className={clsx('px-3 py-1 rounded-full text-xs font-semibold', urgencyInfo.bg, urgencyInfo.color)}>
          {urgencyInfo.level} PRIORITY
        </div>
      </div>

      {/* Demand metrics */}
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div className="bg-gray-900/50 rounded p-2">
          <div className="text-xs text-gray-400 mb-1">Power Demand</div>
          <div className="text-lg font-bold text-white">
            {(log.demand_mw || 0).toFixed(1)} MW
          </div>
        </div>
        <div className="bg-gray-900/50 rounded p-2">
          <div className="text-xs text-gray-400 mb-1">Urgency Score</div>
          <div className="text-lg font-bold text-white">
            {(log.urgency_score || 0).toFixed(1)}/10
          </div>
        </div>
      </div>

      {/* Allocation result */}
      {log.allocated_mw !== undefined && (
        <div className="bg-gray-900/50 rounded p-2 mb-3">
          <div className="text-xs text-gray-400 mb-1">Power Allocated</div>
          <div className="flex items-center gap-2">
            <div className="text-lg font-bold text-green-400">
              {(log.allocated_mw || 0).toFixed(1)} MW
            </div>
            <div className="text-xs text-gray-400">
              ({((log.allocated_mw || 0) / (log.demand_mw || 1) * 100).toFixed(1)}% of demand)
            </div>
          </div>
        </div>
      )}

      {/* LLM Justification */}
      <div className="relative">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-semibold text-purple-400">AI Justification</span>
        </div>
        
        {hasJustification ? (
          <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-3">
            <p className="text-sm text-gray-200 leading-relaxed italic">
              "{log.justification}"
            </p>
          </div>
        ) : (
          <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3">
            <div className="flex items-center gap-2 text-gray-500">
              <MessageSquare className="w-4 h-4" />
              <span className="text-sm">Waiting for AI justification...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Compact Justification Row ─────────────────────────────────────────────────
function CompactJustificationRow({ log, index }) {
  const agentInfo = AGENT_INFO[log.agent_type] || AGENT_INFO.POWER_PLANT;
  const AgentIcon = agentInfo.icon;
  const isNewest = index === 0;

  return (
    <div className={clsx(
      'flex items-start gap-2 py-2 px-2 rounded-lg border transition-all duration-200',
      isNewest ? 'bg-purple-900/10 border-purple-500/30' : 'bg-gray-900/30 border-gray-700',
      'hover:bg-gray-800/50'
    )}>
      {/* Agent icon */}
      <div className={clsx('p-1.5 rounded', agentInfo.bg)}>
        <AgentIcon className={clsx('w-3 h-3', agentInfo.color)} />
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-white truncate">{log.agent_id}</span>
          <span className={clsx('text-xs px-1.5 py-0.5 rounded', agentInfo.bg, agentInfo.color)}>
            {agentInfo.name}
          </span>
          {isNewest && (
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          )}
        </div>
        
        {/* Justification text */}
        <p className="text-xs text-gray-300 leading-relaxed line-clamp-2">
          {log.justification || 'Waiting for AI justification...'}
        </p>
        
        {/* Metrics */}
        <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-500">
          <span>{(log.allocated_mw || 0).toFixed(1)}MW / {(log.demand_mw || 0).toFixed(1)}MW</span>
          <span>Urgency: {(log.urgency_score || 0).toFixed(1)}/10</span>
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────────
export default function LLMJustification({ logs = [] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Filter logs that have justification data
  const justificationLogs = logs.filter(log => 
    log && 
    typeof log === 'object' && 
    log.agent_id && 
    log.justification
  );

  const hasLogs = justificationLogs.length > 0;
  const visibleLogs = isExpanded 
    ? justificationLogs.slice(0, MAX_ITEMS) 
    : justificationLogs.slice(0, 3);
  const hasMore = justificationLogs.length > 3;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
      {/* Compact Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <h3 className="text-sm font-semibold text-white">AI Justifications</h3>
          {hasLogs && (
            <span className="text-xs text-gray-400">({justificationLogs.length})</span>
          )}
        </div>
        
        {hasLogs && (
          <div className="flex items-center gap-1 text-[10px] text-gray-500">
            <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
            Live
          </div>
        )}
      </div>

      {/* Content */}
      {!hasLogs ? (
        <div className="flex flex-col items-center justify-center py-6 text-gray-600">
          <Brain className="w-8 h-8 mb-2 opacity-50" />
          <p className="text-xs text-center">Waiting for AI justifications...</p>
        </div>
      ) : (
        <>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {visibleLogs.map((log, index) => (
              <CompactJustificationRow
                key={`${log.agent_id}-${log.tick}-${index}`}
                log={log}
                index={index}
              />
            ))}
          </div>
          
          {/* View More Button */}
          {hasMore && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full mt-2 flex items-center justify-center gap-1 py-1.5 px-2 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300 transition-colors"
            >
              <ChevronDown className={clsx('w-3 h-3 transition-transform', isExpanded && 'rotate-180')} />
              {isExpanded ? 'Show Less' : `View ${Math.min(justificationLogs.length - 3, MAX_ITEMS - 3)} More`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
