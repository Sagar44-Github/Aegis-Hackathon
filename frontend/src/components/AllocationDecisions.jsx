// frontend/src/components/AllocationDecisions.jsx
import { CheckCircle, XCircle, AlertCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { clsx } from 'clsx';
import { useState } from 'react';

export default function AllocationDecisions({ decisions = [] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const MAX_VISIBLE = 5; // Show max 5 decisions by default
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

  // Get the most recent decisions
  const recentDecisions = decisions.slice(-10).reverse();
  
  // Determine which decisions to show
  const visibleDecisions = isExpanded 
    ? recentDecisions 
    : recentDecisions.slice(0, MAX_VISIBLE);
  
  const hasMore = recentDecisions.length > MAX_VISIBLE;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
        <Clock className="w-4 h-4" />
        Allocation Decisions
      </h3>
      
      <div className="space-y-2">
        {visibleDecisions.map((decision, idx) => {
          const decisionType = decision.decision || 'UNKNOWN';
          const isAccepted = decisionType === 'ACCEPTED';
          const isPartial = decisionType === 'PARTIALLY_ACCEPTED';
          const isDenied = decisionType === 'DENIED';
          
          const statusConfig = {
            ACCEPTED: {
              icon: CheckCircle,
              color: 'text-emerald-400',
              bg: 'bg-emerald-900/20',
              border: 'border-emerald-500/30',
            },
            PARTIALLY_ACCEPTED: {
              icon: AlertCircle,
              color: 'text-yellow-400',
              bg: 'bg-yellow-900/20',
              border: 'border-yellow-500/30',
            },
            DENIED: {
              icon: XCircle,
              color: 'text-red-400',
              bg: 'bg-red-900/20',
              border: 'border-red-500/30',
            },
            UNKNOWN: {
              icon: AlertCircle,
              color: 'text-gray-400',
              bg: 'bg-gray-900/20',
              border: 'border-gray-500/30',
            },
          };
          
          const config = statusConfig[decisionType] || statusConfig.UNKNOWN;
          const StatusIcon = config.icon;

          return (
            <div 
              key={decision.agent_id || idx}
              className={clsx(
                'rounded-lg p-3 border-l-4',
                config.bg,
                config.border
              )}
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <StatusIcon className={clsx('w-4 h-4', config.color)} />
                  <span className="font-semibold text-white text-sm">
                    {decision.agent_id || `Agent ${idx + 1}`}
                  </span>
                  <span className="text-xs text-gray-500 capitalize">
                    {decision.agent_type || 'Unknown'}
                  </span>
                </div>
                <span className={clsx('text-xs font-bold px-2 py-0.5 rounded', config.color, config.bg)}>
                  {decisionType.replace('_', ' ')}
                </span>
              </div>

              {/* Details row */}
              <div className="grid grid-cols-3 gap-2 text-xs mb-2">
                <div>
                  <span className="text-gray-500">Demand:</span>
                  <span className="ml-1 text-white font-mono">
                    {decision.demand?.toFixed(1) || 0} MW
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Allocated:</span>
                  <span className="ml-1 text-white font-mono">
                    {decision.allocated?.toFixed(1) || 0} MW
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">Urgency:</span>
                  <span className="ml-1 text-white font-mono">
                    {decision.urgency?.toFixed(1) || 0}/10
                  </span>
                </div>
              </div>

              {/* Arbiter reasoning */}
              <div className="bg-gray-900/50 rounded p-2">
                <p className="text-xs text-gray-400 mb-1 font-medium">Arbiter Reasoning:</p>
                <p className="text-xs text-gray-300 leading-relaxed">
                  {decision.reason || 'No reasoning provided'}
                </p>
              </div>

              {/* Agent's justification (if available) */}
              {decision.justification && (
                <div className="mt-2 bg-purple-900/10 rounded p-2 border border-purple-500/20">
                  <p className="text-xs text-purple-400 mb-1 font-medium flex items-center gap-1">
                    Agent's LLM Justification:
                  </p>
                  <p className="text-xs text-gray-300 leading-relaxed italic">
                    "{decision.justification}"
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* View More/Less Button */}
      {hasMore && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full mt-3 flex items-center justify-center gap-2 py-2 px-3 bg-gray-700 hover:bg-gray-600 rounded-lg border border-gray-600 text-xs font-medium text-gray-300 transition-colors duration-200"
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-3 h-3" />
              Show Less ({recentDecisions.length - MAX_VISIBLE} hidden)
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              View More ({recentDecisions.length - MAX_VISIBLE} more)
            </>
          )}
        </button>
      )}
    </div>
  );
}
