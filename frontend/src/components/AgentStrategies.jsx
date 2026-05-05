// frontend/src/components/AgentStrategies.jsx
import { Target, Hand, Minus, Power, Pause } from 'lucide-react';
import { clsx } from 'clsx';

export default function AgentStrategies({ allocations = [] }) {
  const allocArray = Array.isArray(allocations) ? allocations : Object.values(allocations);
  
  // Dynamic strategy based on actual demand, allocation, and urgency
  const getStrategy = (agent) => {
    const type = agent.agent_type || 'UNKNOWN';
    const urgency = agent.urgency_score || 5;
    const demand = agent.demand_mw || 0;
    const allocated = agent.allocated_mw || 0;
    const satisfaction = demand > 0 ? (allocated / demand) * 100 : 0;
    
    // Calculate strategy based on actual situation
    if (satisfaction < 50) {
      // High deficit - critical need
      if (type === 'HOSPITAL') {
        return { icon: Target, text: 'Critical: Full power required', color: 'text-red-500' };
      } else if (type === 'FIRE_STATION') {
        return { icon: Target, text: 'Emergency response priority', color: 'text-red-500' };
      } else if (type === 'WATER_PLANT') {
        return { icon: Target, text: 'Essential service restoration', color: 'text-red-500' };
      } else if (type === 'POWER_GRID') {
        return { icon: Target, text: 'Grid stability critical', color: 'text-red-500' };
      } else {
        return { icon: Target, text: 'Critical demand unmet', color: 'text-red-500' };
      }
    } else if (satisfaction < 80) {
      // Partial deficit - negotiating
      if (type === 'HOSPITAL') {
        return { icon: Hand, text: 'Seeking minimum guarantee', color: 'text-orange-400' };
      } else if (type === 'FIRE_STATION') {
        return { icon: Hand, text: 'Cooperative load sharing', color: 'text-yellow-400' };
      } else if (type === 'WATER_PLANT') {
        return { icon: Minus, text: 'Partial reduction accepted', color: 'text-yellow-400' };
      } else if (type === 'POWER_GRID') {
        return { icon: Power, text: 'Load shedding active', color: 'text-orange-400' };
      } else {
        return { icon: Hand, text: 'Negotiating partial supply', color: 'text-yellow-400' };
      }
    } else if (urgency > 7) {
      // High urgency but satisfied - maintaining priority
      if (type === 'HOSPITAL') {
        return { icon: Target, text: 'Maintaining critical levels', color: 'text-red-400' };
      } else if (type === 'FIRE_STATION') {
        return { icon: Hand, text: 'Ready for escalation', color: 'text-orange-400' };
      } else if (type === 'WATER_PLANT') {
        return { icon: Minus, text: 'Monitoring demand spikes', color: 'text-yellow-400' };
      } else if (type === 'POWER_GRID') {
        return { icon: Power, text: 'High alert standby', color: 'text-orange-400' };
      } else {
        return { icon: Hand, text: 'High priority maintained', color: 'text-orange-400' };
      }
    } else {
      // Well supplied - flexible approach
      if (type === 'HOSPITAL') {
        return { icon: Hand, text: 'Stable operation', color: 'text-emerald-400' };
      } else if (type === 'FIRE_STATION') {
        return { icon: Hand, text: 'Yielding to critical needs', color: 'text-emerald-400' };
      } else if (type === 'WATER_PLANT') {
        return { icon: Minus, text: 'Flexible load management', color: 'text-emerald-400' };
      } else if (type === 'POWER_GRID') {
        return { icon: Power, text: 'Excess capacity available', color: 'text-blue-400' };
      } else {
        return { icon: Pause, text: 'Low priority standby', color: 'text-gray-400' };
      }
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
