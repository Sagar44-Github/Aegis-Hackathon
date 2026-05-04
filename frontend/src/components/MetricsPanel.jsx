// frontend/src/components/MetricsPanel.jsx
import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Zap, Gauge, ShieldCheck, Users, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { clsx } from 'clsx';

// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_HISTORY = 20;

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmt(val, decimals = 1, fallback = '—') {
  if (val == null || isNaN(val)) return fallback;
  return Number(val).toFixed(decimals);
}

/** Supports allocations as object OR array */
function agentCount(allocations) {
  if (!allocations) return 0;
  return Array.isArray(allocations)
    ? allocations.length
    : Object.keys(allocations).length;
}

/**
 * Resolve supply/demand from either naming convention:
 *   metrics.supply / metrics.demand  (their API)
 *   metrics.total_supply_mw / metrics.total_demand_mw  (our API)
 */
function resolveSupplyDemand(metrics) {
  const supply = metrics.total_supply_mw ?? metrics.supply ?? null;
  const demand = metrics.total_demand_mw ?? metrics.demand ?? null;
  return { supply, demand };
}

/**
 * Resolve utilization — may arrive as 0-1 fraction or 0-100 percent.
 */
function resolveUtil(metrics, supply, demand) {
  if (metrics.utilization != null) {
    // If it's <= 1 treat as fraction, otherwise as percent
    return metrics.utilization <= 1
      ? metrics.utilization * 100
      : metrics.utilization;
  }
  if (supply != null && demand != null && demand > 0) {
    return (supply / demand) * 100;
  }
  return null;
}

/** Trend icon comparing last two fairness samples. */
function TrendIcon({ history }) {
  if (history.length < 2) return <Minus className="w-3 h-3 text-slate-500" />;
  const delta = history[history.length - 1].value - history[history.length - 2].value;
  if (delta > 0.001)  return <TrendingUp   className="w-3 h-3 text-emerald-400" />;
  if (delta < -0.001) return <TrendingDown  className="w-3 h-3 text-red-400" />;
  return <Minus className="w-3 h-3 text-slate-500" />;
}

// ─── MetricCard ───────────────────────────────────────────────────────────────
function MetricCard({ icon: Icon, iconColor, label, value, accent, barValue, barColor, children }) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 flex flex-col gap-2 hover:border-gray-600 transition-colors">
      <div className="flex items-center gap-2 text-gray-400 text-xs font-medium uppercase tracking-wider">
        <Icon className={clsx('w-4 h-4', iconColor)} />
        {label}
      </div>

      <div className={clsx('text-2xl font-bold tabular-nums leading-none', accent ?? 'text-white')}>
        {value}
      </div>

      {barValue != null && (
        <div className="h-1.5 w-full rounded-full bg-gray-700 overflow-hidden">
          <div
            className={clsx('h-full rounded-full transition-all duration-500', barColor ?? 'bg-blue-500')}
            style={{ width: `${Math.min(barValue, 100)}%` }}
          />
        </div>
      )}

      {children}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
/**
 * MetricsPanel
 * @param {{
 *   metrics: {
 *     supply?: number, total_supply_mw?: number,
 *     demand?: number, total_demand_mw?: number,
 *     utilization?: number,
 *     fairness?: number,
 *     active_agents?: number,
 *     tick?: number,
 *   },
 *   allocations: Object | Array
 * }} props
 */
