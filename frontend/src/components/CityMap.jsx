// frontend/src/components/CityMap.jsx
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { clsx } from 'clsx';
import 'leaflet/dist/leaflet.css';

// ─── Color per node type ──────────────────────────────────────────────────────
// Covers both city-infrastructure types and generic grid types
const TYPE_COLORS = {
  // City infrastructure
  power_plant:  '#fbbf24', // amber
  hospital:     '#ef4444', // red
  water_plant:  '#3b82f6', // blue
  fire_station: '#f97316', // orange
  // Grid / energy types
  solar:        '#facc15', // yellow
  wind:         '#34d399', // emerald
  hydro:        '#38bdf8', // sky
  nuclear:      '#a78bfa', // violet
  gas:          '#fb923c', // orange
  coal:         '#9ca3af', // gray
  battery:      '#f472b6', // pink
  grid:         '#60a5fa', // blue
  load:         '#f87171', // red-400
  substation:   '#e5e7eb', // gray-200
  default:      '#6b7280', // gray-500
};

// ─── Visual style per status ──────────────────────────────────────────────────
// Supports both UPPERCASE (ONLINE/DEGRADED/OFFLINE) and lowercase (active/idle/fault/offline)
const STATUS_STYLE = {
  // Uppercase variants (city model)
  online:   { fillOpacity: 1,   opacity: 1,   weight: 2, dashArray: null },
  degraded: { fillOpacity: 0.6, opacity: 0.8, weight: 2, dashArray: '5,5' },
  offline:  { fillOpacity: 0.2, opacity: 0.5, weight: 1, dashArray: '2,6' },
  // Lowercase variants (grid model)
  active:   { fillOpacity: 0.9, opacity: 1,   weight: 2, dashArray: null },
  idle:     { fillOpacity: 0.45,opacity: 0.7, weight: 2, dashArray: '4,4' },
  fault:    { fillOpacity: 0.9, opacity: 1,   weight: 2, dashArray: '6,2' },
  // Fallback
  default:  { fillOpacity: 0.6, opacity: 0.8, weight: 2, dashArray: null },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
const MIN_RADIUS = 8;
const MAX_RADIUS = 28;

function getColor(type) {
  return TYPE_COLORS[type?.toLowerCase()] ?? TYPE_COLORS.default;
}

function getStyle(status) {
  return STATUS_STYLE[status?.toLowerCase()] ?? STATUS_STYLE.default;
}

/** Scale alloc/demand ratio → circle radius (px). */
function calcRadius(alloc, demand) {
  const safeDemand = Math.max(demand, 1);
  const ratio = Math.min(alloc / safeDemand, 1);
  return MIN_RADIUS + ratio * (MAX_RADIUS - MIN_RADIUS);
}

/** Tailwind class for the status badge in the popup. */
function statusBadgeClass(status) {
  return clsx('font-semibold', {
    'text-emerald-400': ['online',   'active'].includes(status?.toLowerCase()),
    'text-yellow-400':  ['degraded', 'idle'  ].includes(status?.toLowerCase()),
    'text-red-400':     ['offline',  'fault' ].includes(status?.toLowerCase()),
  });
}

// ─── Empty State ──────────────────────────────────────────────────────────────
function EmptyMap() {
  return (
    <div className="h-full w-full bg-slate-800/60 rounded-xl flex flex-col items-center justify-center gap-2 text-slate-400 border border-white/10">
      <span className="text-3xl">🗺️</span>
      <p className="text-sm">No node data available</p>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
/**
 * CityMap
 * @param {{
 *   nodes: Record<string, { type: string, location: [number,number], status: string, capacity?: number }>,
 *   allocations: Record<string, { allocated_mw: number, demand_mw: number }>
 * }} props
 */
export default function CityMap({ nodes = {}, allocations = {} }) {
  const nodeEntries = Object.entries(nodes);

  if (nodeEntries.length === 0) return <EmptyMap />;

  // Fixed center on San Francisco for consistent view
  const center = [37.78, -122.42];

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-white/10 shadow-2xl">
      <MapContainer
        center={center}
        zoom={12}
        scrollWheelZoom
        className="w-full h-full"
        style={{ background: '#0f172a' }}
      >
        {/* Dark tile layer */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          maxZoom={19}
        />

        {nodeEntries.map(([id, node]) => {
          const { type, location, status, capacity } = node;

          // Skip nodes with missing or malformed location
          if (
            !Array.isArray(location) ||
            location.length < 2 ||
            location.some((v) => v == null || isNaN(v))
          ) return null;

          const alloc  = allocations[id]?.allocated_mw ?? 0;
          const demand = allocations[id]?.demand_mw ?? capacity ?? 10;
          const radius = calcRadius(alloc, demand);
          const color  = getColor(type);
          const style  = getStyle(status);

          const usagePct = demand > 0
            ? ((alloc / demand) * 100).toFixed(1)
            : 'N/A';

          return (
            <CircleMarker
              key={id}
              center={location}
              radius={radius}
              color="white"          // border always white for contrast
              fillColor={color}
              fillOpacity={style.fillOpacity}
              opacity={style.opacity}
              weight={style.weight}
              dashArray={style.dashArray ?? undefined}
            >
              <Popup>
                <div className="min-w-[170px] text-sm">
                  {/* Header */}
                  <p
                    className="font-bold text-base mb-2 pb-1 border-b"
                    style={{ color, borderColor: color + '55' }}
                  >
                    {id}
                  </p>

                  <table className="w-full text-xs leading-6">
                    <tbody>
                      <tr>
                        <td className="pr-3 text-slate-400">Type</td>
                        <td className="font-semibold capitalize">{type ?? '—'}</td>
                      </tr>
                      <tr>
                        <td className="pr-3 text-slate-400">Status</td>
                        <td className={statusBadgeClass(status)}>{status ?? '—'}</td>
                      </tr>
                      <tr>
                        <td className="pr-3 text-slate-400">Power</td>
                        <td className="font-semibold">
                          {alloc.toFixed(1)} MW / {demand.toFixed(1)} MW
                        </td>
                      </tr>
                      <tr>
                        <td className="pr-3 text-slate-400">Usage</td>
                        <td className="font-semibold">{usagePct}%</td>
                      </tr>
                      {capacity != null && (
                        <tr>
                          <td className="pr-3 text-slate-400">Capacity</td>
                          <td className="font-semibold">{capacity} MW</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
