// frontend/src/components/AllocationDecisions.jsx
import { CheckCircle, XCircle, AlertCircle, Clock, Activity, Cloud, Zap, AlertTriangle as FireIcon, TrendingUp, TrendingDown } from 'lucide-react';
import { clsx } from 'clsx';

// ─── Agent type icons matching other components ─────────────────────────────
const AGENT_ICONS = {
  HOSPITAL: { icon: Activity, color: 'text-pink-400' },
  WATER_PLANT: { icon: Cloud, color: 'text-blue-400' },
  FIRE_STATION: { icon: FireIcon, color: 'text-orange-400' },
  POWER_PLANT: { icon: Zap, color: 'text-yellow-400' },
  DEFAULT: { icon: AlertCircle, color: 'text-purple-400' },
};

export default function AllocationDecisions({ decisions = [] }) {
  if (!decisions || decisions.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4" />
          Allocation Decisions
        </h3>
        <p className="text-xs text-gray-500 text-center py-4">No decisions available yet</p>
      </div>
    );
  }

  // Get the most recent decisions (last N entries)
  const recentDecisions = decisions.slice(-15).reverse();

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
        <Clock className="w-4 h-4" />
        Allocation Decisions
      </h3>
      
      <div className="space-y-3">
        {recentDecisions.map((decision, idx) => {
          const decisionType = decision.decision || 'UNKNOWN';
          
          const statusConfig = {
            ACCEPTED: {
              icon: CheckCircle,
              color: 'text-emerald-400',
              bg: 'bg-emerald-900/20',
              border: 'border-emerald-500',
              label: 'ACCEPTED',
            },
            PARTIALLY_ACCEPTED: {
              icon: AlertCircle,
              color: 'text-yellow-400',
              bg: 'bg-yellow-900/20',
              border: 'border-yellow-500',
              label: 'PARTIAL',
            },
            DENIED: {
              icon: XCircle,
              color: 'text-red-400',
              bg: 'bg-red-900/20',
              border: 'border-red-500',
              label: 'DENIED',
            },
            UNKNOWN: {
              icon: AlertCircle,
              color: 'text-gray-400',
              bg: 'bg-gray-900/20',
              border: 'border-gray-500',
              label: 'UNKNOWN',
            },
          };
          
          const config = statusConfig[decisionType] || statusConfig.UNKNOWN;
          const StatusIcon = config.icon;
          
          const demand = decision.demand ?? 0;
          const allocated = decision.allocated ?? 0;
          const urgency = decision.urgency ?? 0;
          const satisfaction = demand > 0 ? (allocated / demand) * 100 : 0;
          const shortfall = Math.max(0, demand - allocated);
          
          const agentIcon = AGENT_ICONS[decision.agent_type] || AGENT_ICONS.DEFAULT;
          const AgentIcon = agentIcon.icon;

          return (
            <div 
              key={decision.agent_id ? `${decision.agent_id}-${decision.tick}` : idx}
              className={clsx(
                'rounded-lg p-4 border-l-4',
                config.bg,
                config.border
              )}
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AgentIcon className={clsx('w-5 h-5', agentIcon.color)} />
                  <div>
                    <span className="font-bold text-white text-base">
                      {decision.agent_id || `Agent ${idx + 1}`}
                    </span>
                    <span className="ml-2 text-xs text-gray-500 capitalize bg-gray-800 px-2 py-0.5 rounded">
                      {decision.agent_type?.replace('_', ' ') || 'Unknown'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 font-mono">
                    Tick #{decision.tick || '?'}
                  </span>
                  <span className={clsx('text-sm font-bold px-3 py-1 rounded', config.color, config.bg)}>
                    {config.label}
                  </span>
                </div>
              </div>

              {/* Metrics grid */}
              <div className="grid grid-cols-4 gap-3 mb-3">
                <div className="bg-gray-900/50 rounded p-2">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Demand</p>
                  <p className="text-sm font-mono font-bold text-white">{demand.toFixed(1)} MW</p>
                </div>
                <div className="bg-gray-900/50 rounded p-2">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Allocated</p>
                  <p className={clsx('text-sm font-mono font-bold', config.color)}>{allocated.toFixed(1)} MW</p>
                </div>
                <div className="bg-gray-900/50 rounded p-2">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Urgency</p>
                  <p className={clsx('text-sm font-mono font-bold', urgency >= 8 ? 'text-red-400' : urgency >= 5 ? 'text-yellow-400' : 'text-green-400')}>
                    {urgency.toFixed(1)}/10
                  </p>
                </div>
                <div className="bg-gray-900/50 rounded p-2">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Satisfaction</p>
                  <p className={clsx('text-sm font-mono font-bold', satisfaction >= 90 ? 'text-emerald-400' : satisfaction >= 50 ? 'text-yellow-400' : 'text-red-400')}>
                    {satisfaction.toFixed(0)}%
                  </p>
                </div>
              </div>

              {/* Satisfaction bar */}
              <div className="mb-3">
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={clsx('h-full rounded-full transition-all duration-500', satisfaction >= 90 ? 'bg-emerald-500' : satisfaction >= 50 ? 'bg-yellow-500' : 'bg-red-500')}
                    style={{ width: `${Math.min(satisfaction, 100)}%` }}
                  />
                </div>
                {shortfall > 0 && (
                  <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
                    <XCircle className="w-3 h-3" />
                    Shortfall: {shortfall.toFixed(1)} MW
                  </p>
                )}
              </div>

              {/* Arbiter reasoning */}
              <div className="bg-gray-900/50 rounded p-3 mb-2">
                <p className="text-xs text-gray-400 mb-1 font-medium flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  Arbiter Reasoning:
                </p>
                <p className="text-sm text-gray-300 leading-relaxed">
                  {decision.reason || 'No reasoning provided'}
                </p>
              </div>

              {/* Agent's justification (if available) */}
              {decision.justification && (
                <div className="bg-purple-900/10 rounded p-3 border border-purple-500/30">
                  <p className="text-xs text-purple-400 mb-1 font-medium flex items-center gap-1">
                    <Activity className="w-3 h-3" />
                    Agent's LLM Justification:
                  </p>
                  <p className="text-sm text-gray-300 leading-relaxed italic">
                    "{decision.justification}"
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
