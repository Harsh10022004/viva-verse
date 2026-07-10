import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
const voiceSupported = !!SpeechRecognition

export default function CoachTerminal({ apiBase, token, config, onExit, addToast }) {
    const [messages, setMessages] = useState([
        { role: 'coach', content: config.initial_message }
    ])
    const [input, setInput] = useState('')
    const [thinking, setThinking] = useState(false)
    const [tokens, setTokens] = useState(config.initial_tokens || 0)
    const [questionNum, setQuestionNum] = useState(1)
    const [elapsedSeconds, setElapsedSeconds] = useState(0)
    const [ttsEnabled, setTtsEnabled] = useState(true)
    const [isListening, setIsListening] = useState(false)
    const [attachedImage, setAttachedImage] = useState(null) // {base64, mimeType, previewUrl}
    const [scorecardModal, setScorecardModal] = useState(null)
    const [finalReportModal, setFinalReportModal] = useState(null)
    const [evaluating, setEvaluating] = useState(false)

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
    }, [messages, thinking])

    // Speak initial message
    useEffect(() => {
        if (ttsEnabled && config.initial_message) {
            speakText(config.initial_message)
        }
    }, [])

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

    const handleSend = async () => {
        if (!input.trim() && !attachedImage) return
        if (thinking) return

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
        setMessages(newMessages)
        setAttachedImage(null)
        setThinking(true)

        try {
            const res = await axios.post(`${apiBase}/coach/chat`, {
                provider: config.provider,
                api_key: config.api_key,
                model: config.model,
                messages: newMessages,
                system_prompt: config.system_prompt
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })

            const replyText = res.data.content
            const newTokens = res.data.tokens || 0

            setMessages([...newMessages, { role: 'coach', content: replyText }])
            setTokens(t => t + newTokens)
            if (/Q\d+|question\s*\d+/i.test(replyText)) setQuestionNum(q => q + 1)

            speakText(replyText)
        } catch (err) {
            addToast(err.response?.data?.detail || 'Inference error. Verify API Key or rate limits.', 'error')
        } finally {
            setThinking(false)
        }
    }

    const handleScorecard = async () => {
        setEvaluating(true)
        addToast('Analyzing trajectory against hiring bar...', 'info')
        try {
            const res = await axios.post(`${apiBase}/coach/scorecard`, {
                provider: config.provider,
                api_key: config.api_key,
                model: config.model,
                messages,
                elapsed: formatTimer(elapsedSeconds),
                question_num: questionNum,
                system_prompt: config.system_prompt
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setScorecardModal(res.data.content)
            setTokens(t => t + (res.data.tokens || 0))
        } catch (err) {
            addToast(err.response?.data?.detail || 'Scorecard analysis failed', 'error')
        } finally {
            setEvaluating(false)
        }
    }

    const handleEndReport = async () => {
        setEvaluating(true)
        addToast('Generating exhaustive final evaluation report...', 'info')
        try {
            const res = await axios.post(`${apiBase}/coach/end-report`, {
                provider: config.provider,
                api_key: config.api_key,
                model: config.model,
                messages,
                mode_name: config.mode,
                role: config.role,
                level_name: config.level,
                elapsed: formatTimer(elapsedSeconds),
                question_num: questionNum,
                jd: config.jd,
                resume: config.resume,
                system_prompt: config.system_prompt
            }, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setFinalReportModal(res.data.content)
            setTokens(t => t + (res.data.tokens || 0))
        } catch (err) {
            addToast(err.response?.data?.detail || 'Final report generation failed', 'error')
        } finally {
            setEvaluating(false)
        }
    }

    const downloadReportTxt = () => {
        if (!finalReportModal) return
        const header = `Viva-Verse Production Evaluation Report\n========================================\nArena: ${config.mode.toUpperCase()}\nCandidate Role: ${config.role} (${config.level})\nDuration: ${formatTimer(elapsedSeconds)}\nQuestions: ${questionNum}\n========================================\n\n`
        const blob = new Blob([header + finalReportModal], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `VivaVerse-Report-${config.role.replace(/\s+/g, '_')}.txt`
        a.click()
        URL.revokeObjectURL(url)
    }

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
                        <span>🎯</span> <span className="text-white font-bold">Q{questionNum}</span>
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

                {thinking && (
                    <div className="flex justify-start fade-in-up">
                        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl rounded-bl-xs px-5 py-4 flex items-center gap-3">
                            <div className="w-2 h-2 rounded-full bg-white animate-bounce"></div>
                            <div className="w-2 h-2 rounded-full bg-white animate-bounce [animation-delay:0.2s]"></div>
                            <div className="w-2 h-2 rounded-full bg-white animate-bounce [animation-delay:0.4s]"></div>
                            <span className="text-xs text-zinc-400 ml-1">Interrogating response & formulating probe...</span>
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
                            <button
                                onClick={handleScorecard}
                                disabled={evaluating}
                                className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 text-xs font-medium transition flex items-center gap-1.5 disabled:opacity-50"
                            >
                                <span>📊</span> Mid-Session Scorecard
                            </button>
                            <button
                                onClick={handleEndReport}
                                disabled={evaluating}
                                className="px-4 py-2 rounded-xl bg-white text-black hover:bg-zinc-200 border border-white text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-50 shadow-sm"
                            >
                                <span>🏁</span> End & Get Final Report
                            </button>
                        </div>

                        {/* Attachment & Voice */}
                        <div className="flex items-center gap-2">
                            <label className="px-3.5 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/5 text-xs font-medium cursor-pointer transition flex items-center gap-1.5">
                                <span>📎</span> {attachedImage ? 'Sketch Attached' : 'Attach Sketch'}
                                <input type="file" onChange={handleImageUpload} accept="image/*" className="hidden" />
                            </label>
                            <button
                                onClick={toggleMic}
                                className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-1.5 border ${isListening
                                        ? 'bg-rose-500 text-white border-rose-400 animate-pulse shadow-[0_0_15px_rgba(244,63,94,0.5)]'
                                        : 'bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border-white/5'
                                    }`}
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
                            placeholder={`Type your defense to Q${questionNum} (or click Voice Mic)...`}
                            className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-500 transition-colors shadow-inner resize-none"
                        />
                        <button
                            onClick={handleSend}
                            disabled={thinking || (!input.trim() && !attachedImage)}
                            className="btn-primary px-8 flex items-center justify-center font-bold text-sm uppercase tracking-wider disabled:opacity-40"
                        >
                            Submit →
                        </button>
                    </div>
                </div>
            </div>

            {/* Mid-Session Scorecard Modal */}
            {scorecardModal && (
                <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 fade-in-up">
                    <div className="bg-zinc-950 max-w-2xl w-full max-h-[85vh] overflow-y-auto rounded-3xl p-6 sm:p-8 border border-zinc-800 relative shadow-2xl">
                        <button onClick={() => setScorecardModal(null)} className="absolute top-6 right-6 text-zinc-500 hover:text-white text-lg font-bold">✕</button>
                        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                            <span>📊</span> Mid-Session Progress Shading
                        </h3>
                        <div className="text-xs sm:text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed bg-black p-5 rounded-2xl border border-zinc-900 font-mono">
                            {scorecardModal}
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button onClick={() => setScorecardModal(null)} className="btn-primary px-6 py-2.5 text-xs uppercase font-bold">
                                Resume Arena →
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Final Exhaustive Report Modal */}
            {finalReportModal && (
                <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-xl flex items-center justify-center p-4 fade-in-up">
                    <div className="bg-zinc-950 max-w-3xl w-full max-h-[90vh] overflow-y-auto rounded-3xl p-6 sm:p-10 border border-zinc-800 relative shadow-[0_0_50px_rgba(0,0,0,0.9)]">
                        <button onClick={onExit} className="absolute top-6 right-6 text-zinc-500 hover:text-white text-lg font-bold">✕</button>
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white text-[10px] font-bold uppercase mb-4 tracking-widest border border-white/10">
                            🏁 Final Verdict & Scorecard
                        </div>
                        <h3 className="text-2xl sm:text-3xl font-extrabold text-white mb-6 tracking-tight">
                            Executive Interrogation Report
                        </h3>
                        <div className="text-xs sm:text-sm text-zinc-200 whitespace-pre-wrap leading-relaxed bg-black p-6 rounded-2xl border border-zinc-900 font-mono mb-8">
                            {finalReportModal}
                        </div>
                        <div className="flex items-center justify-between">
                            <button onClick={downloadReportTxt} className="px-6 py-3 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 font-bold text-xs uppercase tracking-wider border border-zinc-800 transition flex items-center gap-2">
                                <span>📥</span> Download Text Report (.txt)
                            </button>
                            <button onClick={onExit} className="btn-primary px-8 py-3 text-xs uppercase font-bold">
                                Return to Setup Studio
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
