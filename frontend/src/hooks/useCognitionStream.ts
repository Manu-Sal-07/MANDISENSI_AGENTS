'use client';
import { useEffect, useRef, useState, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getWsUrl = (apiUrl: string): string => {
    try {
        const url = new URL(apiUrl);
        url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        return url.toString().replace(/\/$/, '');
    } catch {
        return apiUrl.replace(/^http/, 'ws');
    }
};

const WS_API = getWsUrl(API);

export function useCognitionStream() {
    const [latestUpdate, setLatestUpdate] = useState<any>(null);
    const [status, setStatus] = useState<'CONNECTING' | 'LIVE' | 'DISCONNECTED'>('CONNECTING');
    const [memories, setMemories] = useState<any[]>([]);
    const [systemHealth, setSystemHealth] = useState<any>(null);
    const [auditLog, setAuditLog] = useState<any[]>([]);
    const [allStates, setAllStates] = useState<any[]>([]);
    const [cognitionEvents, setCognitionEvents] = useState<any[]>([]);
    const [queryResult, setQueryResult] = useState<any>(null);
    const [isQuerying, setIsQuerying] = useState(false);
    const [quickHealth, setQuickHealth] = useState<any>(null);
    const [allDirectives, setAllDirectives] = useState<any>(null);
    const [isSeeding, setIsSeeding] = useState(false);
    const ws = useRef<WebSocket | null>(null);
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    const addEvent = useCallback((msg: string, type: string = 'info') => {
        setCognitionEvents(prev => [{
            id: Date.now() + Math.random(),
            timestamp: new Date().toISOString(),
            message: msg,
            type
        }, ...prev].slice(0, 80));
    }, []);

    const fetchHealth = useCallback(async () => {
        try {
            const res = await fetch(`${API}/v1/health`);
            if (res.ok) setSystemHealth(await res.json());
        } catch {}
    }, []);

    const fetchQuickHealth = useCallback(async () => {
        try {
            const res = await fetch(`${API}/v1/cognition/quick-health`);
            if (res.ok) setQuickHealth(await res.json());
        } catch {}
    }, []);

    const fetchAllStates = useCallback(async () => {
        try {
            const res = await fetch(`${API}/v1/cognition/states`);
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data) && data.length > 0) {
                    setAllStates(data);
                }
            }
        } catch {}
    }, []);

    const fetchAllDirectives = useCallback(async () => {
        try {
            const res = await fetch(`${API}/v1/cognition/directives/all`);
            if (res.ok) {
                const data = await res.json();
                if (data?.states?.length > 0) {
                    setAllDirectives(data);
                    setAllStates(data.states);
                }
            }
        } catch {}
    }, []);

    const fetchAuditLog = useCallback(async () => {
        try {
            const res = await fetch(`${API}/v1/deployment/audit`);
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data)) setAuditLog(data);
                else if (data?.actions) setAuditLog(data.actions);
            }
        } catch {}
    }, []);

    const fetchMemories = useCallback(async () => {
        try {
            const res = await fetch(`${API}/v1/cognition/memories`);
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data)) setMemories(data);
            }
        } catch {}
    }, []);

    const seedCognition = useCallback(async () => {
        setIsSeeding(true);
        addEvent('Seeding cognition intelligence for all markets...', 'system');
        try {
            const res = await fetch(`${API}/v1/cognition/seed`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                addEvent(`Seed complete: ${data.seeded} states generated across ${data.results?.length || 0} markets`, 'success');
                setTimeout(() => {
                    fetchAllStates();
                    fetchAllDirectives();
                    fetchAuditLog();
                    fetchMemories();
                }, 1000);
            }
        } catch (e) {
            addEvent('Seed request failed — backend may be starting up', 'error');
        } finally {
            setIsSeeding(false);
        }
    }, [addEvent, fetchAllStates, fetchAllDirectives, fetchAuditLog, fetchMemories]);

    const refreshAll = useCallback(() => {
        fetchHealth();
        fetchQuickHealth();
        fetchAllStates();
        fetchAllDirectives();
        fetchAuditLog();
        fetchMemories();
    }, [fetchHealth, fetchQuickHealth, fetchAllStates, fetchAllDirectives, fetchAuditLog, fetchMemories]);

    // WebSocket connection
    useEffect(() => {
        const connect = () => {
            try {
                const socket = new WebSocket(`${WS_API}/v1/ws/cognition`);
                ws.current = socket;

                socket.onopen = () => {
                    setStatus('LIVE');
                    addEvent('TraderOS Cognition Stream: SYNCHRONIZED', 'success');
                    refreshAll();
                };

                socket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'COGNITION_EVOLVED') {
                            setLatestUpdate(data);
                            addEvent(`Cognition evolved: ${data.commodity?.toUpperCase()} @ ${data.mandi_id} — ${data.state?.directives?.[0]?.primary_directive || 'Updated'}`, 'update');
                            fetchAllStates();
                            fetchAuditLog();
                        } else if (data.type === 'SIMULATION_EVOLVED') {
                            addEvent(`Simulation: ${data.scenario_type} for ${data.commodity?.toUpperCase()}`, 'simulation');
                        } else if (data.type === 'PONG') {
                            // heartbeat ack
                        }
                    } catch {}
                };

                socket.onclose = () => {
                    setStatus('DISCONNECTED');
                    addEvent('Cognition stream interrupted — reconnecting...', 'warning');
                    setTimeout(connect, 4000);
                };

                socket.onerror = () => socket.close();
            } catch {
                setStatus('DISCONNECTED');
                setTimeout(connect, 4000);
            }
        };

        connect();

        return () => {
            ws.current?.close();
        };
    }, []);  // eslint-disable-line react-hooks/exhaustive-deps

    // Heartbeat ping
    useEffect(() => {
        const heartbeat = setInterval(() => {
            if (ws.current?.readyState === WebSocket.OPEN) {
                ws.current.send(JSON.stringify({ type: 'PING' }));
            }
        }, 30000);
        return () => clearInterval(heartbeat);
    }, []);

    // Polling — refresh every 45s for freshness even without WS events
    useEffect(() => {
        refreshAll();
        pollRef.current = setInterval(refreshAll, 45000);
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [refreshAll]);

    // Query console
    const submitQuery = useCallback(async (query: string) => {
        setIsQuerying(true);
        setQueryResult(null);
        addEvent(`Query submitted: "${query}"`, 'query');
        try {
            const res = await fetch(`${API}/v1/query/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            if (res.ok) {
                const data = await res.json();
                setQueryResult(data);
                addEvent(`Query resolved: ${data.decision} — ${data.summary?.slice(0, 60)}...`, 'success');
            } else {
                const err = await res.json().catch(() => ({}));
                addEvent(`Query failed: ${err.detail || res.statusText}`, 'error');
            }
        } catch (e) {
            addEvent('Query engine unreachable', 'error');
        } finally {
            setIsQuerying(false);
        }
    }, [addEvent]);

    const triggerRefresh = useCallback(() => {
        addEvent('Manual cognition refresh triggered...', 'system');
        fetch(`${API}/v1/cognition/refresh`, { method: 'POST' }).catch(() => {});
        setTimeout(refreshAll, 3000);
    }, [addEvent, refreshAll]);

    return {
        latestUpdate, status, memories, systemHealth,
        auditLog, allStates, cognitionEvents, queryResult,
        isQuerying, isSeeding, quickHealth, allDirectives,
        submitQuery, seedCognition, triggerRefresh, refreshAll
    };
}