export default function MetricsPanel({ metrics = {}, allocations = {} }) {
  const [fairnessHistory, setFairnessHistory] = useState([]);

  // Track fairness over last MAX_HISTORY ticks
  useEffect(() => {
    if (metrics.fairness == null) return;
    setFairnessHistory((prev) => {
      const entry = { tick: metrics.tick ?? Date.now(), value: metrics.fairness };
      const next = [...prev, entry];
      return next.length > MAX_HISTORY ? next.slice(next.length - MAX_HISTORY) : next;
    });
  }, [metrics.fairness, metrics.tick]);

  // ── Derived values ──────────────────────────────────────────────────────
  const { supply, demand }  = resolveSupplyDemand(metrics);
  const util                = resolveUtil(metrics, supply, demand);
  const fairness            = metrics.fairness ?? null;
  const agents              = metrics.active_agents ?? agentCount(allocations);

  const supplyAccent  = supply == null || demand == null ? 'text-white'
    : supply >= demand      ? 'text-emerald-400'
    : supply >= demand * 0.75 ? 'text-yellow-400'
    : 'text-red-400';

  const utilBarColor  = util == null ? 'bg-blue-500'
    : util >= 90 ? 'bg-red-500'
    : util >= 70 ? 'bg-yellow-500'
    : 'bg-emerald-500';

  const utilAccent    = util == null ? 'text-white'
    : util >= 90 ? 'text-red-400'
    : util >= 70 ? 'text-yellow-400'
    : 'text-blue-400';

  const fairnessAccent = fairness == null ? 'text-white'
    : fairness >= 0.8 ? 'text-emerald-400'
    : fairness >= 0.5 ? 'text-yellow-400'
    : 'text-red-400';

  return (
    <div className="space-y-4">

      {/* ── 4 metric cards ── */}
      <div className="grid grid-cols-2 gap-3">

        <MetricCard
          icon={Zap}
          iconColor="text-yellow-400"
          label="Total Supply"
          value={supply != null ? `${fmt(supply, 0)} MW` : '—'}
          accent={supplyAccent}
          barValue={supply != null && demand != null ? (supply / Math.max(demand, 1)) * 100 : null}
          barColor={utilBarColor}
        />

        <MetricCard
          icon={Gauge}
          iconColor="text-blue-400"
          label="Utilization"
          value={util != null ? `${fmt(util, 1)}%` : '—'}
          accent={utilAccent}
          barValue={util}
          barColor={utilBarColor}
        />

        <MetricCard
          icon={ShieldCheck}
          iconColor="text-emerald-400"
          label="Fairness Index"
          value={fairness != null ? fmt(fairness, 3) : '—'}
          accent={fairnessAccent}
        >
          {fairnessHistory.length > 1 && (
            <div className="flex items-center gap-1 text-[10px] text-gray-500">
              <TrendIcon history={fairnessHistory} />
              trending
            </div>
          )}
        </MetricCard>

        <MetricCard
          icon={Users}
          iconColor="text-violet-400"
          label="Active Agents"
          value={agents ?? '—'}
          accent="text-violet-300"
        >
          <div className="flex flex-wrap gap-1 mt-0.5">
            {Array.from({ length: Math.min(agents, 10) }).map((_, i) => (
              <span
                key={i}
                className="w-2 h-2 rounded-full bg-violet-500 animate-pulse"
                style={{ animationDelay: `${i * 80}ms` }}
              />
            ))}
            {agents > 10 && (
              <span className="text-[10px] text-gray-500 self-center">+{agents - 10}</span>
            )}
          </div>
        </MetricCard>

      </div>

      {/* ── Fairness trend chart ── */}
      <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">
        <h4 className="text-sm text-gray-400 mb-3 flex items-center gap-2">
          Fairness Trend
          {fairnessHistory.length > 1 && <TrendIcon history={fairnessHistory} />}
        </h4>

        {fairnessHistory.length > 1 ? (
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={fairnessHistory} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="tick" stroke="#9ca3af" fontSize={9} tick={false} />
              <YAxis domain={[0, 1]} stroke="#9ca3af" fontSize={10} tickCount={3} />
              <Tooltip
                contentStyle={{
                  background: '#1f2937',
                  border: '1px solid #374151',
                  color: '#e5e7eb',
                  borderRadius: '6px',
                  fontSize: '11px',
                }}
                formatter={(v) => [fmt(v, 4), 'Fairness']}
                labelFormatter={() => ''}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[100px] flex items-center justify-center text-xs text-gray-600">
            Waiting for data…
          </div>
        )}
      </div>

    </div>
  );
}
