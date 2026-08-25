const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HealthStatus = { status: string };
export type Dataset = { id: string; original_filename: string; row_count: number; column_count: number; quality_score: number; profile?: Record<string, unknown> };

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/api/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Health request failed (${response.status})`);
  return response.json() as Promise<HealthStatus>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export const datasetsApi = {
  list: () => request<Dataset[]>("/api/datasets"),
  upload: (file: File) => { const body = new FormData(); body.append("file", file); return request<Dataset>("/api/datasets", { method: "POST", body }); },
  details: (id: string) => request<Dataset>(`/api/datasets/${id}`),
  preview: (id: string) => request<{ columns: string[]; rows: Record<string, unknown>[] }>(`/api/datasets/${id}/preview`),
  analytics: (id: string, body: Record<string, unknown>) => request<{ kpi: number; breakdown: Record<string, unknown>[]; trend: Record<string, unknown>[] }>(`/api/datasets/${id}/analytics`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
};
export type Decision = { id:string; question:string; decision_type:string; recommendation:string|null; reliability_status:"RECOMMEND"|"REVIEW"|"ABSTAIN"|"UNCALIBRATED"; ecds:number|null; review_required:boolean; abstention_reason:string|null; reliability_details:Record<string,unknown>; provenance_root_id:string|null; created_at:string };
export type Evidence = { id:string; evidence_type:string; source_type:string; source_id:string|null; payload:Record<string,unknown>; uncertainty:Record<string,unknown>; metadata_json:Record<string,unknown> };
export type InvestigatorResponse = { question:string; intent:string; status:string; ecds:number|null; review_required:boolean; answer:string; evidence:Array<{id:string;type:string;payload:Record<string,unknown>}>; provenance:Array<{id:string;type:string}>; decision_id?:string };
export const decisionsApi={list:()=>request<Decision[]>("/api/decisions"),detail:(id:string)=>request<Decision>(`/api/decisions/${id}`),evidence:(id:string)=>request<Evidence[]>(`/api/decisions/${id}/evidence`),provenance:(id:string)=>request<{root:Record<string,unknown>;edges:Array<Record<string,unknown>>}>(`/api/decisions/${id}/provenance`),investigate:(question:string,evidence_ids:string[]=[])=>request<InvestigatorResponse>("/api/investigator",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question,evidence_ids})})};
