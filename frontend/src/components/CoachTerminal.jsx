import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
const voiceSupported = !!SpeechRecognition

export default function CoachTerminal({ apiBase, token, config, onExit, onComplete, addToast }) {
    const questions = config.questions || []
    
    const [currentQIndex, setCurrentQIndex] = useState(0)
    const [messages, setMessages] = useState(
        questions.length > 0 ? [{ role: 'coach', content: questions[0] }] : []
    )
    const [qaPairs, setQaPairs] = useState([])
    const [input, setInput] = useState('')
    const [evaluating, setEvaluating] = useState(false)
    const [tokens, setTokens] = useState(config.initial_tokens || 0)
    const [elapsedSeconds, setElapsedSeconds] = useState(0)
    const [ttsEnabled, setTtsEnabled] = useState(true)
    const [isListening, setIsListening] = useState(false)
    const [attachedImage, setAttachedImage] = useState(null)

    const recognitionRef = useRef(null)
    const chatEndRef = useRef(null)

    // Timer loop
    useEffect(() => {
        const timer = setInterval(() => setElapsedSeconds(s => s + 1), 1000)
        return () => clearInterval(timer)
    }, [])

    const formatTimer = (secs) => {
        const mins = Math.floor(secs / 60)
        const rem = secs % 60
        return `${mins.toString().padStart(2, '0')}:${rem.toString().padStart(2, '0')}`
    }

    // Auto scroll chat
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, evaluating])

    // Speak current question
    useEffect(() => {
        if (ttsEnabled && questions[currentQIndex]) {
            speakText(questions[currentQIndex])
        }
    }, [currentQIndex])

    const speakText = (text) => {
        if (!ttsEnabled || typeof window === 'undefined' || !window.speechSynthesis) return
        window.speechSynthesis.cancel()
        const clean = text.replace(/[*#`_]|https?:\/\/\S+/g, '') // remove markdown symbols
        const u = new SpeechSynthesisUtterance(clean)
        u.rate = 1.05
        window.speechSynthesis.speak(u)
    }

    const toggleMic = () => {
        if (!voiceSupported) {
            addToast('Web Speech API mic input is not supported in this browser.', 'warning')
            return
        }
        if (isListening) {
            recognitionRef.current?.stop()
            setIsListening(false)
            return
        }

        const rec = new SpeechRecognition()
        rec.continuous = false
        rec.interimResults = true
        rec.lang = 'en-US'

        rec.onresult = (e) => {
            let final = ''
            for (let i = e.resultIndex; i < e.results.length; i++) {
                if (e.results[i].isFinal) final += e.results[i][0].transcript
            }
            if (final) setInput(prev => (prev ? prev + ' ' : '') + final)
        }
        rec.onerror = () => setIsListening(false)
        rec.onend = () => setIsListening(false)

        recognitionRef.current = rec
        rec.start()
        setIsListening(true)
    }

    const handleImageUpload = (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        if (!file.type.startsWith('image/')) {
            addToast('Only image sketches are permitted', 'warning')
            return
        }

        const reader = new FileReader()
        reader.onload = () => {
            const res = reader.result
            const b64 = res.split(',')[1]
            setAttachedImage({ base64: b64, mimeType: file.type, previewUrl: res })
        }
        reader.readAsDataURL(file)
    }

    const handleSend = () => {
        if (!input.trim() && !attachedImage) return

        if (isListening) {
            recognitionRef.current?.stop()
            setIsListening(false)
        }
        window.speechSynthesis?.cancel()

        const userText = input.trim()
        setInput('')

        const userMsgParts = []
        if (attachedImage) {
            userMsgParts.push({ inlineData: { mimeType: attachedImage.mimeType, data: attachedImage.base64 } })
            userMsgParts.push({ text: userText || 'Architectural diagram attached for evaluation.' })
        } else {
            userMsgParts.push({ text: userText })
        }

        const newMessages = [
            ...messages,
            { role: 'user', content: userText || '📸 [Diagram Attached]', parts: userMsgParts, previewUrl: attachedImage?.previewUrl }
        ]
        
        const newQaPairs = [
            ...qaPairs,
            { question: questions[currentQIndex], answer: userText || '📸 [Diagram Attached]' }
        ]
        
        setQaPairs(newQaPairs)
        setAttachedImage(null)

        const nextIndex = currentQIndex + 1
        if (nextIndex < questions.length) {
            newMessages.push({ role: 'coach', content: questions[nextIndex] })
            setCurrentQIndex(nextIndex)
        } else {
            setCurrentQIndex(nextIndex) // Indicates we are done
            newMessages.push({ role: 'coach', content: 'Session Complete! You can now submit your responses for evaluation.' })
        }
        
        setMessages(newMessages)
    }

    const handleBatchEvaluate = async () => {
        setEvaluating(true)
        addToast('Generating exhaustive final evaluation report...', 'info')
        try {
            const res = await axios.post(`${apiBase}/coach/batch-evaluate`, {
                provider: config.provider,
                api_key: config.api_key,
                model: config.model,
                qa_pairs: qaPairs,
                mode_name: config.mode,
                role: config.role,
                level_name: config.level,
                elapsed: formatTimer(elapsedSeconds),
                jd: config.jd,
                resume: config.resume,
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })
            
            const analyticsRes = await axios.post(`${apiBase}/coach/analytics`, {
                report_text: res.data.content,
                mode_name: config.mode,
                role: config.role,
                level_name: config.level,
                elapsed: formatTimer(elapsedSeconds),
                question_num: qaPairs.length,
                jd: config.jd,
                resume: config.resume,
                messages: qaPairs
            }, { headers: { Authorization: `Bearer ${token}` } })

            setTokens(t => t + (res.data.tokens || 0))
            onComplete(analyticsRes.data)
        } catch (err) {
            addToast(err.response?.data?.detail || 'Final report generation failed', 'error')
        } finally {
            setEvaluating(false)
        }
    }

    const isComplete = currentQIndex >= questions.length

    return (
        <div className="min-h-screen bg-black text-zinc-100 flex flex-col fade-in-up">
            {/* Classy Production Header */}
            <div className="border-b border-white/10 bg-zinc-950/80 backdrop-blur-xl px-6 py-3.5 flex items-center justify-between sticky top-0 z-20">
                <div className="flex items-center gap-4">
                    <button onClick={onExit} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-semibold text-zinc-300 border border-white/5 transition">
                        ← Exit Studio
                    </button>
                    <div className="h-4 w-px bg-white/10"></div>
                    <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-brand-400 animate-ping"></span>
                        <span className="text-xs font-extrabold uppercase tracking-widest text-brand-300">
                            Viva-Verse for {config.mode.replace('-', ' ')}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-6 text-xs font-mono">
                    <div className="flex items-center gap-1.5 text-zinc-400">
                        <span>⏱️</span> <span className="text-white font-bold">{formatTimer(elapsedSeconds)}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-zinc-400">
                        <span>🎯</span> <span className="text-white font-bold">Q{Math.min(currentQIndex + 1, questions.length)}/{questions.length}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-zinc-400">
                        <span>⚡</span> <span className="text-brand-400 font-bold">{tokens.toLocaleString()} tok</span>
                    </div>
                    <button
                        onClick={() => {
                            setTtsEnabled(!ttsEnabled)
                            if (ttsEnabled) window.speechSynthesis?.cancel()
                        }}
                        className={`px-2.5 py-1 rounded text-[10px] uppercase font-bold border transition ${ttsEnabled ? 'bg-brand-500/20 text-brand-300 border-brand-500/40' : 'bg-zinc-900 text-zinc-500 border-white/5'}`}
                    >
                        {ttsEnabled ? '🔊 Audio ON' : '🔇 Audio OFF'}
                    </button>
                </div>
            </div>

            {/* Chat Trajectory View */}
            <div className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 overflow-y-auto space-y-6">
                {messages.map((m, idx) => {
                    const isUser = m.role === 'user'
                    return (
                        <div key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'} fade-in-up`}>
                            <div className={`max-w-3xl rounded-2xl p-5 shadow-xl border ${isUser
                                    ? 'bg-white text-black border-white shadow-[0_4px_20px_rgba(255,255,255,0.1)] rounded-br-xs font-medium'
                                    : 'bg-zinc-900 text-zinc-100 border-zinc-800 rounded-bl-xs'
                                }`}>
                                {!isUser && (
                                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-zinc-800 text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                                        <span>🛡️</span> Antigravity Examiner · Production AI
                                    </div>
                                )}
                                {m.previewUrl && (
                                    <img src={m.previewUrl} alt="Attached sketch" className="max-h-48 rounded-lg mb-3 border border-zinc-300 shadow-md" />
                                )}
                                <div className="text-xs sm:text-sm whitespace-pre-wrap leading-relaxed font-normal">
                                    {m.content}
                                </div>
                            </div>
                        </div>
                    )
                })}

                {evaluating && (
                    <div className="flex justify-start fade-in-up">
                        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl rounded-bl-xs px-5 py-4 flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-brand-400 animate-bounce"></div>
                            <div className="w-2 h-2 rounded-full bg-brand-400 animate-bounce [animation-delay:0.2s]"></div>
                            <div className="w-2 h-2 rounded-full bg-brand-400 animate-bounce [animation-delay:0.4s]"></div>
                            <span className="text-xs text-brand-300 ml-1 font-bold">Evaluating full session & generating remediation plan...</span>
                        </div>
                    </div>
                )}
                <div ref={chatEndRef} />
            </div>

            {/* Classy Input Tray */}
            <div className="border-t border-zinc-800 bg-black p-4 sm:p-6 sticky bottom-0 z-20">
                <div className="max-w-5xl mx-auto space-y-4">
                    {/* Action Trays */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {isComplete && (
                                <button
                                    onClick={handleBatchEvaluate}
                                    disabled={evaluating}
                                    className="px-6 py-2.5 rounded-xl bg-green-600 hover:bg-green-500 text-white text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-50 shadow-[0_0_15px_rgba(16,185,129,0.3)] border border-green-400 uppercase tracking-wider"
                                >
                                    <span>🏁</span> Evaluate Session & Get Final Report
                                </button>
                            )}
                        </div>

                        {/* Attachment & Voice */}
                        <div className="flex items-center gap-2">
                            <label className={`px-3.5 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/5 text-xs font-medium cursor-pointer transition flex items-center gap-1.5 ${isComplete ? 'opacity-50 pointer-events-none' : ''}`}>
                                <span>📎</span> {attachedImage ? 'Sketch Attached' : 'Attach Sketch'}
                                <input type="file" onChange={handleImageUpload} accept="image/*" className="hidden" disabled={isComplete} />
                            </label>
                            <button
                                onClick={toggleMic}
                                disabled={isComplete}
                                className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border ${isListening
                                        ? 'bg-rose-500 text-white border-rose-400 animate-pulse shadow-[0_0_15px_rgba(244,63,94,0.5)]'
                                        : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-white/5'
                                    } ${isComplete ? 'opacity-50 pointer-events-none' : ''}`}
                            >
                                <span>🎙️</span> {isListening ? 'Listening...' : 'Voice Mic'}
                            </button>
                        </div>
                    </div>

                    {attachedImage && (
                        <div className="inline-flex items-center gap-2 bg-zinc-900 px-3 py-1.5 rounded-lg border border-zinc-700 text-xs text-zinc-200">
                            <span>🖼️ Diagram queued</span>
                            <button onClick={() => setAttachedImage(null)} className="text-zinc-400 hover:text-white ml-1 font-bold">✕</button>
                        </div>
                    )}

                    {/* Text Input */}
                    <div className="flex gap-3">
                        <textarea
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                            rows={2}
                            disabled={isComplete}
                            placeholder={isComplete ? "Session complete. Click 'Evaluate Session' to get your report." : `Type your defense to Q${currentQIndex + 1} (or click Voice Mic)...`}
                            className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500 transition-colors shadow-inner resize-none disabled:opacity-50"
                        />
                        <button
                            onClick={handleSend}
                            disabled={isComplete || (!input.trim() && !attachedImage)}
                            className="btn-primary px-8 flex items-center justify-center font-bold text-sm uppercase tracking-wider disabled:opacity-40"
                        >
                            Next →
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
