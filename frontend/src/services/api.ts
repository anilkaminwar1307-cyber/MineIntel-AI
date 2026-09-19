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
  SystemSettingsStatus
} from '../types';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 45000,
  headers: {
    'Accept': 'application/json',
  }
});

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
  ): Promise<{ message: string; document: DocumentItem }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_category', category);
    if (period) formData.append('reporting_period', period);
    formData.append('organization', organization);
    formData.append('auto_process', String(autoProcess));

    const { data } = await apiClient.post<{ message: string; document: DocumentItem }>(
      '/documents/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
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

  // Query
  submitQuery: async (payload: {
    query: string;
    scope?: string;
    response_mode?: string;
  }): Promise<QueryResponse> => {
    const { data } = await apiClient.post<QueryResponse>('/query', payload);
    return data;
  }
};
