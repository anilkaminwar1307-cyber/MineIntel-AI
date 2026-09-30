import axios from 'axios';
import {
  HealthInfo,
  Capabilities,
  DocumentItem,
  DocumentListResponse,
  DocumentPageItem,
  DocumentSheetItem,
  DocumentTableItem,
  DocumentChunkItem,
  DocumentQualityItem,
  ProcessingLogItem,
  ExtractedFact,
  FactSourceProvenance,
  ExtractedFactListResponse,
  AuditEventListResponse,
  AnalyticsOverview,
  AnalyticsExtended,
  ReviewQueueResponse,
  ConflictListResponse,
  QueryResponse,
  GeneratedReportItem,
  GeneratedReportListResponse,
  ReportGuardResult,
  TopicListResponse,
  TopicDetailResponse,
  SystemSettingsStatus,
  CalculationResult,
  CalculationRequest,
  LineageResponse,
  BatchUploadResponse,
  ProcessingStatusResponse,
  ExtractionSummaryResponse,
  SourcePreviewResponse,
  MineGraphResponse,
  MineGraphSubsidiariesResponse,
  MineGraphPathResponse,
  ParliamentaryBriefResponse,
  ParliamentarySampleQuestion,
  DocumentValidationsResponse,
  TokenResponse,
  UserProfile,
} from '../types';

const TOKEN_KEY = 'mineintel_token';
const USER_KEY = 'mineintel_user';

export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setStoredToken = (token: string): void => {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {}
};

export const clearStoredToken = (): void => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {}
};

export const getStoredUser = (): UserProfile | null => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const setStoredUser = (user: UserProfile): void => {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {}
};

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 45000,
  headers: {
    'Accept': 'application/json',
  }
});

