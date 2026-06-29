import { useState, useRef } from 'react'
import axios from 'axios'

export default function UploadView({ apiBase, token, onReady, addToast }) {
    const [files, setFiles] = useState([])
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState('')
    const [dragOver, setDragOver] = useState(false)
    const [chunkCount, setChunkCount] = useState(null)
    const [requiresConfirmation, setRequiresConfirmation] = useState(false)
    const [uploadId, setUploadId] = useState('')
    const [warnings, setWarnings] = useState([])
    const [conflicts, setConflicts] = useState([])
    const [priorities, setPriorities] = useState({})
    
    // New State for Mode Selection
    const [selectedMode, setSelectedMode] = useState('quick') // 'quick' | 'comprehensive'
    const [numQuestions, setNumQuestions] = useState(6)

    const fileInputRef = useRef(null)

    const handleFiles = (newFiles) => {
        const arr = Array.from(newFiles)
        setFiles(prev => [...prev, ...arr])
    }

    const handleDrop = (e) => {
        e.preventDefault()
        setDragOver(false)
        handleFiles(e.dataTransfer.files)
    }

    const removeFile = (idx) => {
        setFiles(prev => prev.filter((_, i) => i !== idx))
    }

    const startVivaProcess = async (currentUploadId = null) => {
        setStatus('Generating AI questions via Gemini (may take ~30s)...')
        const vivaRes = await axios.post(`${apiBase}/start-viva`, { mode: selectedMode, num_questions: numQuestions }, { timeout: 120000, headers: { Authorization: `Bearer ${token}` } })
        setStatus('Engine initialized!')
        addToast(`Engine initialized in ${selectedMode === 'quick' ? 'Quick' : 'Comprehensive'} mode!`, 'success')
        setTimeout(() => onReady(vivaRes.data), 800)
    }

    const handleInitialize = async () => {
        if (files.length === 0) return
        setLoading(true)

        try {
            setStatus('Parsing documents & extracting semantics...')
            const formData = new FormData()
            files.forEach(f => formData.append('files', f))

            const uploadRes = await axios.post(`${apiBase}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data', 'Authorization': `Bearer ${token}` }
            })

            if (uploadRes.data.status === 'requires_confirmation') {
                setUploadId(uploadRes.data.upload_id)
                setWarnings(uploadRes.data.warnings || [])
                setConflicts(uploadRes.data.conflicts || [])

                const initialPriorities = {}
                ;(uploadRes.data.conflicts || []).forEach(c => {
                    initialPriorities[c.topic] = [...c.conflicting_docs]
                })
                setPriorities(initialPriorities)
                setRequiresConfirmation(true)
                setLoading(false)
                return
            }

            setChunkCount(uploadRes.data.total_chunks)
            await startVivaProcess()
            
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message
            setStatus(`Error: ${errorMsg}`)
            addToast(`Upload Failed: ${errorMsg}`, 'error')
            setLoading(false)
        }
    }

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    const movePriority = (topic, index, direction) => {
        setPriorities(prev => {
            const newOrder = [...prev[topic]]
            if (direction === 'up' && index > 0) {
                [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]]
            } else if (direction === 'down' && index < newOrder.length - 1) {
                [newOrder[index + 1], newOrder[index]] = [newOrder[index], newOrder[index + 1]]
            }
            return { ...prev, [topic]: newOrder }
        })
    }

    const handleConfirm = async () => {
        setLoading(true)
        setStatus('Resolving conflicts and finalizing engine...')
        try {
            const confirmRes = await axios.post(`${apiBase}/confirm-upload`, {
                upload_id: uploadId,
                priorities: priorities
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setChunkCount(confirmRes.data.total_chunks)
            await startVivaProcess(uploadId)
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message
            setStatus(`Error: ${errorMsg}`)
            addToast(`Confirmation Failed: ${errorMsg}`, 'error')
            setLoading(false)
        }
    }

    if (requiresConfirmation) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 fade-in-up">
                <div className="text-center max-w-3xl mb-12">
                    <h2 className="text-3xl font-extrabold text-orange-400 mb-3">
                        Manual Resolution Required
                    </h2>
                    <p className="text-gray-400 max-w-lg mx-auto leading-relaxed">
                        The Space-Bound Engine detected semantic discrepancies.
                    </p>
                </div>
                <div className="space-y-6 w-full max-w-2xl glass-panel p-8">
                    {warnings.length > 0 && (
                        <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-5">
                            <h3 className="text-orange-400 font-semibold mb-3">⚠️ Topic Warning</h3>
                            <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
                                {warnings.map((w, i) => <li key={i}>{w}</li>)}
                            </ul>
                        </div>
                    )}
                    {conflicts.length > 0 && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-5">
                            <h3 className="text-red-400 font-semibold mb-4">🚨 Factual Discrepancies Detected</h3>
                            <div className="space-y-4">
                                {conflicts.map((c, i) => (
                                    <div key={i} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
                                        <p className="font-medium text-gray-200 mb-3">Conflict on: <span className="text-brand-400">"{c.topic}"</span></p>
                                        <div className="space-y-2">
                                            {priorities[c.topic]?.map((docName, idx) => (
                                                <div key={docName} className="flex items-center justify-between glass p-2 rounded-md">
                                                    <div className="text-sm text-gray-300">
                                                        <span className="text-brand-500 font-bold mr-2">{idx + 1}.</span>{docName}
                                                    </div>
                                                    <div className="flex gap-1">
                                                        <button onClick={() => movePriority(c.topic, idx, 'up')} disabled={idx === 0} className="p-1 hover:text-white disabled:opacity-30">▲</button>
                                                        <button onClick={() => movePriority(c.topic, idx, 'down')} disabled={idx === priorities[c.topic].length - 1} className="p-1 hover:text-white disabled:opacity-30">▼</button>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
                <div className="mt-8 text-center">
                    {loading ? (
                        <div className="flex flex-col items-center gap-4">
                            <div className="loader-ring" />
                            <p className="gradient-text font-medium">{status}</p>
                        </div>
                    ) : (
                        <div className="flex gap-4 justify-center">
                            <button onClick={handleConfirm} className="btn-glow px-8 py-3 rounded-xl text-white font-bold tracking-wide">Confirm & Initialize</button>
                        </div>
                    )}
                </div>
            </div>
        )
    }

    return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 fade-in-up min-h-[80vh]">
            <div className="text-center max-w-3xl mb-12">
                <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 leading-tight mt-4">
                    <span className="text-white">Master Your</span><br/>
                    <span className="gradient-text">Knowledge</span>
                </h1>
                <p className="text-lg text-gray-400 font-medium max-w-xl mx-auto">Upload your documents and let our advanced AI orchestrate a personalized, comprehensive viva examination.</p>
            </div>

            <div className="w-full max-w-2xl glass-panel rounded-3xl p-1 relative overflow-hidden group transition-all hover:shadow-[0_0_40px_rgba(99,102,241,0.15)] mb-10">
                <div className="absolute inset-0 bg-gradient-to-r from-brand-500/20 via-purple-500/20 to-pink-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-xl"></div>
                <div 
                    className={`relative bg-surface-900/90 backdrop-blur-xl border-2 border-dashed ${dragOver ? 'border-brand-500 bg-brand-500/5' : 'border-surface-600'} rounded-[22px] p-12 text-center transition-all duration-300 flex flex-col items-center`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <input ref={fileInputRef} type="file" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
                    <div className="w-20 h-20 mb-6 rounded-2xl bg-surface-800/80 border border-white/5 flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform duration-500">
                        <svg className="w-10 h-10 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                    </div>
                    <p className="text-gray-100 font-bold text-xl mb-2">
                        Drop PDFs here or <span className="text-brand-400">browse</span>
                    </p>
                    <p className="text-gray-500 text-sm font-medium">Supports intelligent parsing and noise filtering</p>
                </div>
            </div>

            {/* File List */}
            {files.length > 0 && (
                <div className="w-full max-w-2xl mb-10 space-y-3 slide-in-right">
                    {files.map((file, i) => (
                        <div key={i} className="glass-panel rounded-2xl px-6 py-4 flex items-center justify-between group hover:border-brand-500/30 transition-colors">
                            <div className="flex items-center gap-5">
                                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-red-500/20 to-orange-500/20 border border-red-500/30 flex items-center justify-center shadow-inner">
                                    <svg className="w-6 h-6 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div>
                                    <p className="text-base font-bold text-gray-100 truncate max-w-[250px]">{file.name}</p>
                                    <p className="text-xs text-gray-400 font-mono mt-1">{formatSize(file.size)}</p>
                                </div>
                            </div>
                            <button onClick={(e) => { e.stopPropagation(); removeFile(i) }} className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-full p-2 transition-all">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Mode & Question Configuration */}
            {files.length > 0 && (
                <div className="w-full max-w-2xl fade-in-up">
                    
                    {/* Question Amount Slider */}
                    <div className="glass-panel rounded-2xl p-6 mb-8 border border-surface-600">
                        <div className="flex justify-between items-center mb-4">
                            <div>
                                <h4 className="text-lg font-bold text-white">Question Configuration</h4>
                                <p className="text-sm text-gray-400">Select the number of questions for your Viva</p>
                            </div>
                            <div className="bg-brand-500/20 border border-brand-500/30 px-4 py-2 rounded-xl">
                                <span className="text-2xl font-black text-brand-400">{numQuestions}</span>
                                <span className="text-xs text-brand-300 ml-1 font-bold">Q's</span>
                            </div>
                        </div>
                        <div className="px-2">
                            <input 
                                type="range" 
                                min="3" 
                                max="10" 
                                step="1" 
                                value={numQuestions} 
                                onChange={(e) => setNumQuestions(Number(e.target.value))}
                                className="w-full h-2 bg-surface-800 rounded-lg appearance-none cursor-pointer accent-brand-500 focus:outline-none"
                            />
                            <div className="flex justify-between text-xs text-gray-500 font-bold mt-2 px-1">
                                <span>3 (Quick)</span>
                                <span>10 (Deep Dive)</span>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
                        {/* Quick Start Card */}
                        <div 
                            onClick={() => setSelectedMode('quick')}
                            className={`cursor-pointer rounded-2xl p-6 transition-all duration-300 border ${selectedMode === 'quick' ? 'border-brand-500 bg-brand-500/10 shadow-[0_0_20px_rgba(99,102,241,0.2)]' : 'border-surface-700 bg-surface-900/50 hover:border-surface-600'}`}
                        >
                            <div className="flex items-center gap-4 mb-3">
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${selectedMode === 'quick' ? 'bg-brand-500 text-white' : 'bg-surface-800 text-gray-400'}`}>⚡</div>
                                <h4 className={`text-lg font-bold ${selectedMode === 'quick' ? 'text-white' : 'text-gray-300'}`}>Static Assessment</h4>
                            </div>
                            <p className="text-sm text-gray-400 leading-relaxed">Evaluates semantic clusters with predetermined generative questions.</p>
                        </div>

                        {/* Comprehensive Card */}
                        <div 
                            onClick={() => setSelectedMode('comprehensive')}
                            className={`cursor-pointer rounded-2xl p-6 transition-all duration-300 border ${selectedMode === 'comprehensive' ? 'border-purple-500 bg-purple-500/10 shadow-[0_0_20px_rgba(168,85,247,0.2)]' : 'border-surface-700 bg-surface-900/50 hover:border-surface-600'}`}
                        >
                            <div className="flex items-center gap-4 mb-3">
                                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${selectedMode === 'comprehensive' ? 'bg-purple-500 text-white' : 'bg-surface-800 text-gray-400'}`}>🧠</div>
                                <div>
                                    <h4 className={`text-lg font-bold ${selectedMode === 'comprehensive' ? 'text-white' : 'text-gray-300'}`}>Agentic Adaptive</h4>
                                    <span className="text-[10px] uppercase font-bold text-purple-400 tracking-widest block">Multi-Agent</span>
                                </div>
                            </div>
                            <p className="text-sm text-gray-400 leading-relaxed">Dynamic, conversational questioning driven by an AI Supervisor.</p>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        {loading ? (
                            <div className="flex items-center gap-3 text-sm text-gray-300 font-medium glass-panel px-6 py-3 rounded-xl">
                                <div className="w-5 h-5 border-2 border-t-brand-500 border-white/10 rounded-full animate-spin" />
                                {status}
                            </div>
                        ) : (
                            <button
                                onClick={handleInitialize}
                                className="btn-primary w-full md:w-auto"
                            >
                                Initialize Assessment Engine
                            </button>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
