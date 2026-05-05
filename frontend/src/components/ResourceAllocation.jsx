// frontend/src/components/ResourceAllocation.jsx
import { Battery, TrendingUp, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';

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
    <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 shadow-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-yellow-500/20 rounded-xl">
          <Battery className="w-5 h-5 text-yellow-400" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">Resource Allocation</h3>
          <p className="text-sm text-gray-400">Power distribution</p>
        </div>
      </div>
      
      <div className="space-y-3">
        {allocArray.map((alloc, idx) => {
          const allocated = alloc.allocated_mw ?? 0;
          const demand = alloc.demand_mw ?? 1;
          const satisfaction = demand > 0 ? (allocated / demand) * 100 : 0;
          const urgency = alloc.urgency_score ?? 5;
          
          const statusColor = satisfaction >= 90 ? 'bg-emerald-500' 
                            : satisfaction >= 50 ? 'bg-yellow-500' 
                            : 'bg-red-500';
          
          const urgencyColor = urgency >= 8 ? 'text-red-400'
                             : urgency >= 5 ? 'text-yellow-400'
                             : 'text-emerald-400';

          return (
            <div key={alloc.agent_id || idx} className="bg-gray-900/50 rounded-lg p-3 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="font-semibold text-white text-sm">{alloc.agent_id || `Agent ${idx + 1}`}</span>
                  <span className="ml-2 text-xs text-gray-500 capitalize">{alloc.agent_type || 'Unknown'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={clsx('text-xs font-mono', urgencyColor)}>
                    Urgency: {urgency.toFixed(1)}/10
                  </span>
                </div>
              </div>
              
              <div className="mb-2">
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Allocated: {allocated.toFixed(1)} MW</span>
                  <span>Demand: {demand.toFixed(1)} MW</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={clsx('h-full rounded-full transition-all duration-500', statusColor)}
                    style={{ width: `${Math.min(satisfaction, 100)}%` }}
                  />
                </div>
              </div>
              
              <div className="flex justify-between text-xs">
                <span className={clsx(
                  'font-medium',
                  satisfaction >= 90 ? 'text-emerald-400' : 
                  satisfaction >= 50 ? 'text-yellow-400' : 'text-red-400'
                )}>
                  {satisfaction.toFixed(1)}% satisfied
                </span>
                {alloc.shortfall_mw > 0 && (
                  <span className="text-red-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Shortfall: {alloc.shortfall_mw.toFixed(1)} MW
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
