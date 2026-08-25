const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type HealthStatus = { status: string };
export type Dataset = { id: string; original_filename: string; row_count: number; column_count: number; quality_score: number; profile?: Record<string, unknown> };
export type Machine = { id: string; name: string; asset_type: string; status: string; latitude: number | null; longitude: number | null; metadata_json: Record<string, unknown>; created_at: string };
export type SensorReading = { id: string; machine_id: string; recorded_at: string; vibration_rms: number | null; temperature: number | null; current: number | null; rpm: number | null; features: Record<string, unknown> };
export type SignalWindow = { id: string; machine_id: string; recorded_at: string; sample_rate_hz: number; channel: string; unit: string; samples: number[]; source: string; device_id: string | null; metadata_json: Record<string, unknown>; created_at: string; feature_set: { id: string; signal_window_id: string; extractor_version: string; features: Record<string, number>; configuration: Record<string, unknown>; created_at: string } };
export type SignalFaultLabel = { id: string; signal_window_id: string; fault_class: string; label_source: string; confirmed: boolean; notes: string | null; created_at: string };
export type FaultModelRun = { id: string; machine_id: string | null; status: string; configuration: Record<string, unknown>; results: { models?: Record<string, Record<string, unknown>>; unavailable_models?: Record<string, string>; train_size?: number; test_size?: number; validation_size?: number; calibration_size?: number }; feature_names: string[]; class_names: string[]; winning_model: string | null; artifact_location: string | null; created_at: string };
export type FaultPrediction = { id: string; model_run_id: string; signal_window_id: string; predicted_class: string; confidence: number | null; probabilities: Record<string, number>; reliability_status: string; created_at: string };
export type FaultExplanation = { id: string; prediction_id: string; method: string; explained_class: string; base_value: number; output_value: number; contributions: Record<string, number>; feature_values: Record<string, number>; configuration: Record<string, unknown>; created_at: string };
export type AnomalyModelRun = { id: string; machine_id: string | null; status: string; configuration: Record<string, unknown>; results: Record<string, unknown>; feature_names: string[]; artifact_location: string | null; created_at: string };
export type AnomalyScore = { id: string; anomaly_model_run_id: string; signal_window_id: string; decision_score: number; is_anomaly: boolean; interpretation: string; created_at: string };
export type MaintenanceExperiment = { id: string; machine_id: string; intervention: string; treatment_applied: boolean; outcome_metric: string; pre_outcome: number; post_outcome: number; covariates: Record<string, number>; confirmed: boolean; source_window_ids: string[]; recorded_at: string; created_at: string };
export type MaintenanceCausalStudy = { id: string; intervention: string; outcome_metric: string; status: string; configuration: Record<string, unknown>; result: Record<string, unknown>; estimated_effect: number | null; created_at: string };
export type MaintenanceCounterfactual = { id: string; causal_study_id: string; machine_id: string; configuration: Record<string, unknown>; result: Record<string, unknown>; status: string; created_at: string };
export type FaultReliabilityRun = { id: string; fault_model_run_id: string; status: string; configuration: Record<string, unknown>; results: Record<string, unknown>; artifact_location: string | null; created_at: string };
export type SelectivePrediction = { id: string; reliability_run_id: string; fault_prediction_id: string; anomaly_score_id: string | null; action: "ACT" | "MONITOR" | "ABSTAIN"; calibrated_probabilities: Record<string, number>; prediction_set: string[]; details: Record<string, unknown>; created_at: string };
export type GeoAsset = { machine_id: string; machine_name: string; status: string; latitude: number; longitude: number; fault_event_count: number; latest_fault_type: string | null };
export type GeospatialAnalysisRun = { id: string; analysis_type: "haversine_distances" | "dbscan_fault_hotspots"; configuration: Record<string, unknown>; result: Record<string, unknown>; created_at: string };
export type OptimizationEvidenceCandidate = { machine_id: string; machine_name: string; eligible: boolean; missing_evidence: string[]; selective_prediction_id: string | null; counterfactual_id: string | null; action_type: string | null; calibrated_fault_risk: number | null; causal_benefit: number | null; distance_km: number | null };
export type OptimizationEvidence = { distance_analysis_run_id: string | null; candidates: OptimizationEvidenceCandidate[] };
export type MaintenanceOptimizationRun = { id: string; status: "completed" | "abstained"; configuration: Record<string, unknown>; results: { pareto_solutions?: OptimizationSolution[]; baselines?: Record<string, OptimizationSolution>; excluded_candidates?: Array<{ candidate_id: string; reasons: string[] }>; warning?: string; abstention_reason?: string }; provenance: Record<string, unknown>; created_at: string };
export type OptimizationSolution = { selected_candidate_ids: string[]; selected_machine_ids: string[]; objectives: { residual_risk: number; cost: number; downtime_hours: number; travel_km: number; negative_causal_benefit: number }; resource_usage: { action_count: number; technician_hours: number } };
export type MaintenancePlan = { id: string; optimization_run_id: string; solution_index: number; status: "review_required"; solution: OptimizationSolution; provenance: Record<string, unknown>; created_at: string };
export type MaintenanceAction = { id:string; machine_id:string; action_type:string; status:string; scheduled_at:string|null; completed_at:string|null; predicted_benefit:number|null; observed_benefit:number|null; notes:string|null };
export type PhysicalValidationTrial = { id:string; maintenance_action_id:string; pre_reading_id:string; post_reading_id:string; outcome_metric:string; predicted_benefit:number; observed_benefit:number; absolute_error:number; result:Record<string, unknown>; confirmed:boolean; created_at:string };
export type BenchmarkObservation = { id:string; benchmark_name:string; case_id:string; system_variant:string; recommendation_made:boolean; predicted_action:string|null; ground_truth_action:string; observed_harm:boolean; uncertainty_handled:boolean; provenance_references:string[]; evidence_source:string; metadata_json:Record<string,unknown>; created_at:string };
export type ResearchEvaluationRun = { id:string; evaluation_type:string; status:"completed"|"abstained"; configuration:Record<string,unknown>; results:Record<string,unknown>; provenance:Record<string,unknown>; artifact_location:string|null; artifact_sha256:string|null; created_at:string };

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
export const maintenanceApi = {
  machines: () => request<Machine[]>("/api/machines"),
  createMachine: (body: { name: string; asset_type?: string; latitude?: number; longitude?: number }) => request<Machine>("/api/machines", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  readings: (machineId: string) => request<SensorReading[]>(`/api/machines/${machineId}/readings`),
  actions: (machineId: string) => request<MaintenanceAction[]>(`/api/machines/${machineId}/maintenance-actions`),
  recordReading: (machineId: string, body: Omit<SensorReading, "id" | "machine_id" | "features">) => request<SensorReading>(`/api/machines/${machineId}/readings`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  signalWindows: (machineId: string) => request<SignalWindow[]>(`/api/machines/${machineId}/signal-windows`),
  recordSignalWindow: (machineId: string, body: { recorded_at: string; sample_rate_hz: number; channel: string; unit: string; samples: number[]; source: string; device_id?: string }) => request<SignalWindow>(`/api/machines/${machineId}/signal-windows`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  labels: (machineId: string) => request<SignalFaultLabel[]>(`/api/machines/${machineId}/signal-labels`),
  labelWindow: (windowId: string, faultClass: string) => request<SignalFaultLabel>(`/api/signal-windows/${windowId}/label`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fault_class: faultClass, label_source: "controlled_experiment", confirmed: true }) }),
  faultModelRuns: () => request<FaultModelRun[]>("/api/fault-model-runs"),
  trainFaultModel: (machineId: string) => request<FaultModelRun>("/api/fault-model-runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ machine_id: machineId, random_seed: 42, confirmed_labels_only: true }) }),
  predictFault: (runId: string, windowId: string) => request<FaultPrediction>(`/api/fault-model-runs/${runId}/predictions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ signal_window_id: windowId }) }),
  explainFault: (predictionId: string) => request<FaultExplanation>(`/api/fault-predictions/${predictionId}/explanation`, { method: "POST" }),
  anomalyModelRuns: () => request<AnomalyModelRun[]>("/api/anomaly-model-runs"),
  trainAnomalyModel: (machineId: string) => request<AnomalyModelRun>("/api/anomaly-model-runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ machine_id: machineId, random_seed: 42, contamination: 0.05 }) }),
  scoreAnomaly: (runId: string, windowId: string) => request<AnomalyScore>(`/api/anomaly-model-runs/${runId}/scores`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ signal_window_id: windowId }) }),
  maintenanceExperiments: () => request<MaintenanceExperiment[]>("/api/maintenance-experiments"),
  recordMaintenanceExperiment: (machineId: string, body: Omit<MaintenanceExperiment, "id" | "machine_id" | "created_at">) => request<MaintenanceExperiment>(`/api/machines/${machineId}/maintenance-experiments`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  causalStudies: () => request<MaintenanceCausalStudy[]>("/api/maintenance-causal-studies"),
  runMaintenanceCausalStudy: (body: { intervention: string; outcome_metric: string; confounders: string[]; dag_edges: string[][]; minimum_samples: number }) => request<MaintenanceCausalStudy>("/api/maintenance-causal-studies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  counterfactual: (studyId: string, body: { machine_id: string; current_outcome: number; apply_intervention: boolean; feasible: boolean; lower_is_better: boolean }) => request<MaintenanceCounterfactual>(`/api/maintenance-causal-studies/${studyId}/counterfactuals`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  reliabilityRuns: () => request<FaultReliabilityRun[]>("/api/fault-reliability-runs"),
  calibrateFaultModel: (faultModelRunId: string) => request<FaultReliabilityRun>("/api/fault-reliability-runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fault_model_run_id: faultModelRunId, alpha: 0.1, minimum_calibration_size: 20 }) }),
  evaluateReliability: (runId: string, predictionId: string, anomalyScoreId?: string) => request<SelectivePrediction>(`/api/fault-reliability-runs/${runId}/evaluations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ fault_prediction_id: predictionId, anomaly_score_id: anomalyScoreId ?? null, act_threshold: 0.8, monitor_threshold: 0.5 }) }),
  geoAssets: () => request<GeoAsset[]>("/api/geo/assets"),
  geoDistances: (originLatitude: number, originLongitude: number) => request<GeospatialAnalysisRun>("/api/geo/distances", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin_latitude: originLatitude, origin_longitude: originLongitude }) }),
  geoHotspots: (epsilonKm: number, minimumAssets: number, lookbackDays: number) => request<GeospatialAnalysisRun>("/api/geo/hotspots", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ epsilon_km: epsilonKm, minimum_assets: minimumAssets, lookback_days: lookbackDays }) }),
  optimizationEvidence: () => request<OptimizationEvidence>("/api/maintenance-optimization/evidence"),
  optimizationRuns: () => request<MaintenanceOptimizationRun[]>("/api/maintenance-optimization-runs"),
  optimizeMaintenance: (body: Record<string, unknown>) => request<MaintenanceOptimizationRun>("/api/maintenance-optimization-runs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  selectMaintenancePlan: (runId: string, solutionIndex: number) => request<MaintenancePlan>(`/api/maintenance-optimization-runs/${runId}/plans`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ solution_index: solutionIndex }) }),
  maintenancePlans: () => request<MaintenancePlan[]>("/api/maintenance-plans"),
  physicalTrials: () => request<PhysicalValidationTrial[]>("/api/research/physical-trials"),
  recordPhysicalTrial: (body:Record<string,unknown>) => request<PhysicalValidationTrial>("/api/research/physical-trials", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) }),
  benchmarkObservations: (name?:string) => request<BenchmarkObservation[]>(`/api/research/benchmark-observations${name ? `?benchmark_name=${encodeURIComponent(name)}` : ""}`),
  recordBenchmarkObservation: (body:Record<string,unknown>) => request<BenchmarkObservation>("/api/research/benchmark-observations", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) }),
  evaluatePhysicalTrials: (trialIds:string[], minimumTrials:number) => request<ResearchEvaluationRun>("/api/research/evaluations/physical", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({trial_ids:trialIds,minimum_trials:minimumTrials}) }),
  evaluateBenchmark: (benchmarkName:string, minimumAlignedCases:number) => request<ResearchEvaluationRun>("/api/research/evaluations/benchmark", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({benchmark_name:benchmarkName,minimum_aligned_cases:minimumAlignedCases}) }),
  researchEvaluations: () => request<ResearchEvaluationRun[]>("/api/research/evaluations"),
};
export type Decision = { id:string; question:string; decision_type:string; recommendation:string|null; reliability_status:"RECOMMEND"|"REVIEW"|"ABSTAIN"|"UNCALIBRATED"; ecds:number|null; review_required:boolean; abstention_reason:string|null; reliability_details:Record<string,unknown>; provenance_root_id:string|null; created_at:string };
export type Evidence = { id:string; evidence_type:string; source_type:string; source_id:string|null; payload:Record<string,unknown>; uncertainty:Record<string,unknown>; metadata_json:Record<string,unknown> };
export type DecisionEvidenceGraph = { nodes: Array<{ key:string; resource_type:string; resource_id:string }>; edges: Array<{ source:string; target:string; relation:string }>; missing_links:string[] };
export type DecisionReview = { id:string; decision_id:string; reviewer:string; outcome:"approved"|"rejected"; notes:string|null; created_action_ids:string[]; created_at:string };
export type InvestigatorResponse = { question:string; intent:string; status:string; ecds:number|null; review_required:boolean; answer:string; evidence:Array<{id:string;type:string;payload:Record<string,unknown>}>; provenance:Array<{id:string;type:string}>; decision_id?:string };
export const decisionsApi={list:()=>request<Decision[]>("/api/decisions"),detail:(id:string)=>request<Decision>(`/api/decisions/${id}`),evidence:(id:string)=>request<Evidence[]>(`/api/decisions/${id}/evidence`),provenance:(id:string)=>request<{root:Record<string,unknown>;edges:Array<Record<string,unknown>>}>(`/api/decisions/${id}/provenance`),graph:(id:string)=>request<DecisionEvidenceGraph>(`/api/decisions/${id}/evidence-graph`),createIntegrated:(maintenancePlanId:string,question:string)=>request<Decision>("/api/decisions/integrated-maintenance",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({maintenance_plan_id:maintenancePlanId,question})}),reviews:(id:string)=>request<DecisionReview[]>(`/api/decisions/${id}/reviews`),review:(id:string,body:{reviewer:string;outcome:"approved"|"rejected";notes?:string})=>request<DecisionReview>(`/api/decisions/${id}/reviews`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),investigate:(question:string,evidence_ids:string[]=[],decisionId?:string)=>request<InvestigatorResponse>("/api/investigator",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question,evidence_ids,decision_id:decisionId??null})})};
