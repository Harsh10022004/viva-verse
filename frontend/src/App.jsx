import { useState, useEffect } from 'react'
import UploadView from './components/UploadView'
import VivaTerminal from './components/VivaTerminal'
import Dashboard from './components/Dashboard'
import Toast from './components/Toast'
import LoginView from './components/LoginView'
import HistoryView from './components/HistoryView'

const API = 'http://localhost:8000/api/v1'

function App() {
    const [view, setView] = useState('login') // 'login' | 'upload' | 'viva' | 'dashboard' | 'history'
    const [sessionId, setSessionId] = useState(null)
    const [questions, setQuestions] = useState([])
    const [analytics, setAnalytics] = useState(null)
    const [toasts, setToasts] = useState([])
    const [token, setToken] = useState(localStorage.getItem('token') || null)
    const [user, setUser] = useState(null)

    useEffect(() => {
        if (token) {
            // Verify token / get me
            fetch(`${API}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.ok ? res.json() : Promise.reject())
            .then(data => {
                setUser(data);
                if(view === 'login') setView('upload');
            })
            .catch(() => {
                handleLogout();
            });
        } else {
            setView('login');
        }
    }, [token]);

    const handleLogin = (newToken, userData) => {
        localStorage.setItem('token', newToken);
        setToken(newToken);
        setUser(userData);
        setView('upload');
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
        setView('login');
        setSessionId(null);
        setAnalytics(null);
    };

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

    const handleReviewSession = (sessionData) => {
        setAnalytics(sessionData);
        setView('dashboard');
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

                    {/* Progress Steps or Auth Profile */}
                    {user ? (
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setView('history')}
                                className={`text-xs font-semibold px-3 py-1.5 rounded-md border transition-all ${view === 'history' ? 'bg-surface-800 text-blue-400 border-blue-500/50' : 'bg-transparent text-gray-400 border-surface-700 hover:text-gray-200'}`}
                            >
                                My History
                            </button>
                            <div className="h-4 w-px bg-surface-700"></div>
                            <div className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold border border-blue-500/30 uppercase">
                                    {user.username.charAt(0)}
                                </div>
                                <span className="text-xs font-medium text-gray-300">{user.username}</span>
                            </div>
                            <button onClick={handleLogout} className="text-xs text-red-400 hover:text-red-300 font-medium ml-2">
                                Logout
                            </button>
                        </div>
                    ) : null}
                </div>
            </header>

            {/* Main Content */}
            <main className="relative z-10">
                {view === 'login' && <LoginView apiBase={API} onLogin={handleLogin} addToast={addToast} />}
                {view === 'history' && <HistoryView apiBase={API} token={token} onReviewSession={handleReviewSession} onBack={() => setView('upload')} addToast={addToast} />}
                {view === 'upload' && <UploadView apiBase={API} token={token} onReady={handleEngineReady} addToast={addToast} />}
                {view === 'viva' && (
                    <VivaTerminal
                        apiBase={API}
                        token={token}
                        sessionId={sessionId}
                        questions={questions}
                        onComplete={handleVivaComplete}
                        addToast={addToast}
                    />
                )}
                {view === 'dashboard' && <Dashboard apiBase={API} token={token} analytics={analytics} onRestart={handleRestart} />}
            </main>
        </div>
    )
}

export default App
