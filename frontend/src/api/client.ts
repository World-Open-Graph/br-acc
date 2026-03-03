const API_BASE = import.meta.env.VITE_API_URL ?? "";
const STORAGE_KEY = "bracc_auth";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getAuthHeaders(): Record<string, string> {
  try {
    const token = localStorage.getItem(STORAGE_KEY);
    if (token) return { Authorization: `Bearer ${token}` };
  } catch {
    // localStorage unavailable
  }
  return {};
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export interface SourceAttribution {
  database: string;
  record_id?: string | null;
  extracted_at?: string | null;
}

export interface SearchResult {
  id: string;
  name: string;
  type: string;
  document?: string | null;
  sources: SourceAttribution[];
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  page: number;
  size: number;
}

export interface EntityDetail {
  id: string;
  type: string;
  properties: Record<string, string | number | boolean | null>;
  sources: SourceAttribution[];
  is_pep: boolean;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  document_id?: string | null;
  properties: Record<string, unknown>;
  sources: SourceAttribution[];
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
  confidence: number;
  sources: SourceAttribution[];
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export function searchEntities(
  query: string,
  type?: string,
  page = 1,
  size = 20,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, page: String(page), size: String(size) });
  if (type && type !== "all") {
    params.set("type", type);
  }
  return apiFetch<SearchResponse>(`/api/v1/search?${params}`);
}

export function getEntity(id: string): Promise<EntityDetail> {
  return apiFetch<EntityDetail>(`/api/v1/entity/${encodeURIComponent(id)}`);
}

export function getEntityByElementId(elementId: string): Promise<EntityDetail> {
  return apiFetch<EntityDetail>(`/api/v1/entity/by-element-id/${encodeURIComponent(elementId)}`);
}

export interface PatternInfo {
  id: string;
  name_pt: string;
  name_en: string;
  description_pt: string;
  description_en: string;
}

export interface PatternListResponse {
  patterns: PatternInfo[];
}

export interface PatternResult {
  pattern_id: string;
  pattern_name: string;
  description: string;
  data: Record<string, unknown>;
  entity_ids: string[];
  sources: { database: string }[];
  intelligence_tier?: "community" | "full";
}

export interface PatternResponse {
  entity_id: string | null;
  patterns: PatternResult[];
  total: number;
}

export function listPatterns(): Promise<PatternListResponse> {
  return apiFetch<PatternListResponse>("/api/v1/patterns/");
}

export function getEntityPatterns(
  entityId: string,
  lang = "pt",
): Promise<PatternResponse> {
  const params = new URLSearchParams({ lang });
  return apiFetch<PatternResponse>(
    `/api/v1/patterns/${encodeURIComponent(entityId)}?${params}`,
  );
}

export function getGraphData(
  entityId: string,
  depth = 1,
  types?: string[],
  signal?: AbortSignal,
): Promise<GraphData> {
  const params = new URLSearchParams({ depth: String(depth) });
  if (types?.length) {
    params.set("entity_types", types.join(","));
  }
  return apiFetch<GraphData>(`/api/v1/graph/${encodeURIComponent(entityId)}?${params}`, { signal });
}

// --- Baseline ---

export interface BaselineMetrics {
  company_name: string;
  company_cnpj: string;
  company_id: string;
  contract_count: number;
  total_value: number;
  peer_count: number;
  peer_avg_contracts: number;
  peer_avg_value: number;
  contract_ratio: number;
  value_ratio: number;
  comparison_dimension: string;
  comparison_key: string;
  sources: { database: string; retrieved_at: string; url: string }[];
}

export interface BaselineResponse {
  entity_id: string;
  comparisons: BaselineMetrics[];
  total: number;
}

export function getBaseline(entityId: string): Promise<BaselineResponse> {
  return apiFetch<BaselineResponse>(`/api/v1/baseline/${encodeURIComponent(entityId)}`);
}

// --- Investigations ---

