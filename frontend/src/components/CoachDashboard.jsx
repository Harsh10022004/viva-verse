import { useState, useEffect, useMemo } from 'react'
import {
    Chart as ChartJS,
    RadialLinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Legend,
    CategoryScale,
    LinearScale,
    BarElement,
    ArcElement,
    Title
} from 'chart.js'
import { Radar, Bar, Doughnut } from 'react-chartjs-2'

ChartJS.register(
    RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
    CategoryScale, LinearScale, BarElement, ArcElement, Title
)

export default function CoachDashboard({ analytics, onRestart }) {
    const [activeTab, setActiveTab] = useState('overview')
    const [expandedQuestion, setExpandedQuestion] = useState(null)

    if (!analytics) return null

    const {
        overall_score = 0,
        verdict = 'PENDING',
        mode = '',
        role = '',
        level = '',
        elapsed = '00:00',
        question_count = 0,
        competency_scores = [],
        per_question = [],
        strengths = [],
        weaknesses = [],
        remediation_plan = {},
        jd_skill_priorities = [],
        report_text = ''
    } = analytics

    const getGrade = (score) => {
        if (score >= 80) return { grade: 'A+', label: 'Elite Mastery', color: '#22c55e', bg: 'from-emerald-500/20 to-emerald-500/5' }
        if (score >= 60) return { grade: 'B+', label: 'Proficient', color: '#3b82f6', bg: 'from-blue-500/20 to-blue-500/5' }
        if (score >= 40) return { grade: 'C', label: 'Developing', color: '#f59e0b', bg: 'from-amber-500/20 to-amber-500/5' }
        return { grade: 'D', label: 'Critical Gap', color: '#ef4444', bg: 'from-rose-500/20 to-rose-500/5' }
    }

    const getVerdictStyle = (v) => {
        if (v === 'HIRE') return { emoji: '🟢', color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30' }
        if (v === 'STRONG LEAN') return { emoji: '🟡', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30' }
        if (v === 'LEAN NO') return { emoji: '🟠', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' }
        if (v === 'DEFINITE NO') return { emoji: '🔴', color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/30' }
        return { emoji: '⚪', color: 'text-zinc-400', bg: 'bg-zinc-500/10 border-zinc-500/30' }
    }

    const gradeInfo = getGrade(overall_score)
    const verdictStyle = getVerdictStyle(verdict)

    // ── Radar Chart: Competency Matrix ──
    const radarData = {
        labels: competency_scores.map(c => {
            const words = c.dimension.split(' ')
            return words.length > 3 ? words.slice(0, 3).join(' ') + '…' : c.dimension
        }),
        datasets: [{
            label: 'Score',
            data: competency_scores.map(c => (c.score / c.max_score) * 100),
            backgroundColor: 'rgba(99, 102, 241, 0.15)',
            borderColor: '#818cf8',
            borderWidth: 2,
            pointBackgroundColor: '#6366f1',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 8,
        }]
    }

    const radarOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(0,0,0,0.9)', titleColor: '#fff', bodyColor: '#cbd5e1', padding: 12, cornerRadius: 10 } },
        scales: { r: { beginAtZero: true, max: 100, ticks: { display: false }, grid: { color: 'rgba(148,163,184,0.12)', circular: true }, angleLines: { color: 'rgba(148,163,184,0.15)' }, pointLabels: { color: '#94a3b8', font: { size: 10, weight: '600' } } } }
    }

    // ── Bar Chart: Per-Question Score Progression ──
    const barData = {
        labels: per_question.map(q => `Q${q.question_num}`),
        datasets: [{
            label: 'Score',
            data: per_question.map(q => (q.score / q.max_score) * 100),
            backgroundColor: per_question.map(q => {
                const pct = (q.score / q.max_score) * 100
                if (pct >= 70) return 'rgba(34, 197, 94, 0.7)'
                if (pct >= 40) return 'rgba(245, 158, 11, 0.7)'
                return 'rgba(239, 68, 68, 0.7)'
            }),
            borderColor: per_question.map(q => {
                const pct = (q.score / q.max_score) * 100
                if (pct >= 70) return '#22c55e'
                if (pct >= 40) return '#f59e0b'
                return '#ef4444'
            }),
            borderWidth: 1,
            borderRadius: 6,
        }]
    }

    const barOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(0,0,0,0.9)', padding: 10, cornerRadius: 8 } },
        scales: { y: { beginAtZero: true, max: 100, grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: '#64748b', font: { size: 11 } } }, x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 12, weight: '600' } } } }
    }

    // ── Doughnut Chart: Quality Distribution ──
    const qualityCounts = useMemo(() => {
        let strong = 0, fair = 0, weak = 0
        per_question.forEach(q => {
            const pct = (q.score / q.max_score) * 100
            if (pct >= 70) strong++
            else if (pct >= 40) fair++
            else weak++
        })
        return { strong, fair, weak }
    }, [per_question])

    const doughnutData = {
        labels: ['Strong', 'Fair', 'Weak'],
        datasets: [{
            data: [qualityCounts.strong, qualityCounts.fair, qualityCounts.weak],
            backgroundColor: ['rgba(34,197,94,0.8)', 'rgba(245,158,11,0.8)', 'rgba(239,68,68,0.8)'],
            borderColor: ['#22c55e', '#f59e0b', '#ef4444'],
            borderWidth: 2,
            hoverOffset: 8,
        }]
    }

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
            legend: { position: 'bottom', labels: { color: '#94a3b8', padding: 16, usePointStyle: true, pointStyle: 'circle', font: { size: 12, weight: '600' } } },
            tooltip: { backgroundColor: 'rgba(0,0,0,0.9)', padding: 10, cornerRadius: 8 }
        }
    }

    const TABS = [
        { id: 'overview', label: 'Overview', icon: '📊' },
        { id: 'questions', label: 'Question Analysis', icon: '📝' },
        { id: 'remediation', label: 'Remediation Plan', icon: '🎯' },
        { id: 'report', label: 'Full Report', icon: '📄' },
    ]

    const downloadReport = () => {
        const blob = new Blob([report_text], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `VivaVerse_Report_${role.replace(/\s+/g, '_')}.md`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <div className="min-h-screen bg-black pb-20">
            {/* Hero Header */}
            <div className="relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-b from-indigo-950/30 via-black to-black" />
                <div className="relative max-w-7xl mx-auto px-6 pt-12 pb-8">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-bold text-indigo-400 tracking-wider uppercase flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                            Evaluation Complete
                        </div>
                        <span className="text-zinc-600 text-xs">·</span>
                        <span className="text-zinc-500 text-xs font-medium">{mode.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())} Arena</span>
                    </div>

                    <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight mb-3">
                        Performance <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400">Analytics</span>
                    </h1>
                    <p className="text-zinc-500 text-base max-w-2xl">
                        {role} · {level} · {elapsed} elapsed · {question_count} questions examined
                    </p>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-6">
                {/* Score Hero Card */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8 -mt-2">
                    {/* Main Score */}
                    <div className={`col-span-1 lg:col-span-2 rounded-2xl border border-zinc-800/80 bg-gradient-to-br ${gradeInfo.bg} p-8 relative overflow-hidden`}>
                        <div className="absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl opacity-20" style={{ background: gradeInfo.color }} />
                        <div className="relative flex items-center gap-10">
                            <div className="relative w-40 h-40 flex-shrink-0">
                                <svg className="absolute inset-0 w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                                    <circle cx="80" cy="80" r="65" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                                    <circle cx="80" cy="80" r="65" fill="none" stroke={gradeInfo.color} strokeWidth="10" strokeLinecap="round"
                                        strokeDasharray={408} strokeDashoffset={408 - (408 * overall_score / 100)}
                                        className="transition-all duration-[2000ms] ease-out" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-5xl font-black text-white tracking-tight">{overall_score}</span>
                                    <span className="text-[10px] font-bold text-zinc-500 tracking-widest uppercase mt-1">Score</span>
                                </div>
                            </div>
                            <div className="flex-1">
                                <div className="flex items-baseline gap-3 mb-2">
                                    <span className="text-5xl font-black" style={{ color: gradeInfo.color }}>{gradeInfo.grade}</span>
                                    <span className="text-lg font-bold" style={{ color: gradeInfo.color, opacity: 0.8 }}>{gradeInfo.label}</span>
                                </div>
                                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border ${verdictStyle.bg} mt-3`}>
                                    <span>{verdictStyle.emoji}</span>
                                    <span className={`text-sm font-extrabold tracking-wide ${verdictStyle.color}`}>{verdict}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Quick Stats */}
                    <div className="space-y-3">
                        {[
                            { label: 'Questions', value: question_count, icon: '❓' },
                            { label: 'Duration', value: elapsed, icon: '⏱️' },
                            { label: 'Competencies', value: competency_scores.length, icon: '📐' },
                            { label: 'Skills to Fix', value: (remediation_plan?.selected_skills || []).length, icon: '🔧' },
                        ].map((stat, i) => (
                            <div key={i} className="flex items-center gap-4 p-3.5 rounded-xl bg-zinc-900/60 border border-zinc-800/60">
                                <span className="text-lg">{stat.icon}</span>
                                <div className="flex-1">
                                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">{stat.label}</p>
                                    <p className="text-lg font-bold text-white">{stat.value}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Tab Navigation */}
                <div className="flex gap-1.5 mb-8 bg-zinc-900/40 p-1.5 rounded-2xl border border-zinc-800/50 w-fit">
                    {TABS.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                            className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 flex items-center gap-2 ${
                                activeTab === tab.id
                                    ? 'bg-white text-black shadow-lg'
                                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                            }`}
                        >
                            <span>{tab.icon}</span> {tab.label}
                        </button>
                    ))}
                </div>

                {/* ── Overview Tab ── */}
                {activeTab === 'overview' && (
                    <div className="space-y-6 fade-in-up">
                        {/* Charts Row */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            {/* Radar */}
                            {competency_scores.length > 0 && (
                                <div className="lg:col-span-2 rounded-2xl border border-zinc-800/60 bg-zinc-950/80 p-6">
                                    <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">📐 Competency Matrix</h3>
                                    <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-6 font-bold">Multi-dimensional assessment</p>
                                    <div className="h-72"><Radar data={radarData} options={radarOptions} /></div>
                                </div>
                            )}

                            {/* Doughnut */}
                            {per_question.length > 0 && (
                                <div className="rounded-2xl border border-zinc-800/60 bg-zinc-950/80 p-6">
                                    <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">📊 Quality Distribution</h3>
                                    <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-6 font-bold">Answer quality breakdown</p>
                                    <div className="h-64"><Doughnut data={doughnutData} options={doughnutOptions} /></div>
                                </div>
                            )}
                        </div>

                        {/* Score Progression */}
                        {per_question.length > 0 && (
                            <div className="rounded-2xl border border-zinc-800/60 bg-zinc-950/80 p-6">
                                <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">📈 Score Progression</h3>
                                <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-6 font-bold">Performance trend across questions</p>
                                <div className="h-64"><Bar data={barData} options={barOptions} /></div>
                            </div>
                        )}

                        {/* Strengths & Weaknesses */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {strengths.length > 0 && (
                                <div className="rounded-2xl border border-emerald-900/30 bg-emerald-950/20 p-6">
                                    <h3 className="text-base font-bold text-emerald-400 mb-4 flex items-center gap-2">🟢 Strengths Demonstrated</h3>
                                    <div className="space-y-3">
                                        {strengths.map((s, i) => (
                                            <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-emerald-950/30 border border-emerald-900/20">
                                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-2 flex-shrink-0" />
                                                <p className="text-sm text-zinc-300 leading-relaxed">{s}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {weaknesses.length > 0 && (
                                <div className="rounded-2xl border border-rose-900/30 bg-rose-950/20 p-6">
                                    <h3 className="text-base font-bold text-rose-400 mb-4 flex items-center gap-2">🔴 Deficits & Vulnerabilities</h3>
                                    <div className="space-y-3">
                                        {weaknesses.map((w, i) => (
                                            <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-rose-950/30 border border-rose-900/20">
                                                <div className="w-1.5 h-1.5 rounded-full bg-rose-400 mt-2 flex-shrink-0" />
                                                <p className="text-sm text-zinc-300 leading-relaxed">{w}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* ── Question Analysis Tab ── */}
                {activeTab === 'questions' && (
                    <div className="space-y-4 fade-in-up">
                        <div className="rounded-2xl border border-zinc-800/60 bg-zinc-950/80 overflow-hidden">
                            <div className="px-6 py-4 border-b border-zinc-800/60 flex items-center justify-between">
                                <h3 className="text-base font-bold text-white flex items-center gap-2">📝 Per-Question Breakdown</h3>
                                <span className="text-xs text-zinc-500 font-bold">{per_question.length} questions analyzed</span>
                            </div>
                            {per_question.length === 0 ? (
                                <div className="p-12 text-center text-zinc-500">
                                    <p className="text-lg font-bold mb-2">No per-question data available</p>
                                    <p className="text-sm">The LLM report may not have included a structured question table.</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-zinc-800/40">
                                    {per_question.map((q, i) => {
                                        const pct = (q.score / q.max_score) * 100
                                        const scoreColor = pct >= 70 ? 'text-emerald-400' : pct >= 40 ? 'text-amber-400' : 'text-rose-400'
                                        const scoreBg = pct >= 70 ? 'bg-emerald-500/10' : pct >= 40 ? 'bg-amber-500/10' : 'bg-rose-500/10'
                                        const isExpanded = expandedQuestion === i

                                        return (
                                            <div key={i} className="hover:bg-zinc-900/30 transition-colors cursor-pointer" onClick={() => setExpandedQuestion(isExpanded ? null : i)}>
                                                <div className="px-6 py-4 flex items-center gap-6">
                                                    <div className={`w-12 h-12 rounded-xl ${scoreBg} flex items-center justify-center flex-shrink-0`}>
                                                        <span className={`text-lg font-black ${scoreColor}`}>{q.score}</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-sm font-bold text-white truncate">Q{q.question_num}: {q.topic}</p>
                                                        <div className="flex items-center gap-4 mt-1">
                                                            <span className="text-xs text-zinc-500">⏱ {q.time_assessment}</span>
                                                            <div className="flex-1 max-w-32 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                                                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444' }} />
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <span className="text-zinc-600 text-xs">{isExpanded ? '▲' : '▼'}</span>
                                                </div>
                                                {isExpanded && (
                                                    <div className="px-6 pb-5 grid grid-cols-2 gap-4 fade-in-up">
                                                        <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-900/20">
                                                            <p className="text-[10px] font-bold text-emerald-500 uppercase tracking-wider mb-1">Strength</p>
                                                            <p className="text-sm text-zinc-300">{q.strength}</p>
                                                        </div>
                                                        <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-900/20">
                                                            <p className="text-[10px] font-bold text-rose-500 uppercase tracking-wider mb-1">Weakness</p>
                                                            <p className="text-sm text-zinc-300">{q.weakness}</p>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Competency Table */}
                        {competency_scores.length > 0 && (
                            <div className="rounded-2xl border border-zinc-800/60 bg-zinc-950/80 overflow-hidden">
                                <div className="px-6 py-4 border-b border-zinc-800/60">
                                    <h3 className="text-base font-bold text-white flex items-center gap-2">📐 Competency Scores</h3>
                                </div>
                                <div className="divide-y divide-zinc-800/40">
                                    {competency_scores.map((c, i) => (
                                        <div key={i} className="px-6 py-4 flex items-center gap-6">
                                            <div className="flex-1">
                                                <p className="text-sm font-bold text-zinc-200">{c.dimension}</p>
                                                <p className="text-xs text-zinc-500 mt-1">{c.critique}</p>
                                            </div>
                                            <div className="text-right flex-shrink-0">
                                                <span className="text-2xl font-black text-white">{c.score}</span>
                                                <span className="text-sm text-zinc-600">/{c.max_score}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* ── Remediation Plan Tab ── */}
                {activeTab === 'remediation' && (
                    <div className="space-y-6 fade-in-up">
                        <div className="rounded-2xl border border-indigo-900/30 bg-gradient-to-br from-indigo-950/30 to-black p-8">
                            <div className="flex items-center justify-between mb-6">
                                <div>
                                    <h3 className="text-xl font-extrabold text-white flex items-center gap-3">
                                        🎯 {remediation_plan?.num_days || 7}-Day Intensive Remediation Plan
                                    </h3>
                                    <p className="text-sm text-zinc-500 mt-1">Powered by 0/1 Knapsack Dynamic Programming — mathematically optimal</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-2xl font-black text-indigo-400">{remediation_plan?.total_hours_used || 0}<span className="text-sm text-indigo-600">h</span></p>
                                    <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">of {remediation_plan?.budget_hours || 20}h budget</p>
                                </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="w-full h-3 bg-zinc-800 rounded-full overflow-hidden mb-8">
                                <div className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-1000"
                                    style={{ width: `${((remediation_plan?.total_hours_used || 0) / (remediation_plan?.budget_hours || 20)) * 100}%` }} />
                            </div>

                            {/* Timeline */}
                            {(remediation_plan?.selected_skills || []).length > 0 ? (
                                <div className="space-y-4">
                                    {remediation_plan.selected_skills.map((skill, i) => (
                                        <div key={i} className="flex items-center gap-5 p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/50 hover:border-indigo-800/30 transition-colors">
                                            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                                                <span className="text-sm font-black text-indigo-400">D{skill.day}</span>
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-base font-bold text-white capitalize">{skill.skill}</p>
                                                <div className="flex items-center gap-4 mt-1">
                                                    <span className="text-xs text-zinc-500 flex items-center gap-1">⏱ {skill.hours}h study time</span>
                                                    <span className="text-xs text-indigo-400 font-bold">Priority: {skill.priority}</span>
                                                </div>
                                            </div>
                                            <div className="w-16 h-2 bg-zinc-800 rounded-full overflow-hidden">
                                                <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${(skill.priority / 15) * 100}%` }} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-center py-12 text-zinc-500">
                                    <p className="text-lg font-bold mb-2">No remediation needed</p>
                                    <p className="text-sm">No specific skill deficits were detected in your session.</p>
                                </div>
                            )}

                            {/* Dropped Skills */}
                            {(remediation_plan?.dropped_skills || []).length > 0 && (
                                <div className="mt-8 p-5 rounded-xl bg-amber-950/20 border border-amber-900/20">
                                    <h4 className="text-sm font-bold text-amber-400 mb-3">⚠️ Deprioritized by Algorithm (Insufficient Time Budget)</h4>
                                    <div className="space-y-2">
                                        {remediation_plan.dropped_skills.map((s, i) => (
                                            <div key={i} className="flex items-center gap-3 text-sm">
                                                <span className="text-zinc-600 line-through capitalize">{s.skill}</span>
                                                <span className="text-zinc-600">—</span>
                                                <span className="text-zinc-500 text-xs">{s.reason}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* ROI Score */}
                            {remediation_plan?.total_roi_score > 0 && (
                                <div className="mt-6 flex items-center justify-center gap-3 p-4 rounded-xl bg-zinc-900/50 border border-zinc-800/50">
                                    <span className="text-sm text-zinc-400 font-bold">Total Hireability ROI Score:</span>
                                    <span className="text-2xl font-black text-indigo-400">{remediation_plan.total_roi_score}</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* ── Full Report Tab ── */}
                {activeTab === 'report' && (
                    <div className="fade-in-up">
                        <div className="rounded-2xl border border-zinc-800/60 bg-zinc-950/80 overflow-hidden">
                            <div className="px-6 py-4 border-b border-zinc-800/60 flex items-center justify-between">
                                <h3 className="text-base font-bold text-white flex items-center gap-2">📄 Complete LLM Report</h3>
                                <button onClick={downloadReport} className="px-4 py-2 rounded-xl bg-white text-black text-xs font-bold hover:bg-zinc-200 transition flex items-center gap-2">
                                    📥 Download .md
                                </button>
                            </div>
                            <div className="p-6 sm:p-8">
                                <pre className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed font-sans">{report_text}</pre>
                            </div>
                        </div>
                    </div>
                )}

                {/* Action Bar */}
                <div className="flex justify-center gap-4 mt-12">
                    <button onClick={downloadReport} className="px-6 py-3.5 rounded-xl bg-zinc-900 text-white font-bold text-sm border border-zinc-800 hover:bg-zinc-800 transition flex items-center gap-2">
                        📥 Download Report
                    </button>
                    <button onClick={onRestart} className="px-8 py-3.5 rounded-xl bg-white text-black font-bold text-sm hover:bg-zinc-200 transition shadow-lg flex items-center gap-2">
                        🚀 New Session
                    </button>
                </div>
            </div>
        </div>
    )
}
