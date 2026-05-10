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
            <header className="relative z-10 border-b border-surface-800 bg-black/50 backdrop-blur-md">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-surface-800 border border-surface-700 flex items-center justify-center text-gray-100 font-bold text-sm">
                            V
                        </div>
                        <div>
                            <h1 className="text-base font-semibold text-gray-100">The Viva Verse</h1>
                            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-medium">Semantic Examination</p>
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
                                    {i > 0 && <div className={`w-6 h-px ${isDone ? 'bg-gray-400' : 'bg-surface-800'}`} />}
                                    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold transition-all duration-300 ${isActive
                                        ? 'bg-surface-800 text-gray-100 border border-surface-600'
                                        : isDone
                                            ? 'text-gray-400'
                                            : 'text-gray-600'
                                        }`}>
                                        {isDone ? (
                                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                            </svg>
                                        ) : (
                                            <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-gray-300' : 'bg-surface-700'}`} />
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
