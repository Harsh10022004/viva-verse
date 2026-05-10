import { useEffect, useRef, useState } from 'react'
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
    Title
} from 'chart.js'
import { Radar, Chart as ReactChart } from 'react-chartjs-2'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title)

export default function Dashboard({ analytics, onRestart }) {
    const [activeTab, setActiveTab] = useState('overview')

    if (!analytics) return null

    const {
        overall_score,
        topic_mastery,
        recall_heatmap,
        knowledge_map,
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
                backgroundColor: 'rgba(156, 39, 176, 0.25)',
                borderColor: '#e879f9',
                borderWidth: 2,
                pointBackgroundColor: '#c026d3',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 8,
            },
        ],
    }

    const radarOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                titleColor: '#f8fafc',
                bodyColor: '#cbd5e1',
                borderColor: 'rgba(192, 38, 211, 0.4)',
                borderWidth: 1,
                padding: 14,
                cornerRadius: 12,
                displayColors: false,
                callbacks: {
                    label: function(context) {
                        return ` Mastery: ${context.raw}%`
                    }
                }
            },
        },
        scales: {
            r: {
                beginAtZero: true,
                max: 100,
                ticks: {
                    stepSize: 20,
                    color: 'transparent', // Hide numbers
                    backdropColor: 'transparent',
                },
                grid: {
                    color: 'rgba(148, 163, 184, 0.15)',
                    circular: true,
                },
                angleLines: {
                    color: 'rgba(148, 163, 184, 0.2)',
                },
                pointLabels: {
                    color: '#cbd5e1',
                    font: { size: 12, family: 'Inter', weight: 'bold' },
                },
            },
        },
    }

    const getScoreGrade = (score) => {
        if (score >= 80) return { grade: 'A+', label: 'Elite Mastery', color: 'text-green-500' }
        if (score >= 60) return { grade: 'B', label: 'Proficient', color: 'text-brand-500' }
        if (score >= 40) return { grade: 'C', label: 'Developing', color: 'text-yellow-500' }
        return { grade: 'D', label: 'Critical Gap', color: 'text-red-500' }
    }

    const getChunkClass = (score) => {
        if (score === null || score === undefined || score < 0) return 'text-chunk-untested'
        if (score >= 75) return 'text-chunk-strong'
        if (score >= 45) return 'text-chunk-fair'
        return 'text-chunk-weak'
    }

    const gradeInfo = getScoreGrade(overall_score)

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 fade-in-up">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full bg-surface-800/80 border border-surface-600/50 backdrop-blur-md shadow-lg mb-6">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-500"></span>
                    </span>
                    <span className="text-gray-300 text-xs font-bold tracking-widest uppercase">System Evaluation Complete</span>
                </div>
                <h2 className="text-5xl font-extrabold mb-4 leading-tight">
                    <span className="text-white">Comprehensive</span><br/>
                    <span className="gradient-text">Analytics Report</span>
                </h2>
                <p className="text-gray-400 text-lg">AI-driven insights into your knowledge architecture</p>
            </div>

            {/* Navigation Tabs (if knowledge map exists) */}
            {knowledge_map && knowledge_map.length > 0 && (
                <div className="flex justify-center mb-10">
                    <div className="bg-surface-800/60 p-1.5 rounded-2xl backdrop-blur-md border border-surface-600/50 flex gap-2">
                        <button
                            onClick={() => setActiveTab('overview')}
                            className={`px-8 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${activeTab === 'overview' ? 'bg-gradient-to-r from-brand-500 to-purple-500 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-surface-700/50'}`}
                        >
                            Executive Overview
                        </button>
                        <button
                            onClick={() => setActiveTab('knowledge_map')}
                            className={`px-8 py-3 rounded-xl font-bold text-sm transition-all duration-300 ${activeTab === 'knowledge_map' ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-surface-700/50'}`}
                        >
                            Document Knowledge Map
                        </button>
                    </div>
                </div>
            )}

            {activeTab === 'overview' && (
                <div className="space-y-6 fade-in-up">
                    {/* Score Hero Card */}
                    <div className="glass-panel rounded-2xl p-8 border border-surface-700 bg-surface-900 relative overflow-hidden">
                        
                        <div className="flex flex-col md:flex-row items-center gap-10 relative z-10">
                            {/* Score Circle */}
                            <div className="relative w-48 h-48 flex-shrink-0">
                                <svg className="absolute inset-0 w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                                    <circle cx="80" cy="80" r="70" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
                                    <circle
                                        cx="80" cy="80" r="70" fill="none"
                                        stroke={overall_score >= 80 ? '#22c55e' : overall_score >= 60 ? '#3b82f6' : overall_score >= 40 ? '#eab308' : '#ef4444'}
                                        strokeWidth="12"
                                        strokeLinecap="round"
                                        strokeDasharray={440}
                                        strokeDashoffset={440 - (440 * overall_score / 100)}
                                        className="transition-all duration-1000 ease-out"
                                    />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-5xl font-black text-gray-100 tracking-tight">{overall_score}</span>
                                    <span className="text-[10px] font-bold text-gray-500 tracking-widest uppercase mt-1">Score</span>
                                </div>
                            </div>

                            {/* Info */}
                            <div className="flex-1 text-center md:text-left">
                                <p className="text-gray-500 text-[11px] font-bold tracking-widest uppercase mb-1">Final Evaluation</p>
                                <div className="flex items-baseline justify-center md:justify-start gap-3 mb-6">
                                    <span className={`text-6xl font-black ${gradeInfo.color}`}>{gradeInfo.grade}</span>
                                    <span className={`text-xl font-bold ${gradeInfo.color} opacity-80`}>{gradeInfo.label}</span>
                                </div>
                                
                                <div className="grid grid-cols-3 gap-4 mt-6">
                                    <div className="bg-surface-800/50 p-4 rounded-xl text-center border border-surface-700 transition-colors">
                                        <p className="text-2xl font-bold text-gray-100">{total_answered}</p>
                                        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mt-1">Answered</p>
                                    </div>
                                    <div className="bg-surface-800/50 p-4 rounded-xl text-center border border-surface-700 transition-colors">
                                        <p className="text-2xl font-bold text-gray-100">{total_questions}</p>
                                        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mt-1">Questions</p>
                                    </div>
                                    <div className="bg-surface-800/50 p-4 rounded-xl text-center border border-surface-700 transition-colors">
                                        <p className="text-2xl font-bold text-gray-100">
                                            {individual_scores ? Math.max(...individual_scores) : 0}<span className="text-sm text-gray-500">%</span>
                                        </p>
                                        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mt-1">Best Score</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Charts Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Radar Chart */}
                        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden bg-surface-900 border border-surface-700">
                            <div className="relative z-10">
                                <h3 className="text-lg font-semibold text-gray-100 mb-1 flex items-center gap-2">
                                    <svg className="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                                    Knowledge Graph
                                </h3>
                                <p className="text-[11px] text-gray-500 mb-6 font-medium uppercase tracking-wider">Multi-dimensional assessment</p>
                                <div className="h-72 relative">
                                    <Radar data={radarData} options={radarOptions} />
                                </div>
                            </div>
                        </div>

                        {/* Areas for Improvement */}
                        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden flex flex-col bg-surface-900 border border-surface-700">
                            <div className="relative z-10 flex-1 flex flex-col">
                                <h3 className="text-lg font-semibold text-gray-100 mb-1 flex items-center gap-2">
                                    <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                                    Strategic Improvements
                                </h3>
                                <p className="text-[11px] text-gray-500 mb-6 font-medium uppercase tracking-wider">Actionable directives</p>
                                <div className="flex-1 bg-surface-800 rounded-xl p-5 border border-surface-700 overflow-y-auto">
                                    {areas_for_improvement.split('\n').filter(l => l.trim()).map((line, i) => (
                                        <div key={i} className={`flex gap-3 mb-3 last:mb-0 ${line.startsWith('•') ? 'ml-2' : 'mt-2'}`}>
                                            {line.startsWith('•') && (
                                                <div className="w-1.5 h-1.5 rounded-full bg-brand-500 mt-2 flex-shrink-0" />
                                            )}
                                            <p className={`text-sm leading-relaxed ${line.startsWith('•') ? 'text-gray-400' : 'text-gray-300 font-semibold'}`}>
                                                {line.replace('•', '').trim()}
                                            </p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* KDE Histogram */}
                    {individual_scores && individual_scores.length > 0 && (
                        <div className="glass-panel rounded-2xl p-6 border border-surface-700 bg-surface-900 mt-6">
                            <h3 className="text-lg font-semibold text-gray-100 mb-1 flex items-center gap-2">
                                <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg>
                                Score Distribution Analysis
                            </h3>
                            <p className="text-[11px] text-gray-500 mb-6 font-medium uppercase tracking-wider">Density Estimation & Frequency</p>
                            <div className="h-64 relative w-full">
                                {(() => {
                                    const binCounts = Array(10).fill(0);
                                    individual_scores.forEach(s => {
                                        let index = Math.floor(s / 10);
                                        if (index >= 10) index = 9;
                                        binCounts[index]++;
                                    });

                                    const histogramData = {
                                        labels: ['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '60-70', '70-80', '80-90', '90-100'],
                                        datasets: [
                                            {
                                                type: 'line',
                                                label: 'Density Curve (KDE)',
                                                data: binCounts,
                                                borderColor: '#60a5fa',
                                                backgroundColor: 'rgba(96, 165, 250, 0.1)',
                                                borderWidth: 2,
                                                tension: 0.4,
                                                fill: true,
                                                pointRadius: 0,
                                            },
                                            {
                                                type: 'bar',
                                                label: 'Frequency',
                                                data: binCounts,
                                                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                                                borderColor: '#3b82f6',
                                                borderWidth: 1,
                                                borderRadius: 4,
                                            }
                                        ]
                                    };

                                    const histogramOptions = {
                                        responsive: true,
                                        maintainAspectRatio: false,
                                        scales: {
                                            y: {
                                                beginAtZero: true,
                                                grid: { color: 'rgba(148, 163, 184, 0.1)' },
                                                ticks: { color: '#94a3b8', stepSize: 1 }
                                            },
                                            x: {
                                                grid: { display: false },
                                                ticks: { color: '#94a3b8' }
                                            }
                                        },
                                        plugins: {
                                            legend: {
                                                labels: { color: '#cbd5e1', font: { family: 'Inter' } }
                                            },
                                            tooltip: {
                                                backgroundColor: 'rgba(15, 23, 42, 0.95)',
                                                titleColor: '#f8fafc',
                                                bodyColor: '#cbd5e1',
                                                borderColor: 'rgba(59, 130, 246, 0.4)',
                                                borderWidth: 1,
                                                padding: 10,
                                                cornerRadius: 8,
                                            }
                                        }
                                    };

                                    return <ReactChart type="bar" data={histogramData} options={histogramOptions} />;
                                })()}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {activeTab === 'knowledge_map' && knowledge_map && (
                <div className="space-y-6 fade-in-up">
                    <div className="glass-panel rounded-2xl p-6 border border-surface-700 bg-surface-900">
                        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                            <div>
                                <h3 className="text-lg font-semibold text-gray-100 mb-1 flex items-center gap-2">
                                    <svg className="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                                    Semantic Document Analysis
                                </h3>
                                <p className="text-[11px] text-gray-500 uppercase tracking-wider">Your understanding mapped to source texts</p>
                            </div>
                            {/* Legend */}
                            <div className="flex gap-4 bg-surface-800 px-3 py-2 rounded-lg border border-surface-700">
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-green-500/20 border border-green-500" /><span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">Strong</span></div>
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-yellow-500/20 border border-yellow-500" /><span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">Fair</span></div>
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-red-500/20 border border-red-500" /><span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">Weak</span></div>
                                <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-sm bg-surface-700 border border-surface-500" /><span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">Untested</span></div>
                            </div>
                        </div>

                        <div className="space-y-6">
                            {knowledge_map.map((doc, docIdx) => (
                                <div key={docIdx} className="bg-surface-800 rounded-xl overflow-hidden border border-surface-700">
                                    <div className="bg-surface-900/50 px-5 py-3 border-b border-surface-700 flex items-center justify-between">
                                        <h4 className="text-sm font-semibold text-gray-200">{doc.file_name}</h4>
                                        <span className="text-[10px] text-gray-500 uppercase tracking-widest">{doc.chunks.length} segments</span>
                                    </div>
                                    <div className="p-6 document-render">
                                        {doc.chunks.map((chunk, cIdx) => (
                                            <span 
                                                key={cIdx} 
                                                className={`text-chunk ${getChunkClass(chunk.score)}`}
                                                title={chunk.score >= 0 ? `Mastery: ${Math.round(chunk.score)}%` : 'Not tested'}
                                            >
                                                {chunk.text}{' '}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Actions */}
            <div className="flex flex-col sm:flex-row justify-center gap-4 mt-10">
                <button
                    onClick={() => window.open(`http://127.0.0.1:8000/api/v1/download-report/${analytics.session_id}`, '_blank')}
                    className="bg-white text-black px-6 py-3 rounded-xl font-bold inline-flex items-center justify-center gap-2 hover:bg-gray-200 transition-colors shadow-lg"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download Annotated PDF
                </button>
                <button
                    onClick={onRestart}
                    className="btn-glow px-6 py-3 rounded-xl font-bold inline-flex items-center justify-center gap-2"
                >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Initiate New Session
                </button>
            </div>
        </div>
    )
}
