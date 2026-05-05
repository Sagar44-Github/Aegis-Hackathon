// frontend/src/components/PriorityQueue.jsx
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { clsx } from 'clsx';
import { useState, useEffect, useRef } from 'react';

export default function PriorityQueue({ allocations = [] }) {
  const allocArray = Array.isArray(allocations) ? allocations : Object.values(allocations);
  
  // Track previous urgency scores for trend calculation
  const previousUrgencyRef = useRef({});
  const [trends, setTrends] = useState({});

  // Calculate trends when allocations change
  useEffect(() => {
    const newTrends = {};
    
    allocArray.forEach(alloc => {
      const agentId = alloc.agent_id || `Agent ${allocArray.indexOf(alloc) + 1}`;
      const currentUrgency = alloc.urgency_score || 5;
      const previousUrgency = previousUrgencyRef.current[agentId];
      
      if (previousUrgency !== undefined) {
        if (currentUrgency > previousUrgency + 0.5) {
          newTrends[agentId] = 'up'; // Urgency increased
        } else if (currentUrgency < previousUrgency - 0.5) {
          newTrends[agentId] = 'down'; // Urgency decreased
        } else {
          newTrends[agentId] = 'neutral'; // No significant change
        }
      } else {
        newTrends[agentId] = 'neutral'; // First time seeing this agent
      }
    });
    
    setTrends(newTrends);
    
    // Update previous urgency scores for next comparison
    const updatedPrevious = {};
    allocArray.forEach(alloc => {
      const agentId = alloc.agent_id || `Agent ${allocArray.indexOf(alloc) + 1}`;
      updatedPrevious[agentId] = alloc.urgency_score || 5;
    });
    previousUrgencyRef.current = updatedPrevious;
  }, [allocArray]);
  
  if (allocArray.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Priority Queue</h3>
        <p className="text-xs text-gray-500 text-center py-4">No allocation data</p>
      </div>
    );
  }

  // Sort by urgency score (descending)
  const sorted = [...allocArray].sort((a, b) => (b.urgency_score || 0) - (a.urgency_score || 0));
  
  // Calculate percentage of total demand
  const totalDemand = sorted.reduce((sum, a) => sum + (a.demand_mw || 0), 0);
  
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Priority Queue</h3>
      
      <div className="space-y-2">
        {sorted.map((alloc, idx) => {
          const demand = alloc.demand_mw || 0;
          const urgency = alloc.urgency_score || 5;
          const percent = totalDemand > 0 ? (demand / totalDemand) * 100 : 0;
          const rank = idx + 1;
          
          const agentId = alloc.agent_id || `Agent ${allocArray.indexOf(alloc) + 1}`;
          const trend = trends[agentId] || 'neutral';
          
          const trendIcon = trend === 'up' ? <TrendingUp className="w-3 h-3 text-red-400" /> : // Red for increasing urgency (bad)
                          trend === 'down' ? <TrendingDown className="w-3 h-3 text-emerald-400" /> : // Green for decreasing urgency (good)
                          <Minus className="w-3 h-3 text-yellow-400" />; // Yellow for neutral
          
          return (
            <div key={alloc.agent_id || idx} className="flex items-center gap-3">
              <div className="w-6 h-6 rounded-full bg-gray-700 flex items-center justify-center text-xs font-bold text-white">
                {rank}
              </div>
              
              <div className="flex-1">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm text-white font-medium">
                    {alloc.agent_id || `Agent ${idx + 1}`}
                  </span>
                  <span className="text-xs text-gray-400">{percent.toFixed(0)}%</span>
                </div>
                <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={clsx(
                      'h-full rounded-full transition-all duration-500',
                      rank === 1 ? 'bg-emerald-500' :
                      rank === 2 ? 'bg-blue-500' :
                      rank === 3 ? 'bg-yellow-500' :
                      'bg-red-500'
                    )}
                    style={{ width: `${percent}%` }}
                  />
                </div>
              </div>
              
              <div className="flex items-center gap-1">
                {trendIcon}
                <span className="text-xs text-gray-500 w-8 text-right">
                  {urgency.toFixed(1)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
