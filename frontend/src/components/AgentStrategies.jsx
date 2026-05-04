// frontend/src/components/AgentStrategies.jsx
import { Target, Hand, Minus, Power, Pause } from 'lucide-react';

export default function AgentStrategies({ allocations = [] }) {
  const allocArray = Array.isArray(allocations) ? allocations : Object.values(allocations);
  
  // Strategy mapping based on agent type and urgency
  const getStrategy = (agent) => {
    const type = agent.agent_type || 'UNKNOWN';
    const urgency = agent.urgency_score || 5;
    
    if (type === 'HOSPITAL') {
      return { icon: Target, text: 'Demand full minimum', color: 'text-red-400' };
    } else if (type === 'FIRE_STATION') {
      return { icon: Hand, text: 'Cooperative yield', color: 'text-emerald-400' };
    } else if (type === 'WATER_PLANT') {
      return { icon: Minus, text: 'Partial reduction OK', color: 'text-yellow-400' };
    } else if (type === 'POWER_GRID') {
      return { icon: Power, text: 'Shed non-critical load', color: 'text-blue-400' };
    } else {
      return { icon: Pause, text: 'Suspend & yield', color: 'text-gray-400' };
    }
  };

  if (allocArray.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Agent Strategies</h3>
        <p className="text-xs text-gray-500 text-center py-4">No agents active</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Agent Strategies</h3>
      
      <div className="space-y-2">
        {allocArray.map((agent, idx) => {
          const strategy = getStrategy(agent);
          const StrategyIcon = strategy.icon;
          
          return (
            <div key={agent.agent_id || idx} className="flex items-center gap-3 bg-gray-900/50 rounded-lg p-2">
              <StrategyIcon className={clsx('w-4 h-4', strategy.color)} />
              <div className="flex-1">
                <div className="text-sm text-white font-medium">
                  {agent.agent_id || `Agent ${idx + 1}`}
                </div>
                <div className={clsx('text-xs', strategy.color)}>
                  {strategy.text}
                </div>
              </div>
              <div className="text-xs text-gray-500">
                {agent.agent_type || 'Unknown'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
