// frontend/src/components/AnimatedCityMap.jsx
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { ArrowUp, ArrowDown, Zap } from 'lucide-react';
import { clsx } from 'clsx';
import { useEffect, useRef } from 'react';

export default function AnimatedCityMap({ nodes = {}, allocations = {}, previousAllocations = {} }) {
  const nodeEntries = Object.entries(nodes);
  const animationRefs = useRef({});

  if (nodeEntries.length === 0) {
    return (
      <div className="w-full h-full rounded-xl overflow-hidden border border-white/10 bg-gray-900 flex items-center justify-center">
        <p className="text-gray-500">No map data available</p>
      </div>
    );
  }

  // Calculate allocation change for animation
  const getAllocationChange = (nodeId) => {
    const current = allocations[nodeId]?.allocated_mw || 0;
    const previous = previousAllocations[nodeId]?.allocated_mw || 0;
    return current - previous;
  };

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-white/10 shadow-2xl relative">
      <MapContainer
        center={[50, 50]}
        zoom={7}
        scrollWheelZoom
        className="w-full h-full"
        style={{ background: '#0f172a' }}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          maxZoom={19}
        />

        {nodeEntries.map(([id, node]) => {
          const { type, location, status, capacity } = node;

          if (
            !Array.isArray(location) ||
            location.length < 2 ||
            location.some((v) => v == null || isNaN(v))
          ) return null;

          const alloc = allocations[id]?.allocated_mw || 0;
          const demand = (allocations[id]?.demand_mw) ?? capacity ?? 10;
          const change = getAllocationChange(id);
          
          const radius = Math.max(8, Math.min(25, (alloc / demand) * 20));
          const color = type === 'POWER_PLANT' ? '#3b82f6' :
                       type === 'HOSPITAL' ? '#ef4444' :
                       type === 'WATER_PLANT' ? '#06b6d4' :
                       type === 'FIRE_STATION' ? '#f97316' : '#8b5cf6';
          
          const style = status === 'OFFLINE' ? { fillOpacity: 0.3, opacity: 0.5 } :
                       status === 'DEGRADED' ? { fillOpacity: 0.6, opacity: 0.7 } :
                       { fillOpacity: 0.8, opacity: 1 };

          const usagePct = demand > 0 ? ((alloc / demand) * 100).toFixed(1) : 'N/A';

          return (
            <CircleMarker
              key={id}
              center={location}
              radius={radius}
              color="white"
              fillColor={color}
              fillOpacity={style.fillOpacity}
              opacity={style.opacity}
              weight={2}
              className={clsx(
                change > 0.5 && 'animate-pulse',
                change < -0.5 && 'animate-pulse'
              )}
            >
              <Popup>
                <div className="min-w-[200px] text-sm">
                  <p className="font-bold text-base mb-2 pb-1 border-b" style={{ color }}>
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
                        <td className={status === 'ONLINE' ? 'text-emerald-400' : status === 'DEGRADED' ? 'text-yellow-400' : 'text-red-400'}>
                          {status ?? '—'}
                        </td>
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
                      {Math.abs(change) > 0.1 && (
                        <tr>
                          <td className="pr-3 text-slate-400">Change</td>
                          <td className={clsx('font-semibold flex items-center gap-1', change > 0 ? 'text-emerald-400' : 'text-red-400')}>
                            {change > 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                            {Math.abs(change).toFixed(1)} MW
                          </td>
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

      {/* Supply Change Indicator */}
      <div className="absolute top-4 right-4 bg-gray-900/90 rounded-lg p-3 border border-gray-700">
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
          <Zap className="w-4 h-4" />
          <span>Supply Changes</span>
        </div>
        {Object.entries(allocations).map(([id, alloc]) => {
          const change = getAllocationChange(id);
          if (Math.abs(change) < 0.1) return null;
          
          return (
            <div key={id} className={clsx('text-xs flex items-center gap-1', change > 0 ? 'text-emerald-400' : 'text-red-400')}>
              {change > 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
              <span>{id}: {Math.abs(change).toFixed(1)} MW</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
