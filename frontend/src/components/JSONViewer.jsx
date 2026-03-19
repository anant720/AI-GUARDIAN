import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';

const JSONViewer = ({ data, expanded = true }) => {
  const [isExpanded, setIsExpanded] = useState(expanded);
  const [copied, setCopied] = useState(false);

  if (data === undefined || data === null) {
    return <span className="text-slate-500">null</span>;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isObject = typeof data === 'object';
  const isArray = Array.isArray(data);

  if (!isObject) {
    // Basic types rendering
    if (typeof data === 'string') return <span className="text-emerald-400">"{data}"</span>;
    if (typeof data === 'number') return <span className="text-amber-400">{data}</span>;
    if (typeof data === 'boolean') return <span className="text-sky-400">{data ? 'true' : 'false'}</span>;
    return <span>{String(data)}</span>;
  }

  return (
    <div className="font-mono text-sm relative group w-full">
      <div 
        className="flex items-center cursor-pointer hover:bg-slate-800/50 -ml-5 pl-1 pr-2 py-0.5 rounded text-slate-400"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown className="w-4 h-4 mr-1" /> : <ChevronRight className="w-4 h-4 mr-1" />}
        <span>{isArray ? '[' : '{'}</span>
        {!isExpanded && (
          <span className="text-slate-500 ml-2">
            {Object.keys(data).length} {isArray ? 'items' : 'keys'} {isArray ? ']' : '}'}
          </span>
        )}
      </div>

      <div className="absolute top-0 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button 
          onClick={handleCopy}
          className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
          title="Copy JSON block"
        >
          {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
        </button>
      </div>

      {isExpanded && (
        <div className="pl-4 border-l border-slate-700/50 mt-1 space-y-1">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="flex flex-col sm:flex-row sm:items-start my-1">
              {!isArray && (
                <span className="text-sky-300 mr-2 shrink-0">
                  "{key}": 
                </span>
              )}
              <div className="overflow-x-auto">
                <JSONViewer data={value} expanded={false} />
              </div>
            </div>
          ))}
        </div>
      )}
      {isExpanded && <div className="text-slate-400 mt-1">{isArray ? ']' : '}'}</div>}
    </div>
  );
};

export default JSONViewer;
