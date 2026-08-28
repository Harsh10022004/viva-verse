import React, { useState } from 'react';

const LoginView = ({ apiBase, onLogin, addToast }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const endpoint = isLogin ? '/auth/login' : '/auth/signup';
            const body = isLogin ? { username, password } : { username, email, password };
            
            const response = await fetch(`${apiBase}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await response.json();
            
            if (response.ok) {
                if (isLogin) {
                    addToast('Login successful!', 'success');
                    onLogin(data.access_token, data.user);
                } else {
                    addToast('Signup successful! Please login.', 'success');
                    setIsLogin(true);
                    setPassword('');
                }
            } else {
                addToast(data.detail || (isLogin ? 'Login failed' : 'Signup failed'), 'error');
            }
        } catch (error) {
            addToast(`Network error during ${isLogin ? 'login' : 'signup'}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-[80vh] flex items-center justify-center px-4 relative z-10">
            <div className="w-full max-w-md">
                <div className="mb-8 text-center space-y-2">
                    <div className="w-16 h-16 mx-auto bg-zinc-900 border border-zinc-700 rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                        <span className="text-2xl font-black text-white">V</span>
                    </div>
                    <h2 className="text-3xl font-black text-white tracking-tight">{isLogin ? 'Access Portal' : 'Create Account'}</h2>
                    <p className="text-zinc-400 text-sm">{isLogin ? 'Sign in to your Viva Verse workspace' : 'Join the platform to share and explore'}</p>
                </div>

                <div className="bg-zinc-900/50 backdrop-blur-xl border border-zinc-800 rounded-2xl p-8 shadow-2xl">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider">Username</label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-white transition-all duration-300"
                                placeholder="Enter your username"
                                required
                            />
                        </div>
                        
                        {!isLogin && (
                            <div className="space-y-2">
                                <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider">Email</label>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-white transition-all duration-300"
                                    placeholder="Enter your email"
                                    required
                                />
                            </div>
                        )}
                        
                        <div className="space-y-2">
                            <label className="block text-xs font-bold text-zinc-500 uppercase tracking-wider">Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-black border border-zinc-700 rounded-xl px-4 py-3 text-white placeholder-zinc-600 focus:outline-none focus:border-white transition-all duration-300"
                                placeholder="Enter your password"
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading || !username || !password || (!isLogin && !email)}
                            className="w-full bg-white hover:bg-zinc-200 text-black font-black py-3 rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Sign Up')}
                        </button>
                    </form>
                    
                    <div className="mt-6 text-center">
                        <button onClick={() => setIsLogin(!isLogin)} className="text-sm font-bold text-zinc-400 hover:text-white transition">
                            {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Login"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginView;
