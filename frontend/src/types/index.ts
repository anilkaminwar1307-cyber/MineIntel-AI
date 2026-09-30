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
  stored_filename?: string;
  file_type: string;
  source_type?: string | null;
  quality_label?: string | null;
  mime_type?: string;
  file_size: number;
  document_category: string;
  organization: string;
  reporting_period?: string | null;
  storage_path?: string;
  page_count: number;
  sheet_count: number;
  table_count?: number;
  status: string;
  processing_progress: number;
  processing_message?: string | null;
  processing_error?: string | null;
  fact_count: number;
  real_fact_count?: number;
  warning_count?: number;
  topic_count?: number;
  is_demo?: boolean;
  sha256?: string | null;
  revision_number?: number;
  is_latest_version?: boolean;
  pipeline_version?: string | null;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
  created_at: string;
  processed_at?: string | null;
  updated_at?: string | null;
  quality_score?: number | null;
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
  organization?: string;
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
  human_verified?: boolean;
  created_at?: string;
  updated_at?: string;
  is_demo?: boolean;
  source?: any;
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

export interface DocumentValidationIssueItem {
  id: string;
  document_id: string;
  fact_id?: string | null;
  issue_type: string;
  severity: string;
  description: string;
  is_resolved: boolean;
  created_at: string;
  metric_name?: string | null;
  numeric_value?: number | null;
  unit?: string | null;
  cell_reference?: string | null;
  page_number?: number | null;
}

export interface DocumentConflictItem {
  id: string;
  metric_code: string;
  primary_fact_id: string;
  conflicting_fact_id: string;
  description: string;
  discrepancy_percent?: number | null;
  status: string;
  created_at: string;
  primary_value?: string | null;
  conflicting_value?: string | null;
}

export interface DocumentValidationsResponse {
  document_id: string;
  total_issues: number;
  open_issues: number;
  resolved_issues: number;
  conflicts_count: number;
  issues: DocumentValidationIssueItem[];
  conflicts: DocumentConflictItem[];
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
  query_id?: string;
  query: string;
  status: 'SUCCESS' | 'INSUFFICIENT_EVIDENCE' | 'ERROR' | string;
  answer_status?: string;
  intent?: string;
  answer: string;
  scope?: string;
  response_mode?: string;
  resolved_context?: {
    subsidiary?: string | null;
    subsidiaries?: string[];
    mine?: string | null;
    metric_code?: string | null;
    metric_name?: string | null;
    period?: string | null;
    document_ids?: string[] | null;
    was_inherited?: boolean;
  } | null;
  confidence?: number;
  confidence_score: number;
  confidence_level?: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence_reason?: string | null;
  confidence_details?: Record<string, any> | null;
  records_used?: number;
  verified_facts_count: number;
  verification_status?: string | null;
  verification_result?: 'SUPPORTED' | 'CONFLICTING' | 'CONTRADICTED' | 'PARTIALLY_SUPPORTED' | 'INSUFFICIENT_EVIDENCE' | string | null;
  citations?: EvidenceSourceCitation[];
  sources: EvidenceSourceCitation[];
  calculation?: string | null;
  calculation_steps?: string[] | null;
  calculation_result?: CalculationResult | null;
  direct_metric_value?: number | null;
  metric_unit?: string | null;
  sql_query?: string | null;
  chart?: QueryChart | null;
  key_figures?: Array<{
    subsidiary?: string;
    metric_name?: string;
    value?: number;
    unit?: string;
    period?: string;
    verified?: boolean;
  }> | null;
  conflicts?: Array<{
    id?: string;
    metric_code?: string;
    subsidiary?: string;
    period?: string;
    values?: any[];
    discrepancy?: number;
    discrepancy_detail?: string;
    description?: string;
  }> | null;
  data_scope?: string;
  is_demo?: boolean;
  suggestions?: string[] | null;
  suggested_followups?: string[] | null;
  execution_time_ms?: number | null;
  mode?: string | null;
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
  generated_by?: string;
  created_at: string;
  content?: Record<string, any> | null;
  subsidiary?: string | null;
  period?: string | null;
  format?: string | null;
  facts_used?: number | null;
  confidence_avg?: number | null;
  file_size?: number;
  only_verified?: boolean;
  is_demo?: boolean;
}

