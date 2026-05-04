// frontend/src/App.jsx
import { useState, useMemo, useEffect } from 'react';
import { Wifi, WifiOff, Zap, MapPin, AlertCircle } from 'lucide-react';
import { useWebSocket }   from './hooks/useWebSocket';
import CityMap            from './components/CityMap';
import MetricsPanel       from './components/MetricsPanel';
import AgentLog           from './components/AgentLog';
import DisasterControls   from './components/DisasterControls';
import ResourceAllocation from './components/ResourceAllocation';
import AllocationDecisions from './components/AllocationDecisions';

// ─── Endpoints ────────────────────────────────────────────────────────────────
const WS_URL  = 'ws://localhost:8001/ws';
const API_URL = 'http://localhost:8001';

// ─── Static node positions (fallback until backend sends graph topology) ──────
// Types match backend AgentType enum (uppercase)
const STATIC_NODES = {
  pp_main:    { id: 'pp_main',    type: 'POWER_PLANT',  location: [51.50, -0.12], capacity: 100, status: 'ONLINE' },
  hosp_main:  { id: 'hosp_main',  type: 'HOSPITAL',     location: [51.48,  0.20], capacity:  10, status: 'ONLINE' },
  water_main: { id: 'water_main', type: 'WATER_PLANT',  location: [51.20, -0.30], capacity:  10, status: 'ONLINE' },
  fire_main:  { id: 'fire_main',  type: 'FIRE_STATION', location: [51.70,  0.60], capacity:   5, status: 'ONLINE' },
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
  const [userLocation, setUserLocation] = useState(null);
  const [locationError, setLocationError] = useState(null);

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

  // Get user location on mount
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation({ lat: latitude, lng: longitude });
          // Send location to backend to generate agents around user
          fetch(`${API_URL}/api/set-location`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ latitude, longitude })
          }).catch(err => console.error('Failed to send location:', err));
        },
        (err) => {
          setLocationError('Location access denied. Using default location.');
          console.error('Geolocation error:', err);
        }
      );
    } else {
      setLocationError('Geolocation not supported. Using default location.');
    }
  }, []);

  // ── Disaster handler — calls real backend API ─────────────────────────────
  const handleDisaster = async (type) => {
    try {
      const res = await fetch(`${API_URL}/api/disaster/${type}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const event = await res.json();
      console.log('[Disaster] triggered:', event);
      setDisasterHistory((prev) => [
        ...prev,
        { type, time: Date.now(), event: event?.event ?? event },
      ]);
    } catch (err) {
      console.error('[Disaster] trigger failed:', err);
      setDisasterHistory((prev) => [
        ...prev,
        { type, time: Date.now(), error: err.message },
      ]);
    }
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
          {/* User location */}
          {userLocation && (
            <span className="flex items-center gap-1.5 text-gray-400">
              <MapPin className="w-4 h-4 text-blue-400" />
              <span className="font-mono">
                {userLocation.lat.toFixed(4)}, {userLocation.lng.toFixed(4)}
              </span>
            </span>
          )}

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

      {/* Location notice */}
      {locationError && (
        <div className="bg-orange-900/30 border-b border-orange-700/40 text-orange-300 text-xs text-center py-1.5 px-4 flex items-center justify-center gap-2">
          <AlertCircle className="w-3 h-3" />
          {locationError}
        </div>
      )}

      {/* Disconnected notice */}
      {!isConnected && (
        <div className="bg-yellow-900/30 border-b border-yellow-700/40 text-yellow-300 text-xs text-center py-1.5 px-4">
          ⚠️ Not connected to server — showing static demo data
        </div>
      )}

      {/* ── Main Grid ── */}
      <main className="p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">

        {/* Left column: Map + Allocation Decisions */}
        <section className="space-y-4">
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-blue-400" />
              Infrastructure Map
            </h2>
            <div className="h-[400px] rounded-lg overflow-hidden">
              <CityMap nodes={nodes} allocations={allocationsMap} />
            </div>
          </div>
          
          <AllocationDecisions decisions={state?.allocation_decisions} />
          
          <DisasterControls
            connected={isConnected}
            onTriggerDisaster={handleDisaster}
          />
        </section>

        {/* Right column: Metrics, Allocations, Agent log */}
        <aside className="space-y-4">
          <MetricsPanel metrics={state?.metrics} allocations={allocationsMap} />
          <ResourceAllocation allocations={state?.allocations} />
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
