import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

const SpeechRecognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
const voiceSupported = !!SpeechRecognition

export default function VivaTerminal({ apiBase, sessionId, questions: initialQuestions, onComplete, addToast }) {
    const [localQuestions, setLocalQuestions] = useState(initialQuestions)
    const [currentIdx, setCurrentIdx] = useState(0)
    const [answer, setAnswer] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [feedback, setFeedback] = useState(null)
    const [history, setHistory] = useState([]) 
    const [finalizing, setFinalizing] = useState(false)
    const [isComplete, setIsComplete] = useState(false)
    const [isListening, setIsListening] = useState(false)
    const recognitionRef = useRef(null)
    const baseAnswerRef = useRef('')
    const userStoppedRef = useRef(false)

    const toggleVoice = () => {
        if (!voiceSupported) {
            addToast('Voice input not supported in this browser. Try Chrome or Edge.', 'warning')
            return
        }
        if (isListening) {
            userStoppedRef.current = true
            recognitionRef.current?.stop()
            return
        }
        userStoppedRef.current = false
        baseAnswerRef.current = answer ? answer.trim() + ' ' : ''
        startRecognition()
        setIsListening(true)
    }

    const startRecognition = () => {
        const rec = new SpeechRecognition()
        rec.continuous = false
        rec.interimResults = true
        rec.maxAlternatives = 1
        rec.lang = 'en-US'

        rec.onresult = (event) => {
            let interim = '', finalText = ''
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const t = event.results[i][0].transcript
                if (event.results[i].isFinal) finalText += t
                else interim += t
            }
            if (finalText) baseAnswerRef.current += finalText + ' '
            setAnswer(baseAnswerRef.current + interim)
        }
        rec.onerror = (e) => {
            if (e.error === 'no-speech' || e.error === 'aborted') return
            addToast(`Mic error: ${e.error}`, 'error')
            userStoppedRef.current = true
        }
        rec.onend = () => {
            if (userStoppedRef.current) {
                setIsListening(false)
            } else {
                setTimeout(() => {
                    if (userStoppedRef.current) return
                    try { startRecognition() } catch { setIsListening(false) }
                }, 250)
            }
        }
        recognitionRef.current = rec
        try { rec.start() } catch { /* ignore double-start */ }
    }

    useEffect(() => () => { userStoppedRef.current = true; recognitionRef.current?.stop() }, [])
    useEffect(() => { if (isListening) { userStoppedRef.current = true; recognitionRef.current?.stop() } }, [currentIdx])

    const current = localQuestions[currentIdx]
    const isLast = isComplete || (currentIdx === localQuestions.length - 1 && !feedback?.next_question)

    const progress = ((currentIdx + (feedback ? 1 : 0)) / (localQuestions.length + (feedback?.next_question ? 1 : 0))) * 100

    const handleSubmit = async () => {
        if (submitting) return

        if (!answer.trim()) {
            addToast('Please provide the text in the response box', 'warning')
            return
        }

        setSubmitting(true)

        try {
            const res = await axios.post(`${apiBase}/submit-answer`, {
                session_id: sessionId,
                question_id: current.id,
                answer: answer,
            })

            const fb = res.data
            setFeedback(fb)
            setHistory(prev => [...prev, {
                question: current.question,
                answer: answer,
                score: fb.score,
                critique: fb.critique,
            }])
            addToast(`Answer evaluated! Score: ${fb.score}%`, 'success')

            if (fb.next_question) {
                setLocalQuestions(prev => [...prev, fb.next_question])
            }
            if (fb.is_complete) {
                setIsComplete(true)
            }

        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message
            setFeedback({ score: 0, critique: `Error: ${errorMsg}` })
            addToast(`Failed to evaluate answer: ${errorMsg}`, 'error')
        } finally {
            setSubmitting(false)
        }
    }

    const handleNext = async () => {
        if (isLast || isComplete) {
            setFinalizing(true)
            try {
                const res = await axios.post(`${apiBase}/finalize`, { session_id: sessionId })
                addToast('Viva finalized. Generating your 3D Dashboard!', 'success')
                onComplete(res.data)
            } catch (err) {
                console.error('Finalize error:', err)
                const errorMsg = err.response?.data?.detail || err.message
                addToast(`Finalization failed: ${errorMsg}`, 'error')
                setFinalizing(false)
            }
        } else {
            setCurrentIdx(prev => prev + 1)
            setAnswer('')
            setFeedback(null)
        }
    }

    const getScoreColor = (score) => {
        if (score >= 75) return 'text-green-400'
        if (score >= 45) return 'text-yellow-400'
        return 'text-red-400'
    }

    const getScoreBg = (score) => {
        if (score >= 75) return 'bg-green-500/10 border-green-500/30 shadow-[0_0_20px_rgba(34,197,94,0.15)]'
        if (score >= 45) return 'bg-yellow-500/10 border-yellow-500/30 shadow-[0_0_20px_rgba(234,179,8,0.15)]'
        return 'bg-red-500/10 border-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.15)]'
    }

    return (
        <div className="max-w-3xl mx-auto px-4 py-8 fade-in-up">
            {/* Terminal Header */}
            <div className="bg-surface-900 border border-surface-700 rounded-2xl overflow-hidden shadow-2xl">
                {/* Title Bar */}
                <div className="flex items-center justify-between px-5 py-3 bg-surface-800/50 border-b border-surface-700">
                    <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full bg-surface-600" />
                        <div className="w-2.5 h-2.5 rounded-full bg-surface-600" />
                        <div className="w-2.5 h-2.5 rounded-full bg-surface-600" />
                    </div>
                    <div className="text-xs font-medium text-gray-400">
                        Session {sessionId?.slice(0, 6)}
                    </div>
                    <div className="text-xs font-semibold text-gray-500 bg-surface-800 px-2 py-0.5 rounded border border-surface-700">
                        Question {currentIdx + 1} of {localQuestions.length}
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="h-0.5 bg-surface-800">
                    <div
                        className="h-full bg-brand-500 transition-all duration-500 ease-out"
                        style={{ width: `${Math.min(100, progress)}%` }}
                    />
                </div>

                {/* Terminal Content */}
                <div className="p-6 sm:p-8 bg-surface-900">
                    
                    {/* Past interactions (collapsed) */}
                    {history.length > 0 && (
                        <div className="mb-8 space-y-4 max-h-48 overflow-y-auto pr-3 scrollbar-thin">
                            {history.map((h, i) => (
                                <div key={i} className="opacity-60 hover:opacity-100 transition-opacity bg-surface-800/50 p-4 rounded-xl border border-surface-700/50">
                                    <p className="text-brand-300 font-bold mb-1">
                                        <span className="text-brand-500/50">[{i + 1}]</span> {h.question}
                                    </p>
                                    <p className="text-gray-400 pl-6 mb-2">→ {h.answer.slice(0, 100)}{h.answer.length > 100 ? '...' : ''}</p>
                                    <div className={`pl-6 font-bold ${getScoreColor(h.score)} flex items-center gap-2`}>
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                        EVAL SCORE: {h.score}%
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Current Question */}
                    <div className="mb-8 slide-in-right">
                        <div className="flex items-start gap-4">
                            <div className="w-8 h-8 rounded-lg bg-surface-800 border border-surface-700 flex items-center justify-center flex-shrink-0 text-brand-400">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
                            </div>
                            <div className="flex-1 pt-1">
                                <p className="text-gray-100 text-[15px] leading-relaxed">
                                    {current?.question}
                                </p>
                                {current?.context_label && (
                                    <div className="mt-3 inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium text-gray-500 bg-surface-800 border border-surface-700">
                                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                        Context: {current.context_label}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Answer Input or Feedback */}
                    {!feedback ? (
                        <div className="mt-6 slide-in-right" style={{ animationDelay: '0.1s' }}>
                            <div className="flex items-start gap-4">
                                <div className="w-8 h-8 rounded-full bg-surface-800 border border-surface-700 flex items-center justify-center flex-shrink-0 text-gray-400 text-xs font-semibold">
                                    You
                                </div>
                                <div className="flex-1">
                                    <textarea
                                        className="w-full bg-surface-900 border border-surface-700 rounded-xl px-4 py-3 text-[15px] text-gray-100 
                                            focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50
                                            resize-none transition-all placeholder:text-gray-600"
                                        rows={4}
                                        placeholder="Type your answer here..."
                                        value={answer}
                                        onChange={(e) => setAnswer(e.target.value)}
                                        onKeyDown={(e) => { if (e.key === 'Enter' && e.ctrlKey) handleSubmit() }}
                                        disabled={submitting}
                                        autoFocus
                                    />
                                    <div className="flex items-center justify-between mt-3">
                                        <div className="text-gray-500 text-xs">
                                            <kbd className="font-sans px-1.5 py-0.5 bg-surface-800 rounded border border-surface-700 mr-1">⌘</kbd>
                                            <kbd className="font-sans px-1.5 py-0.5 bg-surface-800 rounded border border-surface-700">Enter</kbd> to submit
                                        </div>
                                        <div className="flex items-center">
                                            {voiceSupported && (
                                                <button
                                                    onClick={toggleVoice}
                                                    disabled={submitting}
                                                    title={isListening ? 'Stop recording' : 'Start voice input'}
                                                    className={`p-2 rounded-lg border transition-all mr-2 ${
                                                        isListening
                                                            ? 'bg-red-500/20 border-red-500/50 text-red-400 animate-pulse'
                                                            : 'bg-surface-800 border-surface-700 text-gray-400 hover:text-brand-400 hover:border-brand-500/50'
                                                    }`}
                                                >
                                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                        <rect x="9" y="2" width="6" height="12" rx="3"/>
                                                        <path d="M5 10v2a7 7 0 0 0 14 0v-2"/>
                                                        <line x1="12" y1="19" x2="12" y2="22"/>
                                                    </svg>
                                                </button>
                                            )}
                                            <button
                                                onClick={handleSubmit}
                                                disabled={submitting}
                                                className="btn-glow px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
                                            >
                                                {submitting ? 'Evaluating...' : 'Submit'}
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="mt-8 slide-in-right border-t border-surface-800 pt-6">
                            {/* Minimal Score Card */}
                            <div className="flex items-start gap-6 mb-6">
                                <div className="text-center shrink-0">
                                    <div className={`text-4xl font-bold tracking-tight ${getScoreColor(feedback.score)}`}>
                                        {feedback.score}<span className="text-xl text-gray-500">%</span>
                                    </div>
                                    <div className="text-[10px] uppercase font-semibold text-gray-500 mt-1">Score</div>
                                </div>
                                <div className="w-px bg-surface-700 self-stretch hidden sm:block" />
                                <div className="flex-1">
                                    <p className="text-[15px] text-gray-300 leading-relaxed">{feedback.critique}</p>
                                </div>
                            </div>

                            <div className="flex justify-end">
                                <button
                                    onClick={handleNext}
                                    disabled={finalizing}
                                    className="btn-glow px-6 py-2.5 rounded-lg text-sm font-medium"
                                >
                                    {finalizing ? 'Generating Report...' : (isLast ? 'View Dashboard' : 'Next Question')}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