export interface GeneratedReportListResponse {
  items: GeneratedReportItem[];
  total: number;
  available_templates: string[];
}

export interface ReportGuardCheck {
  name: string;
  description?: string;
  status: 'PASSED' | 'WARNING' | 'FAILED';
  value: any;
  threshold: any;
  message?: string;
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

// ─────────────────────────────────────────────────────────────────────────────
// NumberSafe 2.0 — Calculation Audit Trail Types
// ─────────────────────────────────────────────────────────────────────────────

export interface IncludedFact {
  fact_id: string;
  metric_code: string;
  subsidiary?: string | null;
  mine?: string | null;
  reporting_period?: string | null;
  numeric_value?: number | null;
  unit?: string | null;
  confidence_score: number;
  validation_status: string;
  is_demo: boolean;
  document_id: string;
  page_number?: number | null;
  sheet_name?: string | null;
  cell_reference?: string | null;
  source_context?: string | null;
}

export interface ExclusionDecision {
  fact_id: string;
  reason: string;
  excluded_in_favour_of?: string | null;
}

export interface CalculationResult {
  success: boolean;
  error_code?: string | null;
  error_message?: string | null;

  result?: number | null;
  unit?: string | null;
  calculation_method?: string | null;
  formula?: string | null;

  metric_code: string;
  filters_applied: Record<string, any>;

  evidence_count_total: number;
  evidence_count_used: number;
  excluded_count: number;
  verified_count: number;
  verified_pct: number;

  /** 'REAL' | 'DEMO' | 'MIXED' | 'UNKNOWN' */
  is_demo_scope: string;

  included_facts: IncludedFact[];
  exclusions: ExclusionDecision[];
  warnings: string[];
  sql_description: string;
  lineage_id?: string | null;
}

export interface CalculationRequest {
  metric_code: string;
  operation?: string;
  subsidiary?: string | null;
  mine?: string | null;
  reporting_period?: string | null;
  only_verified?: boolean;
  only_real?: boolean;
  only_demo?: boolean;
  exclude_consolidated?: boolean;
  document_ids?: string[] | null;
}

export interface LineageResponse {
  id: string;
  operation: string;
  metric_code: string;
  filters: Record<string, any>;
  result?: number | null;
  unit?: string | null;
  formula?: string | null;
  calculation_method?: string | null;
  sql_description?: string | null;
  success: boolean;
  error_code?: string | null;
  evidence_count: number;
  evidence_used_count: number;
  verified_count: number;
  excluded_count: number;
  verified_pct?: number | null;
  is_demo_scope?: string | null;
  warnings: string[];
  initiated_by?: string | null;
  created_at?: string | null;
  included_facts: Record<string, any>[];
  excluded_facts: Record<string, any>[];
}

// ─────────────────────────────────────────────────────────────────────────────
// Batch Upload & Pipeline Monitoring Types
// ─────────────────────────────────────────────────────────────────────────────

export interface BatchUploadItemResult {
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  document_id?: string | null;
  is_duplicate: boolean;
  duplicate_of_id?: string | null;
  duplicate_of_filename?: string | null;
  detected_organization?: string | null;
  detected_period?: string | null;
  facts_extracted: number;
  warnings: string[];
  error?: string | null;
}

export interface BatchUploadResponse {
  total_files: number;
  successful: number;
  duplicates: number;
  failed: number;
  items: BatchUploadItemResult[];
}

export interface ProcessingStatusResponse {
  document_id: string;
  status: string;
  processing_progress: number;
  processing_message?: string | null;
  current_stage?: string | null;
  fact_count: number;
  warning_count: number;
  warnings: string[];
  processing_error?: string | null;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
}

export interface ExtractionSummaryResponse {
  document_id: string;
  original_filename: string;
  file_type: string;
  document_category?: string | null;
  organization: string;
  reporting_period?: string | null;
  quality_label?: string | null;
  quality_score?: number | null;
  page_count: number;
  sheet_count: number;
  table_count: number;
  total_facts: number;
  high_confidence_facts: number;
  needs_review_facts: number;
  conflicts_count: number;
  warning_count: number;
  warnings: string[];
  is_demo: boolean;
  duration_seconds?: number | null;
}

export interface SourcePreviewPage {
  page_number: number;
  raw_text?: string | null;
  has_native_text: boolean;
  is_ocr_page: boolean;
  ocr_confidence?: number | null;
  extraction_method?: string | null;
}

export interface SourcePreviewSheet {
  sheet_name: string;
  used_range?: string | null;
  headers: string[];
  rows: any[][];
  row_count: number;
  col_count: number;
}

export interface SourcePreviewResponse {
  document_id: string;
  original_filename: string;
  file_type: string;
  pages: SourcePreviewPage[];
  sheets: SourcePreviewSheet[];
  text_preview?: string | null;
}

export type DataScope = 'ALL' | 'REAL' | 'DEMO';

// ─────────────────────────────────────────────────────────────────────────────
// Phase 9 — MineGraph Types
// ─────────────────────────────────────────────────────────────────────────────

export type MineGraphNodeType =
  | 'CIL'
  | 'SUBSIDIARY'
  | 'COALFIELD'
  | 'MINE'
  | 'METRIC'
  | 'DOCUMENT'
  | 'FACT';

export interface MineGraphNode {
  id: string;
  label: string;
  type: MineGraphNodeType;
  color: string;
  size: number;
  level?: number;
  fact_count?: number;
  subsidiary?: string;
  coalfield?: string;
  mine?: string;
  metric_code?: string;
  document_id?: string;
  file_type?: string;
  description?: string;
  value?: number;
  unit?: string;
  period?: string;
  confidence?: number;
  page_number?: number;
  sheet_name?: string;
  cell_reference?: string;
  source_context?: string;
}

export interface MineGraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
  conflict?: boolean;
}

