// frontend/src/components/DisasterControls.jsx
import { useState } from 'react';
import { Waves, AlertTriangle, Droplet } from 'lucide-react';
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
 * }} props
 */
export default function DisasterControls({ onTriggerDisaster, connected }) {
  return (
    <div className="bg-gray-800 p-4 rounded-lg border border-gray-700">

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm text-gray-400 flex items-center gap-2 font-medium tracking-wide">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          DISASTER INJECTION
        </h4>
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

      {/* Buttons */}
      <div className="grid grid-cols-3 gap-2">
        {DISASTERS.map((d) => (
          <DisasterButton
            key={d.id}
            disaster={d}
            connected={connected}
            onTrigger={onTriggerDisaster}
          />
        ))}
      </div>

      {!connected && (
        <p className="text-[10px] text-gray-600 text-center mt-2">
          Connect to server to enable
        </p>
      )}
    </div>
  );
}
