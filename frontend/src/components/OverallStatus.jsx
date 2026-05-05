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
  const totalAgents = metrics.total_agents || allocations.length || 3; // Use actual total from backend
  
  // Dynamic satisfaction from backend
  const overallSatisfaction = metrics.overall_satisfaction ?? 1;
  
  // Dynamic failure risk based on multiple factors
  const fairness = metrics.fairness_index ?? 1;
  const supplyDeficit = metrics.supply_deficit_mw ?? 0;
  const utilization = metrics.utilization ?? 0;
  const agentsOffline = metrics.agents_offline ?? 0;
  
  // Calculate failure risk based on multiple factors - more balanced approach
  const riskScore = 
    // Supply deficit - only significant deficits add risk
    (supplyDeficit > 50 ? 50 : supplyDeficit > 25 ? 30 : supplyDeficit > 10 ? 15 : supplyDeficit > 0 ? 5 : 0) +
    // Fairness - only poor fairness adds risk
    (fairness < 0.3 ? 40 : fairness < 0.5 ? 25 : fairness < 0.7 ? 10 : fairness < 0.85 ? 3 : 0) +
    // Utilization - only over-utilization adds risk
    (utilization > 150 ? 30 : utilization > 120 ? 15 : utilization > 100 ? 5 : 0) +
    // Offline agents - proportionate risk
    (agentsOffline > 0 ? Math.min(30, (agentsOffline / totalAgents) * 40) : 0);
  
  const failureRisk = riskScore > 70 ? 'Critical' 
                    : riskScore > 50 ? 'High' 
                    : riskScore > 25 ? 'Med' 
                    : 'Low';
  
  // Dynamic time from ticks (2s per tick)
  const totalSeconds = tick * 2;
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const timeStr = `T+${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  return (
    <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 shadow-2xl p-8">
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-2xl">
          <Activity className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h3 className="text-2xl font-bold text-white">System Overview</h3>
          <p className="text-sm text-gray-400">Real-time grid status and metrics</p>
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
        {/* Available Power */}
        <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 rounded-2xl p-6 border border-blue-700/30">
          <div className="flex flex-col items-center">
            <div className="text-3xl font-bold text-blue-400 mb-2">{supply.toFixed(0)} MW</div>
            <div className="text-sm text-gray-300 font-medium">Supply</div>
            <div className="text-xs text-gray-500">{allocated.toFixed(0)} MW allocated</div>
          </div>
        </div>

        {/* Total Demand */}
        <div className={`bg-gradient-to-br ${demand > supply ? 'from-red-900/30 to-red-800/20 border-red-700/30' : 'from-cyan-900/30 to-cyan-800/20 border-cyan-700/30'} rounded-2xl p-6 border`}>
          <div className="flex flex-col items-center">
            <div className={`text-3xl font-bold ${demand > supply ? 'text-red-400' : 'text-cyan-400'} mb-2`}>
              {demand.toFixed(0)} MW
            </div>
            <div className="text-sm text-gray-300 font-medium">Demand</div>
            <div className="text-xs text-gray-500">
              {demand > supply ? `${(demand - supply).toFixed(0)} MW deficit` : 'Supply OK'}
            </div>
          </div>
        </div>
        
        {/* Active Agents */}
        <div className="bg-gradient-to-br from-emerald-900/30 to-emerald-800/20 rounded-2xl p-6 border border-emerald-700/30">
          <div className="flex flex-col items-center">
            <div className="text-3xl font-bold text-emerald-400 mb-2">{agentCount}/{totalAgents}</div>
            <div className="text-sm text-gray-300 font-medium">Active Agents</div>
            <div className="text-xs text-gray-500">
              {(metrics.agents_degraded ?? 0) > 0 
                ? `${metrics.agents_degraded} degraded` 
                : 'All negotiating'}
            </div>
          </div>
        </div>
        
        {/* Satisfaction */}
        <div className={`bg-gradient-to-br ${
          overallSatisfaction >= 0.9 ? 'from-emerald-900/30 to-emerald-800/20 border-emerald-700/30' : 
          overallSatisfaction >= 0.6 ? 'from-yellow-900/30 to-yellow-800/20 border-yellow-700/30' : 
          'from-red-900/30 to-red-800/20 border-red-700/30'
        } rounded-2xl p-6 border`}>
          <div className="flex flex-col items-center">
            <div className={`text-3xl font-bold ${
              overallSatisfaction >= 0.9 ? 'text-emerald-400' : 
              overallSatisfaction >= 0.6 ? 'text-yellow-400' : 'text-red-400'
            } mb-2`}>{(overallSatisfaction * 100).toFixed(0)}%</div>
            <div className="text-sm text-gray-300 font-medium">Satisfaction</div>
            <div className="text-xs text-gray-500">Avg across agents</div>
          </div>
        </div>
        
        {/* Failure Risk */}
        <div className={`bg-gradient-to-br ${
          failureRisk === 'Critical' ? 'from-red-900/30 to-red-800/20 border-red-700/30' :
          failureRisk === 'High' ? 'from-orange-900/30 to-orange-800/20 border-orange-700/30' : 
          failureRisk === 'Med' ? 'from-yellow-900/30 to-yellow-800/20 border-yellow-700/30' : 
          'from-emerald-900/30 to-emerald-800/20 border-emerald-700/30'
        } rounded-2xl p-6 border`}>
          <div className="flex flex-col items-center">
            <div className={`text-3xl font-bold ${
              failureRisk === 'Critical' ? 'text-red-500' :
              failureRisk === 'High' ? 'text-orange-400' : 
              failureRisk === 'Med' ? 'text-yellow-400' : 'text-emerald-400'
            } mb-2`}>{failureRisk}</div>
            <div className="text-sm text-gray-300 font-medium">Failure Risk</div>
            <div className="text-xs text-gray-500">Fairness: {fairness.toFixed(2)}</div>
          </div>
        </div>
        
        {/* Time */}
        <div className="bg-gradient-to-br from-gray-900/30 to-gray-800/20 rounded-2xl p-6 border border-gray-700/30">
          <div className="flex flex-col items-center">
            <div className="text-3xl font-bold text-white mb-2">{timeStr}</div>
            <div className="text-sm text-gray-300 font-medium">Elapsed</div>
            <div className="text-xs text-gray-500">Tick {tick}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
