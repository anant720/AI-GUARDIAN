import React, { useState } from 'react';
import axiosClient from '../api/axiosClient';
import JSONViewer from '../components/JSONViewer';
import { 
  Shield, 
  ShieldAlert, 
  ShieldCheck, 
  Search, 
  MessageSquare, 
  Link as LinkIcon, 
  Loader2, 
  ChevronRight, 
  Terminal,
  Info,
  ExternalLink
} from 'lucide-react';
import toast from 'react-hot-toast';

const TestingInterface = () => {
  const [url, setUrl] = useState('');
  const [messageText, setMessageText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'json'

  const handleScan = async (e) => {
    e.preventDefault();
    if (!messageText.trim() && !url.trim()) {
      return toast.error("Please provide either a URL or a Text Message to scan.");
    }
    
    setLoading(true);
    setResult(null);

    try {
      // Calling /scan directly as requested for a testing site
      const response = await axiosClient.post('/scan', {
        url: url.trim() || null,
        message: messageText.trim() || null
      });
      setResult(response.data);
      toast.success("Analysis complete.");
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || "Execution failed. Check backend connection.");
      setResult({ error: err.response?.data || err.message });
    } finally {
      setLoading(false);
    }
  };

  const score = result?.combined_score ?? result?.risk_score ?? 0;
  const isHighRisk = score >= 60;
  const isMediumRisk = score >= 30 && score < 60;

  const getStatusConfig = () => {
    if (isHighRisk) return {
      color: 'text-rose-500',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/30',
      label: 'SCAM DETECTED',
      icon: <ShieldAlert className="w-12 h-12 text-rose-500" />,
      glow: 'shadow-[0_0_50px_-12px_rgba(244,63,94,0.4)]'
    };
    if (isMediumRisk) return {
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      label: 'SUSPICIOUS',
      icon: <Info className="w-12 h-12 text-amber-500" />,
      glow: 'shadow-[0_0_50px_-12px_rgba(245,158,11,0.4)]'
    };
    return {
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      label: 'SAFE',
      icon: <ShieldCheck className="w-12 h-12 text-emerald-500" />,
      glow: 'shadow-[0_0_50px_-12px_rgba(16,185,129,0.4)]'
    };
  };

  const status = getStatusConfig();

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 flex flex-col font-sans selection:bg-sky-500/30">
      {/* Background Decor */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-sky-600/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 blur-[120px] rounded-full" />
      </div>

      {/* Header */}
      <header className="h-20 border-b border-slate-800/50 backdrop-blur-md sticky top-0 z-50 px-8 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-sky-500/10 rounded-lg border border-sky-500/20">
            <Shield className="w-6 h-6 text-sky-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              AI Guardian Lab
            </h1>
            <p className="text-[10px] uppercase tracking-[0.2em] font-semibold text-sky-500/70">Secure Testing Environment</p>
          </div>
        </div>
        <div className="hidden sm:flex items-center space-x-6 text-sm font-medium text-slate-400">
          <span className="flex items-center cursor-default hover:text-slate-200 transition-colors">
            <Terminal className="w-4 h-4 mr-2" /> Self-Healing Engine
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-[1600px] w-full mx-auto p-6 md:p-10 grid grid-cols-1 lg:grid-cols-12 gap-10 relative z-10">
        
        {/* Left Side: Input Controls */}
        <section className="lg:col-span-4 flex flex-col space-y-8">
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white">Security Bypass</h2>
            <p className="text-slate-400 text-sm">Deploy payloads directly into the analysis pipeline for high-fidelity verification.</p>
          </div>

          <form onSubmit={handleScan} className="space-y-6">
            <div className="group space-y-2">
              <label className="text-sm font-semibold text-slate-400 flex items-center group-focus-within:text-sky-400 transition-colors">
                <MessageSquare className="w-4 h-4 mr-2" /> Message Content
              </label>
              <div className="relative">
                <textarea
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  placeholder="Paste raw notification text, SMS, or email body..."
                  className="w-full h-48 bg-slate-900/40 border border-slate-800 rounded-2xl p-4 text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500/50 transition-all placeholder:text-slate-600 resize-none backdrop-blur-sm"
                />
              </div>
            </div>

            <div className="group space-y-2">
              <label className="text-sm font-semibold text-slate-400 flex items-center group-focus-within:text-sky-400 transition-colors">
                <LinkIcon className="w-4 h-4 mr-2" /> Target URL
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/phish"
                  className="w-full bg-slate-900/40 border border-slate-800 rounded-xl p-4 text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500/50 transition-all placeholder:text-slate-600 backdrop-blur-sm"
                />
                <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-600 group-focus-within:text-sky-500/50 transition-colors" />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full group relative flex items-center justify-center p-4 bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold rounded-xl transition-all active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 overflow-hidden shadow-lg shadow-sky-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-in-out" />
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin mr-3" />
                  <span>Analyzing Sequence...</span>
                </>
              ) : (
                <>
                  <ChevronRight className="w-5 h-5 mr-1 group-hover:translate-x-1 transition-transform" />
                  <span>Execute Analysis</span>
                </>
              )}
            </button>
          </form>

          <div className="p-4 bg-slate-900/30 border border-slate-800/50 rounded-xl space-y-3">
            <h3 className="text-xs font-bold text-slate-500 uppercase flex items-center">
              <Info className="w-3 h-3 mr-2 text-sky-500" /> Lab Notes
            </h3>
            <p className="text-[13px] text-slate-400 leading-relaxed">
              Analysis bypasses standard user logging and directly queries the core risk engine. Output includes LLM reasoning, threat intelligence, and behavioral signals.
            </p>
          </div>
        </section>

        {/* Right Side: Results Display */}
        <section className="lg:col-span-8 flex flex-col h-full bg-slate-900/20 border border-slate-800/50 rounded-3xl overflow-hidden backdrop-blur-sm relative">
          
          {/* Tabs */}
          <div className="h-16 flex items-center px-6 border-b border-slate-800/50 space-x-8">
            <button 
              onClick={() => setActiveTab('summary')}
              className={`h-full text-sm font-semibold flex items-center transition-colors relative ${activeTab === 'summary' ? 'text-sky-400' : 'text-slate-500 hover:text-slate-300'}`}
            >
              Security Summary
              {activeTab === 'summary' && <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.5)]" />}
            </button>
            <button 
              onClick={() => setActiveTab('json')}
              className={`h-full text-sm font-semibold flex items-center transition-colors relative ${activeTab === 'json' ? 'text-sky-400' : 'text-slate-500 hover:text-slate-300'}`}
            >
              JSON Laboratory
              {activeTab === 'json' && <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.5)]" />}
            </button>
          </div>

          <div className="flex-1 p-8 overflow-y-auto custom-scrollbar">
            {!result && !loading ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-6 max-w-md mx-auto text-center">
                <div className="w-24 h-24 bg-slate-800/30 border border-slate-800 rounded-full flex items-center justify-center animate-pulse">
                  <Terminal className="w-10 h-10 opacity-20" />
                </div>
                <div className="space-y-2">
                  <p className="text-lg font-medium text-slate-400">System Idle</p>
                  <p className="text-sm">Awaiting payload deployment for deep verification across 9 detection phases.</p>
                </div>
              </div>
            ) : loading ? (
              <div className="h-full flex flex-col items-center justify-center space-y-8 py-10">
                <div className="relative">
                  <div className="w-24 h-24 border-2 border-sky-500/20 rounded-full" />
                  <div className="absolute inset-0 border-t-2 border-sky-500 rounded-full animate-spin" />
                  <div className="absolute inset-4 border-2 border-purple-500/20 rounded-full" />
                  <div className="absolute inset-4 border-r-2 border-purple-500 rounded-full animate-spin-slow" />
                </div>
                <div className="text-center space-y-3">
                  <p className="text-xl font-bold bg-gradient-to-r from-sky-400 to-purple-400 bg-clip-text text-transparent animate-pulse">
                    Initiating Analysis Sequence
                  </p>
                  <div className="flex justify-center space-x-2">
                    {[0, 1, 2].map(i => <div key={i} className={`w-1.5 h-1.5 rounded-full bg-sky-500/50 animate-bounce`} style={{ animationDelay: `${i * 0.2}s` }} />)}
                  </div>
                </div>
              </div>
            ) : activeTab === 'summary' ? (
              result.error ? (
                <div className="h-full flex flex-col items-center justify-center space-y-4 text-center">
                  <ShieldAlert className="w-16 h-16 text-rose-500 mb-2" />
                  <h3 className="text-xl font-bold text-white">Execution Error</h3>
                  <p className="text-slate-400 max-w-sm">
                    {typeof result.error === 'object' 
                      ? (result.error.detail?.[0]?.msg || JSON.stringify(result.error)) 
                      : result.error}
                  </p>
                  <button 
                    onClick={() => setActiveTab('json')}
                    className="text-xs text-sky-400 hover:underline"
                  >
                    View detailed debug logs
                  </button>
                </div>
              ) : (
                <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {/* Result Status Header */}
                <div className={`p-8 rounded-3xl border ${status.border} ${status.bg} ${status.glow} flex flex-col items-center text-center space-y-4`}>
                  {status.icon}
                  <div>
                    <h3 className={`text-4xl font-black tracking-tight ${status.color}`}>{status.label}</h3>
                    <p className="text-slate-400 font-mono mt-1">Unified Risk Index: {score}/100</p>
                  </div>
                </div>

                {/* Explanation Block */}
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 space-y-6 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-4 opacity-5">
                    <MessageSquare size={120} />
                  </div>
                  <div className="space-y-2 relative">
                    <h4 className="text-slate-400 text-xs font-bold uppercase tracking-widest">AI reasoning & explanation</h4>
                    <p className="text-lg text-slate-200 leading-relaxed font-medium">
                      {result.explanation || "No explanation provided by analysis engine."}
                    </p>
                  </div>

                  {result.evidence && result.evidence.length > 0 && (
                    <div className="space-y-4 relative">
                      <h4 className="text-slate-400 text-xs font-bold uppercase tracking-widest">Core Evidence</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {result.evidence.map((item, i) => (
                          <div key={i} className="flex items-start space-x-3 p-3 bg-slate-800/40 rounded-xl border border-slate-700/50">
                            <div className="mt-1 w-1.5 h-1.5 rounded-full bg-sky-500 shrink-0 shadow-[0_0_8px_rgba(14,165,233,0.5)]" />
                            <span className="text-sm text-slate-300">{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Result Metrics: 2 Bars */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                   <MetricBox 
                     label="Risk Score" 
                     value={result.main_metrics?.risk_score ?? result.combined_score ?? 0} 
                     info="Combined Threat Probability"
                     isRisk={true}
                    />
                   <MetricBox 
                     label="Scan Confidence" 
                     value={result.main_metrics?.confidence ?? (result.llm_verdict?.confidence * 100) ?? 0} 
                     info="AI Analysis Certainty"
                     isRisk={false}
                    />
                </div>
                </div>
              )
            ) : (
              <div className="h-full animate-in fade-in duration-300">
                <div className="bg-slate-950/50 rounded-2xl border border-slate-800 p-6 h-full font-mono text-[13px]">
                   <JSONViewer data={result} expanded={true} />
                </div>
              </div>
            )}
          </div>

          {/* Footer Metadata */}
          {result && !loading && (
            <div className="h-12 border-t border-slate-800/50 px-6 flex items-center justify-between text-[10px] font-mono text-slate-500">
              <div className="flex space-x-4">
                <span>MID: {result.message_id || 'LOCAL-SIM'}</span>
                <span>ENGINE: v3.0.0-STABLE</span>
              </div>
              <div className="flex items-center">
                 <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 shadow-[0_0_6px_rgba(16,185,129,0.5)]" />
                 SERVER LINK SECURE
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

const MetricBox = ({ label, value, info, isRisk }) => {
  const getProgressColor = () => {
    if (isRisk) {
      if (value >= 70) return 'bg-rose-500 shadow-[0_0_12px_rgba(244,63,94,0.4)]';
      if (value >= 30) return 'bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.4)]';
      return 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]';
    } else {
      // Confidence: High is Good (Emerald)
      if (value >= 80) return 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]';
      if (value >= 50) return 'bg-sky-500 shadow-[0_0_12px_rgba(14,165,233,0.4)]';
      return 'bg-slate-500';
    }
  };

  return (
    <div className="bg-slate-900/40 border border-slate-800/80 p-5 rounded-2xl flex flex-col space-y-4">
      <div className="flex justify-between items-start">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{label}</span>
        <span className="text-xl font-bold font-mono text-white">{value}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full ${getProgressColor()} transition-all duration-1000 shadow-[0_0_8px_rgba(0,0,0,0.5)]`} 
          style={{ width: `${value}%` }} 
        />
      </div>
      <span className="text-[10px] font-mono text-slate-400 flex items-center">
        <ExternalLink className="w-3 h-3 mr-1 opacity-50" /> STATUS: {info}
      </span>
    </div>
  );
};

export default TestingInterface;
