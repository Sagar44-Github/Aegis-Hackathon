// frontend/src/components/NetworkTopology.jsx
import { clsx } from 'clsx';

export default function NetworkTopology({ nodes = {}, allocations = {} }) {
  const nodeEntries = Object.entries(nodes);
  
  if (nodeEntries.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">Network Topology</h3>
        <p className="text-xs text-gray-500 text-center py-4">No network data</p>
      </div>
    );
  }

  // Simple visualization - in a real app, this would use a force-directed graph
  const centerX = 150;
  const centerY = 100;
  const radius = 60;
  
  const positionedNodes = nodeEntries.map(([id, node], idx) => {
    const angle = (idx / nodeEntries.length) * 2 * Math.PI;
    return {
      id,
      type: node.type,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
      allocated: allocations[id]?.allocated_mw || 0,
      demand: allocations[id]?.demand_mw || node.capacity || 10,
    };
  });

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-3">Network Topology</h3>
      
      <div className="relative bg-gray-900 rounded-lg" style={{ height: '200px' }}>
        <svg width="100%" height="100%" viewBox="0 0 300 200">
          {/* Connections */}
          {positionedNodes.map((node, idx) => {
            const nextNode = positionedNodes[(idx + 1) % positionedNodes.length];
            const isReduced = node.allocated < node.demand * 0.7;
            return (
              <line
                key={`line-${idx}`}
                x1={node.x}
                y1={node.y}
                x2={nextNode.x}
                y2={nextNode.y}
                stroke={isReduced ? '#f59e0b' : '#22c55e'}
                strokeWidth={isReduced ? 1 : 2}
                strokeDasharray={isReduced ? '4,4' : '0'}
              />
            );
          })}
          
          {/* Nodes */}
          {positionedNodes.map((node) => {
            const satisfaction = node.demand > 0 ? node.allocated / node.demand : 1;
            const color = satisfaction >= 0.9 ? '#22c55e' : satisfaction >= 0.5 ? '#f59e0b' : '#ef4444';
            
            return (
              <g key={node.id}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={12}
                  fill={color}
                  opacity={0.8}
                />
                <text
                  x={node.x}
                  y={node.y + 4}
                  textAnchor="middle"
                  fill="white"
                  fontSize="8"
                  fontWeight="bold"
                >
                  {node.id.split('_')[0].substring(0, 3).toUpperCase()}
                </text>
              </g>
            );
          })}
        </svg>
        
        {/* Legend */}
        <div className="absolute bottom-2 left-2 flex gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-gray-400">Active link</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-gray-400">Reduced link</span>
          </div>
        </div>
      </div>
    </div>
  );
}
