import { useState, useEffect } from 'react'
import axios from 'axios'

export default function SetupStudio({ apiBase, token, user, onStartCoach, addToast }) {
    const [provider, setProvider] = useState('google')
    const [apiKey, setApiKey] = useState('')
    const [selectedMode, setSelectedMode] = useState('behavioral')
    const [targetRole, setTargetRole] = useState('')
    const [expLevel, setExpLevel] = useState('Entry-level (0-2 yrs)')
    const [jobDesc, setJobDesc] = useState('')
    const [resumeText, setResumeText] = useState('')
    const [numQuestions, setNumQuestions] = useState(5)
    const [testingKey, setTestingKey] = useState(false)
    const [keyStatus, setKeyStatus] = useState(null) // {ok: boolean, msg: string}
    const [starting, setStarting] = useState(false)
    const [showContext, setShowContext] = useState(false)
    const [uploading, setUploading] = useState(false)

    const handleFileUpload = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        
        const formData = new FormData()
        formData.append('file', file)
        
        setUploading(true)
        addToast('Extracting document text...', 'info')
        try {
            const res = await axios.post(`${apiBase}/coach/parse-resume`, formData, {
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'multipart/form-data'
                }
            })
            setResumeText(res.data.text)
            addToast('Resume uploaded & parsed successfully', 'success')
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to parse document', 'error')
        } finally {
            setUploading(false)
            e.target.value = '' // reset input
        }
    }

    useEffect(() => {
        const savedKey = localStorage.getItem('viva_byok_api_key')
        if (savedKey) setApiKey(savedKey)
    }, [])

    const PROVIDERS = [
        { id: 'google', name: 'Google AI Studio', icon: '🔷', desc: 'Direct API — highest throughput' },
        { id: 'openrouter', name: 'OpenRouter', icon: '🌐', desc: 'Gemma 4 Free Tier fallback' },
        { id: 'nvidia', name: 'NVIDIA NIM', icon: '💚', desc: 'Ultra-fast inference credits' },
        { id: 'huggingface', name: 'Hugging Face', icon: '🤗', desc: 'Open-source router hub' }
    ]

    const MODES = [
        { id: 'behavioral', title: 'Viva-Verse for Behavioral', icon: '🗣️', tag: 'STAR Method & Executive Leadership' },
        { id: 'technical', title: 'Viva-Verse for Technical', icon: '💻', tag: 'Big-O Algorithms & Code Rigor' },
        { id: 'system-design', title: 'Viva-Verse for System Design', icon: '🏗️', tag: 'Distributed Scalability & Tradeoffs' },
        { id: 'assessment', title: 'Viva-Verse for Online Assessment', icon: '📝', tag: 'Timed Aptitude & Logical Deduction' },
        { id: 'certification', title: 'Viva-Verse for Certification', icon: '🏆', tag: 'MCQ Practice & Decoupled Option Analysis' },
        { id: 'case-study', title: 'Viva-Verse for Case Study', icon: '📊', tag: 'MECE Business Structuring & Mental Math' }
    ]

    const LEVELS = [
        'Entry-level (0-2 yrs)',
        'Mid-level (3-5 yrs)',
        'Senior (6-8 yrs)',
        'Staff / Lead (9+ yrs)',
        'Executive / Director'
    ]

    const handleTestKey = async () => {
        if (!apiKey.trim()) {
            addToast('Please input an API Key first', 'warning')
            return
        }
        setTestingKey(true)
        setKeyStatus(null)

        try {
            const res = await axios.post(`${apiBase}/coach/test-key`, {
                provider,
                api_key: apiKey.trim()
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setKeyStatus({ ok: true, msg: res.data.message })
            localStorage.setItem('viva_byok_api_key', apiKey.trim())
        } catch (err) {
            setKeyStatus({ ok: false, msg: err.response?.data?.detail || 'Key authentication failed' })
        } finally {
            setTestingKey(false)
        }
    }

    const handleLaunch = async () => {
        if (!apiKey.trim()) {
            addToast('Industry BYOK Protocol: API Key is required', 'warning')
            return
        }
        if (!targetRole.trim()) {
            addToast('Please specify your Target Role', 'warning')
            return
        }

        localStorage.setItem('viva_byok_api_key', apiKey.trim())
        setStarting(true)

        const config = {
            provider,
            api_key: apiKey.trim(),
            mode: selectedMode,
            role: targetRole.trim() || 'Thesis Candidate',
            level: expLevel,
            jd: jobDesc.trim(),
            resume: resumeText.trim(),
            num_questions: numQuestions
        }

        try {
            const res = await axios.post(`${apiBase}/coach/init`, config, {
                headers: { Authorization: `Bearer ${token}` }
            })
            onStartCoach({
                ...config,
                system_prompt: res.data.system_prompt,
                questions: res.data.questions,
                initial_tokens: res.data.tokens
            })
        } catch (err) {
            addToast(err.response?.data?.detail || 'Failed to initialize arena', 'error')
            setStarting(false)
        }
    }

    return (
        <div className="min-h-screen pt-12 pb-24 px-4 sm:px-6 max-w-7xl mx-auto fade-in-up">
            {/* Classy Hero Banner */}
            <div className="text-center mb-16 relative">
                <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md text-xs tracking-wider uppercase text-brand-400 mb-6 shadow-inner">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    Industry Production Grade · Gemma 4 Architecture
                </div>
                <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight text-white mb-6 leading-tight">
                    The AI Interrogation & <span className="gradient-text">Defense Studio</span>
                </h1>
                <p className="text-lg sm:text-xl text-zinc-400 max-w-3xl mx-auto font-light leading-relaxed">
                    Welcome, <span className="text-white font-medium">{user?.username}</span>. Calibrate your arena with zero-cost BYOK passthrough. Practice behavioral leadership, algorithmic coding, system design, or launch our flagship multi-thesis defense.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left Column: BYOK & Configuration */}
                <div className="lg:col-span-5 space-y-8">
                    {/* Provider Selection */}
                    <div className="glass-panel p-6 rounded-2xl relative overflow-hidden border border-zinc-800 bg-black/80">
                        <div className="absolute top-0 left-0 w-1 h-full bg-white"></div>
                        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <span>🔑</span> Bring Your Own Key (BYOK)
                        </h2>
                        <div className="grid grid-cols-2 gap-3 mb-5">
                            {PROVIDERS.map(p => (
                                <button
                                    key={p.id}
                                    onClick={() => { setProvider(p.id); setKeyStatus(null); }}
                                    className={`p-3 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between ${
                                        provider === p.id 
                                            ? 'bg-zinc-900 border-white text-white shadow-[0_0_15px_rgba(255,255,255,0.15)] font-medium' 
                                            : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200'
                                    }`}
                                >
                                    <div className="text-base mb-1">{p.icon} <span className="font-semibold text-sm">{p.name}</span></div>
                                    <div className="text-[10px] opacity-75">{p.desc}</div>
                                </button>
                            ))}
                        </div>

                        {/* API Key Password Input */}
                        <div className="space-y-3">
                            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-300 block">
                                {PROVIDERS.find(p => p.id === provider)?.name} API Credential
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="password"
                                    value={apiKey}
                                    onChange={e => { setApiKey(e.target.value); setKeyStatus(null); }}
                                    placeholder={provider === 'google' ? 'AIzaSy...' : 'sk-or-...'}
                                    className="flex-1 bg-black/60 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-brand-500 transition-colors shadow-inner"
                                />
                                <button
                                    onClick={handleTestKey}
                                    disabled={testingKey}
                                    className="px-5 py-3 rounded-xl bg-white/10 hover:bg-white/15 text-white text-xs font-semibold transition tracking-wide disabled:opacity-50 border border-white/5"
                                >
                                    {testingKey ? 'Ping...' : 'Test Key'}
                                </button>
                            </div>
                            {keyStatus && (
                                <div className={`text-xs p-2.5 rounded-lg flex items-center gap-2 ${keyStatus.ok ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                                    <span>{keyStatus.ok ? '🟢' : '🔴'}</span> {keyStatus.msg}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Candidate Calibration Drawer */}
                    <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
                        <h2 className="text-lg font-bold text-white mb-4 flex items-center justify-between">
                            <span className="flex items-center gap-2"><span>🎯</span> Target Role Rigor</span>
                            <button onClick={() => setShowContext(!showContext)} className="text-xs text-brand-400 hover:text-brand-300 underline">
                                {showContext ? 'Hide Context' : '+ Inject Resume & JD'}
                            </button>
                        </h2>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="text-xs font-medium text-zinc-400 block mb-1.5">Target Job Title / Role</label>
                                <input
                                    type="text"
                                    value={targetRole}
                                    onChange={e => setTargetRole(e.target.value)}
                                    placeholder="e.g. Senior Distributed Backend Engineer"
                                    className="w-full bg-black/60 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-brand-500 transition-colors"
                                />
                            </div>

                            <div>
                                <label className="text-xs font-medium text-zinc-400 block mb-1.5">Interrogation Difficulty Calibration</label>
                                <select
                                    value={expLevel}
                                    onChange={e => setExpLevel(e.target.value)}
                                    className="w-full bg-black/60 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand-500 transition-colors"
                                >
                                    {LEVELS.map(lvl => <option key={lvl} value={lvl} className="bg-zinc-900">{lvl}</option>)}
                                </select>
                            </div>

                            <div>
                                <label className="text-xs font-medium text-zinc-400 block mb-1.5">Number of Questions ({numQuestions})</label>
                                <input
                                    type="range"
                                    min="1"
                                    max="15"
                                    value={numQuestions}
                                    onChange={e => setNumQuestions(Number(e.target.value))}
                                    className="w-full accent-brand-500"
                                />
                            </div>

                            {showContext && (
                                <div className="space-y-4 pt-3 border-t border-white/10 fade-in-up">
                                    <div>
                                        <label className="text-xs font-medium text-zinc-400 block mb-1.5">Target Job Description (Optional)</label>
                                        <textarea
                                            value={jobDesc}
                                            onChange={e => setJobDesc(e.target.value)}
                                            rows={3}
                                            placeholder="Paste exact JD requirements here..."
                                            className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-brand-500 transition-colors resize-none"
                                        />
                                    </div>
                                    <div>
                                        <div className="flex items-center justify-between mb-1.5">
                                            <label className="text-xs font-medium text-zinc-400 block">Candidate Resume (Optional)</label>
                                            <label className="text-xs text-brand-400 hover:text-brand-300 cursor-pointer flex items-center gap-1 transition-colors">
                                                {uploading ? '⏳ Extracting...' : '📎 Upload Full PDF/TXT'}
                                                <input type="file" className="hidden" accept=".pdf,.txt" onChange={handleFileUpload} disabled={uploading} />
                                            </label>
                                        </div>
                                        <textarea
                                            value={resumeText}
                                            onChange={e => setResumeText(e.target.value)}
                                            rows={3}
                                            placeholder="Paste your resume experience or upload a file for tailored cross-examination..."
                                            className="w-full bg-black/60 border border-white/10 rounded-xl p-3 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-brand-500 transition-colors resize-none"
                                            disabled={uploading}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Column: 7 Viva-Verse Arenas */}
                <div className="lg:col-span-7 space-y-6">
                    <h2 className="text-xl font-bold text-white flex items-center justify-between">
                        <span>⚡ Select Active Interrogation Mode</span>
                        <span className="text-xs px-3 py-1 rounded-full bg-zinc-800 text-zinc-300 border border-white/5">6 Specialized Arenas</span>
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {MODES.map(m => {
                            const isSelected = selectedMode === m.id
                            return (
                                <div
                                    key={m.id}
                                    onClick={() => setSelectedMode(m.id)}
                                    className={`p-5 rounded-2xl border transition-all duration-200 cursor-pointer relative overflow-hidden flex flex-col justify-between group ${
                                        isSelected 
                                            ? 'bg-zinc-900 border-white shadow-[0_0_25px_rgba(255,255,255,0.15)] scale-[1.01]' 
                                            : 'bg-zinc-950/60 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/50'
                                    } ${m.isFlagship ? 'md:col-span-2 border-zinc-700 bg-black' : ''}`}
                                >
                                    {m.isFlagship && (
                                        <div className="absolute top-3 right-4 px-2.5 py-0.5 rounded-full bg-white/10 border border-white/20 text-[10px] font-bold text-white tracking-wider uppercase animate-pulse">
                                            Flagship Arena
                                        </div>
                                    )}
                                    <div className="flex items-start gap-4 mb-4">
                                        <div className={`text-3xl p-3 rounded-xl border ${isSelected ? 'bg-white text-black border-white shadow-md' : 'bg-zinc-900 text-zinc-300 border-zinc-800 group-hover:border-zinc-700'}`}>
                                            {m.icon}
                                        </div>
                                        <div>
                                            <h3 className="text-base font-bold text-white mb-1 group-hover:text-zinc-200 transition-colors">
                                                {m.title}
                                            </h3>
                                            <p className="text-xs text-zinc-400 leading-relaxed font-light">
                                                {m.tag}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between pt-3 border-t border-zinc-800 text-xs font-semibold">
                                        <span className={isSelected ? 'text-white' : 'text-zinc-500'}>
                                            {isSelected ? '● Active Selection' : '○ Click to Mount'}
                                        </span>
                                        <span className="text-zinc-400 group-hover:translate-x-1 transition-transform">Configure →</span>
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    {/* Launch Action Bar */}
                    <div className="pt-6">
                        <button
                            onClick={handleLaunch}
                            disabled={starting}
                            className="w-full btn-primary py-5 text-lg uppercase tracking-wider font-extrabold flex items-center justify-center gap-3"
                        >
                            {starting ? (
                                <span className="inline-flex items-center gap-2">
                                    <span className="w-2.5 h-2.5 rounded-full bg-white animate-bounce"></span>
                                    Synchronizing Space-Bound BYOK Arena...
                                </span>
                            ) : (
                                <><span>🚀</span> Initialize {MODES.find(m => m.id === selectedMode)?.title}</>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
