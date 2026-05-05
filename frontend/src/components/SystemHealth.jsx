// frontend/src/components/SystemHealth.jsx
import { Activity, Heart, Shield, Zap, Users, AlertTriangle, TrendingUp } from 'lucide-react';
import { clsx } from 'clsx';

export default function SystemHealth({ state = {} }) {
  const metrics = state?.metrics || {};
  const allocations = state?.allocations || [];
  const agentStates = state?.agent_states || {};
  
  // All dynamic — derived from backend data
  const fairness = metrics.fairness_index ?? 1;
  const utilization = metrics.utilization ?? 0;
  const totalSupply = metrics.total_supply_mw ?? 0;
  const totalDemand = metrics.total_demand_mw ?? 0;
  const totalAllocated = metrics.total_allocated_mw ?? 0;
  const supplyDeficit = metrics.supply_deficit_mw ?? 0;
  const overallSatisfaction = metrics.overall_satisfaction ?? 1;
  
  // Dynamic agent status counts from backend
  const agentsOnline = metrics.agents_online ?? 0;
  const agentsDegraded = metrics.agents_degraded ?? 0;
  const agentsOffline = metrics.agents_offline ?? 0;
  const totalAgents = metrics.total_agents || agentsOnline + agentsDegraded + agentsOffline || 3;
  
  // Dynamic shortfall count from actual allocations
  const failureEvents = allocations.filter(a => (a.shortfall_mw || 0) > 0).length;
  
  // Dynamic allocation efficiency
  const allocEfficiency = totalSupply > 0 ? (totalAllocated / totalSupply) * 100 : 0;
  
  const metricsData = [
    {
      label: 'Allocation Efficiency',
      value: `${allocEfficiency.toFixed(0)}%`,
      sub: `${totalAllocated.toFixed(0)}/${totalSupply.toFixed(0)} MW`,
      icon: Activity,
      color: allocEfficiency > 80 ? 'text-emerald-400' : allocEfficiency > 50 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Supply Deficit',
      value: supplyDeficit > 0 ? `${supplyDeficit.toFixed(1)} MW` : 'None',
      sub: supplyDeficit > 0 ? 'Demand exceeds supply' : 'Supply sufficient',
      icon: AlertTriangle,
      color: supplyDeficit <= 0 ? 'text-emerald-400' : supplyDeficit < 10 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Agents Status',
      value: `${agentsOnline}/${totalAgents}`,
      sub: agentsDegraded > 0 ? `${agentsDegraded} degraded` : agentsOffline > 0 ? `${agentsOffline} offline` : 'All healthy',
      icon: Users,
      color: agentsOnline === totalAgents ? 'text-emerald-400' : agentsOffline > 0 ? 'text-red-400' : 'text-yellow-400',
    },
    {
      label: 'Satisfaction',
      value: `${(overallSatisfaction * 100).toFixed(0)}%`,
      sub: failureEvents > 0 ? `${failureEvents} shortfalls` : 'All met',
      icon: TrendingUp,
      color: overallSatisfaction >= 0.9 ? 'text-emerald-400' : overallSatisfaction >= 0.6 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Fairness Index',
      value: fairness.toFixed(3),
      sub: fairness > 0.9 ? 'Equitable' : fairness > 0.7 ? 'Moderate' : 'Unfair',
      icon: Shield,
      color: fairness > 0.9 ? 'text-emerald-400' : fairness > 0.7 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Grid Utilization',
      value: `${utilization.toFixed(0)}%`,
      sub: utilization > 90 ? 'Near capacity' : utilization > 60 ? 'Moderate load' : 'Light load',
      icon: Zap,
      color: utilization > 90 ? 'text-red-400' : utilization > 60 ? 'text-yellow-400' : 'text-emerald-400',
    },
  ];

  return (
    <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 shadow-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-green-500/20 rounded-xl">
          <Activity className="w-5 h-5 text-green-400" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-white">System Health</h3>
          <p className="text-sm text-gray-400">Performance metrics</p>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {metricsData.map((metric, idx) => {
          const Icon = metric.icon;
          return (
            <div key={idx} className="bg-gray-900/50 rounded-lg p-3 border border-gray-700">
              <div className="flex items-center gap-2 mb-1">
                <Icon className={clsx('w-4 h-4', metric.color)} />
                <span className="text-xs text-gray-500">{metric.label}</span>
              </div>
              <div className={clsx('text-lg font-bold', metric.color)}>
                {metric.value}
              </div>
              <div className="text-[10px] text-gray-600 mt-0.5">
                {metric.sub}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
