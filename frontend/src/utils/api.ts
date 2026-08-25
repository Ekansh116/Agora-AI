const API_BASE = (import.meta.env.VITE_API_BASE_URL as string || "http://localhost:8000/api").replace(/\/$/, "");

export interface Source {
  id: number;
  name: string;
  source_type: string;
  status: string;
  message_count: number;
  uploaded_at: string;
}

export interface DashboardData {
  total_members: number;
  total_messages: number;
  most_active_member: string;
  most_active_day: string;
  top_senders: { sender: string; count: number }[];
  message_volume: { date: string; count: number }[];
  active_hours: { hour: number; count: number }[];
}

export interface EvidenceCitation {
  timestamp: string;
  sender: string;
  content: string;
}

export interface ChatResponse {
  observation: string;
  inference: string;
  recommendation: string;
  evidence: EvidenceCitation[];
  confidence: string;
  confidence_reason: string;
}

export interface ReportResponse {
  executive_summary: string;
  most_discussed_topics: string[];
  community_mood: string;
  active_contributors: string[];
  engagement_highlights: string[];
  interesting_trends: string[];
  ai_recommendations: string[];
  confidence: string;
  confidence_reason: string;
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  async getSources(): Promise<Source[]> {
    const res = await fetch(`${API_BASE}/sources/`);
    if (!res.ok) throw new Error("Failed to fetch sources list");
    return res.json();
  },

  async uploadSource(file: File, sourceType: string = "whatsapp"): Promise<Source> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source_type", sourceType);

    const res = await fetch(`${API_BASE}/sources/upload`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "File upload failed");
    }
    return res.json();
  },

  async deleteSource(sourceId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/sources/${sourceId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to delete source");
    }
  },

  async getDashboard(sourceId?: number | null): Promise<DashboardData> {
    const url = sourceId 
      ? `${API_BASE}/insights/dashboard?source_id=${sourceId}` 
      : `${API_BASE}/insights/dashboard`;
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error("Failed to load dashboard statistics");
    }
    return res.json();
  },

  async getCommunityReport(sourceId?: number | null): Promise<ReportResponse> {
    const res = await fetch(`${API_BASE}/insights/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_id: sourceId || null }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to generate community report");
    }
    return res.json();
  },

  async queryChat(query: string, sourceId?: number | null): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/chat/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, source_id: sourceId || null }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to get AI query response");
    }
    return res.json();
  },

  async getExplorerMessages(params: {
    sourceId?: number | null;
    relativeRange?: string;
    startDate?: string;
    endDate?: string;
    sender?: string;
    keyword?: string;
    hasMedia?: boolean | null;
    limit?: number;
    offset?: number;
  }): Promise<ExplorerResponse> {
    const queryParts: string[] = [];
    if (params.sourceId !== undefined && params.sourceId !== null) queryParts.push(`source_id=${params.sourceId}`);
    if (params.relativeRange) queryParts.push(`relative_range=${params.relativeRange}`);
    if (params.startDate) queryParts.push(`start_date=${encodeURIComponent(params.startDate)}`);
    if (params.endDate) queryParts.push(`end_date=${encodeURIComponent(params.endDate)}`);
    if (params.sender) queryParts.push(`sender=${encodeURIComponent(params.sender)}`);
    if (params.keyword) queryParts.push(`keyword=${encodeURIComponent(params.keyword)}`);
    if (params.hasMedia !== undefined && params.hasMedia !== null) queryParts.push(`has_media=${params.hasMedia}`);
    if (params.limit !== undefined) queryParts.push(`limit=${params.limit}`);
    if (params.offset !== undefined) queryParts.push(`offset=${params.offset}`);

    const queryString = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";
    const res = await fetch(`${API_BASE}/explorer/messages${queryString}`);
    if (!res.ok) throw new Error("Failed to fetch explorer conversation messages");
    return res.json();
  },

  getExplorerExportUrl(params: {
    sourceId?: number | null;
    relativeRange?: string;
    startDate?: string;
    endDate?: string;
    sender?: string;
    keyword?: string;
    hasMedia?: boolean | null;
    exportFormat: string;
  }): string {
    const queryParts: string[] = [];
    if (params.sourceId !== undefined && params.sourceId !== null) queryParts.push(`source_id=${params.sourceId}`);
    if (params.relativeRange) queryParts.push(`relative_range=${params.relativeRange}`);
    if (params.startDate) queryParts.push(`start_date=${encodeURIComponent(params.startDate)}`);
    if (params.endDate) queryParts.push(`end_date=${encodeURIComponent(params.endDate)}`);
    if (params.sender) queryParts.push(`sender=${encodeURIComponent(params.sender)}`);
    if (params.keyword) queryParts.push(`keyword=${encodeURIComponent(params.keyword)}`);
    if (params.hasMedia !== undefined && params.hasMedia !== null) queryParts.push(`has_media=${params.hasMedia}`);
    queryParts.push(`export_format=${params.exportFormat}`);

    return `${API_BASE}/explorer/export?${queryParts.join("&")}`;
  }
};

export interface MessageExplorerItem {
  id: number;
  timestamp: string;
  sender: string;
  content: string;
}

export interface ExplorerStats {
  total_messages: number;
  unique_members: number;
  most_active_sender: string;
  most_discussed_hour: number | null;
  avg_messages_per_hour: number;
}

export interface ExplorerResponse {
  messages: MessageExplorerItem[];
  total_count: number;
  stats: ExplorerStats;
}
