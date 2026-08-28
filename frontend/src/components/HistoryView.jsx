import React, { useState, useEffect } from 'react';

const HistoryView = ({ apiBase, token, onReviewSession, onBack, addToast }) => {
    const [sessions, setSessions] = useState([]);
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('sessions'); // 'sessions' | 'posts'

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [sessionsRes, postsRes] = await Promise.all([
                fetch(`${apiBase}/sessions`, { headers: { 'Authorization': `Bearer ${token}` } }),
                fetch(`${apiBase}/interview-experiences/mine`, { headers: { 'Authorization': `Bearer ${token}` } })
            ]);

            if (sessionsRes.ok) {
                setSessions(await sessionsRes.json());
            } else {
                addToast('Failed to fetch sessions history', 'error');
            }

            if (postsRes.ok) {
                const postsData = await postsRes.json();
                setPosts(postsData.data || []);
            } else {
                addToast('Failed to fetch posts history', 'error');
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
                const dashboardData = {
                    session_id: data.id,
                    mode: data.mode,
                    overall_score: data.overall_score,
                    topic_mastery: [],
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

    const handleDeletePost = async (id) => {
        if (!window.confirm('Are you sure you want to delete this experience?')) return;
        try {
            const res = await fetch(`${apiBase}/interview-experiences/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                addToast('Experience deleted', 'success');
                setPosts(posts.filter(p => p.id !== id));
            } else {
                addToast('Failed to delete experience', 'error');
            }
        } catch (error) {
            addToast('Network error', 'error');
        }
    };

    if (loading && sessions.length === 0 && posts.length === 0) {
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
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-4xl font-black text-white tracking-tight">Archives</h2>
                    <p className="text-zinc-400 mt-2 font-medium">Review your past semantic examinations and shared posts</p>
                </div>
                <button
                    onClick={onBack}
                    className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-sm text-zinc-300 font-bold transition-colors"
                >
                    ← Back
                </button>
            </div>

            <div className="flex gap-4 mb-8 border-b border-zinc-800 pb-2">
                <button
                    onClick={() => setActiveTab('sessions')}
                    className={`px-4 py-2 font-bold text-sm transition-all ${activeTab === 'sessions' ? 'text-white border-b-2 border-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                    My Viva Sessions
                </button>
                <button
                    onClick={() => setActiveTab('posts')}
                    className={`px-4 py-2 font-bold text-sm transition-all ${activeTab === 'posts' ? 'text-white border-b-2 border-white' : 'text-zinc-500 hover:text-zinc-300'}`}
                >
                    My Posted Experiences
                </button>
            </div>

            {activeTab === 'sessions' && (
                sessions.length === 0 ? (
                    <div className="bg-zinc-900/30 border border-zinc-800 border-dashed rounded-2xl p-12 text-center">
                        <h3 className="text-xl font-bold text-zinc-300 mb-2">No Past Sessions Found</h3>
                        <p className="text-zinc-500">You haven't completed any viva sessions yet.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {sessions.map((session) => {
                            const date = new Date(session.created_at);
                            const isGood = session.overall_score >= 75;
                            const isMedium = session.overall_score >= 45 && session.overall_score < 75;
                            
                            return (
                                <div key={session.id} className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-6 flex items-center justify-between hover:border-zinc-600 transition-colors">
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
                                                <h4 className="text-lg font-bold text-white">
                                                    {session.mode === 'comprehensive' ? 'Agentic Assessment' : 'Quick Assessment'}
                                                </h4>
                                            </div>
                                            <div className="flex items-center gap-4 text-sm font-semibold text-zinc-500">
                                                <span>{date.toLocaleDateString()}</span>
                                                <span>ID: {session.id.substring(0,8)}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleReviewClick(session.id)}
                                        disabled={loading}
                                        className="px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50"
                                    >
                                        Review Details
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                )
            )}

            {activeTab === 'posts' && (
                posts.length === 0 ? (
                    <div className="bg-zinc-900/30 border border-zinc-800 border-dashed rounded-2xl p-12 text-center">
                        <h3 className="text-xl font-bold text-zinc-300 mb-2">No Posts Found</h3>
                        <p className="text-zinc-500">You haven't shared any interview experiences yet.</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {posts.map((post) => {
                            const date = new Date(post.created_at);
                            return (
                                <div key={post.id} className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-6 flex items-center justify-between hover:border-zinc-600 transition-colors">
                                    <div>
                                        <h4 className="text-lg font-bold text-white mb-1">{post.company}</h4>
                                        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-500">
                                            <span>{post.role}</span>
                                            <span>•</span>
                                            <span>{post.level}</span>
                                            <span>•</span>
                                            <span>{date.toLocaleDateString()}</span>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDeletePost(post.id)}
                                        className="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 rounded-lg font-bold transition-colors"
                                    >
                                        Delete
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                )
            )}
        </div>
    );
};

export default HistoryView;
