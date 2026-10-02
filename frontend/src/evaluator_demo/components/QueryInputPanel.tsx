import React, { useState } from 'react';
import { Search, Play, RotateCcw, ToggleLeft, ToggleRight } from 'lucide-react';

interface QueryInputPanelProps {
  onRun: (queryText: string) => void;
  onReset: () => void;
  demoMode: boolean;
  onToggleDemoMode: (val: boolean) => void;
  isSimulating: boolean;
}

export default function QueryInputPanel({
  onRun,
  onReset,
  demoMode,
  onToggleDemoMode,
  isSimulating
}: QueryInputPanelProps) {
  const [inputText, setInputText] = useState("Can I sell 5 tons of tomato in Kolar today?");

  const sampleChips = [
    "Can I sell 5 tons of tomato in Kolar today?",
    "Will onion prices increase next week in Bengaluru?",
    "Should I hold my potato stock for 7 days?",
    "What is the outlook for chilli in Hubli?"
  ];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim()) {
      onRun(inputText);
    }
  };

  const handleChipClick = (chip: string) => {
    setInputText(chip);
    onRun(chip);
  };

  const handleResetClick = () => {
    setInputText("");
    onReset();
  };

  return (
    <div className="border border-slate-900 bg-slate-950/80 rounded-xl p-5 shadow-2xl backdrop-blur-xl space-y-4">
      
      {/* Ask MandiSense Header & Demo Toggle */}
      <div className="flex items-center justify-between border-b border-slate-900/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-sky-950/50 border border-sky-400/20 flex items-center justify-center">
            <Search className="w-3.5 h-3.5 text-sky-400" />
          </div>
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-widest font-mono">
            Ask MandiSense
          </h3>
        </div>

        {/* Demo Mode Toggle */}
        <div className="flex items-center gap-2 font-mono text-[9px]">
          <span className="text-slate-500 uppercase font-bold">Demo Mode:</span>
          <button 
            onClick={() => onToggleDemoMode(!demoMode)}
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            {demoMode ? (
              <ToggleRight className="w-6 h-6 text-sky-400" />
            ) : (
              <ToggleLeft className="w-6 h-6 text-slate-650" />
            )}
          </button>
        </div>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={isSimulating}
            placeholder="Ask a commodity intelligence question..."
            className="w-full pl-4 pr-10 py-2.5 rounded-lg border border-slate-900 bg-slate-900/20 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-sky-500/50 focus:bg-slate-900/40 disabled:opacity-50 transition-all"
          />
        </div>

        <div className="flex gap-2 shrink-0">
          <button
            type="submit"
            disabled={isSimulating || !inputText.trim()}
            className="flex-1 sm:flex-none py-2.5 px-5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:bg-slate-900 text-white disabled:text-slate-650 font-bold text-xs tracking-wide transition-all shadow-[0_0_12px_rgba(56,189,248,0.15)] flex items-center justify-center gap-1.5 active:scale-[0.98]"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Run Analysis
          </button>

          <button
            type="button"
            onClick={handleResetClick}
            className="py-2.5 px-4 rounded-lg border border-slate-900 hover:bg-slate-900/40 text-slate-400 hover:text-slate-250 font-semibold text-xs transition-all flex items-center justify-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>
      </form>

      {/* Query Chips */}
      <div className="space-y-1.5">
        <span className="text-[8px] font-mono text-slate-500 uppercase font-bold tracking-wider block">Sample Scenarios:</span>
        <div className="flex flex-wrap gap-2">
          {sampleChips.map((chip, idx) => {
            const isSelected = inputText === chip;
            return (
              <button
                key={idx}
                type="button"
                disabled={isSimulating}
                onClick={() => handleChipClick(chip)}
                className={`
                  px-2.5 py-1.5 rounded-md text-[9px] font-mono text-left border transition-all duration-300
                  ${isSelected
                    ? 'border-sky-500/30 text-sky-400 bg-sky-950/20'
                    : 'border-slate-900 text-slate-400 bg-slate-950/40 hover:border-slate-800 hover:text-slate-300'
                  }
                  disabled:opacity-50 disabled:pointer-events-none
                `}
              >
                {chip}
              </button>
            );
          })}
        </div>
      </div>

    </div>
  );
}
