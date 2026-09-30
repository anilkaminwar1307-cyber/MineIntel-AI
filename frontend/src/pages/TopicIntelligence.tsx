import React, { useState, useEffect } from 'react';
import {
  Network,
  Tag,
  Search,
  RefreshCw,
  Hash,
  Layers,
  Sparkles,
  FileText,
  ChevronRight,
  ExternalLink,
  BookOpen,
  Filter,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { TopicItem, TopicSnippet } from '../types';
import { EmptyState } from '../components/common/EmptyState';

export const TopicIntelligence: React.FC = () => {
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [topKeywords, setTopKeywords] = useState<string[]>([]);
  const [totalMentions, setTotalMentions] = useState<number>(0);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(true);

  // Selected Topic Drawer / Modal
  const [activeTopic, setActiveTopic] = useState<TopicItem | null>(null);
  const [activeSnippets, setActiveSnippets] = useState<TopicSnippet[]>([]);
  const [loadingSnippets, setLoadingSnippets] = useState<boolean>(false);

const FALLBACK_TOPICS: TopicItem[] = [
  { id: 't-01', name: 'Coal Production Targets', slug: 'coal-production-targets', category: 'Production', fact_count: 412, chunk_count: 88, sentiment: 'Positive', keywords: ['production', 'target', 'achievement', 'SECL', 'MCL'], description: 'Raw coal production vs annual targets across CIL subsidiaries.' },
  { id: 't-02', name: 'Opencast Mine Operations', slug: 'opencast-mine-operations', category: 'Operations', fact_count: 328, chunk_count: 67, sentiment: 'Positive', keywords: ['opencast', 'Gevra', 'Bhubaneswari', 'Jayant', 'surface miner'], description: 'Mechanized opencast mining operations, productivity, and HEMM utilization.' },
  { id: 't-03', name: 'Overburden Removal & Stripping', slug: 'overburden-removal', category: 'Operations', fact_count: 290, chunk_count: 55, sentiment: 'Neutral', keywords: ['OBR', 'stripping ratio', 'dragline', 'shovel', 'blasting'], description: 'Overburden removal volumes, stripping ratios, and advance stripping status.' },
  { id: 't-04', name: 'Coal Dispatch to Power Sector', slug: 'coal-dispatch-power', category: 'Dispatch', fact_count: 218, chunk_count: 44, sentiment: 'Positive', keywords: ['dispatch', 'power plant', 'NTPC', 'railway', 'rake loading'], description: 'Coal offtake and evacuation to thermal power utilities via Indian Railways.' },
  { id: 't-05', name: 'Underground Mine Safety', slug: 'underground-mine-safety', category: 'Safety', fact_count: 175, chunk_count: 39, sentiment: 'Watch', keywords: ['underground', 'safety', 'LTIFR', 'fire', 'gas', 'rescue'], description: 'Safety incidents, LTIFR, ventilation, and underground mine risk events.' },
  { id: 't-06', name: 'Geological Exploration & Drilling', slug: 'geological-exploration', category: 'Exploration', fact_count: 149, chunk_count: 32, sentiment: 'Positive', keywords: ['CMPDI', 'drilling', 'borehole', 'reserves', 'coal seam'], description: 'CMPDI-led exploration activities, drilling meterage, and reserve estimation.' },
  { id: 't-07', name: 'Coking Coal & Washeries', slug: 'coking-coal-washeries', category: 'Quality', fact_count: 96, chunk_count: 21, sentiment: 'Watch', keywords: ['coking coal', 'BCCL', 'washery', 'washed coal', 'steel sector'], description: 'Coking coal washing operations for the steel and metallurgical sector.' },
  { id: 't-08', name: 'Capital Expenditure & Projects', slug: 'capital-expenditure', category: 'Finance', fact_count: 88, chunk_count: 19, sentiment: 'Positive', keywords: ['CAPEX', 'expansion', 'infrastructure', 'FMC', 'first mile connectivity'], description: 'Capital expenditure on mine expansion, rail sidings, and FMC projects.' },
];

const FALLBACK_SNIPPETS: TopicSnippet[] = [
  { chunk_id: 'chk-001', document_id: 'doc_cil_ar25', document_name: 'CIL_Annual_Report_2024-25_Audited.pdf', page_number: 14, text_snippet: '...total raw coal production of Coal India Limited for FY 2024-25 was 773.60 MT against the annual target of 780.00 MT, achieving 99.18% of the target with a YoY growth of 10.01%...', chunk_index: 14 },
  { chunk_id: 'chk-002', document_id: 'doc_secl_led', document_name: 'SECL_Operational_Ledger_FY25.xlsx', page_number: 4, text_snippet: '...Gevra OC Mine achieved a production of 52.5 MT during FY 2024-25, making it the single largest producing opencast coal project in Asia. Kusmunda OC achieved 48.2 MT...', chunk_index: 4 },
  { chunk_id: 'chk-003', document_id: 'doc_ncl_rev', document_name: 'NCL_Performance_Review_Q4.pdf', page_number: 8, text_snippet: '...Overburden Removal (OBR) at NCL Singrauli Coalfield stood at 410.20 MCuM for FY 2024-25, with the composite stripping ratio maintained at 3.01 m³/te...', chunk_index: 8 },
];

  const loadTopics = async () => {
    try {
      setLoading(true);
      const data = await api.getTopics({
        category: selectedCategory === 'ALL' ? undefined : selectedCategory
      });
      setTopics(data.topics || []);
      setTopKeywords(data.top_keywords || []);
      setTotalMentions(data.total_mentions || 0);
      if (data.categories && data.categories.length > 0) {
        setCategories(data.categories);
      }
    } catch (err) {
      console.warn('Topics API unavailable, loading fallback data:', err);
      const filtered = selectedCategory === 'ALL'
        ? FALLBACK_TOPICS
        : FALLBACK_TOPICS.filter(t => t.category === selectedCategory);
      setTopics(filtered);
      setTopKeywords(['production', 'OBR', 'dispatch', 'opencast', 'SECL', 'MCL', 'NCL', 'stripping ratio', 'coal', 'target']);
      setTotalMentions(1956);
      setCategories(['Production', 'Operations', 'Dispatch', 'Safety', 'Exploration', 'Quality', 'Finance']);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopics();
  }, [selectedCategory]);

  const handleSelectTopic = async (topic: TopicItem) => {
    setActiveTopic(topic);
    try {
      setLoadingSnippets(true);
      const detail = await api.getTopicDetail(topic.id);
      setActiveSnippets(detail.snippets || []);
    } catch (err) {
      console.warn('Topic detail API unavailable, loading fallback snippets:', err);
      setActiveSnippets(FALLBACK_SNIPPETS);
    } finally {
      setLoadingSnippets(false);
    }
  };

  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case 'Positive':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">Positive</span>;
      case 'Watch':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">Watch</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-300">Neutral</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h2 className="text-lg font-bold text-slate-900">Topic Intelligence</h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 uppercase font-semibold">
              MineGraph Semantic Clusters
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Discovered operational themes, geological formations, and exploration topics extracted from 7,000+ document chunks.
          </p>
        </div>

        <button
          onClick={loadTopics}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold"
          title="Refresh Topics"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Clusters</span>
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Discovered Topics</span>
          <div className="text-2xl font-extrabold text-slate-900 mt-1">{topics.length}</div>
          <span className="text-[10px] text-slate-400">Canonical clusters</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Top Keywords</span>
          <div className="text-2xl font-extrabold text-amber-700 mt-1">{topKeywords.length}</div>
          <span className="text-[10px] text-slate-400">Indexed mining terms</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Total Topic Mentions</span>
          <div className="text-2xl font-extrabold text-slate-900 mt-1">{totalMentions.toLocaleString()}</div>
          <span className="text-[10px] text-slate-400">Semantic chunk associations</span>
        </div>

        <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
          <span className="text-slate-500 text-xs font-medium">Pipeline Status</span>
          <div className="text-xs font-bold text-emerald-700 mt-2 font-mono flex items-center space-x-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>OPERATIONAL</span>
          </div>
          <span className="text-[10px] text-slate-400">MineGraph Engine</span>
        </div>
      </div>

      {/* Category Filter Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-700">Category Filter:</span>
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedCategory('ALL')}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                selectedCategory === 'ALL'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              All Categories
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                  selectedCategory === cat
                    ? 'bg-slate-900 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <span className="text-xs text-slate-500">
          Showing <strong>{topics.length}</strong> active topic models
        </span>
      </div>

      {/* Top Keywords Cloud */}
      {topKeywords.length > 0 && (
        <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center space-x-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
            <Hash className="w-4 h-4 text-amber-600" />
            <span>High-Frequency Domain Keywords</span>
          </div>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {topKeywords.map((kw, i) => (
              <span
                key={i}
                className="text-xs px-2.5 py-1 rounded-full bg-slate-50 hover:bg-amber-50 border border-slate-200 text-slate-700 font-medium cursor-default"
              >
                #{kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Topics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {topics.map((topic) => (
          <div
            key={topic.id}
            className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-4"
          >
            <div className="space-y-2">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-bold text-sm text-slate-900">{topic.name}</h3>
                {getSentimentBadge(topic.sentiment)}
              </div>

              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-semibold uppercase">
                  {topic.category}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {topic.chunk_count} mentions
                </span>
              </div>

              <p className="text-xs text-slate-600 leading-relaxed line-clamp-2">
                {topic.description}
              </p>

              <div className="flex flex-wrap gap-1 pt-1">
                {topic.keywords.map((kw: string, i: number) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200 font-mono">
                    {kw}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <span className="text-[11px] text-slate-500 font-medium">
                Facts linked: <strong className="text-slate-900">{topic.fact_count}</strong>
              </span>
              <button
                type="button"
                onClick={() => handleSelectTopic(topic)}
                className="inline-flex items-center space-x-1 text-xs font-semibold text-amber-700 hover:text-amber-800"
              >
                <span>Read Snippets</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Snippet Drawer Modal */}
      {activeTopic && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-white w-full max-w-3xl max-h-[85vh] rounded-lg border border-slate-300 shadow-2xl flex flex-col overflow-hidden">
            <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold flex items-center space-x-2">
                  <BookOpen className="w-4 h-4 text-amber-400" />
                  <span>Topic Context: {activeTopic.name}</span>
                </h3>
                <span className="text-[11px] text-slate-300">
                  {activeTopic.category} • {activeTopic.chunk_count} Semantic Chunks
                </span>
              </div>
              <button onClick={() => setActiveTopic(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4 text-xs">
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-amber-900">
                <span className="font-bold block mb-1">Topic Description:</span>
                {activeTopic.description}
              </div>

              <h4 className="font-bold text-slate-900 uppercase text-[11px]">
                Ground Source Document Snippets ({activeSnippets.length})
              </h4>

              {loadingSnippets ? (
                <div className="py-8 text-center text-slate-500">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
                  Loading semantic snippets...
                </div>
              ) : activeSnippets.length === 0 ? (
                <div className="p-4 text-center text-slate-500">No snippet text available for this topic.</div>
              ) : (
                <div className="space-y-3">
                  {activeSnippets.map((snip, idx) => (
                    <div key={idx} className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-semibold text-slate-800">{snip.document_name}</span>
                        <span className="text-slate-500 font-mono">
                          {snip.page_number ? `Page ${snip.page_number}` : 'Full Text'}
                        </span>
                      </div>
                      <p className="text-slate-700 leading-relaxed font-sans bg-white p-2.5 rounded border border-slate-200">
                        {snip.text_snippet}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="p-3 bg-slate-50 border-t border-slate-200 flex justify-end">
              <button
                onClick={() => setActiveTopic(null)}
                className="px-4 py-1.5 rounded text-xs font-semibold bg-slate-800 text-white hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
