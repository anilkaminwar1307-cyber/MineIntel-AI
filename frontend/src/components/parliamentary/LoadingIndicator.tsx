import React, { useState, useEffect } from 'react';
import { Landmark, Shield, Database, Sparkles } from 'lucide-react';

const STEPS = [
  { icon: Database, text: 'Querying 50,000+ Evidence Ledger facts…' },
  { icon: Shield, text: 'Validating NumberSafe 2.0 deterministic SQL aggregates…' },
  { icon: Landmark, text: 'Synthesizing official Ministry of Coal parliamentary brief…' },
];

export const LoadingIndicator: React.FC = () => {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex(prev => (prev + 1) % STEPS.length);
    }, 2200);
    return () => clearInterval(timer);
  }, []);

  const CurrentIcon = STEPS[stepIndex].icon;

  return (
    <div className="flex flex-col items-center justify-center p-12 space-y-5 bg-white rounded-2xl border border-slate-200/80 shadow-xs max-w-lg mx-auto my-8">
      <div className="relative w-14 h-14 flex items-center justify-center">
        <div className="absolute inset-0 rounded-2xl bg-rose-100 animate-ping opacity-30" />
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-rose-700 to-amber-600 flex items-center justify-center text-white shadow-md animate-pulse">
          <CurrentIcon className="w-6 h-6" />
        </div>
      </div>

      <div className="text-center space-y-1.5">
        <h4 className="text-sm font-bold text-slate-800 flex items-center justify-center space-x-1.5">
          <Sparkles className="w-4 h-4 text-amber-500 animate-spin" />
          <span>Generating Official Parliamentary Brief</span>
        </h4>
        <p className="text-xs text-slate-500 font-medium transition-all duration-300">
          {STEPS[stepIndex].text}
        </p>
      </div>

      <div className="flex items-center space-x-1.5">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              i === stepIndex ? 'w-6 bg-rose-600' : 'w-2 bg-slate-200'
            }`}
          />
        ))}
      </div>
    </div>
  );
};
