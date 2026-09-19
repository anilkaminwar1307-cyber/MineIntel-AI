export interface HealthInfo {
  status: 'ok' | 'degraded' | 'error';
  database: 'connected' | 'error' | 'disconnected';
  storage: 'available' | 'error' | 'unavailable';
  gemini: 'configured' | 'not_configured';
  version: string;
  app_name: string;
}

export interface Capabilities {
  document_upload: boolean;
  pdf_extraction: boolean;
  spreadsheet_processing: boolean;
  ocr: boolean;
  evidence_ledger: boolean;
  query_engine: boolean;
  semantic_search: boolean;
  report_generation: boolean;
  topic_intelligence: boolean;
}

export interface DocumentItem {
  id: string;
  original_filename: string;
  stored_filename: string;
  file_type: string;
  source_type?: string | null;
  quality_label?: string | null;
  mime_type: string;
  file_size: number;
  document_category: string;
  organization: string;
  reporting_period?: string | null;
  storage_path: string;
  page_count: number;
  sheet_count: number;
  table_count?: number;
  status: string;
  processing_progress: number;
  processing_message?: string | null;
  processing_error?: string | null;
  fact_count: number;
  topic_count: number;
  created_at: string;
  processed_at?: string | null;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentPageItem {
  id: string;
  document_id: string;
  page_number: number;
  raw_text?: string | null;
  char_count: number;
  word_count: number;
  has_native_text: boolean;
  is_ocr_page: boolean;
  ocr_confidence?: number | null;
  extraction_method?: string | null;
  created_at: string;
}

export interface DocumentSheetItem {
  id: string;
  document_id: string;
  sheet_name: string;
  sheet_index: number;
  row_count: number;
  col_count: number;
  used_range?: string | null;
  header_row?: number | null;
  has_merged_cells: boolean;
  created_at: string;
}

export interface DocumentTableItem {
  id: string;
  document_id: string;
  sheet_id?: string | null;
  table_index: number;
  source_type: string;
  page_number?: number | null;
  sheet_name?: string | null;
  title?: string | null;
  row_count: number;
  col_count: number;
  headers_json?: string | null;
  data_json?: string | null;
  confidence: number;
  structure_status?: string | null;
  created_at: string;
}

export interface DocumentChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  page_number?: number | null;
  sheet_name?: string | null;
  section?: string | null;
  content: string;
  token_count?: number | null;
  created_at: string;
}

export interface DocumentQualityItem {
  id: string;
  document_id: string;
  quality_score?: number | null;
  quality_label?: string | null;
  enhancement_recommended: boolean;
  enhancement_applied: boolean;
  enhancement_methods?: string | null;
  blur_level?: string | null;
  contrast_level?: string | null;
  noise_level?: string | null;
  skew_angle?: number | null;
  detected_dpi?: number | null;
  quality_score_before?: number | null;
  quality_score_after?: number | null;
  ocr_confidence_before?: number | null;
  ocr_confidence_after?: number | null;
  created_at: string;
}

export interface ProcessingLogItem {
  id: string;
  document_id: string;
  level: string;
  stage?: string | null;
  message: string;
  timestamp: string;
}

