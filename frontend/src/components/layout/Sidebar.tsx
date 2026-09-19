import React from 'react';
import {
  LayoutDashboard,
  MessageSquareText,
  LineChart,
  Files,
  Database,
  CheckSquare,
  Network,
  FileSpreadsheet,
  History,
  Settings,
  ShieldCheck,
  Server,
  Layers
} from 'lucide-react';
import { HealthInfo } from '../../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  health: HealthInfo | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, health }) => {
  const navSections = [
    {
      heading: 'INTELLIGENCE',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'ask', label: 'Ask MineIntel', icon: MessageSquareText },
        { id: 'analytics', label: 'Analytics', icon: LineChart },
      ]
    },
    {
      heading: 'EVIDENCE',
      items: [
        { id: 'documents', label: 'Documents', icon: Files },
        { id: 'evidence', label: 'Evidence Ledger', icon: Database },
        { id: 'reviews', label: 'Review Queue', icon: CheckSquare },
      ]
    },
    {
      heading: 'INSIGHTS',
      items: [
        { id: 'topics', label: 'Topic Intelligence', icon: Network },
        { id: 'reports', label: 'Report Studio', icon: FileSpreadsheet },
      ]
    },
    {
      heading: 'GOVERNANCE',
      items: [
        { id: 'audit', label: 'Audit Trail', icon: History },
        { id: 'settings', label: 'Settings', icon: Settings },
      ]
    }
  ];

  const isHealthy = health?.status === 'ok';

  return (
    <aside className="w-64 bg-[#0c1322] text-slate-300 flex flex-col h-screen border-r border-slate-800 select-none flex-shrink-0">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 bg-[#090e1a]">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-slate-950 font-black text-lg shadow-inner">
            <Layers className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-bold text-base tracking-wider text-white">MINEINTEL</span>
              <span className="text-[10px] px-1.5 py-0.2 font-semibold bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded">
                PHASE 1
              </span>
            </div>
            <p className="text-[11px] text-slate-400 tracking-tight">Evidence Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
        {navSections.map((section) => (
          <div key={section.heading} className="space-y-1">
            <p className="px-3 text-[10px] font-semibold text-slate-500 tracking-wider uppercase">
              {section.heading}
            </p>
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-medium rounded-md transition-all ${
                    isActive
                      ? 'bg-amber-600/20 text-amber-300 border-l-2 border-amber-500'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-amber-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom Status & Demo User Bar */}
      <div className="p-3 border-t border-slate-800/80 bg-[#090e1a] space-y-2.5">
        {/* System Status Indicator */}
        <div className="flex items-center justify-between text-[11px] px-2 py-1.5 rounded bg-slate-900/80 border border-slate-800">
          <div className="flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`}></span>
            <span className="text-slate-300">
              {isHealthy ? 'Core Operational' : 'Backend Disconnected'}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">v0.1.0</span>
        </div>

        {/* Demo User Info */}
        <div className="flex items-center space-x-2.5 px-2 py-1">
          <div className="w-7 h-7 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-amber-400 font-semibold text-xs">
            CA
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-200 truncate">CMPDI Analyst</p>
            <div className="flex items-center space-x-1.5 text-[10px] text-slate-400">
              <ShieldCheck className="w-3 h-3 text-amber-500" />
              <span>Analyst Role • CIL</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
