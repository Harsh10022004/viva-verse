export default function Toast({ toasts, removeToast }) {
    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-3 pointer-events-none">
            {toasts.map(t => (
                <div key={t.id} className={`pointer-events-auto px-4 py-3 min-w-[300px] rounded-xl shadow-lg border flex items-center justify-between gap-4 text-sm font-medium animate-fade-in-up ${t.type === 'error' ? 'bg-red-500/10 border-red-500/30 text-red-400 backdrop-blur-md' :
                        t.type === 'success' ? 'bg-green-500/10 border-green-500/30 text-green-400 backdrop-blur-md' :
                            'bg-surface-800 border-surface-600 text-gray-200'
                    }`}>
                    <div className="flex items-center gap-3">
                        {t.type === 'error' ? (
                            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>
                        ) : t.type === 'success' ? (
                            <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
                        ) : null}
                        <span>{t.message}</span>
                    </div>
                    <button onClick={() => removeToast(t.id)} className="opacity-70 hover:opacity-100 transition-opacity">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            ))}
        </div>
    )
}
