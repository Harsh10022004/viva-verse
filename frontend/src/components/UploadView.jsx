import { useState, useRef } from 'react'
import axios from 'axios'

export default function UploadView({ apiBase, onReady, addToast }) {
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

    const fileInputRef = useRef(null)

    const handleFiles = (newFiles) => {
        // Allowing all files to test backend API validation
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

    const handleInitialize = async () => {
        if (files.length === 0) return
        setLoading(true)

        try {
            // Step 1: Upload PDFs
            setStatus('Parsing documents...')
            const formData = new FormData()
            files.forEach(f => formData.append('files', f))

            const uploadRes = await axios.post(`${apiBase}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })

            if (uploadRes.data.status === 'requires_confirmation') {
                setUploadId(uploadRes.data.upload_id)
                setWarnings(uploadRes.data.warnings || [])
                setConflicts(uploadRes.data.conflicts || [])

                // Initialize priorities
                const initialPriorities = {}
                    ; (uploadRes.data.conflicts || []).forEach(c => {
                        initialPriorities[c.topic] = [...c.conflicting_docs]
                    })
                setPriorities(initialPriorities)
                setRequiresConfirmation(true)
                setLoading(false)
                return
            }

            setChunkCount(uploadRes.data.total_chunks)

            // Step 2: Start Viva
            setStatus('Generating questions...')
            const vivaRes = await axios.post(`${apiBase}/start-viva`)

            setStatus('Engine initialized!')
            addToast('Documents successfully parsed and engine initialized!', 'success')
            setTimeout(() => onReady(vivaRes.data), 800)
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
            })
            setChunkCount(confirmRes.data.total_chunks)

            setStatus('Generating questions...')
            const vivaRes = await axios.post(`${apiBase}/start-viva`)

            setStatus('Engine initialized!')
            addToast('Conflicts resolved and engine initialized!', 'success')
            setTimeout(() => onReady(vivaRes.data), 800)
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message
            setStatus(`Error: ${errorMsg}`)
            addToast(`Confirmation Failed: ${errorMsg}`, 'error')
            setLoading(false)
        }
    }

    if (requiresConfirmation) {
        return (
            <div className="max-w-3xl mx-auto px-6 py-16 fade-in-up">
                <div className="text-center mb-8">
                    <h2 className="text-3xl font-extrabold text-orange-400 mb-3">
                        Manual Resolution Required
                    </h2>
                    <p className="text-gray-400 max-w-lg mx-auto leading-relaxed">
                        The Space-Bound Engine detected semantic discrepancies or completely unrelated topics.
                    </p>
                </div>

                <div className="space-y-6">
                    {warnings.length > 0 && (
                        <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-5">
                            <h3 className="text-orange-400 font-semibold flex items-center gap-2 mb-3">
                                ⚠️ Topic Warning
                            </h3>
                            <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
                                {warnings.map((w, i) => <li key={i}>{w}</li>)}
                            </ul>
                            <p className="text-xs text-orange-400/80 mt-3 pt-3 border-t border-orange-500/20">Are you ready to instantiate viva given that the documents cover completely different topics?</p>
                        </div>
                    )}

                    {conflicts.length > 0 && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-5">
                            <h3 className="text-red-400 font-semibold flex items-center gap-2 mb-4">
                                🚨 Factual Discrepancies Detected
                            </h3>
                            <p className="text-sm text-gray-300 mb-4">
                                The engine found contradicting information regarding the exact same topics across different documents. Please select the priority of source truth so we compare against accurate facts.
                            </p>

                            <div className="space-y-4">
                                {conflicts.map((c, i) => (
                                    <div key={i} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
                                        <p className="font-medium text-gray-200 mb-3">
                                            Conflict on Topic: <span className="text-brand-400">"{c.topic}"</span>
                                        </p>
                                        <div className="space-y-2">
                                            {priorities[c.topic]?.map((docName, idx) => (
                                                <div key={docName} className="flex items-center justify-between glass p-2 rounded-md">
                                                    <div className="flex items-center gap-3 text-sm text-gray-300">
                                                        <span className="w-5 text-center text-brand-500 font-mono text-xs font-bold">{idx + 1}.</span>
                                                        {docName}
                                                        {idx === 0 && <span className="text-[10px] text-green-400 ml-2 px-1.5 py-0.5 rounded bg-green-400/10">Highest Priority Truth</span>}
                                                    </div>
                                                    <div className="flex gap-1">
                                                        <button
                                                            onClick={() => movePriority(c.topic, idx, 'up')}
                                                            disabled={idx === 0}
                                                            className="p-1 text-gray-400 hover:text-white disabled:opacity-30"
                                                        >
                                                            ▲
                                                        </button>
                                                        <button
                                                            onClick={() => movePriority(c.topic, idx, 'down')}
                                                            disabled={idx === priorities[c.topic].length - 1}
                                                            className="p-1 text-gray-400 hover:text-white disabled:opacity-30"
                                                        >
                                                            ▼
                                                        </button>
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
                            <p className="text-brand-400 font-medium">{status}</p>
                        </div>
                    ) : (
                        <div className="flex gap-4 justify-center">
                            <button
                                onClick={() => {
                                    setRequiresConfirmation(false)
                                    setUploadId('')
                                    setConflicts([])
                                }}
                                className="px-6 py-3 rounded-xl border border-gray-700 text-gray-400 hover:bg-gray-800 transition text-sm font-semibold"
                            >
                                Re-upload Documents
                            </button>
                            <button
                                onClick={handleConfirm}
                                className="btn-glow px-8 py-3 rounded-xl text-white font-semibold text-sm tracking-wide"
                            >
                                Confirm & Initialize
                            </button>
                        </div>
                    )}
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-3xl mx-auto px-6 py-16 fade-in-up">
            {/* Hero */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-6">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
                    Space-Bound Engine v1.0
                </div>
                <h2 className="text-4xl font-extrabold gradient-text mb-3">
                    Upload Your Documents
                </h2>
                <p className="text-gray-400 max-w-lg mx-auto leading-relaxed">
                    Feed your PDFs into the Space-Bound Engine. The AI will analyze, index, and prepare
                    a personalized viva examination based on the content.
                </p>
            </div>

            {/* Drop Zone */}
            <div
                className={`drop-zone rounded-2xl p-12 text-center cursor-pointer transition-all ${dragOver ? 'drag-over' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => handleFiles(e.target.files)}
                />

                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center animate-float">
                    <svg className="w-8 h-8 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                </div>
                <p className="text-gray-300 font-medium mb-1">
                    Drop PDF files here or <span className="text-brand-400 underline">browse</span>
                </p>
                <p className="text-gray-500 text-sm">Supports multiple PDF files</p>
            </div>

            {/* File List */}
            {files.length > 0 && (
                <div className="mt-6 space-y-2 fade-in-up">
                    {files.map((file, i) => (
                        <div key={i} className="glass rounded-xl px-4 py-3 flex items-center justify-between group">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center justify-center flex-shrink-0">
                                    <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                    </svg>
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-gray-200 truncate max-w-xs">{file.name}</p>
                                    <p className="text-xs text-gray-500">{formatSize(file.size)}</p>
                                </div>
                            </div>
                            <button
                                onClick={(e) => { e.stopPropagation(); removeFile(i) }}
                                className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all p-1"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Initialize Button */}
            {files.length > 0 && (
                <div className="mt-8 text-center fade-in-up">
                    {loading ? (
                        <div className="flex flex-col items-center gap-4">
                            <div className="loader-ring" />
                            <div>
                                <p className="text-brand-400 font-medium">{status}</p>
                                {chunkCount && (
                                    <p className="text-gray-500 text-sm mt-1">{chunkCount} semantic chunks indexed</p>
                                )}
                            </div>
                        </div>
                    ) : (
                        <button
                            onClick={handleInitialize}
                            className="btn-glow px-8 py-3.5 rounded-xl text-white font-semibold text-sm tracking-wide"
                        >
                            <span className="relative z-10 flex items-center gap-2">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Initialize Space-Bound Engine
                            </span>
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}
