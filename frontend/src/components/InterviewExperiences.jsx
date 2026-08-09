import React, { useState, useEffect } from 'react';
import axios from 'axios';

const InterviewExperiences = ({ apiBase, token, user, addToast, onBack }) => {
    const [view, setView] = useState('list'); // list, create, detail, search
    const [experiences, setExperiences] = useState([]);
    const [searchResults, setSearchResults] = useState([]);
    const [loading, setLoading] = useState(false);
    
    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [filters, setFilters] = useState({ company: '', role: '', level: '' });
    
    // Form state
    const [formData, setFormData] = useState({
        company: '', role: '', level: '', interview_date: '', overall_experience: '',
        rounds: [{ round_name: '', notes: '', questions: [{ question_text: '' }] }]
    });
    
    const [activeExp, setActiveExp] = useState(null);

    const authHeaders = { headers: { Authorization: `Bearer ${token}` } };

    useEffect(() => {
        if (view === 'list') fetchExperiences();
    }, [view]);

    const fetchExperiences = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${apiBase}/interview-experiences`, authHeaders);
            setExperiences(res.data.data);
        } catch (err) {
            addToast('Failed to fetch experiences', 'error');
        }
        setLoading(false);
    };

    const handleSearch = async (e) => {
        if (e) e.preventDefault();
        if (!searchQuery.trim()) {
            setView('list');
            return;
        }
        
        setLoading(true);
        setView('search');
        try {
            const res = await axios.post(`${apiBase}/interview-experiences/search`, {
                query: searchQuery,
                ...filters
            }, authHeaders);
            setSearchResults(res.data.results);
        } catch (err) {
            addToast('Search failed', 'error');
        }
        setLoading(false);
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
        setLoading(true);
        try {
            await axios.post(`${apiBase}/interview-experiences`, formData, authHeaders);
            addToast('Experience posted successfully!', 'success');
            setView('list');
            setFormData({
                company: '', role: '', level: '', interview_date: '', overall_experience: '',
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

    return (
        <div className="max-w-6xl mx-auto px-6 py-8">
            {/* Header & Navigation */}
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <button onClick={onBack} className="text-zinc-400 hover:text-white transition">
                        ← Back to Studio
                    </button>
                    <h2 className="text-2xl font-black text-white">Interview Experiences</h2>
                </div>
                {view !== 'create' && (
                    <button 
                        onClick={() => setView('create')}
                        className="px-4 py-2 bg-white text-black font-bold rounded-lg hover:bg-zinc-200 transition"
                    >
                        + Post Experience
                    </button>
                )}
            </div>

            {/* Search Bar */}
            {view !== 'create' && view !== 'detail' && (
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 mb-8 backdrop-blur-sm">
                    <form onSubmit={handleSearch} className="flex flex-wrap gap-4">
                        <input 
                            type="text" 
                            placeholder="Search questions (e.g., 'How to scale Redis?')"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="flex-1 bg-black border border-zinc-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-white transition"
                        />
                        <input 
                            type="text" placeholder="Company" value={filters.company} onChange={e => setFilters({...filters, company: e.target.value})}
                            className="w-32 bg-black border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-white transition"
                        />
                        <input 
                            type="text" placeholder="Role" value={filters.role} onChange={e => setFilters({...filters, role: e.target.value})}
                            className="w-32 bg-black border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-white transition"
                        />
                        <button type="submit" className="px-6 py-2 bg-zinc-800 text-white font-bold rounded-lg hover:bg-zinc-700 transition" disabled={loading}>
                            {loading ? '...' : 'Search'}
                        </button>
                    </form>
                </div>
            )}

            {/* Main Content Area */}
            {loading && <div className="text-center py-12 text-zinc-500 font-bold animate-pulse">Loading...</div>}

            {!loading && view === 'list' && (
                <div className="grid gap-4">
                    {experiences.map(exp => (
                        <div key={exp.id} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 hover:border-zinc-600 transition cursor-pointer" onClick={() => viewDetails(exp.id)}>
                            <div className="flex justify-between items-start">
                                <div>
                                    <h3 className="text-xl font-bold text-white mb-1">{exp.company}</h3>
                                    <p className="text-zinc-400 font-medium">{exp.role} · {exp.level}</p>
                                </div>
                                <span className="text-xs text-zinc-500 font-bold">{new Date(exp.created_at).toLocaleDateString()}</span>
                            </div>
                        </div>
                    ))}
                    {experiences.length === 0 && <p className="text-zinc-500 text-center py-8">No experiences posted yet.</p>}
                </div>
            )}

            {!loading && view === 'search' && (
                <div>
                    <h3 className="text-lg font-bold text-white mb-4">Search Results (Hybrid RRF)</h3>
                    <div className="grid gap-4">
                        {searchResults.map(res => (
                            <div key={res.id} className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 p-3 flex gap-2">
                                    {res.bm25_score != null && (
                                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-blue-900/30 text-blue-400 border border-blue-800/50" title={`BM25 Lexical Score (Rank: ${res.bm25_rank})`}>
                                            BM25: {res.bm25_score.toFixed(2)}
                                        </span>
                                    )}
                                    {res.vector_score != null && (
                                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-purple-900/30 text-purple-400 border border-purple-800/50" title={`Vector Semantic Score (Rank: ${res.vector_rank})`}>
                                            Vector: {res.vector_score.toFixed(3)}
                                        </span>
                                    )}
                                    <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-zinc-800 text-zinc-300 border border-zinc-700" title="Reciprocal Rank Fusion Score">
                                        RRF: {res.rrf_score.toFixed(3)}
                                    </span>
                                </div>
                                <h4 className="text-lg font-medium text-white mb-3 pr-24">{res.question_text}</h4>
                                <div className="flex items-center gap-3 text-xs font-semibold text-zinc-500">
                                    <span className="text-zinc-300">{res.company}</span>
                                    <span>•</span>
                                    <span>{res.role}</span>
                                    <span>•</span>
                                    <span>{res.round_name}</span>
                                    <button onClick={() => viewDetails(res.experience_id)} className="ml-auto text-white hover:underline">
                                        View Full Experience →
                                    </button>
                                </div>
                            </div>
                        ))}
                        {searchResults.length === 0 && <p className="text-zinc-500 text-center py-8">No matching questions found.</p>}
                    </div>
                </div>
            )}

            {!loading && view === 'detail' && activeExp && (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8">
                    <div className="flex justify-between items-start mb-8 pb-8 border-b border-zinc-800">
                        <div>
                            <h2 className="text-3xl font-black text-white mb-2">{activeExp.company}</h2>
                            <p className="text-lg text-zinc-400 font-medium">{activeExp.role} · {activeExp.level}</p>
                        </div>
                        {/* Only show delete if user owns it (assuming generic implementation or admin for now, actually API checks ownership) */}
                        <button onClick={() => deleteExperience(activeExp.id)} className="px-4 py-2 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 font-bold rounded-lg transition">
                            Delete
                        </button>
                    </div>

                    {activeExp.overall_experience && (
                        <div className="mb-8">
                            <h3 className="text-sm uppercase tracking-widest text-zinc-500 font-bold mb-3">Overall Experience</h3>
                            <p className="text-zinc-300 leading-relaxed whitespace-pre-wrap">{activeExp.overall_experience}</p>
                        </div>
                    )}

                    <div>
                        <h3 className="text-sm uppercase tracking-widest text-zinc-500 font-bold mb-4">Interview Rounds</h3>
                        <div className="grid gap-6">
                            {activeExp.rounds.map((r, i) => (
                                <div key={r.id} className="bg-black border border-zinc-800 rounded-lg p-5">
                                    <h4 className="text-lg font-bold text-white mb-2">Round {i+1}: {r.round_name}</h4>
                                    {r.notes && <p className="text-sm text-zinc-400 mb-4">{r.notes}</p>}
                                    <div className="space-y-3">
                                        {r.questions.map((q, idx) => (
                                            <div key={q.id} className="flex gap-3 text-zinc-300">
                                                <span className="font-bold text-zinc-600">{idx+1}.</span>
                                                <p>{q.question_text}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {!loading && view === 'create' && (
                <form onSubmit={handleCreateSubmit} className="max-w-3xl">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 mb-6">
                        <h3 className="text-xl font-bold text-white mb-6">Basic Info</h3>
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <input required placeholder="Company" className="bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white w-full" value={formData.company} onChange={e => setFormData({...formData, company: e.target.value})} />
                            <input required placeholder="Role (e.g., Backend Engineer)" className="bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white w-full" value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} />
                            <input required placeholder="Level (e.g., SDE-2)" className="bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white w-full" value={formData.level} onChange={e => setFormData({...formData, level: e.target.value})} />
                            <input type="date" className="bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white w-full" value={formData.interview_date} onChange={e => setFormData({...formData, interview_date: e.target.value})} />
                        </div>
                        <textarea placeholder="Overall experience or general advice..." className="bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white w-full min-h-[100px]" value={formData.overall_experience} onChange={e => setFormData({...formData, overall_experience: e.target.value})} />
                    </div>

                    <div className="space-y-6 mb-8">
                        {formData.rounds.map((r, rIdx) => (
                            <div key={rIdx} className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 relative">
                                <h4 className="text-lg font-bold text-white mb-4">Round {rIdx + 1}</h4>
                                <div className="grid gap-4 mb-4">
                                    <input required placeholder="Round Name (e.g., System Design)" className="bg-black border border-zinc-700 rounded-lg px-4 py-3 text-white w-full" value={r.round_name} onChange={e => updateRound(rIdx, 'round_name', e.target.value)} />
                                    <textarea placeholder="Notes for this round..." className="bg-black border border-zinc-700 rounded-lg px-4 py-2 text-white w-full text-sm" value={r.notes} onChange={e => updateRound(rIdx, 'notes', e.target.value)} />
                                </div>
                                
                                <div className="space-y-3 pl-4 border-l-2 border-zinc-800">
                                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Questions Asked</label>
                                    {r.questions.map((q, qIdx) => (
                                        <input key={qIdx} required placeholder="Enter question..." className="bg-black border border-zinc-800 rounded-lg px-4 py-2 text-white w-full" value={q.question_text} onChange={e => updateQuestion(rIdx, qIdx, e.target.value)} />
                                    ))}
                                    <button type="button" onClick={() => addQuestion(rIdx)} className="text-xs text-zinc-400 hover:text-white font-bold transition">
                                        + Add another question
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="flex gap-4">
                        <button type="button" onClick={addRound} className="px-6 py-3 bg-zinc-800 text-white font-bold rounded-lg hover:bg-zinc-700 transition">
                            + Add Round
                        </button>
                        <button type="submit" className="px-8 py-3 bg-white text-black font-black rounded-lg hover:bg-zinc-200 transition ml-auto">
                            Submit Experience
                        </button>
                    </div>
                </form>
            )}
        </div>
    );
};

export default InterviewExperiences;
