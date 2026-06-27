import React, { useState } from 'react';

const LoginView = ({ apiBase, onLogin, addToast }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const response = await fetch(`${apiBase}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            
            if (response.ok) {
                addToast('Login successful!', 'success');
                onLogin(data.access_token, data.user);
            } else {
                addToast(data.detail || 'Login failed', 'error');
            }
        } catch (error) {
            addToast('Network error during login', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-[80vh] flex items-center justify-center px-4 relative z-10">
            <div className="w-full max-w-md">
                <div className="mb-8 text-center space-y-2">
                    <div className="w-16 h-16 mx-auto bg-surface-800 border border-surface-700 rounded-2xl flex items-center justify-center mb-6 shadow-neon-blue">
                        <span className="text-2xl font-bold text-gray-100">V</span>
                    </div>
                    <h2 className="text-3xl font-bold text-gray-100 tracking-tight">Access Portal</h2>
                    <p className="text-gray-400 text-sm">Sign in to your Viva Verse workspace</p>
                </div>

                <div className="bg-surface-800/50 backdrop-blur-xl border border-surface-700 rounded-2xl p-8 shadow-2xl">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider">Username</label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full bg-surface-900 border border-surface-700 rounded-xl px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all duration-300"
                                placeholder="Enter your username"
                                required
                            />
                        </div>
                        
                        <div className="space-y-2">
                            <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider">Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-surface-900 border border-surface-700 rounded-xl px-4 py-3 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all duration-300"
                                placeholder="Enter your password"
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading || !username || !password}
                            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-neon-blue relative overflow-hidden group"
                        >
                            <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-in-out" />
                            <span className="relative flex items-center justify-center gap-2">
                                {loading ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        <span>Authenticating...</span>
                                    </>
                                ) : (
                                    'Initialize Access Sequence'
                                )}
                            </span>
                        </button>
                    </form>
                </div>
                
                <div className="mt-8 text-center text-xs text-gray-500">
                    <p>Contact your administrator to request access credentials.</p>
                </div>
            </div>
        </div>
    );
};

export default LoginView;
