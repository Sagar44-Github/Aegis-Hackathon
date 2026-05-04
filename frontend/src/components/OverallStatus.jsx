// frontend/src/components/OverallStatus.jsx
import { Zap, Users, Clock, AlertTriangle, Activity } from 'lucide-react';

export default function OverallStatus({ state = {} }) {
  const metrics = state?.metrics || {};
  const supply = metrics.supply_mw || metrics.total_supply_mw || 0;
  const demand = metrics.demand_mw || metrics.total_demand_mw || 0;
  const tick = state?.tick || 0;
  const agents = state?.allocations?.length || 0;
  
  // Calculate baseline (assuming 100 MW as baseline)
  const baseline = 100;
  const supplyPercent = (supply / baseline) * 100;
  
  // Calculate failure risk based on fairness and utilization
  const fairness = metrics.fairness_index || 1;
  const utilization = metrics.utilisation || 0;
  const failureRisk = fairness < 0.7 || utilization > 0.9 ? 'High' : fairness < 0.85 ? 'Med' : 'Low';
  
  // Format time from ticks (assuming 2s per tick)
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
      
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Available Power */}
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-400">{supply.toFixed(0)} MW</div>
          <div className="text-xs text-gray-500">Available Power</div>
          <div className="text-xs text-gray-600">{supplyPercent.toFixed(0)}% of baseline</div>
        </div>
        
        {/* Active Agents */}
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-400">{agents}/5</div>
          <div className="text-xs text-gray-500">Active Agents</div>
          <div className="text-xs text-gray-600">All negotiating</div>
        </div>
        
        {/* Allocation Rounds */}
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-400">{tick}</div>
          <div className="text-xs text-gray-500">Allocation Rounds</div>
          <div className="text-xs text-gray-600">Avg 2.0s/round</div>
        </div>
        
        {/* Failure Risk */}
        <div className="text-center">
          <div className={`text-2xl font-bold ${
            failureRisk === 'High' ? 'text-red-400' : 
            failureRisk === 'Med' ? 'text-yellow-400' : 'text-emerald-400'
          }`}>{failureRisk}</div>
          <div className="text-xs text-gray-500">Failure Risk</div>
          <div className="text-xs text-gray-600">
            {fairness < 0.7 ? '3 zones at-risk' : fairness < 0.85 ? '2 zones at-risk' : 'All stable'}
          </div>
        </div>
        
        {/* Time */}
        <div className="text-center">
          <div className="text-2xl font-bold text-white">{timeStr}</div>
          <div className="text-xs text-gray-500">Time</div>
          <div className="text-xs text-gray-600">Elapsed</div>
        </div>
      </div>
    </div>
  );
}
