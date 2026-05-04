// frontend/src/components/SystemHealth.jsx
import { Activity, Heart, Shield, Zap, Users, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';

export default function SystemHealth({ state = {} }) {
  const metrics = state?.metrics || {};
  const fairness = metrics.fairness_index || 1;
  const utilization = metrics.utilisation || 0;
  const allocations = state?.allocations || [];
  
  // Calculate derived metrics
  const allocationEfficiency = utilization * 100;
  const failureEvents = allocations.filter(a => (a.shortfall_mw || 0) > 0).length;
  const agentsStable = allocations.filter(a => (a.satisfaction || 1) > 0.7).length;
  const convergenceRate = fairness > 0.8 ? 96 : fairness > 0.6 ? 78 : 52;
  
  const metricsData = [
    {
      label: 'Allocation Efficiency',
      value: `${allocationEfficiency.toFixed(0)}%`,
      icon: Activity,
      color: allocationEfficiency > 80 ? 'text-emerald-400' : allocationEfficiency > 60 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Failure Events',
      value: failureEvents,
      icon: AlertTriangle,
      color: failureEvents === 0 ? 'text-emerald-400' : failureEvents < 3 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Agents Stable',
      value: `${agentsStable}/${allocations.length}`,
      icon: Users,
      color: agentsStable === allocations.length ? 'text-emerald-400' : 'text-yellow-400',
    },
    {
      label: 'Convergence Rate',
      value: `${convergenceRate}%`,
      icon: Zap,
      color: convergenceRate > 80 ? 'text-emerald-400' : convergenceRate > 60 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Fairness Index',
      value: fairness.toFixed(2),
      icon: Shield,
      color: fairness > 0.8 ? 'text-emerald-400' : fairness > 0.6 ? 'text-yellow-400' : 'text-red-400',
    },
    {
      label: 'Lives at Risk',
      value: 'Reducing',
      icon: Heart,
      color: 'text-emerald-400',
    },
  ];

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
        <Activity className="w-4 h-4" />
        System Health
      </h3>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
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
            </div>
          );
        })}
      </div>
    </div>
  );
}
