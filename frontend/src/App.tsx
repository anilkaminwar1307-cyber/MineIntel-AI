import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { Overview } from './pages/Overview';
import { Documents } from './pages/Documents';
import { DocumentDetail } from './pages/DocumentDetail';
import { EvidenceLedger } from './pages/EvidenceLedger';
import { ReviewQueue } from './pages/ReviewQueue';
import { AskMineIntel } from './pages/AskMineIntel';
import { Analytics } from './pages/Analytics';
import { TopicIntelligence } from './pages/TopicIntelligence';
import { ReportStudio } from './pages/ReportStudio';
import { AuditTrail } from './pages/AuditTrail';
import { Settings } from './pages/Settings';
import { NotFound } from './pages/NotFound';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { api } from './services/api';
import { HealthInfo, DocumentItem } from './types';
import { Files } from 'lucide-react';

const VALID_TABS = [
  'overview',
  'ask',
  'analytics',
  'documents',
  'document_detail',
  'evidence',
  'reviews',
  'topics',
  'reports',
  'audit',
  'settings'
] as const;

type TabType = typeof VALID_TABS[number] | '404';

const getInitialTabFromUrl = (): TabType => {
  // 1. Check hash first (e.g. #/ask or #ask)
  const hash = window.location.hash.replace(/^#[/]?/, '').trim().toLowerCase();
  if (hash) {
    if (VALID_TABS.includes(hash as any)) {
      return hash as TabType;
    }
    return '404';
  }

  // 2. Check pathname (e.g. /ask or /analytics)
  const pathname = window.location.pathname.replace(/^\/+|\/+$/g, '').trim().toLowerCase();
  if (pathname && pathname !== '' && pathname !== 'index.html') {
    if (VALID_TABS.includes(pathname as any)) {
      return pathname as TabType;
    }
    return '404';
  }

  return 'overview';
};

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<TabType>(getInitialTabFromUrl);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);

  const fetchHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.warn('Backend currently unreachable', err);
      setHealth({
        status: 'error',
        database: 'error',
        storage: 'unavailable',
        gemini: 'not_configured',
        version: '0.1.0',
        app_name: 'MineIntel'
      });
    }
  };

  const navigateTab = useCallback((tab: string) => {
    const normalized = tab.trim().toLowerCase();
    const targetTab: TabType = VALID_TABS.includes(normalized as any)
      ? (normalized as TabType)
      : '404';

    if (targetTab !== 'document_detail') {
      setSelectedDoc(null);
    }

    setCurrentTab(targetTab);

    // Update browser URL without reloading
    const newHash = targetTab === 'overview' ? '#/' : `#/${targetTab}`;
    if (window.location.hash !== newHash) {
      window.history.pushState(null, '', newHash);
    }
  }, []);

  // Listen for browser back / forward navigation
  useEffect(() => {
    const handleLocationChange = () => {
      const detected = getInitialTabFromUrl();
      setCurrentTab(detected);
    };

    window.addEventListener('popstate', handleLocationChange);
    window.addEventListener('hashchange', handleLocationChange);

    return () => {
      window.removeEventListener('popstate', handleLocationChange);
      window.removeEventListener('hashchange', handleLocationChange);
    };
  }, []);

  useEffect(() => {
    fetchHealth();
    // Poll health status every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getPageMeta = () => {
    switch (currentTab) {
      case 'overview':
        return {
          title: 'Operations Intelligence Overview',
          subtitle: 'Evidence-backed geological, production, and drilling intelligence'
        };
      case 'ask':
        return {
          title: 'Ask MineIntel',
          subtitle: 'Grounded natural language query interface for mining records'
        };
      case 'analytics':
        return {
          title: 'Mining Intelligence Analytics',
          subtitle: 'Aggregated subsidiary metrics, targets, and production distributions'
        };
      case 'documents':
        return {
          title: 'Document Library',
          subtitle: 'Multi-format mining document ingestion repository'
        };
      case 'document_detail':
        return {
          title: selectedDoc ? selectedDoc.original_filename : 'Document Details',
          subtitle: 'Granular provenance coordinates, storage, and metadata'
        };
      case 'evidence':
        return {
          title: 'Evidence Ledger',
          subtitle: 'Structured relational facts with source page and cell coordinates'
        };
      case 'reviews':
        return {
          title: 'Review Queue',
          subtitle: 'Human-in-the-loop validation and discrepancy resolution'
        };
      case 'topics':
        return {
          title: 'Topic Intelligence',
          subtitle: 'Semantic clustering and operational theme discovery'
        };
      case 'reports':
        return {
          title: 'Report Studio',
          subtitle: 'Audit-ready report generator with ReportGuard citation verification'
        };
      case 'audit':
        return {
          title: 'Audit Trail',
          subtitle: 'Immutable record of document mutations and analyst verifications'
        };
      case 'settings':
        return {
          title: 'Platform Settings',
          subtitle: 'Subsystem diagnostics, storage paths, and AI provider configurations'
        };
      default:
        return {
          title: 'MineIntel Platform',
          subtitle: 'Evidence Intelligence for Mining & Geological Operations'
        };
    }
  };

  const meta = getPageMeta();

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      {/* Fixed Left Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={navigateTab}
        health={health}
      />

      {/* Main Workspace Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header */}
        <Header
          title={meta.title}
          subtitle={meta.subtitle}
          health={health}
          onRefreshHealth={fetchHealth}
        />

        {/* Scrollable Page Content with Global ErrorBoundary */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-100/70">
          <ErrorBoundary
            key={currentTab}
            fallbackTitle="MineIntel encountered a display error."
            fallbackMessage="An unexpected error occurred while rendering this module. Your evidence data and backend connections remain unaffected."
            onReset={() => navigateTab('overview')}
          >
            {currentTab === 'overview' && <Overview onNavigate={navigateTab} />}
            {currentTab === 'documents' && (
              <Documents
                onViewDocument={(doc) => {
                  setSelectedDoc(doc);
                  setCurrentTab('document_detail');
                  window.history.pushState(null, '', '#/document_detail');
                }}
              />
            )}
            {currentTab === 'document_detail' && (
              selectedDoc ? (
                <DocumentDetail
                  document={selectedDoc}
                  onBack={() => navigateTab('documents')}
                />
              ) : (
                <div className="bg-white p-8 rounded-lg border border-slate-200 text-center space-y-4 max-w-lg mx-auto mt-10">
                  <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-amber-600">
                    <Files className="w-6 h-6" />
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-base font-bold text-slate-900">No Document Selected</h3>
                    <p className="text-xs text-slate-500">
                      Please choose a file from the Document Library to inspect its coordinates and provenance.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigateTab('documents')}
                    className="inline-flex items-center space-x-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                  >
                    Return to Document Library
                  </button>
                </div>
              )
            )}
            {currentTab === 'evidence' && <EvidenceLedger onNavigate={navigateTab} />}
            {currentTab === 'reviews' && <ReviewQueue onNavigate={navigateTab} />}
            {currentTab === 'ask' && <AskMineIntel />}
            {currentTab === 'analytics' && <Analytics />}
            {currentTab === 'topics' && <TopicIntelligence />}
            {currentTab === 'reports' && <ReportStudio />}
            {currentTab === 'audit' && <AuditTrail />}
            {currentTab === 'settings' && <Settings />}
            {currentTab === '404' && (
              <NotFound onNavigate={navigateTab} requestedRoute={window.location.hash || window.location.pathname} />
            )}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
};

export default App;
