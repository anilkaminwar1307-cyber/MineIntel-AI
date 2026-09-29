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
  Layers,
  GitBranch,
  Landmark,
  LogOut,
  Lock,
  UploadCloud,
  ShieldAlert,
} from 'lucide-react';
import { HealthInfo, UserProfile } from '../../types';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  health: HealthInfo | null;
  user?: UserProfile | null;
  onLogout?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, health, user, onLogout }) => {
  const role = user?.role || 'Analyst';
  const isAdmin = role === 'Admin';
  const isReviewerOrAdmin = role === 'Reviewer' || role === 'Admin';

  const navSections = [
    {
      heading: 'INTELLIGENCE',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'ask', label: 'Ask MineIntel', icon: MessageSquareText },
        { id: 'analytics', label: 'Analytics', icon: LineChart },
        { id: 'minegraph', label: 'MineGraph', icon: GitBranch },
        { id: 'parliamentary', label: 'Parliamentary Brief', icon: Landmark },
      ]
    },
    {
      heading: 'EVIDENCE',
      items: [
        { id: 'upload', label: 'Upload & Ingestion', icon: UploadCloud },
        { id: 'documents', label: 'Documents', icon: Files },
        { id: 'evidence', label: 'Evidence Ledger', icon: Database },
        {
          id: 'reviews',
          label: 'Review Queue',
          icon: CheckSquare,
          restricted: !isReviewerOrAdmin,
          requiredRole: 'Reviewer+'
        },
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
        { id: 'data_quality', label: 'Data Quality', icon: ShieldAlert },
        { id: 'audit', label: 'Audit Trail', icon: History },
        {
          id: 'settings',
          label: 'Settings',
          icon: Settings,
          restricted: !isAdmin,
          requiredRole: 'Admin only'
        },
      ]
    }
  ];

  const isHealthy = health?.status === 'ok';
  const userInitials = (user?.full_name || user?.username || 'OP')
    .split(' ')
    .map(p => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

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
                SIH 2026
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
              const isRestricted = (item as any).restricted;
              const requiredRole = (item as any).requiredRole;

              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  title={isRestricted ? `Requires ${requiredRole}` : item.label}
                  className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-md transition-all ${
                    isActive
                      ? 'bg-amber-600/20 text-amber-300 border-l-2 border-amber-500'
                      : isRestricted
                      ? 'text-slate-500 hover:text-slate-400 hover:bg-slate-900/40 opacity-70'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 truncate">
                    <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-amber-400' : 'text-slate-400'}`} />
                    <span className="truncate">{item.label}</span>
                  </div>
                  {isRestricted && (
                    <span className="flex items-center space-x-1 text-[9px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60 font-mono">
                      <Lock className="w-2.5 h-2.5" />
                      <span>{requiredRole}</span>
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Bottom Status & Authenticated User Bar */}
      <div className="p-3 border-t border-slate-800/80 bg-[#090e1a] space-y-2.5">
        {/* System Status Indicator */}
        <div className="flex items-center justify-between text-[11px] px-2 py-1.5 rounded bg-slate-900/80 border border-slate-800">
          <div className="flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`}></span>
            <span className="text-slate-300">
              {isHealthy ? 'Core Operational' : 'Backend Disconnected'}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">{health?.version || 'v0.2.0'}</span>
        </div>

        {/* Authenticated Operator Profile Card */}
        <div className="flex items-center justify-between px-2 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800">
          <div className="flex items-center space-x-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-amber-600/30 to-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-300 font-bold text-xs flex-shrink-0">
              {userInitials}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-slate-200 truncate">
                {user?.full_name || user?.username || 'Analyst'}
              </p>
              <div className="flex items-center space-x-1 text-[10px] text-slate-400">
                <span className={`px-1.5 py-0.2 rounded font-medium text-[9px] ${
                  role === 'Admin'
                    ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                    : role === 'Reviewer'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}>
                  {role}
                </span>
                <span className="truncate">&bull; CIL</span>
              </div>
            </div>
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              title="Sign Out"
              className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};

