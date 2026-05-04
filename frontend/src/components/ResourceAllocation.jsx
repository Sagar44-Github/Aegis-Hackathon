// frontend/src/components/ResourceAllocation.jsx
import { Battery, TrendingUp, AlertTriangle, Activity, Cloud, Zap, AlertTriangle as FireIcon } from 'lucide-react';
import { clsx } from 'clsx';

// ─── Agent type icons matching AgentLog ─────────────────────────────────────
const AGENT_ICONS = {
  HOSPITAL: { icon: Activity, color: 'text-pink-400' },
  WATER_PLANT: { icon: Cloud, color: 'text-blue-400' },
  FIRE_STATION: { icon: FireIcon, color: 'text-orange-400' },
  POWER_PLANT: { icon: Zap, color: 'text-yellow-400' },
  DEFAULT: { icon: Battery, color: 'text-purple-400' },
};

// ─── Urgency color coding ─────────────────────────────────────────────────────
function getUrgencyColor(urgency) {
  if (urgency >= 8) return { color: 'text-red-400', bg: 'bg-red-900/20', border: 'border-red-500' };
  if (urgency >= 5) return { color: 'text-yellow-400', bg: 'bg-yellow-900/20', border: 'border-yellow-500' };
  return { color: 'text-green-400', bg: 'bg-green-900/20', border: 'border-green-500' };
}

export default function ResourceAllocation({ allocations = {} }) {
  const allocArray = Array.isArray(allocations) ? allocations : Object.values(allocations);
  
  if (allocArray.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
          <Battery className="w-4 h-4" />
          Resource Allocation
        </h3>
        <p className="text-xs text-gray-500 text-center py-4">No allocation data available</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
        <Battery className="w-4 h-4" />
        Resource Allocation
      </h3>
      
      <div className="space-y-3">
        {allocArray.map((alloc, idx) => {
          const allocated = alloc.allocated_mw ?? 0;
          const demand = alloc.demand_mw ?? 1;
          const satisfaction = demand > 0 ? (allocated / demand) * 100 : 0;
          const urgency = alloc.urgency_score ?? 5;
          const shortfall = Math.max(0, demand - allocated);
          
          const statusColor = satisfaction >= 90 ? 'bg-emerald-500' 
                            : satisfaction >= 50 ? 'bg-yellow-500' 
                            : 'bg-red-500';
          
          const urgencyStyle = getUrgencyColor(urgency);
          const agentIcon = AGENT_ICONS[alloc.agent_type] || AGENT_ICONS.DEFAULT;
          const AgentIcon = agentIcon.icon;

          return (
            <div 
              key={alloc.agent_id || idx} 
              className={clsx(
                'bg-gray-900/50 rounded-lg p-3 border-l-4',
                urgencyStyle.border
              )}
            >
              {/* Header with agent info */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AgentIcon className={clsx('w-4 h-4', agentIcon.color)} />
                  <div>
                    <span className="font-semibold text-white text-sm">{alloc.agent_id || `Agent ${idx + 1}`}</span>
                    <span className="ml-2 text-xs text-gray-500 capitalize bg-gray-800 px-2 py-0.5 rounded">
                      {alloc.agent_type?.replace('_', ' ') || 'Unknown'}
                    </span>
                  </div>
                </div>
                <div className={clsx('text-xs font-mono font-bold px-2 py-1 rounded', urgencyStyle.bg, urgencyStyle.color)}>
                  Urgency: {urgency.toFixed(1)}/10
                </div>
              </div>
              
              {/* Allocation bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Allocated: <span className="text-white font-semibold">{allocated.toFixed(1)} MW</span></span>
                  <span>Demand: <span className="text-white font-semibold">{demand.toFixed(1)} MW</span></span>
                </div>
                <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={clsx('h-full rounded-full transition-all duration-500', statusColor)}
                    style={{ width: `${Math.min(satisfaction, 100)}%` }}
                  />
                </div>
              </div>
              
              {/* Status and shortfall */}
              <div className="flex justify-between items-center text-xs">
                <div className="flex items-center gap-2">
                  <span className={clsx(
                    'font-medium px-2 py-1 rounded',
                    satisfaction >= 90 ? 'bg-emerald-900/30 text-emerald-400' : 
                    satisfaction >= 50 ? 'bg-yellow-900/30 text-yellow-400' : 'bg-red-900/30 text-red-400'
                  )}>
                    {satisfaction >= 90 ? '✓ Fully Satisfied' : 
                     satisfaction >= 50 ? '⚠ Partially Satisfied' : '✗ Underallocated'}
                  </span>
                  <span className="text-gray-400">
                    ({satisfaction.toFixed(1)}%)
                  </span>
                </div>
                {shortfall > 0 && (
                  <span className="text-red-400 flex items-center gap-1 font-medium">
                    <AlertTriangle className="w-3 h-3" />
                    Shortfall: {shortfall.toFixed(1)} MW
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