export interface ExtractedFact {
  id: string;
  document_id: string;
  metric_code: string;
  metric_name: string;
  raw_metric_name?: string | null;
  numeric_value?: number | null;
  text_value?: string | null;
  unit?: string | null;
  raw_unit?: string | null;
  reporting_period?: string | null;
  organization: string;
  subsidiary?: string | null;
  coalfield?: string | null;
  mine?: string | null;
  location?: string | null;
  page_number?: number | null;
  sheet_name?: string | null;
  row_number?: number | null;
  column_name?: string | null;
  cell_reference?: string | null;
  table_reference?: string | null;
  source_context?: string | null;
  extraction_method: string;
  confidence_score: number;
  validation_status: string;
  human_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface FactSourceProvenance {
  fact_id: string;
  metric_code: string;
  metric_name: string;
  numeric_value?: number | null;
  unit?: string | null;
  reporting_period?: string | null;
  subsidiary?: string | null;
  confidence_score: number;
  validation_status: string;
  human_verified: boolean;
  provenance: {
    document_id: string;
    document_name: string;
    document_category?: string | null;
    page_number?: number | null;
    sheet_name?: string | null;
    row_number?: number | null;
    column_name?: string | null;
    cell_reference?: string | null;
    table_reference?: string | null;
    source_context?: string | null;
    extraction_method: string;
  };
}

export interface ExtractedFactListResponse {
  items: ExtractedFact[];
  total: number;
  page: number;
  page_size: number;
  verified_count: number;
  needs_review_count: number;
  conflict_count: number;
}

export interface AuditItem {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  details?: string | null;
}

export interface AuditEventListResponse {
  items: AuditItem[];
  total: number;
}

export interface OverviewKPIs {
  documents_processed: number;
  facts_extracted: number;
  verified_evidence: number;
  pending_reviews: number;
  average_confidence: number;
  reports_generated: number;
}

export interface SubsidiarySummary {
  subsidiary: string;
  fact_count: number;
  coalfield_count: number;
}

export interface MetricDistribution {
  metric_code: string;
  metric_name: string;
  count: number;
}

export interface AnalyticsOverview {
  kpis: OverviewKPIs;
  subsidiaries: SubsidiarySummary[];
  top_metrics: MetricDistribution[];
  recent_activity_count: number;
  multi_year_production_trends?: Array<{
    period: string;
    total_production_mt: number;
    target_mt: number;
    dispatch_mt: number;
    achievement_rate_pct: number;
  }>;
  target_vs_achievement?: Array<{
    subsidiary: string;
    actual_mt: number;
    target_mt: number;
    variance_mt: number;
    achievement_pct: number;
  }>;
  production_vs_dispatch?: Array<{
    subsidiary: string;
    production_mt: number;
    dispatch_mt: number;
    stock_addition_mt: number;
  }>;
  confidence_distribution?: Record<string, number>;
  available_financial_years?: string[];
  available_subsidiaries?: string[];
}

export interface AnalyticsExtended {
  production_growth_yoy: Array<{ period: string; production_mt: number; yoy_growth_pct: number }>;
  metric_type_breakdown: Array<{ metric_code: string; metric_name: string; count: number }>;
  subsidiary_fact_share: Array<{ subsidiary: string; count: number; share_pct: number }>;
  extraction_method_mix: Array<{ method: string; count: number }>;
  monthly_uploads: Array<{ month: string; count: number }>;
  coalfield_production: Array<{ coalfield: string; production_mt: number }>;
  verification_rate_by_sub: Array<{ subsidiary: string; total_facts: number; verified_facts: number; verification_rate_pct: number }>;
  stripping_ratio_trend: Array<{ period: string; ob_bcm: number; coal_mt: number; stripping_ratio: number }>;
  confidence_histogram: Array<{ bucket: string; count: number }>;
  top_mines: Array<{ mine: string; production_mt: number }>;
  offtake_gap: Array<{ subsidiary: string; production_mt: number; offtake_mt: number; gap_mt: number }>;
  issue_type_dist: Array<{ type: string; count: number }>;
  doc_type_mix: Array<{ file_type: string; count: number }>;
  audit_activity_trend: Array<{ day: string; events: number }>;
}

export interface ReviewItem {
  id: string;
  document_id: string;
  fact_id?: string | null;
  issue_type: string;
  severity: string;
  description: string;
  is_resolved: boolean;
  created_at: string;
  metric_name?: string | null;
  raw_value?: string | null;
  source_reference?: string | null;
}

export interface ReviewQueueResponse {
  open_reviews: number;
  conflicts: number;
  low_confidence: number;
  missing_metadata: number;
  items: ReviewItem[];
  total?: number;
  page?: number;
  page_size?: number;
}

export interface ConflictItem {
  id: string;
  subsidiary: string;
  metric_code: string;
  reporting_period: string;
  fact_a_id: string;
  fact_a_value: number;
  fact_a_doc: string;
  fact_b_id: string;
  fact_b_value: number;
  fact_b_doc: string;
  discrepancy_pct: number;
  status: string;
  detected_at: string;
}

export interface ConflictListResponse {
  conflicts: ConflictItem[];
  total: number;
}

export interface EvidenceSourceCitation {
  fact_id: string;
  document_id: string;
  document_name: string;
  metric_code: string;
  metric_name: string;
  numeric_value: number;
  unit: string;
  subsidiary?: string | null;
  reporting_period?: string | null;
  page_number?: number | null;
  sheet_name?: string | null;
  row_number?: number | null;
  column_name?: string | null;
  cell_reference?: string | null;
  source_context?: string | null;
  confidence_score: number;
  human_verified: boolean;
}

export interface QueryChart {
  type: string; // 'bar' | 'line'
  title: string;
  data: Array<Record<string, any>>;
}

export interface QueryResponse {
  query: string;
  status: 'SUCCESS' | 'INSUFFICIENT_EVIDENCE' | 'ERROR';
  answer: string;
  sql_query?: string | null;
  calculation_steps?: string[] | null;
  direct_metric_value?: number | null;
  metric_unit?: string | null;
  verification_result?: 'SUPPORTED' | 'CONFLICTING' | 'PARTIALLY_SUPPORTED' | 'INSUFFICIENT_EVIDENCE' | null;
  verified_facts_count: number;
  confidence_score: number;
  sources: EvidenceSourceCitation[];
  chart?: QueryChart | null;
  suggestions?: string[] | null;
}

export interface GeneratedReportItem {
  id: string;
  title: string;
  report_type: string;
  parameters?: string | null;
  status: string;
  summary?: string | null;
  output_path?: string | null;
  pdf_path?: string | null;
  evidence_count: number;
  generated_by: string;
  created_at: string;
  content?: Record<string, any> | null;
}

export interface GeneratedReportListResponse {
  items: GeneratedReportItem[];
  total: number;
  available_templates: string[];
}

export interface ReportGuardCheck {
  name: string;
  description: string;
  status: 'PASSED' | 'WARNING' | 'FAILED';
  value: any;
  threshold: any;
}

export interface ReportGuardResult {
  status: 'PASSED' | 'WARNING' | 'BLOCKED';
  total_evidence_records: number;
  verified_evidence_ratio: number;
  open_conflicts_count: number;
  low_confidence_count: number;
  checks: ReportGuardCheck[];
  can_proceed: boolean;
}

export interface TopicItem {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  category: string;
  fact_count: number;
  chunk_count: number;
  sentiment: string;
  keywords: string[];
}

export interface TopicSnippet {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number?: number | null;
  text_snippet: string;
  chunk_index: number;
}

export interface TopicDetailResponse {
  topic: TopicItem;
  snippets: TopicSnippet[];
}

export interface TopicListResponse {
  topics: TopicItem[];
  top_keywords: string[];
  total_mentions: number;
  categories: string[];
}

export interface ComponentStatus {
  name: string;
  status: 'OPERATIONAL' | 'NOT_CONFIGURED' | 'DEGRADED' | 'ERROR';
  details?: string | null;
  category: string;
}

export interface SystemSettingsStatus {
  app_name: string;
  version: string;
  environment: string;
  demo_mode: boolean;
  record_counts?: Record<string, number> | null;
  components: Record<string, ComponentStatus>;
}
