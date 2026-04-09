import { useState } from 'react'
import UploadView from './components/UploadView'
import VivaTerminal from './components/VivaTerminal'
import Dashboard from './components/Dashboard'
import Toast from './components/Toast'

const API = 'http://localhost:8000/api/v1'

function App() {
    const [view, setView] = useState('upload') // 'upload' | 'viva' | 'dashboard'
    const [sessionId, setSessionId] = useState(null)
    const [questions, setQuestions] = useState([])
    const [analytics, setAnalytics] = useState(null)
    const [toasts, setToasts] = useState([])

    const addToast = (message, type = 'info') => {
        const id = Date.now()
        setToasts(prev => [...prev, { id, message, type }])
        setTimeout(() => removeToast(id), 5000)
    }

    const removeToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id))
    }

    const handleEngineReady = (data) => {
        setSessionId(data.session_id)
        setQuestions(data.questions)
        setView('viva')
    }

    const handleVivaComplete = (data) => {
        setAnalytics(data)
        setView('dashboard')
    }

    const handleRestart = () => {
        setView('upload')
        setSessionId(null)
        setQuestions([])
        setAnalytics(null)
    }

    return (
        <div className="min-h-screen relative">
            <Toast toasts={toasts} removeToast={removeToast} />
            {/* Background particles */}
            <div className="bg-particles" />

            {/* Header */}
            <header className="relative z-10 border-b border-surface-600/50 backdrop-blur-md bg-surface-900/50">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-purple-500 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-brand-500/30">
                            V
                        </div>
                        <div>
                            <h1 className="text-xl font-bold gradient-text">The Viva Verse</h1>
                            <p className="text-xs text-gray-500 font-mono">AI-Powered Semantic Examination</p>
                        </div>
                    </div>

                    {/* Progress Steps */}
                    <div className="flex items-center gap-2">
                        {['Upload', 'Viva', 'Dashboard'].map((step, i) => {
                            const stepKey = ['upload', 'viva', 'dashboard'][i]
                            const isActive = view === stepKey
                            const isDone = ['upload', 'viva', 'dashboard'].indexOf(view) > i
                            return (
                                <div key={step} className="flex items-center gap-2">
                                    {i > 0 && <div className={`w-8 h-px ${isDone ? 'bg-brand-500' : 'bg-surface-600'}`} />}
                                    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${isActive
                                        ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                                        : isDone
                                            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                            : 'bg-surface-700 text-gray-500 border border-surface-600'
                                        }`}>
                                        {isDone ? (
                                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                        ) : (
                                            <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-brand-400' : 'bg-gray-600'}`} />
                                        )}
                                        {step}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="relative z-10">
                {view === 'upload' && <UploadView apiBase={API} onReady={handleEngineReady} addToast={addToast} />}
                {view === 'viva' && (
                    <VivaTerminal
                        apiBase={API}
                        sessionId={sessionId}
                        questions={questions}
                        onComplete={handleVivaComplete}
                        addToast={addToast}
                    />
                )}
                {view === 'dashboard' && <Dashboard analytics={analytics} onRestart={handleRestart} />}
            </main>
        </div>
    )
}

export default App