// Request interceptor: attach Bearer token if present
apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearStoredToken();
      window.dispatchEvent(new CustomEvent('mineintel:unauthorized'));
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Health & System
  getHealth: async (): Promise<HealthInfo> => {
    const { data } = await apiClient.get<HealthInfo>('/health');
    return data;
  },

  getCapabilities: async (): Promise<Capabilities> => {
    const { data } = await apiClient.get<Capabilities>('/system/capabilities');
    return data;
  },

  getSystemSettings: async (): Promise<SystemSettingsStatus> => {
    const { data } = await apiClient.get<SystemSettingsStatus>('/settings');
    return data;
  },

  // Documents
  getDocuments: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    status_filter?: string;
    category?: string;
    organization?: string;
  }): Promise<DocumentListResponse> => {
    const { data } = await apiClient.get<DocumentListResponse>('/documents', { params });
    return data;
  },

  getDocument: async (id: string): Promise<DocumentItem> => {
    const { data } = await apiClient.get<DocumentItem>(`/documents/${id}`);
    return data;
  },

  uploadDocument: async (
    file: File,
    category: string = 'General Mining Report',
    period?: string,
    organization: string = 'CMPDI / CIL',
    autoProcess: boolean = true
  ): Promise<{ message: string; document: DocumentItem; is_duplicate: boolean; existing_document?: DocumentItem | null }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_category', category);
    if (period) formData.append('reporting_period', period);
    formData.append('organization', organization);
    formData.append('auto_process', String(autoProcess));

    const { data } = await apiClient.post<{ message: string; document: DocumentItem; is_duplicate: boolean; existing_document?: DocumentItem | null }>(
      '/documents/upload',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );
    return data;
  },

  batchUploadDocuments: async (
    files: File[],
    category: string = 'General Mining Report',
    period?: string,
    organization: string = 'CMPDI / CIL',
    autoProcess: boolean = true
  ): Promise<BatchUploadResponse> => {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    formData.append('document_category', category);
    if (period) formData.append('reporting_period', period);
    formData.append('organization', organization);
    formData.append('auto_process', String(autoProcess));

    const { data } = await apiClient.post<BatchUploadResponse>(
      '/documents/batch-upload',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000, // 2 minutes for batch
      }
    );
    return data;
  },

  deleteDocument: async (id: string): Promise<{ message: string; id: string }> => {
    const { data } = await apiClient.delete<{ message: string; id: string }>(`/documents/${id}`);
    return data;
  },

  processDocument: async (id: string): Promise<DocumentItem> => {
    const { data } = await apiClient.post<DocumentItem>(`/documents/${id}/process`);
    return data;
  },

  reprocessDocument: async (id: string): Promise<DocumentItem> => {
    const { data } = await apiClient.post<DocumentItem>(`/documents/${id}/reprocess`);
    return data;
  },

  getDocumentPages: async (id: string): Promise<DocumentPageItem[]> => {
    const { data } = await apiClient.get<DocumentPageItem[]>(`/documents/${id}/pages`);
    return data;
  },

  getDocumentSheets: async (id: string): Promise<DocumentSheetItem[]> => {
    const { data } = await apiClient.get<DocumentSheetItem[]>(`/documents/${id}/sheets`);
    return data;
  },

  getDocumentTables: async (id: string): Promise<DocumentTableItem[]> => {
    const { data } = await apiClient.get<DocumentTableItem[]>(`/documents/${id}/tables`);
    return data;
  },

  getDocumentChunks: async (id: string): Promise<DocumentChunkItem[]> => {
    const { data } = await apiClient.get<DocumentChunkItem[]>(`/documents/${id}/chunks`);
    return data;
  },

  getDocumentFacts: async (id: string): Promise<ExtractedFact[]> => {
    const { data } = await apiClient.get<ExtractedFact[]>(`/documents/${id}/facts`);
    return data;
  },

  getDocumentQuality: async (id: string): Promise<DocumentQualityItem | null> => {
    const { data } = await apiClient.get<DocumentQualityItem | null>(`/documents/${id}/quality`);
    return data;
  },

  getDocumentProcessingLog: async (id: string): Promise<ProcessingLogItem[]> => {
    const { data } = await apiClient.get<ProcessingLogItem[]>(`/documents/${id}/processing-log`);
    return data;
  },

  getDocumentProcessingStatus: async (id: string): Promise<ProcessingStatusResponse> => {
    const { data } = await apiClient.get<ProcessingStatusResponse>(`/documents/${id}/status`);
    return data;
  },

  getDocumentExtractionSummary: async (id: string): Promise<ExtractionSummaryResponse> => {
    const { data } = await apiClient.get<ExtractionSummaryResponse>(`/documents/${id}/extraction-summary`);
    return data;
  },

  getDocumentSourcePreview: async (id: string): Promise<SourcePreviewResponse> => {
    const { data } = await apiClient.get<SourcePreviewResponse>(`/documents/${id}/source-preview`);
    return data;
  },

  updateDocumentMetadata: async (
    id: string,
    payload: { document_category?: string; organization?: string; reporting_period?: string }
  ): Promise<DocumentItem> => {
    const { data } = await apiClient.patch<DocumentItem>(`/documents/${id}/metadata`, payload);
    return data;
  },

  // Evidence Ledger
  getEvidence: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    metric?: string;
    period?: string;
    organization?: string;
    subsidiary?: string;
    document_id?: string;
    status_filter?: string;
    min_confidence?: number;
  }): Promise<ExtractedFactListResponse> => {
    const { data } = await apiClient.get<ExtractedFactListResponse>('/evidence', { params });
    return data;
  },

  getFactSource: async (factId: string): Promise<FactSourceProvenance> => {
    const { data } = await apiClient.get<FactSourceProvenance>(`/evidence/${factId}/source`);
    return data;
  },

  // Analytics
  getAnalyticsOverview: async (params?: {
    subsidiary?: string;
    financial_year?: string;
    metric?: string;
  }): Promise<AnalyticsOverview> => {
    const { data } = await apiClient.get<AnalyticsOverview>('/analytics/overview', { params });
    return data;
  },

  getAnalyticsExtended: async (params?: {
    subsidiary?: string;
    financial_year?: string;
  }): Promise<AnalyticsExtended> => {
    const { data } = await apiClient.get<AnalyticsExtended>('/analytics/extended', { params });
    return data;
  },

  // Reports
  getReports: async (): Promise<GeneratedReportListResponse> => {
    const { data } = await apiClient.get<GeneratedReportListResponse>('/reports');
    return data;
  },

  getReport: async (id: string): Promise<GeneratedReportItem> => {
    const { data } = await apiClient.get<GeneratedReportItem>(`/reports/${id}`);
    return data;
  },

  checkReportGuard: async (payload: {
    report_type: string;
    subsidiary?: string;
    period?: string;
  }): Promise<ReportGuardResult> => {
    const { data } = await apiClient.post<ReportGuardResult>('/reports/reportguard', payload);
    return data;
  },

  generateReport: async (payload: {
    title: string;
    report_type: string;
    subsidiary?: string;
    period?: string;
  }): Promise<GeneratedReportItem> => {
    const { data } = await apiClient.post<GeneratedReportItem>('/reports/generate', payload);
    return data;
  },

  deleteReport: async (id: string): Promise<{ message: string }> => {
    const { data } = await apiClient.delete<{ message: string }>(`/reports/${id}`);
    return data;
  },

  getReportPdfUrl: (id: string): string => {
    return `/api/reports/${id}/pdf`;
  },

  getReportCsvUrl: (id: string): string => {
    return `/api/reports/${id}/export-csv`;
  },

  // Audit
  getAuditEvents: async (params?: {
    page?: number;
    page_size?: number;
    action?: string;
    entity_type?: string;
  }): Promise<AuditEventListResponse> => {
    const { data } = await apiClient.get<AuditEventListResponse>('/audit', { params });
    return data;
  },

  // Reviews
  getReviewQueue: async (params?: {
    status?: string;
    severity?: string;
    issue_type?: string;
    page?: number;
    page_size?: number;
  }): Promise<ReviewQueueResponse> => {
    const { data } = await apiClient.get<ReviewQueueResponse>('/reviews', { params });
    return data;
  },

  approveReview: async (issueId: string): Promise<{ message: string; issue_id: string; fact_id?: string }> => {
    const { data } = await apiClient.post(`/reviews/${issueId}/approve`);
    return data;
  },

  rejectReview: async (issueId: string): Promise<{ message: string; issue_id: string }> => {
    const { data } = await apiClient.post(`/reviews/${issueId}/reject`);
    return data;
  },

  editReview: async (
    issueId: string,
    payload: { corrected_value: number; notes?: string }
  ): Promise<{ message: string; issue_id: string; fact_id?: string; new_value?: number }> => {
    const { data } = await apiClient.post(`/reviews/${issueId}/edit-and-approve`, payload);
    return data;
  },

  getConflicts: async (): Promise<ConflictListResponse> => {
    const { data } = await apiClient.get<ConflictListResponse>('/reviews/conflicts');
    return data;
  },

  resolveConflict: async (
    conflictId: string,
    payload: { chosen_fact_id: string; resolution_notes: string }
  ): Promise<{ message: string }> => {
    const { data } = await apiClient.post(`/reviews/conflicts/${conflictId}/resolve`, payload);
    return data;
  },

  verifyFact: async (factId: string): Promise<{ message: string; fact_id: string }> => {
    const { data } = await apiClient.post(`/reviews/facts/${factId}/verify`);
    return data;
  },

  // Topics
  getTopics: async (params?: { category?: string }): Promise<TopicListResponse> => {
    const { data } = await apiClient.get<TopicListResponse>('/topics', { params });
    return data;
  },

  getTopicDetail: async (topicId: string): Promise<TopicDetailResponse> => {
    const { data } = await apiClient.get<TopicDetailResponse>(`/topics/${topicId}`);
    return data;
  },

  // ── Data Quality API ─────────────────────────────────────────────────────────

  /** List data quality issues with filtering */
  getDataQualityIssues: async (params?: {
    page?: number;
    page_size?: number;
    severity?: string;
    status?: string;
    issue_type?: string;
    subsidiary?: string;
    document_id?: string;
    is_resolved?: boolean;
    q?: string;
  }): Promise<{ total: number; page: number; page_size: number; items: any[] }> => {
    const { data } = await apiClient.get('/data-quality/issues', { params });
    return data;
  },

  /** Get data quality stats summary */
  getDataQualityStats: async (): Promise<any> => {
    const { data } = await apiClient.get('/data-quality/stats');
    return data;
  },

  /** Resolve a data quality issue */
  resolveDataQualityIssue: async (
    issueId: string,
    payload: { resolution_notes?: string }
  ): Promise<any> => {
    const { data } = await apiClient.post(`/data-quality/issues/${issueId}/resolve`, payload);
    return data;
  },

  /** Assign a data quality issue to a reviewer */
  assignDataQualityIssue: async (
    issueId: string,
    payload: { assigned_to: string }
  ): Promise<any> => {
    const { data } = await apiClient.post(`/data-quality/issues/${issueId}/assign`, payload);
    return data;
  },

  /** List evidence conflicts */
  getDataQualityConflicts: async (params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<any> => {
    const { data } = await apiClient.get('/data-quality/conflicts', { params });
    return data;
  },

  // Query
  submitQuery: async (payload: {
    query: string;
    scope?: string;
    response_mode?: string;
  }): Promise<QueryResponse> => {
    const { data } = await apiClient.post<QueryResponse>('/query', payload);
    return data;
  },

  // ── NumberSafe 2.0 Calculation API ───────────────────────────────────────────

  /** Run a fully audited NumberSafe calculation */
  runCalculation: async (payload: CalculationRequest): Promise<CalculationResult> => {
    const { data } = await apiClient.post<CalculationResult>('/calculations/calculate', payload);
    return data;
  },

  /** Retrieve a persisted CalculationRun by lineage_id */
  getCalculation: async (calcId: string): Promise<LineageResponse> => {
    const { data } = await apiClient.get<LineageResponse>(`/calculations/${calcId}`);
    return data;
  },

  /** Full lineage detail for a calculation run including all inputs */
  getCalculationLineage: async (calcId: string): Promise<LineageResponse> => {
    const { data } = await apiClient.get<LineageResponse>(`/calculations/${calcId}/lineage`);
    return data;
  },

  /** Calculate achievement: actual vs target for a metric */
  calculateAchievement: async (payload: {
    metric_code: string;
    target_metric_code?: string;
    subsidiary?: string;
    reporting_period?: string;
  }): Promise<{ actual: CalculationResult; target: CalculationResult; achievement_pct: number | null }> => {
    const { data } = await apiClient.post('/calculations/achievement', payload);
    return data;
  },

  /** Run reconciliation checks across evidence */
  reconcileCalculations: async (params?: {
    metric_code?: string;
    subsidiary?: string;
    reporting_period?: string;
  }): Promise<{ issues: any[]; total: number }> => {
    const { data } = await apiClient.get('/calculations/reconcile', { params });
    return data;
  },

  // ── Phase 9: MineGraph API ────────────────────────────────────────────────

  /** Get MineGraph nodes + edges for visualization */
  getMineGraph: async (params?: {
    subsidiary?: string;
    metric_code?: string;
    include_documents?: boolean;
    include_metrics?: boolean;
    max_mines?: number;
  }): Promise<MineGraphResponse> => {
    const { data } = await apiClient.get<MineGraphResponse>('/minegraph/graph', { params });
    return data;
  },

  /** Get per-subsidiary summary data for MineGraph panel */
  getMineGraphSubsidiaries: async (): Promise<MineGraphSubsidiariesResponse> => {
    const { data } = await apiClient.get<MineGraphSubsidiariesResponse>('/minegraph/subsidiaries');
    return data;
  },

  /** Trace full CIL→Subsidiary→Coalfield→Mine→Metric→Fact→Document path for a fact */
  getMineGraphPath: async (factId: string): Promise<MineGraphPathResponse> => {
    const { data } = await apiClient.get<MineGraphPathResponse>('/minegraph/paths', {
      params: { fact_id: factId },
    });
    return data;
  },

  // ── Phase 10: Parliamentary Brief API ────────────────────────────────────

  /** Generate a parliamentary-style question brief from grounded evidence */
  generateParliamentaryBrief: async (payload: {
    query: string;
    period?: string;
    subsidiary?: string;
  }): Promise<ParliamentaryBriefResponse> => {
    const { data } = await apiClient.post<ParliamentaryBriefResponse>(
      '/parliamentary/brief',
      null,
      {
        params: {
          query: payload.query,
          period: payload.period || 'ALL',
          subsidiary: payload.subsidiary || 'ALL',
        },
      }
    );
    return data;
  },

  /** Get sample parliamentary questions for demo mode */
  getParliamentarySampleQuestions: async (): Promise<{ questions: ParliamentarySampleQuestion[] }> => {
    const { data } = await apiClient.get<{ questions: ParliamentarySampleQuestion[] }>(
      '/parliamentary/sample-questions'
    );
    return data;
  },

  // ── Authentication API ──────────────────────────────────────────────────

  /** Authenticate with username and password, return JWT Bearer token */
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const { data } = await apiClient.post<TokenResponse>('/auth/token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    setStoredToken(data.access_token);
    setStoredUser({
      id: '',
      username: data.username,
      email: '',
      full_name: data.full_name,
      role: data.role,
      organization: 'CMPDI / CIL',
      is_demo: false,
    });
    return data;
  },

  /** Get profile of current authenticated user */
  getMe: async (): Promise<UserProfile> => {
    const { data } = await apiClient.get<UserProfile>('/auth/me');
    setStoredUser(data);
    return data;
  },

  /** Log out and clear saved session */
  logout: (): void => {
    clearStoredToken();
  },
};


