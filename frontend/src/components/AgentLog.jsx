// frontend/src/components/AgentLog.jsx
import { clsx } from 'clsx';
import { Terminal } from 'lucide-react';

// ─── Constants ────────────────────────────────────────────────────────────────
const MAX_ITEMS = 20;

// ─── Severity detection (broader regex from their version) ────────────────────
function getSeverity(message = '') {
  if (/critical|imminent|failure/i.test(message)) return 'critical';
  if (/high|urgent|generator/i.test(message))     return 'high';
  return 'normal';
}

const SEVERITY = {
  critical: {
    row:   'border-l-2 border-red-500 bg-red-900/20',
    badge: 'text-red-400',
    dot:   'bg-red-500',
  },
  high: {
    row:   'border-l-2 border-yellow-500 bg-yellow-900/20',
    badge: 'text-yellow-400',
    dot:   'bg-yellow-400',
  },
  normal: {
    row:   'border-l-2 border-green-500 bg-green-900/10',
    badge: 'text-green-400',
    dot:   'bg-green-400',
  },
};

// ─── Timestamp helper ─────────────────────────────────────────────────────────
// Use entry's own timestamp when available; fall back to current time (their approach)
function formatTs(entry) {
  const raw = typeof entry === 'object' ? (entry.timestamp ?? entry.ts ?? null) : null;
  try {
    const d = raw != null ? new Date(raw) : new Date();
    return isNaN(d.getTime()) ? new Date().toLocaleTimeString() : d.toLocaleTimeString();
  } catch {
    return new Date().toLocaleTimeString();
  }
}

// ─── Single log row ───────────────────────────────────────────────────────────
function LogRow({ entry, index }) {
  const message  = typeof entry === 'string' ? entry : (entry.message ?? String(entry));
  const severity = getSeverity(message);
  const s        = SEVERITY[severity];
  const isNewest = index === 0;

  return (
    <div
      className={clsx(
        'px-2 py-1.5 rounded-r text-gray-300 whitespace-pre-wrap',
        'flex items-start gap-2',
        s.row,
      )}
    >
      {/* Live pulse dot (only newest) */}
      <span className="mt-1 shrink-0">
        <span
          className={clsx('block w-1.5 h-1.5 rounded-full', s.dot, isNewest && 'animate-pulse')}
        />
      </span>

      {/* Timestamp + message */}
      <span className="font-mono text-xs leading-snug">
        <span className="text-gray-500 select-none">[{formatTs(entry)}]</span>{' '}
        <span className={clsx(severity !== 'normal' && s.badge)}>{message}</span>
      </span>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
/**
 * AgentLog
 * @param {{ logs: Array<string | { message: string, timestamp?: number|string }> }} props
 */
export default function AgentLog({ logs = [] }) {
  const visible = [...logs].reverse().slice(0, MAX_ITEMS);

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 flex flex-col h-64">

      {/* Header — terminal aesthetic */}
      <div className="px-3 py-2 border-b border-gray-700 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-gray-400">
          <Terminal className="w-4 h-4" />
          <span className="font-mono text-sm tracking-wide">AGENT NEGOTIATION LOG</span>
        </div>
        {logs.length > 0 && (
          <span className="font-mono text-[10px] text-gray-600 tabular-nums">
            {Math.min(logs.length, MAX_ITEMS)}/{logs.length}
          </span>
        )}
      </div>

      {/* Scrollable log list */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {visible.length === 0 ? (
          <p className="font-mono text-xs text-gray-500 text-center py-4">
            Waiting for agent bids…
          </p>
        ) : (
          visible.map((entry, i) => (
            <LogRow
              key={typeof entry === 'object' ? (entry.id ?? i) : i}
              entry={entry}
              index={i}
            />
          ))
        )}
      </div>

    </div>
  );
}
