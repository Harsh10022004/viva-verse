import React, { useState, useEffect } from 'react';

const HistoryView = ({ apiBase, token, onReviewSession, onBack, addToast }) => {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSessions();
    }, []);

    const fetchSessions = async () => {
        try {
            const response = await fetch(`${apiBase}/sessions`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                setSessions(data);
            } else {
                addToast('Failed to fetch history', 'error');
            }
        } catch (error) {
            addToast('Network error fetching history', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleReviewClick = async (sessionId) => {
        try {
            setLoading(true);
            const response = await fetch(`${apiBase}/sessions/${sessionId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const data = await response.json();
                // We re-format it back into the structure expected by Dashboard
                const dashboardData = {
                    session_id: data.id,
                    mode: data.mode,
                    overall_score: data.overall_score,
                    topic_mastery: [], // Not persisted fully in simplified model, dashboard handles gracefully if missing
                    recall_heatmap: data.recall_heatmap,
                    areas_for_improvement: "Review past performance from history.",
                    total_questions: Object.keys(data.answers || {}).length,
                    total_answered: Object.keys(data.answers || {}).length,
                    knowledge_map: data.knowledge_map
                };
                onReviewSession(dashboardData);
            } else {
                addToast('Failed to fetch session details', 'error');
            }
        } catch (error) {
            addToast('Network error loading session', 'error');
        } finally {
            setLoading(false);
        }
    };

    if (loading && sessions.length === 0) {
        return (
            <div className="min-h-[80vh] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-gray-400 font-medium tracking-wide">Retrieving Archives...</span>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto px-6 py-12">
            <div className="flex items-center justify-between mb-12">
                <div>
                    <h2 className="text-3xl font-bold text-gray-100 tracking-tight">Personal History</h2>
                    <p className="text-gray-400 mt-2">Review your past semantic examinations</p>
                </div>
                <button
                    onClick={onBack}
                    className="px-4 py-2 bg-surface-800 hover:bg-surface-700 border border-surface-600 rounded-lg text-sm text-gray-300 font-medium transition-colors"
                >
                    Back to Upload
                </button>
            </div>

            {sessions.length === 0 ? (
                <div className="bg-surface-800/30 border border-surface-700 border-dashed rounded-2xl p-12 text-center">
                    <div className="w-16 h-16 mx-auto bg-surface-800 rounded-full flex items-center justify-center mb-4">
                        <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-gray-200 mb-2">No Past Sessions Found</h3>
                    <p className="text-gray-400">You haven't completed any viva sessions yet.</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {sessions.map((session) => {
                        const date = new Date(session.created_at);
                        const isGood = session.overall_score >= 75;
                        const isMedium = session.overall_score >= 45 && session.overall_score < 75;
                        
                        return (
                            <div key={session.id} className="bg-surface-800/50 backdrop-blur-md border border-surface-700 rounded-xl p-6 flex items-center justify-between hover:border-surface-500 transition-colors">
                                <div className="flex items-center gap-6">
                                    <div className={`w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold
                                        ${isGood ? 'bg-green-500/10 text-green-400 border border-green-500/20' :
                                          isMedium ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20' :
                                          'bg-red-500/10 text-red-400 border border-red-500/20'}`}
                                    >
                                        {Math.round(session.overall_score || 0)}%
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-3 mb-1">
                                            <h4 className="text-lg font-semibold text-gray-200">
                                                {session.mode === 'comprehensive' ? 'Agentic Assessment' : 'Quick Assessment'}
                                            </h4>
                                        </div>
                                        <div className="flex items-center gap-4 text-sm text-gray-400">
                                            <span className="flex items-center gap-1.5">
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                                </svg>
                                                {date.toLocaleDateString()} at {date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                                                </svg>
                                                ID: {session.id.substring(0,8)}...
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleReviewClick(session.id)}
                                    disabled={loading}
                                    className="px-5 py-2.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 rounded-lg font-medium transition-colors disabled:opacity-50"
                                >
                                    Review Details
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default HistoryView;
