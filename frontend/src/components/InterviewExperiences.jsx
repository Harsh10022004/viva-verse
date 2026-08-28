import React, { useState, useEffect } from 'react';
import axios from 'axios';

const InterviewExperiences = ({ apiBase, token, user, addToast, onBack, onStartMock }) => {
    const [view, setView] = useState('list'); // list, create, detail, search
    const [experiences, setExperiences] = useState([]);
    const [searchResults, setSearchResults] = useState([]);
    const [loading, setLoading] = useState(false);
    
    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [filters, setFilters] = useState({ company: '', role: '', level: '', source: 'both' });
    const [topK, setTopK] = useState('');
    
    // Pagination state
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    
    // Form state
    const [formData, setFormData] = useState({
        company: '', role: '', level: '', interview_date: '', overall_experience: '', source: 'platform', topics: '',
        rounds: [{ round_name: '', notes: '', questions: [{ question_text: '' }] }]
    });
    
    const [activeExp, setActiveExp] = useState(null);
    const [aiSummary, setAiSummary] = useState(null);
    const [generatingSummary, setGeneratingSummary] = useState(false);

    // New features state
    const [insightsApiKey, setInsightsApiKey] = useState('');
    
    const [showSubModal, setShowSubModal] = useState(false);
    const [subEmail, setSubEmail] = useState('');
    const [subWhatsapp, setSubWhatsapp] = useState('');
    const [subscribing, setSubscribing] = useState(false);
    
    const [showMockModal, setShowMockModal] = useState(false);
    const [mockApiKey, setMockApiKey] = useState('');
    const [mockJd, setMockJd] = useState('');
    const [mockResume, setMockResume] = useState('');
    const [startingMock, setStartingMock] = useState(false);

    const authHeaders = token ? { headers: { Authorization: `Bearer ${token}` } } : {};

    useEffect(() => {
        if (view === 'list') {
            fetchExperiences(1);
        }
    }, [view]);

    const fetchExperiences = async (pageNum = 1) => {
        setLoading(true);
        try {
            const res = await axios.get(`${apiBase}/interview-experiences?page=${pageNum}&page_size=24`, authHeaders);
            if (res.data && Array.isArray(res.data.data)) {
                if (pageNum === 1) {
                    setExperiences(res.data.data);
                } else {
                    setExperiences(prev => [...prev, ...res.data.data]);
                }
                setHasMore(res.data.data.length === 24 && res.data.total > pageNum * 24);
                setPage(pageNum);
            } else {
                if (pageNum === 1) setExperiences([]);
            }
        } catch (err) {
            addToast('Failed to fetch experiences', 'error');
            if (pageNum === 1) setExperiences([]);
        }
        setLoading(false);
    };

    const handleSearch = async (e) => {
        if (e) e.preventDefault();
        if (!searchQuery.trim() && !filters.company && !filters.role && filters.source === 'both') {
            setView('list');
            return;
        }
        
        setLoading(true);
        setView('search');
        try {
            const reqFilters = {};
            if (filters.company) reqFilters.company = filters.company;
            if (filters.role) reqFilters.role = filters.role;
            if (filters.level) reqFilters.level = filters.level;
            if (filters.source && filters.source !== 'both') reqFilters.source = filters.source;
            if (topK && !isNaN(parseInt(topK))) reqFilters.top_k = parseInt(topK);

            const res = await axios.post(`${apiBase}/interview-experiences/search`, {
                query: searchQuery,
                ...reqFilters
            }, authHeaders);
            setSearchResults(res.data.results);
            setAiSummary(null); // Reset summary on new search
        } catch (err) {
            addToast('Search failed', 'error');
        }
        setLoading(false);
    };

    const generateInsights = async () => {
        if (searchResults.length === 0) return;
        setGeneratingSummary(true);
        try {
            const expIds = searchResults.map(r => r.experience_id);
            // Remove duplicates
            const uniqueIds = [...new Set(expIds)].slice(0, 5); // Limit to top 5 for summary
            
            const res = await axios.post(`${apiBase}/interview-experiences/summary`, {
                experience_ids: uniqueIds,
                api_key: insightsApiKey || null
            }, authHeaders);
            
            setAiSummary(res.data.summary);
            addToast('AI Insights generated successfully!', 'success');
        } catch (err) {
            addToast('Failed to generate insights', 'error');
        }
        setGeneratingSummary(false);
    };

    const viewDetails = async (id) => {
        setLoading(true);
        try {
            const res = await axios.get(`${apiBase}/interview-experiences/${id}`, authHeaders);
            setActiveExp(res.data);
            setView('detail');
        } catch (err) {
            addToast('Failed to load details', 'error');
        }
        setLoading(false);
    };

    const deleteExperience = async (id) => {
        if (!window.confirm('Are you sure you want to delete this experience?')) return;
        try {
            await axios.delete(`${apiBase}/interview-experiences/${id}`, authHeaders);
            addToast('Experience deleted', 'success');
            if (view === 'detail') setView('list');
            else fetchExperiences();
        } catch (err) {
            addToast('Failed to delete', 'error');
        }
    };

    const handleCreateSubmit = async (e) => {
        e.preventDefault();
        if (!user) {
            addToast('You must be logged in to post.', 'error');
            return;
        }
        setLoading(true);
        try {
            await axios.post(`${apiBase}/interview-experiences`, formData, authHeaders);
            addToast('Experience posted successfully!', 'success');
            setView('list');
            setFormData({
                company: '', role: '', level: '', interview_date: '', overall_experience: '', source: 'platform', topics: '',
                rounds: [{ round_name: '', notes: '', questions: [{ question_text: '' }] }]
            });
        } catch (err) {
            addToast('Failed to post experience', 'error');
        }
        setLoading(false);
    };

    // Form helpers
    const updateRound = (rIdx, field, val) => {
        const newRounds = [...formData.rounds];
        newRounds[rIdx][field] = val;
        setFormData({ ...formData, rounds: newRounds });
    };
    const addRound = () => setFormData({ ...formData, rounds: [...formData.rounds, { round_name: '', notes: '', questions: [{ question_text: '' }] }] });
    const addQuestion = (rIdx) => {
        const newRounds = [...formData.rounds];
        newRounds[rIdx].questions.push({ question_text: '' });
        setFormData({ ...formData, rounds: newRounds });
    };
    const updateQuestion = (rIdx, qIdx, val) => {
        const newRounds = [...formData.rounds];
        newRounds[rIdx].questions[qIdx].question_text = val;
        setFormData({ ...formData, rounds: newRounds });
    };

    const handleSubscribe = async (e) => {
        e.preventDefault();
        if (!subEmail && !subWhatsapp) {
            addToast('Please provide an email or WhatsApp number.', 'error');
            return;
        }
        setSubscribing(true);
        try {
            await axios.post(`${apiBase}/interview-experiences/subscribe`, {
                query: searchQuery,
                email: subEmail || null,
                whatsapp: subWhatsapp || null
            }, authHeaders);
            addToast('Successfully subscribed to alerts!', 'success');
            setShowSubModal(false);
            setSubEmail('');
            setSubWhatsapp('');
        } catch (err) {
            addToast('Failed to subscribe to alerts.', 'error');
        }
        setSubscribing(false);
    };

    const handleLaunchMock = async (e) => {
        e.preventDefault();
        if (!mockApiKey) {
            addToast('API Key is required to launch the AI.', 'error');
            return;
        }
        
        setStartingMock(true);
        try {
            // Get the IDs of the Top K search results
            const expIds = searchResults.map(r => r.id).slice(0, 10);
            if (expIds.length === 0) {
                addToast('No experiences to base the mock interview on.', 'warning');
                setStartingMock(false);
                return;
            }
            
            addToast('Generating strict questions based on Top K results...', 'info');
            const res = await axios.post(`${apiBase}/coach/generate-topk-questions`, {
                provider: 'openai',
                api_key: mockApiKey,
                model: 'gpt-4o-mini',
                experience_ids: expIds,
                jd: mockJd || null,
                resume: mockResume || null
            }, authHeaders);
            
            const generatedQuestions = res.data.questions;
            
            setShowMockModal(false);
            
            // Invoke the coach terminal prop in App.jsx
            if (onStartMock) {
                onStartMock({
                    provider: 'openai',
                    api_key: mockApiKey,
                    model: 'gpt-4o-mini',
                    mode: 'topk-rubric',
                    role: 'Candidate',
                    level: 'Target Level',
                    jd: mockJd,
                    resume: mockResume,
                    questions: generatedQuestions,
                    initial_tokens: 0
                });
            }
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to initialize mock interview.', 'error');
        }
        setStartingMock(false);
    };

    return (
        <div className="relative min-h-screen">
            {/* Hero Section */}
            {(view === 'list' || view === 'search') && (
                <div className="relative pt-20 pb-32 overflow-hidden border-b border-white/5">
                    <div className="absolute inset-0 bg-gradient-to-b from-blue-900/10 via-zinc-950 to-zinc-950" />
                    <div className="max-w-7xl mx-auto px-6 relative z-10 text-center">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold text-zinc-300 mb-8 fade-in-up">
                            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                            AI-Powered Interview Intelligence
                        </div>
                        <h1 className="text-5xl md:text-7xl font-black text-white tracking-tight mb-6 fade-in-up" style={{animationDelay: '100ms'}}>
                            Don't just read.<br />
                            <span className="gradient-text">Dominate your interviews.</span>
                        </h1>
                        <p className="max-w-2xl mx-auto text-lg text-zinc-400 mb-12 fade-in-up" style={{animationDelay: '200ms'}}>
                            Glassdoor is outdated. Leetcode Discuss is unorganized. <br/>
                            Welcome to the world's first hybrid-search experience repository with instant AI Mock Interviews and Contextual Summaries.
                        </p>
                        
                        {/* Search Bar - Center Stage */}
                        <div className="max-w-4xl mx-auto fade-in-up" style={{animationDelay: '300ms'}}>
                            <div className="glass-panel p-2 flex flex-wrap md:flex-nowrap gap-2 items-center">
                                <div className="flex-1 min-w-[250px] relative">
                                    <svg className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                                    <input 
                                        type="text" 
                                        placeholder="Search topics, questions, or general vibes..."
                                        value={searchQuery}
                                        onChange={e => setSearchQuery(e.target.value)}
                                        onKeyDown={e => e.key === 'Enter' && handleSearch()}
                                        className="w-full bg-transparent border-none px-12 py-4 text-white placeholder-zinc-500 focus:outline-none font-medium"
                                    />
                                </div>
                                <div className="h-8 w-px bg-white/10 hidden md:block"></div>
                                <input 
                                    type="text" placeholder="Company" value={filters.company} onChange={e => setFilters({...filters, company: e.target.value})}
                                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                                    className="w-full md:w-32 bg-transparent border-none px-4 py-4 text-white placeholder-zinc-500 focus:outline-none font-medium"
                                />
                                <div className="h-8 w-px bg-white/10 hidden md:block"></div>
                                <select 
                                    value={filters.source} 
                                    onChange={e => setFilters({...filters, source: e.target.value})}
                                    className="w-full md:w-32 bg-transparent border-none px-4 py-4 text-zinc-300 focus:outline-none font-medium [&>option]:bg-zinc-900"
                                >
                                    <option value="both">All Sources</option>
                                    <option value="platform">Native</option>
                                    <option value="ingested">Aggregated</option>
                                </select>
                                <div className="h-8 w-px bg-white/10 hidden md:block"></div>
                                <input 
                                    type="number" placeholder="Top K" value={topK} onChange={e => setTopK(e.target.value)}
                                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                                    className="w-full md:w-24 bg-transparent border-none px-4 py-4 text-white placeholder-zinc-500 focus:outline-none font-medium"
                                />
                                <button onClick={handleSearch} className="w-full md:w-auto btn-primary ml-auto py-4 px-8">
                                    {loading ? 'Searching...' : 'Explore'}
                                </button>
                            </div>
                            
                            {searchQuery.trim().length > 0 && (
                                <div className="mt-4 flex justify-center">
                                    <button 
                                        onClick={() => setShowSubModal(true)} 
                                        className="text-xs font-bold px-4 py-2 bg-blue-900/20 text-blue-400 border border-blue-500/20 rounded-lg hover:bg-blue-900/40 transition flex items-center gap-2"
                                    >
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
                                        Subscribe to "{searchQuery}" Alerts
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="mt-8 flex items-center justify-center gap-6 text-sm font-semibold text-zinc-500 fade-in-up" style={{animationDelay: '400ms'}}>
                            <div className="flex items-center gap-2"><svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg> Vector Semantic Search</div>
                            <div className="flex items-center gap-2"><svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg> BM25 Lexical Ranking</div>
                            <div className="flex items-center gap-2"><svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg> RRF Fusion</div>
                        </div>
                    </div>
                </div>
            )}

            <div className="max-w-7xl mx-auto px-6 py-12 relative z-10">
                {/* Header for non-list views */}
                {view !== 'list' && view !== 'search' && (
                    <div className="flex items-center justify-between mb-12">
                        <button onClick={() => setView('list')} className="text-zinc-400 font-bold hover:text-white transition flex items-center gap-2">
                            ← Back to Hub
                        </button>
                    </div>
                )}

                {/* Actions Toolbar */}
                {(view === 'list' || view === 'search') && (
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-4">
                            <h3 className="text-2xl font-black text-white">{view === 'search' ? 'Search Results' : 'Recent Submissions'}</h3>
                            {view === 'search' && searchResults.length > 0 && (
                                <button 
                                    onClick={() => setShowMockModal(true)}
                                    className="ml-4 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg transition shadow-[0_0_15px_rgba(147,51,234,0.3)] flex items-center gap-2"
                                >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    Launch AI Mock Interview
                                </button>
                            )}
                        </div>
                        <button 
                            onClick={() => {
                                if(!user) { addToast('Please login to post.', 'error'); return; }
                                setView('create')
                            }}
                            className="btn-glow"
                        >
                            + Share Experience
                        </button>
                    </div>
                )}

                {/* Main Content Area */}
                {loading && <div className="text-center py-20 text-zinc-500 font-bold animate-pulse text-xl">Analyzing Data Streams...</div>}

                {!loading && view === 'list' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {experiences.map(exp => (
                            <div key={exp.id} className="premium-card p-6 cursor-pointer group" onClick={() => viewDetails(exp.id)}>
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-xl font-bold text-white mb-1 group-hover:text-blue-400 transition-colors">{exp.company}</h3>
                                        <p className="text-zinc-400 font-medium text-sm">{exp.role} · {exp.level}</p>
                                    </div>
                                    <span className="text-xs px-2 py-1 bg-white/5 border border-white/10 rounded-md text-zinc-400 font-bold">{new Date(exp.created_at).toLocaleDateString()}</span>
                                </div>
                                {exp.topics && (
                                    <div className="mt-4 flex flex-wrap gap-2">
                                        {exp.topics.split(',').slice(0,3).map((t, i) => (
                                            <span key={i} className="text-[10px] uppercase tracking-wider font-bold px-2 py-1 bg-blue-900/20 text-blue-400 rounded border border-blue-500/20">{t.trim()}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                        {experiences.length === 0 && <div className="col-span-full text-center py-12 text-zinc-500 font-medium">The vault is empty. Be the first to share.</div>}
                    </div>
                )}
                
                {!loading && view === 'list' && hasMore && experiences.length > 0 && (
                    <div className="mt-12 flex justify-center">
                        <button 
                            onClick={() => fetchExperiences(page + 1)}
                            className="btn-glow px-8"
                        >
                            Load More Experiences
                        </button>
                    </div>
                )}

                {!loading && view === 'search' && (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                        <div className="lg:col-span-8 space-y-6">
                            {searchResults.map((res, i) => (
                                <div key={res.id || i} className="premium-card p-6">
                                    <div className="flex flex-wrap gap-2 mb-4">
                                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                                            RRF Score: {res.rrf_score.toFixed(3)}
                                        </span>
                                        {res.bm25_score !== null && res.bm25_score !== undefined && (
                                            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-blue-900/30 text-blue-400 border border-blue-800/50">
                                                Lexical: {Number(res.bm25_score).toFixed(3)}
                                            </span>
                                        )}
                                        {res.vector_score !== null && res.vector_score !== undefined && (
                                            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-purple-900/30 text-purple-400 border border-purple-800/50">
                                                Semantic: {Number(res.vector_score).toFixed(3)}
                                            </span>
                                        )}
                                    </div>
                                    <h4 className="text-xl font-bold text-white mb-4 leading-relaxed">{res.snippet}</h4>
                                    <div className="flex items-center justify-between border-t border-white/10 pt-4">
                                        <div className="flex items-center gap-3 text-sm font-semibold text-zinc-400">
                                            <span className="text-white">{res.company}</span>
                                            <span className="w-1 h-1 rounded-full bg-zinc-600"></span>
                                            <span>{res.role}</span>
                                        </div>
                                        <button onClick={() => viewDetails(res.id)} className="text-sm font-bold text-blue-400 hover:text-blue-300 transition">
                                            Read Full Log →
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {searchResults.length === 0 && <div className="text-center py-12 text-zinc-500 font-medium">No records match your query.</div>}
                        </div>
                        
                        {/* AI Insights Sidebar */}
                        <div className="lg:col-span-4">
                            <div className="glass-panel p-6 sticky top-24">
                                <h3 className="text-lg font-black text-white mb-4 flex items-center gap-2">
                                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                    AI Insights Generator
                                </h3>
                                <p className="text-sm text-zinc-400 mb-6 leading-relaxed">
                                    Instantly summarize the patterns, frequent topics, and difficulty from the search results on the left.
                                </p>
                                
                                {!aiSummary ? (
                                    <div className="space-y-4">
                                        <input 
                                            type="password"
                                            placeholder="OpenAI API Key (Optional BYOK)"
                                            className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500 transition"
                                            value={insightsApiKey}
                                            onChange={(e) => setInsightsApiKey(e.target.value)}
                                        />
                                        <button 
                                            onClick={generateInsights}
                                            disabled={generatingSummary || searchResults.length === 0}
                                            className="w-full btn-primary py-3 disabled:opacity-50"
                                        >
                                            {generatingSummary ? 'Synthesizing...' : 'Generate Summary'}
                                        </button>
                                    </div>
                                ) : (
                                    <div className="bg-zinc-900/80 rounded-xl p-4 border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
                                        <div className="prose prose-invert prose-sm max-w-none text-zinc-300">
                                            {aiSummary.split('\n').map((line, i) => (
                                                <p key={i} className="mb-2">{line.replace(/\*/g, '')}</p>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {!loading && view === 'detail' && activeExp && (
                    <div className="max-w-4xl mx-auto">
                        <div className="glass-panel p-8 md:p-12">
                            <div className="flex justify-between items-start mb-8 pb-8 border-b border-white/10">
                                <div>
                                    <div className="flex items-center gap-3 mb-2">
                                        <h2 className="text-4xl font-black text-white tracking-tight">{activeExp.company}</h2>
                                        {activeExp.source === 'ingested' && (
                                            <span className="px-2 py-1 bg-purple-900/30 text-purple-400 border border-purple-500/30 text-[10px] uppercase font-bold tracking-widest rounded-md">Aggregated</span>
                                        )}
                                    </div>
                                    <p className="text-xl text-zinc-400 font-medium">{activeExp.role} <span className="mx-2 text-zinc-700">|</span> {activeExp.level}</p>
                                </div>
                                {user && activeExp.user_id === user.id && (
                                    <button onClick={() => deleteExperience(activeExp.id)} className="px-4 py-2 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 font-bold rounded-lg transition border border-rose-500/20">
                                        Delete Post
                                    </button>
                                )}
                            </div>

                            {activeExp.overall_experience && (
                                <div className="mb-12">
                                    <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-4">Overall Experience</h3>
                                    <div className="bg-white/5 border border-white/10 rounded-xl p-6 text-zinc-300 leading-relaxed whitespace-pre-wrap">
                                        {activeExp.overall_experience}
                                    </div>
                                </div>
                            )}

                            <div>
                                <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-6">Interview Rounds Breakdown</h3>
                                <div className="space-y-6">
                                    {activeExp.rounds.map((r, i) => (
                                        <div key={r.id} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 relative overflow-hidden">
                                            <div className="absolute top-0 left-0 w-1 h-full bg-blue-500/50"></div>
                                            <h4 className="text-xl font-bold text-white mb-3 flex items-center gap-3">
                                                <span className="text-zinc-600">0{i+1}</span> {r.round_name}
                                            </h4>
                                            {r.notes && <p className="text-zinc-400 mb-6 leading-relaxed">{r.notes}</p>}
                                            <div className="space-y-4">
                                                {r.questions.map((q, idx) => (
                                                    <div key={q.id} className="flex gap-4 p-4 bg-black/40 rounded-lg border border-white/5">
                                                        <span className="font-black text-blue-500/50 pt-0.5">Q.</span>
                                                        <p className="text-zinc-200 font-medium">{q.question_text}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            
                            <div className="mt-12 pt-8 border-t border-white/10 flex justify-end">
                                <button 
                                    onClick={() => {
                                        setSearchResults([{ id: activeExp.id }]);
                                        setShowMockModal(true);
                                    }}
                                    className="btn-primary flex items-center gap-2"
                                >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    Launch AI Mock Interview
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {!loading && view === 'create' && (
                    <form onSubmit={handleCreateSubmit} className="max-w-4xl mx-auto">
                        <div className="glass-panel p-8 md:p-12">
                            <h2 className="text-3xl font-black text-white mb-2">Share Your Experience</h2>
                            <p className="text-zinc-400 mb-8">Contribute to the vault. Help others prepare by sharing your interview details.</p>
                            
                            <div className="bg-black/40 border border-white/10 rounded-xl p-6 mb-8">
                                <h3 className="text-lg font-bold text-white mb-6">Basic Info</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-zinc-500 uppercase">Company</label>
                                        <input required placeholder="e.g. Meta" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" value={formData.company} onChange={e => setFormData({...formData, company: e.target.value})} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-zinc-500 uppercase">Role</label>
                                        <input required placeholder="e.g. Backend Engineer" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-zinc-500 uppercase">Level</label>
                                        <input required placeholder="e.g. E4" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" value={formData.level} onChange={e => setFormData({...formData, level: e.target.value})} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-zinc-500 uppercase">Date</label>
                                        <input type="date" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition [color-scheme:dark]" value={formData.interview_date} onChange={e => setFormData({...formData, interview_date: e.target.value})} />
                                    </div>
                                </div>
                                <div className="space-y-2 mb-6">
                                    <label className="text-xs font-bold text-zinc-500 uppercase">Topics (Comma separated)</label>
                                    <input placeholder="e.g. system design, dynamic programming, leadership" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" value={formData.topics} onChange={e => setFormData({...formData, topics: e.target.value})} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-xs font-bold text-zinc-500 uppercase">Overall Experience</label>
                                    <textarea placeholder="General advice, how the interviewers were, overall difficulty..." className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white min-h-[120px] focus:outline-none focus:border-blue-500 transition" value={formData.overall_experience} onChange={e => setFormData({...formData, overall_experience: e.target.value})} />
                                </div>
                            </div>

                            <div className="space-y-6 mb-8">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-lg font-bold text-white">Interview Rounds</h3>
                                    <button type="button" onClick={addRound} className="text-xs font-bold text-blue-400 hover:text-blue-300 transition">
                                        + Add Round
                                    </button>
                                </div>
                                {formData.rounds.map((r, rIdx) => (
                                    <div key={rIdx} className="bg-black/40 border border-white/10 rounded-xl p-6 relative">
                                        <h4 className="text-md font-bold text-zinc-300 mb-4">Round {rIdx + 1}</h4>
                                        <div className="grid gap-4 mb-6">
                                            <input required placeholder="Round Name (e.g. System Design)" className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" value={r.round_name} onChange={e => updateRound(rIdx, 'round_name', e.target.value)} />
                                            <textarea placeholder="Notes for this round..." className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" value={r.notes} onChange={e => updateRound(rIdx, 'notes', e.target.value)} />
                                        </div>
                                        
                                        <div className="space-y-4 pl-4 border-l-2 border-zinc-800">
                                            <label className="text-xs font-bold text-zinc-500 uppercase">Questions Asked</label>
                                            {r.questions.map((q, qIdx) => (
                                                <input key={qIdx} required placeholder="Enter question..." className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white transition" value={q.question_text} onChange={e => updateQuestion(rIdx, qIdx, e.target.value)} />
                                            ))}
                                            <button type="button" onClick={() => addQuestion(rIdx)} className="text-xs text-zinc-400 hover:text-white font-bold transition">
                                                + Add another question
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="flex justify-end pt-6 border-t border-white/10">
                                <button type="submit" className="btn-primary">
                                    Encrypt & Store Data
                                </button>
                            </div>
                        </div>
                    </form>
                )}
            </div>

            {/* Subscribe Modal */}
            {showSubModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl relative">
                        <div className="p-6">
                            <h3 className="text-xl font-bold text-white mb-2">Subscribe to Search Alerts</h3>
                            <p className="text-sm text-zinc-400 mb-6">
                                We'll notify you when new interview experiences matching <span className="text-blue-400 font-bold">"{searchQuery}"</span> are posted using our standard deviation threshold algorithm.
                            </p>
                            <form onSubmit={handleSubscribe} className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">Email (Optional)</label>
                                    <input 
                                        type="email" 
                                        placeholder="you@example.com"
                                        className="w-full bg-black/50 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition"
                                        value={subEmail}
                                        onChange={e => setSubEmail(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">WhatsApp (Optional)</label>
                                    <input 
                                        type="text" 
                                        placeholder="+1234567890"
                                        className="w-full bg-black/50 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition"
                                        value={subWhatsapp}
                                        onChange={e => setSubWhatsapp(e.target.value)}
                                    />
                                </div>
                                <div className="pt-4 flex gap-3 justify-end">
                                    <button type="button" onClick={() => setShowSubModal(false)} className="px-4 py-2 text-zinc-400 hover:text-white font-bold transition">Cancel</button>
                                    <button type="submit" disabled={subscribing || (!subEmail && !subWhatsapp)} className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg transition disabled:opacity-50">
                                        {subscribing ? 'Saving...' : 'Subscribe'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* Mock Interview Launch Modal */}
            {showMockModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl relative">
                        <div className="p-6">
                            <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
                                <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                AI Mock Interview Setup
                            </h3>
                            <p className="text-sm text-zinc-400 mb-6">
                                We'll use the Top K experiences as a hidden rubric to generate targeted, strict questions for you.
                            </p>
                            <form onSubmit={handleLaunchMock} className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">OpenAI API Key (Required for BYOK)</label>
                                    <input 
                                        type="password" 
                                        required
                                        placeholder="sk-..."
                                        className="w-full bg-black/50 border border-zinc-700 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-purple-500 transition"
                                        value={mockApiKey}
                                        onChange={e => setMockApiKey(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">Job Description (Optional Tailoring)</label>
                                    <textarea 
                                        placeholder="Paste JD here to tailor questions..."
                                        className="w-full bg-black/50 border border-zinc-700 rounded-lg px-4 py-3 text-white h-24 focus:outline-none focus:border-purple-500 transition"
                                        value={mockJd}
                                        onChange={e => setMockJd(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">Resume (Optional Cross-examination)</label>
                                    <textarea 
                                        placeholder="Paste your resume here..."
                                        className="w-full bg-black/50 border border-zinc-700 rounded-lg px-4 py-3 text-white h-24 focus:outline-none focus:border-purple-500 transition"
                                        value={mockResume}
                                        onChange={e => setMockResume(e.target.value)}
                                    />
                                </div>
                                <div className="pt-4 flex gap-3 justify-end">
                                    <button type="button" onClick={() => setShowMockModal(false)} className="px-4 py-2 text-zinc-400 hover:text-white font-bold transition">Cancel</button>
                                    <button type="submit" disabled={startingMock || !mockApiKey} className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg transition shadow-[0_0_15px_rgba(147,51,234,0.3)] disabled:opacity-50 flex items-center gap-2">
                                        {startingMock ? 'Synthesizing...' : 'Launch Terminal'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default InterviewExperiences;