export interface Investigation {
  id: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  entity_ids: string[];
  share_token: string | null;
}

export interface InvestigationListResponse {
  investigations: Investigation[];
  total: number;
}

export interface Annotation {
  id: string;
  entity_id: string;
  investigation_id: string;
  text: string;
  created_at: string;
}

export interface Tag {
  id: string;
  investigation_id: string;
  name: string;
  color: string;
}

export function listInvestigations(
  page = 1,
  size = 20,
): Promise<InvestigationListResponse> {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  return apiFetch<InvestigationListResponse>(`/api/v1/investigations/?${params}`);
}

export function getInvestigation(id: string): Promise<Investigation> {
  return apiFetch<Investigation>(`/api/v1/investigations/${encodeURIComponent(id)}`);
}

export function createInvestigation(
  title: string,
  description?: string,
): Promise<Investigation> {
  return apiFetch<Investigation>("/api/v1/investigations/", {
    method: "POST",
    body: JSON.stringify({ title, description: description ?? "" }),
  });
}

export function updateInvestigation(
  id: string,
  data: { title?: string; description?: string },
): Promise<Investigation> {
  return apiFetch<Investigation>(
    `/api/v1/investigations/${encodeURIComponent(id)}`,
    { method: "PATCH", body: JSON.stringify(data) },
  );
}

export function deleteInvestigation(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/investigations/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

export function addEntityToInvestigation(
  investigationId: string,
  entityId: string,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/entities/${encodeURIComponent(entityId)}`,
    { method: "POST" },
  );
}

export function listAnnotations(investigationId: string): Promise<Annotation[]> {
  return apiFetch<Annotation[]>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/annotations`,
  );
}

export function createAnnotation(
  investigationId: string,
  entityId: string,
  text: string,
): Promise<Annotation> {
  return apiFetch<Annotation>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/annotations`,
    { method: "POST", body: JSON.stringify({ entity_id: entityId, text }) },
  );
}

export function listTags(investigationId: string): Promise<Tag[]> {
  return apiFetch<Tag[]>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/tags`,
  );
}

export function createTag(
  investigationId: string,
  name: string,
  color?: string,
): Promise<Tag> {
  return apiFetch<Tag>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/tags`,
    { method: "POST", body: JSON.stringify({ name, color: color ?? "#e07a2f" }) },
  );
}

export function removeEntityFromInvestigation(
  investigationId: string,
  entityId: string,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/entities/${encodeURIComponent(entityId)}`,
    { method: "DELETE" },
  );
}

export function deleteAnnotation(
  investigationId: string,
  annotationId: string,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/annotations/${encodeURIComponent(annotationId)}`,
    { method: "DELETE" },
  );
}

export function deleteTag(
  investigationId: string,
  tagId: string,
): Promise<void> {
  return apiFetch<void>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/tags/${encodeURIComponent(tagId)}`,
    { method: "DELETE" },
  );
}

export function getSharedInvestigation(token: string): Promise<Investigation> {
  return apiFetch<Investigation>(`/api/v1/shared/${encodeURIComponent(token)}`);
}

