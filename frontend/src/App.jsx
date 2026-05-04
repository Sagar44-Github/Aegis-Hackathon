// frontend/src/App.jsx
import { useState, useMemo } from 'react';
import { Wifi, WifiOff, Zap } from 'lucide-react';
import { useWebSocket }   from './hooks/useWebSocket';
import CityMap            from './components/CityMap';
import MetricsPanel       from './components/MetricsPanel';
import AgentLog           from './components/AgentLog';
import DisasterControls   from './components/DisasterControls';

// ─── WebSocket endpoint ───────────────────────────────────────────────────────
const WS_URL = 'ws://localhost:8000/ws';

// ─── Static node positions (fallback until backend sends graph topology) ──────
const STATIC_NODES = {
  pp_main:    { id: 'pp_main',    type: 'power_plant',  location: [51.50, -0.12], capacity: 100, status: 'ONLINE' },
  hosp_main:  { id: 'hosp_main',  type: 'hospital',     location: [51.48,  0.20], capacity:  10, status: 'ONLINE' },
  water_main: { id: 'water_main', type: 'water_plant',  location: [51.20, -0.30], capacity:  10, status: 'ONLINE' },
  fire_main:  { id: 'fire_main',  type: 'fire_station', location: [51.70,  0.60], capacity:   5, status: 'ONLINE' },
};

// ─── Merge backend nodes with static fallback (fills missing locations) ───────
function mergeNodes(backendNodes, staticFallback) {
  if (!backendNodes || Object.keys(backendNodes).length === 0) return staticFallback;
  return Object.fromEntries(
    Object.entries(backendNodes).map(([id, node]) => [
      id,
      { ...(staticFallback[id] ?? {}), ...node, location: node.location ?? staticFallback[id]?.location ?? null },
    ])
  );
}

// ─── Transform allocations (array or map) → id-keyed map ─────────────────────
function toAllocMap(allocations) {
  if (!allocations) return {};
  if (Array.isArray(allocations)) {
    return allocations.reduce((acc, a) => {
      const key = a.agent_id ?? a.id ?? a.node_id;
      if (key) acc[key] = a;
      return acc;
    }, {});
  }
  return allocations;
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const { state, isConnected, error } = useWebSocket(WS_URL);
  const [disasterHistory, setDisasterHistory] = useState([]);

  // ── Derived data ───────────────────────────────────────────────────────────
  const nodes = useMemo(
    () => mergeNodes(state?.nodes, STATIC_NODES),
    [state?.nodes]
  );

  const allocationsMap = useMemo(
    () => toAllocMap(state?.allocations),
    [state?.allocations]
  );

  const logs = state?.agent_logs ?? state?.logs ?? [];

  // ── Disaster handler ───────────────────────────────────────────────────────
  const handleDisaster = (type) => {
    alert(`Disaster "${type}" triggered! (Backend integration pending)`);
    setDisasterHistory((prev) => [...prev, { type, time: Date.now() }]);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white font-sans">

      {/* ── Header ── */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Zap className="w-8 h-8 text-amber-400" />
          <div>
            <h1 className="text-xl font-bold tracking-wide">AEGIS COMMAND</h1>
            <p className="text-xs text-gray-500">Autonomous Emergency Grid Intelligence System</p>
          </div>
        </div>

        <div className="flex items-center gap-5 text-sm">
          {/* Tick counter */}
          <span className="font-mono text-gray-400">
            TICK: <span className="text-white font-semibold">{state?.tick ?? 0}</span>
          </span>

          {/* Connection status */}
          <span className={`flex items-center gap-1.5 font-medium ${
            error       ? 'text-red-400' :
            isConnected ? 'text-green-400' :
                          'text-yellow-400'
          }`}>
            {isConnected
              ? <Wifi    className="w-4 h-4" />
              : <WifiOff className="w-4 h-4" />}
            {error ? 'ERROR' : isConnected ? 'LIVE' : 'CONNECTING'}
          </span>
        </div>
      </header>

      {/* Disconnected notice */}
      {!isConnected && (
        <div className="bg-yellow-900/30 border-b border-yellow-700/40 text-yellow-300 text-xs text-center py-1.5 px-4">
          ⚠️ Not connected to server — showing static demo data
        </div>
      )}

      {/* ── Main Grid ── */}
      <main className="p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">

        {/* Left column: Map + Disaster controls */}
        <section className="lg:col-span-2 space-y-4">
          <CityMap nodes={nodes} allocations={allocationsMap} />
          <DisasterControls
            connected={isConnected}
            onTriggerDisaster={handleDisaster}
          />
        </section>

        {/* Right column: Metrics + Agent log */}
        <aside className="space-y-4">
          <MetricsPanel metrics={state?.metrics} allocations={allocationsMap} />
          <AgentLog logs={logs} />

          {/* Disaster history (only when events exist) */}
          {disasterHistory.length > 0 && (
            <div className="bg-gray-800 rounded-lg border border-gray-700 px-4 py-3 text-xs space-y-1">
              <p className="text-sm font-semibold text-slate-300 mb-2">Disaster History</p>
              {disasterHistory.slice().reverse().slice(0, 5).map((d, i) => (
                <div key={i} className="flex justify-between text-gray-400">
                  <span className="capitalize text-orange-300">{d.type}</span>
                  <span className="font-mono tabular-nums">
                    {new Date(d.time).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </aside>

      </main>
    </div>
  );
}
