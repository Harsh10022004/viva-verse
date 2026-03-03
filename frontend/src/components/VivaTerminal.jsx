import { useState } from 'react'
import axios from 'axios'

export default function VivaTerminal({ apiBase, sessionId, questions, onComplete, addToast }) {
    const [currentIdx, setCurrentIdx] = useState(0)
    const [answer, setAnswer] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [feedback, setFeedback] = useState(null)
    const [history, setHistory] = useState([]) // array of {question, answer, score, critique}
    const [finalizing, setFinalizing] = useState(false)

    const current = questions[currentIdx]
    const isLast = currentIdx === questions.length - 1
    const progress = ((currentIdx + (feedback ? 1 : 0)) / questions.length) * 100

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
            addToast(`Answer submitted! Score: ${fb.score}%`, 'success')
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message
            setFeedback({ score: 0, critique: `Error: ${errorMsg}` })
            addToast(`Failed to evaluate answer: ${errorMsg}`, 'error')
        } finally {
            setSubmitting(false)
        }
    }

    const handleNext = async () => {
        if (isLast) {
            // Finalize
            setFinalizing(true)
            try {
                const res = await axios.post(`${apiBase}/finalize`, { session_id: sessionId })
                addToast('Viva finalized. Generating your dashboard!', 'success')
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
        if (score >= 70) return 'text-green-400'
        if (score >= 40) return 'text-yellow-400'
        return 'text-red-400'
    }

    const getScoreBg = (score) => {
        if (score >= 70) return 'bg-green-500/10 border-green-500/30'
        if (score >= 40) return 'bg-yellow-500/10 border-yellow-500/30'
        return 'bg-red-500/10 border-red-500/30'
    }

    return (
        <div className="max-w-4xl mx-auto px-6 py-10 fade-in-up">
            {/* Terminal Header */}
            <div className="glass rounded-2xl overflow-hidden">
                {/* Title Bar */}
                <div className="flex items-center gap-2 px-5 py-3 bg-surface-800/80 border-b border-surface-600/50">
                    <div className="flex gap-1.5">
                        <div className="w-3 h-3 rounded-full bg-red-500/80" />
                        <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                        <div className="w-3 h-3 rounded-full bg-green-500/80" />
                    </div>
                    <div className="flex-1 text-center">
                        <span className="text-xs font-mono text-gray-500">
                            viva-session://{sessionId?.slice(0, 8)}
                        </span>
                    </div>
                    <span className="text-xs font-mono text-gray-600">
                        Q {currentIdx + 1}/{questions.length}
                    </span>
                </div>

                {/* Progress Bar */}
                <div className="h-0.5 bg-surface-700">
                    <div
                        className="h-full bg-gradient-to-r from-brand-500 to-purple-500 transition-all duration-500 ease-out"
                        style={{ width: `${progress}%` }}
                    />
                </div>

                {/* Terminal Content */}
                <div className="p-6 font-mono text-sm">
                    {/* Past interactions (collapsed) */}
                    {history.length > 0 && (
                        <div className="mb-6 space-y-3 max-h-48 overflow-y-auto pr-2">
                            {history.map((h, i) => (
                                <div key={i} className="opacity-50">
                                    <p className="text-brand-400">
                                        <span className="text-gray-600">[Q{i + 1}]</span> {h.question}
                                    </p>
                                    <p className="text-gray-400 pl-4">→ {h.answer.slice(0, 80)}...</p>
                                    <p className={`pl-4 ${getScoreColor(h.score)}`}>
                                        ✓ Score: {h.score}%
                                    </p>
                                </div>
                            ))}
                            <div className="border-t border-surface-600/30 mt-3" />
                        </div>
                    )}

                    {/* Current Question */}
                    <div className="mb-6">
                        <div className="flex items-start gap-3">
                            <span className="text-brand-400 font-bold mt-0.5">❯</span>
                            <div>
                                <p className="text-gray-500 text-xs mb-1">SYSTEM-LEAD — Question {currentIdx + 1} of {questions.length}</p>
                                <p className="text-gray-200 leading-relaxed text-base font-sans">
                                    {current.question}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Answer Input or Feedback */}
                    {!feedback ? (
                        <div className="mt-4">
                            <div className="flex items-start gap-3">
                                <span className="text-green-400 font-bold mt-3">$</span>
                                <div className="flex-1">
                                    <textarea
                                        className="w-full bg-surface-800/60 border border-surface-600/50 rounded-xl px-4 py-3 text-gray-200 font-sans text-sm
                      focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20
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
                                        <p className="text-gray-600 text-xs">Press Ctrl+Enter to submit</p>
                                        <button
                                            onClick={handleSubmit}
                                            disabled={submitting}
                                            className="btn-glow px-6 py-2 rounded-lg text-white text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:transform-none"
                                        >
                                            {submitting ? (
                                                <span className="flex items-center gap-2">
                                                    <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                    Evaluating...
                                                </span>
                                            ) : (
                                                <span className="relative z-10">Submit Answer</span>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="mt-4 fade-in-up">
                            {/* Score Card */}
                            <div className={`rounded-xl border p-5 ${getScoreBg(feedback.score)}`}>
                                <div className="flex items-center gap-4 mb-3">
                                    <div className={`text-4xl font-extrabold score-pop ${getScoreColor(feedback.score)}`}>
                                        {feedback.score}%
                                    </div>
                                    <div className="h-10 w-px bg-surface-600" />
                                    <div>
                                        <p className="text-gray-400 text-xs uppercase tracking-wider mb-1">Semantic Similarity</p>
                                        <p className="text-sm text-gray-300 leading-relaxed font-sans">{feedback.critique}</p>
                                    </div>
                                </div>

                                <button
                                    onClick={handleNext}
                                    disabled={finalizing}
                                    className="btn-glow mt-3 px-6 py-2.5 rounded-lg text-white text-sm font-semibold w-full"
                                >
                                    {finalizing ? (
                                        <span className="relative z-10 flex items-center justify-center gap-2">
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            Generating Analytics...
                                        </span>
                                    ) : (
                                        <span className="relative z-10">
                                            {isLast ? '📊 View Dashboard' : `Next Question →`}
                                        </span>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
