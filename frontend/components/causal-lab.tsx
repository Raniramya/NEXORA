"use client";

import { FormEvent, useEffect, useState } from "react";
import { Machine, maintenanceApi, MaintenanceCausalStudy, MaintenanceCounterfactual, MaintenanceExperiment } from "../services/api";

export function CausalLab() {
  const [machines, setMachines] = useState<Machine[]>([]), [machineId, setMachineId] = useState("");
  const [experiments, setExperiments] = useState<MaintenanceExperiment[]>([]), [studies, setStudies] = useState<MaintenanceCausalStudy[]>([]);
  const [applied, setApplied] = useState(true), [preOutcome, setPreOutcome] = useState(""), [postOutcome, setPostOutcome] = useState(""), [load, setLoad] = useState("");
  const [currentOutcome, setCurrentOutcome] = useState(""), [scenario, setScenario] = useState<MaintenanceCounterfactual>();
  const [error, setError] = useState(""), [busy, setBusy] = useState(false);

  useEffect(() => { Promise.all([maintenanceApi.machines(), maintenanceApi.maintenanceExperiments(), maintenanceApi.causalStudies()]).then(([assets, records, studyItems]) => { setMachines(assets); setMachineId(assets[0]?.id ?? ""); setExperiments(records); setStudies(studyItems); }).catch(() => setError("Maintenance causal services are unavailable.")); }, []);

  async function recordExperiment(event: FormEvent) {
    event.preventDefault();
    const before = Number(preOutcome), after = Number(postOutcome), measuredLoad = Number(load);
    if (!machineId || [preOutcome, postOutcome, load].some((value) => value.trim() === "") || ![before, after, measuredLoad].every(Number.isFinite)) { setError("Enter finite pre, post, and load measurements."); return; }
    setBusy(true); setError("");
    try {
      await maintenanceApi.recordMaintenanceExperiment(machineId, { intervention: "correct_imbalance", treatment_applied: applied, outcome_metric: "vibration_rms", pre_outcome: before, post_outcome: after, covariates: { load: measuredLoad }, confirmed: true, source_window_ids: [], recorded_at: new Date().toISOString() });
      setExperiments(await maintenanceApi.maintenanceExperiments()); setPreOutcome(""); setPostOutcome(""); setLoad("");
    } catch { setError("The physical experiment could not be recorded."); }
    finally { setBusy(false); }
  }

  async function runStudy() {
    setBusy(true); setError(""); setScenario(undefined);
    try { const study = await maintenanceApi.runMaintenanceCausalStudy({ intervention: "correct_imbalance", outcome_metric: "vibration_rms", confounders: ["load"], dag_edges: [["load", "treatment_applied"], ["load", "outcome_change"], ["treatment_applied", "outcome_change"]], minimum_samples: 20 }); setStudies((current) => [study, ...current]); }
    catch { setError("The causal study could not be evaluated."); }
    finally { setBusy(false); }
  }

  async function runCounterfactual() {
    const study = studies.find((item) => item.intervention === "correct_imbalance"), observed = Number(currentOutcome);
    if (!study || !machineId || !Number.isFinite(observed)) { setError("Choose a completed study and enter the current observed RMS."); return; }
    setBusy(true); setError("");
    try { setScenario(await maintenanceApi.counterfactual(study.id, { machine_id: machineId, current_outcome: observed, apply_intervention: true, feasible: true, lower_is_better: true })); }
    catch { setError("The counterfactual could not be evaluated."); }
    finally { setBusy(false); }
  }

  const latestStudy = studies[0];
  const confirmedRecords = experiments.filter((item) => item.confirmed && item.intervention === "correct_imbalance" && item.outcome_metric === "vibration_rms").length;
  return <div className="space-y-7">
    <section className="page-hero"><p className="eyebrow">CAUSAL MAINTENANCE</p><h1>Estimate what an intervention may change.</h1><p>Record controlled pre/post experiments, declare the causal graph and adjustment set, then evaluate feasible interventions. Prediction and SHAP evidence are not treated as causal effects.</p></section>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <section className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">PHYSICAL EXPERIMENT</p><h2 className="panel-title mt-2">Correct imbalance vs control</h2><p className="panel-copy">Record observed vibration RMS before and after each confirmed trial. Controls retain the candidate intervention but do not apply it.</p><form className="mt-5 grid grid-cols-2 gap-3" onSubmit={recordExperiment}><label className="col-span-2 text-xs font-bold uppercase text-slate-600">Machine<select className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={machineId} onChange={(event) => setMachineId(event.target.value)}>{machines.map((machine) => <option value={machine.id} key={machine.id}>{machine.name}</option>)}</select></label><label className="text-xs font-bold uppercase text-slate-600">Pre RMS<input type="number" step="any" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={preOutcome} onChange={(event) => setPreOutcome(event.target.value)} /></label><label className="text-xs font-bold uppercase text-slate-600">Post RMS<input type="number" step="any" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={postOutcome} onChange={(event) => setPostOutcome(event.target.value)} /></label><label className="text-xs font-bold uppercase text-slate-600">Measured load<input type="number" step="any" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={load} onChange={(event) => setLoad(event.target.value)} /></label><label className="flex items-end gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold"><input type="checkbox" checked={applied} onChange={(event) => setApplied(event.target.checked)} />Intervention applied</label><button className="primary-button col-span-2" disabled={busy || !machineId}>{busy ? "Saving..." : "Record confirmed experiment"}</button></form></article>
      <article className="panel"><p className="eyebrow !text-teal-700">IDENTIFICATION GATE</p><h2 className="panel-title mt-2">Backdoor-adjusted effect study</h2><p className="panel-copy">DAG: load → treatment, load → outcome change, treatment → outcome change. Adjustment set: load.</p><div className="mt-5 grid grid-cols-2 gap-3"><div className="rounded-lg bg-slate-50 p-4"><p className="text-xs font-bold uppercase text-slate-500">Confirmed records</p><p className="mt-1 text-2xl font-extrabold">{confirmedRecords}</p></div><div className="rounded-lg bg-slate-50 p-4"><p className="text-xs font-bold uppercase text-slate-500">Required minimum</p><p className="mt-1 text-2xl font-extrabold">20</p></div></div><button type="button" className="primary-button mt-5 w-full" disabled={busy} onClick={() => void runStudy()}>{busy ? "Evaluating..." : "Run causal identification"}</button>{latestStudy && <div className={`mt-5 rounded-lg p-4 ${latestStudy.status === "abstained" ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-900"}`}><p className="text-xs font-bold uppercase">{latestStudy.status.replaceAll("_", " ")}</p>{latestStudy.estimated_effect == null ? <p className="mt-2 text-sm">No effect reported: {String(latestStudy.result.abstention_reason ?? "identification failed").replaceAll("_", " ")}.</p> : <><p className="mt-2 text-2xl font-extrabold">{latestStudy.estimated_effect.toFixed(4)} RMS change</p><p className="mt-1 text-sm">95% interval {JSON.stringify(latestStudy.result.confidence_interval)}</p></>}</div>}</article>
    </section>
    <section className="panel"><p className="eyebrow !text-teal-700">FEASIBLE COUNTERFACTUAL</p><h2 className="panel-title mt-2">Apply the identified intervention</h2><p className="panel-copy">This produces a model-based estimate only when the study passed identification. It never replaces the actual post-maintenance measurement.</p><div className="mt-4 flex flex-wrap gap-3"><input type="number" step="any" className="min-w-56 flex-1 rounded-lg border border-slate-300 px-3 py-2" placeholder="Current observed vibration RMS" value={currentOutcome} onChange={(event) => setCurrentOutcome(event.target.value)} /><button type="button" className="primary-button" disabled={busy || !latestStudy} onClick={() => void runCounterfactual()}>Estimate counterfactual</button></div>{scenario && <div className={`mt-5 rounded-lg p-4 ${scenario.status === "abstained" ? "bg-amber-50 text-amber-900" : "bg-teal-50 text-teal-900"}`}><p className="text-xs font-bold uppercase">{scenario.status.replaceAll("_", " ")}</p><p className="mt-2 text-lg font-extrabold">{scenario.result.estimated_outcome == null ? `No estimate: ${String(scenario.result.abstention_reason).replaceAll("_", " ")}` : `Estimated outcome ${Number(scenario.result.estimated_outcome).toFixed(4)}`}</p><p className="mt-2 text-sm">{String(scenario.result.warning ?? "Evidence gate prevented this counterfactual.")}</p></div>}</section>
  </div>;
}
