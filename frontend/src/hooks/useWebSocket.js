// frontend/src/hooks/useWebSocket.js
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useWebSocket
 * @param {string} url - WebSocket server URL.
 * @returns {{ state: any, isConnected: boolean, error: string|null }}
 */
export function useWebSocket(url) {
  const [state, setState] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isMountedRef = useRef(true);
  const urlRef = useRef(url);

  // Keep urlRef current without triggering re-renders
  useEffect(() => {
    urlRef.current = url;
  }, [url]);

  const connect = useCallback(() => {
    // Don't open a second socket if one is already live
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    try {
      const ws = new WebSocket(urlRef.current);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        console.log('[WS] Connected');
        setIsConnected(true);
        setError(null);
        // Cancel any pending reconnect — we're live
        if (reconnectTimeoutRef.current !== null) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          setState(data);
        } catch (e) {
          // Non-JSON payload — store as-is
          console.error('[WS] Parse error:', e);
          setState(event.data);
        }
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;
        console.log('[WS] Disconnected. Reconnecting in 3 s…');
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      ws.onerror = (event) => {
        if (!isMountedRef.current) return;
        console.error('[WS] Error:', event);
        setError('WebSocket error — check the server and URL.');
        ws.close(); // triggers onclose → reconnect
      };
    } catch (e) {
      // Catches invalid URLs or environments without WebSocket
      console.error('[WS] Could not create socket:', e);
      setError(e.message);
    }
  }, []); // stable — reads url via urlRef, not a closure

  useEffect(() => {
    isMountedRef.current = true;

    // On url change: tear down the old socket without triggering reconnect
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.onclose = null; // suppress reconnect for this intentional close
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    if (reconnectTimeoutRef.current !== null) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    connect();

    return () => {
      isMountedRef.current = false;

      // Clear any pending reconnect timer
      if (reconnectTimeoutRef.current !== null) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Null all handlers before closing to prevent stale callbacks
      if (wsRef.current) {
        wsRef.current.onopen = null;
        wsRef.current.onmessage = null;
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url, connect]); // re-run when url changes

  return { state, isConnected, error };
}

export default useWebSocket;
