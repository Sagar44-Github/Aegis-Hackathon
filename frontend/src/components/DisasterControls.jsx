// frontend/src/components/DisasterControls.jsx
import { useState, useEffect } from 'react';
import { Waves, AlertTriangle, Droplet, Flame, Zap, Settings, Gauge, Activity, Brain, Pause, Play } from 'lucide-react';
import { clsx } from 'clsx';

// ─── Disaster definitions ─────────────────────────────────────────────────────
const DISASTERS = [
  {
    id:    'earthquake',
    label: 'Earthquake',
    icon:  Waves,
    color: 'bg-amber-600 hover:bg-amber-500 border-amber-700',
  },
  {
    id:    'cyber',
    label: 'Cyber Attack',
    icon:  AlertTriangle,
    color: 'bg-red-600 hover:bg-red-500 border-red-700',
  },
  {
    id:    'flood',
    label: 'Flood',
    icon:  Droplet,
    color: 'bg-blue-600 hover:bg-blue-500 border-blue-700',
  },
  {
    id:    'aftershock',
    label: 'Aftershock',
    icon:  Activity,
    color: 'bg-orange-600 hover:bg-orange-500 border-orange-700',
  },
];

// ─── Single button ────────────────────────────────────────────────────────────
function DisasterButton({ disaster, connected, onTrigger }) {
  const [firing, setFiring] = useState(false);
  const { id, label, icon: Icon, color } = disaster;

  const handleClick = () => {
    if (!connected || firing) return;
    setFiring(true);
    onTrigger(id);
    setTimeout(() => setFiring(false), 800);
  };

  return (
    <button
      id={`disaster-btn-${id}`}
      onClick={handleClick}
      disabled={!connected}
      aria-label={`Trigger ${label}`}
      className={clsx(
        'relative flex flex-col items-center justify-center gap-1.5',
        'py-3 px-2 rounded-lg border text-white text-xs font-semibold',
        'transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40',
        !connected
          ? 'opacity-50 cursor-not-allowed bg-gray-700 border-gray-600 text-gray-400'
          : [color, 'cursor-pointer active:scale-95'],
      )}
    >
      <Icon className={clsx('w-5 h-5', firing && 'animate-spin')} />
      <span className="leading-none">{label}</span>

      {/* Firing flash */}
      {firing && (
        <span className="absolute top-1 right-1 text-[9px] font-bold bg-white/20 px-1 rounded">
          SENT
        </span>
      )}
    </button>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
/**
 * DisasterControls
 * @param {{
 *   onTriggerDisaster: (id: string) => void,
 *   connected: boolean,
 *   onToggleApiCalls: (enabled: boolean) => void,
 *   apiCallsEnabled: boolean,
 * }} props
 */
export default function DisasterControls({ onTriggerDisaster, connected, onToggleApiCalls, apiCallsEnabled, state }) {
  const [severity, setSeverity] = useState(4);
  const [speed, setSpeed] = useState(3);
  
  // Use actual supply from backend state, not hardcoded
  const currentSupply = state?.metrics?.total_supply_mw || 62;
  const [supply, setSupply] = useState(currentSupply);
  
  // Update local supply when backend state changes
  useEffect(() => {
    if (state?.metrics?.total_supply_mw) {
      setSupply(state.metrics.total_supply_mw);
    }
  }, [state?.metrics?.total_supply_mw]);

  return (
    <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm text-gray-400 flex items-center gap-2 font-medium tracking-wide">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          SCENARIO CONTROLS
        </h4>
        <div className="flex items-center gap-2">
          {/* API Control Status */}
          <span
            className={clsx(
              'text-[10px] px-2 py-0.5 rounded-full font-semibold border',
              apiCallsEnabled
                ? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                : 'bg-orange-500/20 text-orange-400 border-orange-500/30',
            )}
          >
            {apiCallsEnabled ? 'AI ON' : 'AI OFF'}
          </span>
          <span
            className={clsx(
              'text-[10px] px-2 py-0.5 rounded-full font-semibold border',
              connected
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                : 'bg-gray-700 text-gray-500 border-gray-600',
            )}
          >
            {connected ? 'ARMED' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* API Control Toggle */}
      <div className="mb-4">
        <button
          onClick={() => onToggleApiCalls(!apiCallsEnabled)}
          disabled={!connected}
          className={clsx(
            'w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-sm font-semibold transition-all duration-200',
            !connected
              ? 'opacity-50 cursor-not-allowed bg-gray-700 border-gray-600 text-gray-400'
              : apiCallsEnabled
                ? 'bg-orange-600 hover:bg-orange-500 border-orange-700 text-white'
                : 'bg-green-600 hover:bg-green-500 border-green-700 text-white',
          )}
        >
          {apiCallsEnabled ? (
            <>
              <Pause className="w-4 h-4" />
              STOP AI CALLS
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              START AI CALLS
            </>
          )}
        </button>
        <p className="text-[10px] text-gray-500 text-center mt-1">
          {apiCallsEnabled 
            ? 'AI justifications are being generated (using API quota)'
            : 'Using rule-based justifications (saving API quota)'
          }
        </p>
      </div>

      {/* Disaster Buttons */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {DISASTERS.map((d) => (
          <DisasterButton
            key={d.id}
            disaster={d}
            connected={connected}
            onTrigger={onTriggerDisaster}
          />
        ))}
      </div>

      {/* Sliders */}
      <div className="space-y-3">
        {/* Total Available Power */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-gray-400 flex items-center gap-1">
              <Gauge className="w-3 h-3" />
              Total Available Power
            </label>
            <span className="text-xs text-white font-mono">{supply} MW</span>
          </div>
          <input
            type="range"
            min="20"
            max="150"
            value={supply}
            onChange={(e) => setSupply(parseInt(e.target.value))}
            disabled={!connected}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500 disabled:opacity-50"
          />
        </div>

        {/* Disaster Severity */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-gray-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              Disaster Severity
            </label>
            <span className="text-xs text-white font-mono">{severity}/5</span>
          </div>
          <input
            type="range"
            min="1"
            max="5"
            value={severity}
            onChange={(e) => setSeverity(parseInt(e.target.value))}
            disabled={!connected}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-red-500 disabled:opacity-50"
          />
        </div>

        {/* Negotiation Speed */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-gray-400 flex items-center gap-1">
              <Activity className="w-3 h-3" />
              Negotiation Speed
            </label>
            <span className="text-xs text-white font-mono">{speed}x</span>
          </div>
          <input
            type="range"
            min="1"
            max="5"
            value={speed}
            onChange={(e) => setSpeed(parseInt(e.target.value))}
            disabled={!connected}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500 disabled:opacity-50"
          />
        </div>
      </div>

      {!connected && (
        <p className="text-[10px] text-gray-600 text-center mt-3">
          Connect to server to enable
        </p>
      )}
    </div>
  );
}