export interface MineGraphStats {
  node_count: number;
  edge_count: number;
  subsidiaries: number;
  coalfields: number;
  mines: number;
  total_facts_in_db: number;
  total_documents: number;
}

export interface MineGraphResponse {
  nodes: MineGraphNode[];
  edges: MineGraphEdge[];
  stats: MineGraphStats;
}

export interface SubsidiaryGraphSummary {
  subsidiary: string;
  coalfields: string[];
  fact_count: number;
  mine_count: number;
  top_metrics: Array<{ metric_code: string; count: number }>;
}

export interface MineGraphSubsidiariesResponse {
  subsidiaries: SubsidiaryGraphSummary[];
  total: number;
}

export interface MineGraphPathNode {
  level: number;
  type: string;
  label: string;
  id: string;
  value?: number;
  unit?: string;
  period?: string;
  confidence?: number;
  page_number?: number;
  sheet_name?: string;
  cell_reference?: string;
  source_context?: string;
  document_id?: string;
  file_type?: string;
}

export interface MineGraphPathResponse {
  fact_id: string;
  path: MineGraphPathNode[];
  path_length: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Phase 10 — Parliamentary Brief Types
// ─────────────────────────────────────────────────────────────────────────────

export interface ParliamentaryBriefRequest {
  query: string;
  period: string;
  subsidiary: string;
}

export interface ParliamentaryBriefResponse {
  query: string;
  period: string;
  subsidiary: string;
  brief_text: string;
  answer_markdown: string;
  status: string;
  records_used: number;
  confidence: number;
  citations: EvidenceSourceCitation[];
  direct_metric_value?: number | null;
  metric_unit?: string | null;
  calculation?: any;
  verification_status?: string;
  verification_result?: string;
  chart?: any;
  suggestions?: string[];
  calculation_steps?: string[];
  sql_query?: string;
  mode?: string;
}


export interface ParliamentarySampleQuestion {
  id: string;
  question: string;
  period: string;
  subsidiary: string;
  category: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: 'Analyst' | 'Reviewer' | 'Admin' | string;
  username: string;
  full_name: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: 'Analyst' | 'Reviewer' | 'Admin' | string;
  organization: string;
  is_demo: boolean;
}

