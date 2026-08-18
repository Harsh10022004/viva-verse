import { useState, useEffect } from 'react'
import CoachTerminal from './components/CoachTerminal'
import SetupStudio from './components/SetupStudio'
import CoachDashboard from './components/CoachDashboard'
import Toast from './components/Toast'
import LoginView from './components/LoginView'
import HistoryView from './components/HistoryView'
import InterviewExperiences from './components/InterviewExperiences'

const API = 'http://localhost:8000/api/v1'

function App() {
    const [view, setView] = useState('studio') // 'login' | 'studio' | 'coach' | 'dashboard' | 'history'
    const [analytics, setAnalytics] = useState(null)
    const [toasts, setToasts] = useState([])
    const [token, setToken] = useState('free-passthrough-token')
    const [user, setUser] = useState({ id: 1, username: 'Candidate Explorer', role: 'student' })
    const [coachConfig, setCoachConfig] = useState(null)
    const [byokConfig, setByokConfig] = useState(null)

    const handleLogin = (newToken, userData) => {
        localStorage.setItem('token', newToken);
        setToken(newToken);
        setUser(userData);
        setView('studio');
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
        setView('login');
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

    const handleRestart = () => {
        setView('studio')
        setAnalytics(null)
        setCoachConfig(null)
    }

    const handleReviewSession = (sessionData) => {
        setAnalytics(sessionData);
        setView('dashboard');
    }

    return (
        <div className="min-h-screen relative bg-black text-zinc-100">
            <Toast toasts={toasts} removeToast={removeToast} />
            <div className="bg-particles" />

            <header className="relative z-10 border-b border-zinc-800 bg-black/95 backdrop-blur-xl">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3 cursor-pointer group" onClick={() => user && setView('studio')}>
                        <div className="w-9 h-9 rounded-xl bg-zinc-900 border border-white/20 flex items-center justify-center text-white font-black text-base shadow-sm group-hover:bg-zinc-800 transition">
                            V
                        </div>
                        <div>
                            <h1 className="text-base font-extrabold text-white tracking-tight">The Viva Verse</h1>
                            <p className="text-[10px] text-zinc-400 uppercase tracking-widest font-bold">Production AI Interrogation Studio</p>
                        </div>
                    </div>

                    {user ? (
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setView('studio')}
                                className={`text-xs font-bold px-3.5 py-2 rounded-xl border transition-all ${view === 'studio' ? 'bg-white text-black border-white shadow-[0_0_15px_rgba(255,255,255,0.2)]' : 'bg-transparent text-zinc-400 border-zinc-800 hover:text-white hover:border-zinc-700'}`}
                            >
                                ⚡ Setup Studio
                            </button>
                            <button
                                onClick={() => setView('history')}
                                className={`text-xs font-bold px-3.5 py-2 rounded-xl border transition-all ${view === 'history' ? 'bg-white text-black border-white shadow-[0_0_15px_rgba(255,255,255,0.2)]' : 'bg-transparent text-zinc-400 border-zinc-800 hover:text-white hover:border-zinc-700'}`}
                            >
                                📜 Archives
                            </button>
                            <button
                                onClick={() => setView('experiences')}
                                className={`text-xs font-bold px-3.5 py-2 rounded-xl border transition-all ${view === 'experiences' ? 'bg-white text-black border-white shadow-[0_0_15px_rgba(255,255,255,0.2)]' : 'bg-transparent text-zinc-400 border-zinc-800 hover:text-white hover:border-zinc-700'}`}
                            >
                                🏢 Interview Experiences
                            </button>
                            <div className="h-4 w-px bg-zinc-800"></div>
                            <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-full bg-zinc-900 text-zinc-200 flex items-center justify-center text-xs font-extrabold border border-zinc-700 uppercase">
                                    {user.username.charAt(0)}
                                </div>
                                <span className="text-xs font-semibold text-zinc-300 hidden sm:inline">{user.username}</span>
                            </div>
                            <button onClick={handleLogout} className="text-xs text-zinc-500 hover:text-rose-400 font-bold ml-1 transition">
                                Logout
                            </button>
                        </div>
                    ) : null}
                </div>
            </header>

            <main className="relative z-10">
                {view === 'login' && <LoginView apiBase={API} onLogin={handleLogin} addToast={addToast} />}
                {view === 'studio' && (
                    <SetupStudio
                        apiBase={API}
                        token={token}
                        user={user}
                        onStartCoach={(cfg) => { setCoachConfig(cfg); setView('coach'); }}
                        addToast={addToast}
                    />
                )}
                {view === 'coach' && coachConfig && (
                    <CoachTerminal
                        apiBase={API}
                        token={token}
                        config={coachConfig}
                        onExit={() => setView('studio')}
                        onComplete={(data) => { setAnalytics(data); setView('dashboard'); }}
                        addToast={addToast}
                    />
                )}
                {view === 'history' && <HistoryView apiBase={API} token={token} onReviewSession={handleReviewSession} onBack={() => setView('studio')} addToast={addToast} />}
                {view === 'dashboard' && <CoachDashboard apiBase={API} token={token} analytics={analytics} onRestart={handleRestart} />}
                {view === 'experiences' && <InterviewExperiences apiBase={API} token={token} user={user} addToast={addToast} onBack={() => setView('studio')} />}
            </main>
        </div>
    )
}

export default App