export function generateShareLink(
  investigationId: string,
): Promise<{ share_token: string }> {
  return apiFetch<{ share_token: string }>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/share`,
    { method: "POST" },
  );
}

export function exportInvestigation(investigationId: string): Promise<Blob> {
  const url = `${API_BASE}/api/v1/investigations/${encodeURIComponent(investigationId)}/export`;
  return fetch(url, { headers: getAuthHeaders() }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, `API error: ${res.statusText}`);
    return res.blob();
  });
}

// --- Chat ---

export interface ChatEntityCard {
  id: string;
  type: string;
  name: string;
  properties: Record<string, unknown>;
  connections: number;
  sources: string[];
}

export interface EvidenceItem {
  tool: string;
  source: string;
  query: string;
  result_count: number;
  timestamp: string;
  api_url: string;
}

export interface ChatResponse {
  reply: string;
  entities: ChatEntityCard[];
  suggestions: string[];
  evidence_chain: EvidenceItem[];
  cost_usd: number;
}

export function sendChatMessage(
  message: string,
  conversationId?: string,
): Promise<ChatResponse> {
  const clientId = getOrCreateClientId();
  return apiFetch<ChatResponse>("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify({ message, conversation_id: conversationId ?? "" }),
    headers: { "x-client-id": clientId },
  });
}

// --- Client Identity (anonymous, localStorage-based) ---

const CLIENT_ID_KEY = "egos_client_id";

export function getOrCreateClientId(): string {
  try {
    let id = localStorage.getItem(CLIENT_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(CLIENT_ID_KEY, id);
    }
    return id;
  } catch {
    return "anon";
  }
}

// --- Conversations ---

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  messages: { role: string; content: string }[];
}

function convHeaders(): Record<string, string> {
  return { "x-client-id": getOrCreateClientId() };
}

export function listConversations(): Promise<{ conversations: ConversationSummary[]; client_id: string }> {
  return apiFetch("/api/v1/conversations", { headers: convHeaders() });
}

export function createConversation(title?: string): Promise<ConversationDetail> {
  return apiFetch("/api/v1/conversations", {
    method: "POST",
    body: JSON.stringify({ title: title ?? "Nova pesquisa" }),
    headers: convHeaders(),
  });
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return apiFetch(`/api/v1/conversations/${encodeURIComponent(id)}`, { headers: convHeaders() });
}

export function deleteConversation(id: string): Promise<{ status: string }> {
  return apiFetch(`/api/v1/conversations/${encodeURIComponent(id)}`, {
    method: "DELETE",
    headers: convHeaders(),
  });
}

// --- Stats ---

export interface StatsResponse {
  total_nodes: number;
  total_relationships: number;
  person_count: number;
  company_count: number;
  health_count: number;
  finance_count: number;
  contract_count: number;
  sanction_count: number;
  election_count: number;
  amendment_count: number;
  embargo_count: number;
  education_count: number;
  convenio_count: number;
  laborstats_count: number;
  data_sources: number;
}

export function getStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>("/api/v1/meta/stats");
}

// --- Exposure & Timeline ---

export interface ExposureFactor {
  name: string;
  value: number;
  percentile: number;
  weight: number;
  sources: string[];
}

export interface ExposureResponse {
  entity_id: string;
  exposure_index: number;
  factors: ExposureFactor[];
  peer_group: string;
  peer_count: number;
  sources: SourceAttribution[];
  intelligence_tier?: "community" | "full";
}

export interface TimelineEvent {
  id: string;
  date: string;
  label: string;
  entity_type: string;
  properties: Record<string, unknown>;
  sources: SourceAttribution[];
}

export interface TimelineResponse {
  entity_id: string;
  events: TimelineEvent[];
  total: number;
  next_cursor: string | null;
}

export interface HealthResponse {
  status: string;
}

export function getEntityExposure(entityId: string): Promise<ExposureResponse> {
  return apiFetch<ExposureResponse>(`/api/v1/entity/${encodeURIComponent(entityId)}/exposure`);
}

export function getEntityTimeline(
  entityId: string,
  cursor?: string,
  limit = 50,
): Promise<TimelineResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<TimelineResponse>(`/api/v1/entity/${encodeURIComponent(entityId)}/timeline?${params}`);
}

export function getHealthStatus(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/meta/health");
}

export function exportInvestigationPDF(
  investigationId: string,
  lang = "pt",
): Promise<Blob> {
  const params = new URLSearchParams({ lang });
  const url = `${API_BASE}/api/v1/investigations/${encodeURIComponent(investigationId)}/export/pdf?${params}`;
  return fetch(url, { headers: getAuthHeaders() }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, `API error: ${res.statusText}`);
    return res.blob();
  });
}
