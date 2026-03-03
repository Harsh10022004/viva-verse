import { useEffect, useRef } from 'react'
import {
    Chart as ChartJS,
    RadialLinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Legend,
} from 'chart.js'
import { Radar } from 'react-chartjs-2'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

export default function Dashboard({ analytics, onRestart }) {
    if (!analytics) return null

    const {
        overall_score,
        topic_mastery,
        recall_heatmap,
        areas_for_improvement,
        total_questions,
        total_answered,
        individual_scores,
    } = analytics

    // ── Radar Chart Data ──
    const radarData = {
        labels: topic_mastery.map(t => t.topic),
        datasets: [
            {
                label: 'Mastery Score',
                data: topic_mastery.map(t => t.score),
                backgroundColor: 'rgba(92, 124, 250, 0.15)',
                borderColor: 'rgba(92, 124, 250, 0.8)',
                borderWidth: 2,
                pointBackgroundColor: '#5c7cfa',
                pointBorderColor: '#fff',
                pointBorderWidth: 1,
                pointRadius: 4,
                pointHoverRadius: 6,
            },
        ],
    }

    const radarOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#e5e7eb',
                bodyColor: '#9ca3af',
                borderColor: 'rgba(92, 124, 250, 0.3)',
                borderWidth: 1,
                padding: 12,
                cornerRadius: 8,
            },
        },
        scales: {
            r: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    stepSize: 20,
                    color: '#4b5563',
                    backdropColor: 'transparent',
                    font: { size: 10 },
                },
                grid: {
                    color: 'rgba(75, 85, 99, 0.3)',
                },
                angleLines: {
                    color: 'rgba(75, 85, 99, 0.3)',
                },
                pointLabels: {
                    color: '#9ca3af',
                    font: { size: 11, family: 'Inter' },
                },
            },
        },
    }

    const getScoreGrade = (score) => {
        if (score >= 80) return { grade: 'A', label: 'Excellent', color: 'text-green-400', bg: 'from-green-500/20 to-emerald-500/10' }
        if (score >= 60) return { grade: 'B', label: 'Good', color: 'text-blue-400', bg: 'from-blue-500/20 to-cyan-500/10' }
        if (score >= 40) return { grade: 'C', label: 'Fair', color: 'text-yellow-400', bg: 'from-yellow-500/20 to-orange-500/10' }
        return { grade: 'D', label: 'Needs Work', color: 'text-red-400', bg: 'from-red-500/20 to-rose-500/10' }
    }

    const gradeInfo = getScoreGrade(overall_score)

    return (
        <div className="max-w-7xl mx-auto px-6 py-10 fade-in-up">
            {/* Header */}
            <div className="text-center mb-10">
                <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium mb-4">
                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    Viva Complete
                </div>
                <h2 className="text-3xl font-extrabold gradient-text mb-2">Performance Dashboard</h2>
                <p className="text-gray-400">Your AI-evaluated viva examination results</p>
            </div>

            {/* Score Hero Card */}
            <div className={`glass rounded-2xl p-8 mb-8 bg-gradient-to-br ${gradeInfo.bg}`}>
                <div className="flex flex-col md:flex-row items-center gap-8">
                    {/* Score Circle */}
                    <div className="relative w-40 h-40 flex-shrink-0">
                        <svg className="w-40 h-40 transform -rotate-90" viewBox="0 0 160 160">
                            <circle cx="80" cy="80" r="70" fill="none" stroke="#1f2937" strokeWidth="8" />
                            <circle
                                cx="80" cy="80" r="70" fill="none"
                                stroke="url(#scoreGradient)" strokeWidth="8"
                                strokeLinecap="round"
                                strokeDasharray={440}
                                strokeDashoffset={440 - (440 * overall_score / 100)}
                                className="transition-all duration-1000 ease-out"
                            />
                            <defs>
                                <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stopColor="#5c7cfa" />
                                    <stop offset="100%" stopColor="#da77f2" />
                                </linearGradient>
                            </defs>
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-4xl font-extrabold text-white score-pop">{overall_score}</span>
                            <span className="text-xs text-gray-400 mt-0.5">out of 100</span>
                        </div>
                    </div>

                    {/* Info */}
                    <div className="flex-1 text-center md:text-left">
                        <div className="flex items-center justify-center md:justify-start gap-3 mb-3">
                            <span className={`text-5xl font-black ${gradeInfo.color}`}>{gradeInfo.grade}</span>
                            <span className={`text-lg font-semibold ${gradeInfo.color}`}>{gradeInfo.label}</span>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-4">
                            <div className="glass rounded-xl p-3 text-center">
                                <p className="text-2xl font-bold text-white">{total_answered}</p>
                                <p className="text-xs text-gray-500">Answered</p>
                            </div>
                            <div className="glass rounded-xl p-3 text-center">
                                <p className="text-2xl font-bold text-white">{total_questions}</p>
                                <p className="text-xs text-gray-500">Questions</p>
                            </div>
                            <div className="glass rounded-xl p-3 text-center">
                                <p className="text-2xl font-bold text-white">
                                    {individual_scores ? Math.max(...individual_scores) : 0}%
                                </p>
                                <p className="text-xs text-gray-500">Best Score</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                {/* Radar Chart */}
                <div className="glass rounded-2xl p-6">
                    <h3 className="text-lg font-bold text-white mb-1">Topic Mastery</h3>
                    <p className="text-xs text-gray-500 mb-4">Competency across document sections</p>
                    <div className="h-72">
                        <Radar data={radarData} options={radarOptions} />
                    </div>
                </div>

                {/* Recall Heatmap */}
                <div className="glass rounded-2xl p-6">
                    <h3 className="text-lg font-bold text-white mb-1">Recall Heatmap</h3>
                    <p className="text-xs text-gray-500 mb-4">Score distribution across document chunks</p>
                    <div className="grid grid-cols-6 gap-1.5 mt-2">
                        {recall_heatmap.map((cell, i) => (
                            <div
                                key={i}
                                className="heatmap-cell aspect-square flex items-center justify-center relative group"
                                style={{ backgroundColor: cell.color }}
                                title={`${cell.section} — Score: ${cell.score >= 0 ? cell.score + '%' : 'Not tested'}`}
                            >
                                <span className="text-[9px] font-mono text-white/70 font-bold">
                                    {cell.score >= 0 ? Math.round(cell.score) : '—'}
                                </span>
                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-surface-800 text-[10px] text-gray-300 rounded-md whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 border border-surface-600">
                                    {cell.section}
                                    <br />
                                    {cell.score >= 0 ? `${cell.score}%` : 'Not tested'}
                                </div>
                            </div>
                        ))}
                    </div>
                    {/* Legend */}
                    <div className="flex items-center gap-4 mt-4 justify-center">
                        {[
                            { color: '#22c55e', label: '≥70% (Strong)' },
                            { color: '#eab308', label: '40-69% (Fair)' },
                            { color: '#ef4444', label: '<40% (Weak)' },
                            { color: '#374151', label: 'Not tested' },
                        ].map(l => (
                            <div key={l.label} className="flex items-center gap-1.5">
                                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: l.color }} />
                                <span className="text-[10px] text-gray-500">{l.label}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Areas for Improvement */}
            <div className="glass rounded-2xl p-6 mb-8">
                <h3 className="text-lg font-bold text-white mb-1">Areas for Improvement</h3>
                <p className="text-xs text-gray-500 mb-4">AI-generated recommendations based on your performance</p>
                <div className="bg-surface-800/50 rounded-xl p-5 border border-surface-600/30">
                    {areas_for_improvement.split('\n').map((line, i) => (
                        <p key={i} className={`text-sm leading-relaxed ${line.startsWith('•') ? 'text-gray-300 ml-2 mb-2' : 'text-gray-400 mb-3 font-medium'
                            }`}>
                            {line}
                        </p>
                    ))}
                </div>
            </div>

            {/* Individual Scores */}
            {individual_scores && individual_scores.length > 0 && (
                <div className="glass rounded-2xl p-6 mb-8">
                    <h3 className="text-lg font-bold text-white mb-4">Question-wise Performance</h3>
                    <div className="space-y-3">
                        {individual_scores.map((score, i) => (
                            <div key={i} className="flex items-center gap-4">
                                <span className="text-xs text-gray-500 font-mono w-8">Q{i + 1}</span>
                                <div className="flex-1 h-3 bg-surface-700 rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full transition-all duration-700 ease-out"
                                        style={{
                                            width: `${score}%`,
                                            background: score >= 70
                                                ? 'linear-gradient(90deg, #22c55e, #4ade80)'
                                                : score >= 40
                                                    ? 'linear-gradient(90deg, #eab308, #facc15)'
                                                    : 'linear-gradient(90deg, #ef4444, #f87171)',
                                        }}
                                    />
                                </div>
                                <span className={`text-sm font-bold w-12 text-right ${score >= 70 ? 'text-green-400' : score >= 40 ? 'text-yellow-400' : 'text-red-400'
                                    }`}>
                                    {score}%
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Restart Button */}
            <div className="text-center">
                <button
                    onClick={onRestart}
                    className="btn-glow px-8 py-3 rounded-xl text-white font-semibold text-sm"
                >
                    <span className="relative z-10 flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Start New Viva
                    </span>
                </button>
            </div>
        </div>
    )
}
