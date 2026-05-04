// frontend/src/components/OverallStatus.jsx
import { Zap, Users, Clock, AlertTriangle, Activity, TrendingUp } from 'lucide-react';

export default function OverallStatus({ state = {} }) {
  const metrics = state?.metrics || {};
  const allocations = state?.allocations || [];
  
  // All dynamic values from backend
  const supply = metrics.total_supply_mw ?? 0;
  const demand = metrics.total_demand_mw ?? 0;
  const allocated = metrics.total_allocated_mw ?? 0;
  const tick = state?.tick ?? 0;
  const agentCount = allocations.length || 0;
  const totalAgents = 3; // We have exactly 3 bidding agents
  
  // Dynamic satisfaction from backend
  const overallSatisfaction = metrics.overall_satisfaction ?? 1;
  
  // Dynamic failure risk based on actual metrics
  const fairness = metrics.fairness_index ?? 1;
  const supplyDeficit = metrics.supply_deficit_mw ?? 0;
  const failureRisk = supplyDeficit > 20 ? 'Critical' 
                    : supplyDeficit > 10 ? 'High' 
                    : supplyDeficit > 0 ? 'Med' 
                    : 'Low';
  
  // Dynamic time from ticks (2s per tick)
  const totalSeconds = tick * 2;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const timeStr = `T+${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
        <Activity className="w-4 h-4" />
        Overall Status
      </h3>
      
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        {/* Available Power */}
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{supply.toFixed(0)} MW</div>
          <div className="text-xs text-gray-500">Supply</div>
          <div className="text-xs text-gray-600">{allocated.toFixed(0)} MW allocated</div>
        </div>

        {/* Total Demand */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${demand > supply ? 'text-red-400' : 'text-cyan-400'}`}>
            {demand.toFixed(0)} MW
          </div>
          <div className="text-xs text-gray-500">Demand</div>
          <div className="text-xs text-gray-600">
            {demand > supply ? `${(demand - supply).toFixed(0)} MW deficit` : 'Supply OK'}
          </div>
        </div>
        
        {/* Active Agents */}
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-400">{agentCount}/{totalAgents}</div>
          <div className="text-xs text-gray-500">Active Agents</div>
          <div className="text-xs text-gray-600">
            {(metrics.agents_degraded ?? 0) > 0 
              ? `${metrics.agents_degraded} degraded` 
              : 'All negotiating'}
          </div>
        </div>
        
        {/* Satisfaction */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${
            overallSatisfaction >= 0.9 ? 'text-emerald-400' : 
            overallSatisfaction >= 0.6 ? 'text-yellow-400' : 'text-red-400'
          }`}>{(overallSatisfaction * 100).toFixed(0)}%</div>
          <div className="text-xs text-gray-500">Satisfaction</div>
          <div className="text-xs text-gray-600">Avg across agents</div>
        </div>
        
        {/* Failure Risk */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${
            failureRisk === 'Critical' ? 'text-red-500' :
            failureRisk === 'High' ? 'text-red-400' : 
            failureRisk === 'Med' ? 'text-yellow-400' : 'text-emerald-400'
          }`}>{failureRisk}</div>
          <div className="text-xs text-gray-500">Failure Risk</div>
          <div className="text-xs text-gray-600">
            Fairness: {fairness.toFixed(2)}
          </div>
        </div>
        
        {/* Time */}
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{timeStr}</div>
          <div className="text-xs text-gray-500">Elapsed</div>
          <div className="text-xs text-gray-600">Tick {tick}</div>
        </div>
      </div>
    </div>
  );
}
