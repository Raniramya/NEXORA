"use client";

import { FormEvent, useEffect, useState } from "react";
import { MaintenanceOptimizationRun, MaintenancePlan, maintenanceApi, OptimizationEvidence } from "../services/api";

type OperationalInput = { cost: string; downtime: string; duration: string };

export function MaintenancePlanner() {
  const [evidence, setEvidence] = useState<OptimizationEvidence>();
  const [inputs, setInputs] = useState<Record<string, OperationalInput>>({});
  const [budget, setBudget] = useState("10000"), [downtime, setDowntime] = useState("24"), [hours, setHours] = useState("16"), [maxActions, setMaxActions] = useState("5");
  const [run, setRun] = useState<MaintenanceOptimizationRun>(), [plan, setPlan] = useState<MaintenancePlan>();
  const [busy, setBusy] = useState(false), [error, setError] = useState("");

  useEffect(() => { maintenanceApi.optimizationEvidence().then(setEvidence).catch(() => setError("Optimization evidence could not be loaded.")); }, []);
  const eligible = evidence?.candidates.filter((candidate) => candidate.eligible) ?? [];

  function updateInput(machineId: string, field: keyof OperationalInput, value: string) {
    setInputs((current) => {
      const existing = current[machineId] ?? { cost: "", downtime: "", duration: "" };
      return { ...current, [machineId]: { ...existing, [field]: value } };
    });
  }

  async function optimize(event: FormEvent) {
    event.preventDefault(); setError(""); setPlan(undefined);
    if (!evidence?.distance_analysis_run_id) { setError("Create a Haversine distance run in Geo Intelligence first."); return; }
    const candidates = eligible.map((candidate) => ({ candidate, values: inputs[candidate.machine_id] })).filter(({ values }) => values && [values.cost, values.downtime, values.duration].every((value) => value.trim() !== "" && Number.isFinite(Number(value))));
    if (!candidates.length) { setError("Enter cost, downtime, and duration for at least one eligible asset."); return; }
    setBusy(true);
    try {
      setRun(await maintenanceApi.optimizeMaintenance({
        distance_analysis_run_id: evidence.distance_analysis_run_id,
        candidates: candidates.map(({ candidate, values }) => ({ candidate_id: `${candidate.machine_id}:${candidate.action_type}`, machine_id: candidate.machine_id, selective_prediction_id: candidate.selective_prediction_id, counterfactual_id: candidate.counterfactual_id, action_type: candidate.action_type, cost: Number(values.cost), downtime_hours: Number(values.downtime), duration_hours: Number(values.duration) })),
        budget: Number(budget), max_downtime_hours: Number(downtime), technician_hours: Number(hours), max_actions: Number(maxActions), population_size: 80, generations: 100, random_seed: 42,
      }));
    } catch { setError("Optimization failed. Verify positive constraints and complete operational inputs."); }
    finally { setBusy(false); }
  }

  async function selectPlan(index: number) {
    if (!run) return; setBusy(true); setError("");
    try { setPlan(await maintenanceApi.selectMaintenancePlan(run.id, index)); }
    catch { setError("This Pareto option could not be preserved for review."); }
    finally { setBusy(false); }
  }

  const solutions = run?.results.pareto_solutions ?? [];
  return <div className="space-y-7">
    <section className="page-hero"><p className="eyebrow">MULTI-OBJECTIVE OPTIMIZATION</p><h1>Balance risk, benefit, cost, downtime, and travel.</h1><p>Binary NSGA-II generates feasible Pareto options from calibrated ACT evidence, identified causal benefit, and computed distance. Every option requires human review and cannot authorize maintenance.</p></section>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <section className="grid gap-5 lg:grid-cols-[1.2fr_.8fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">EVIDENCE GATE</p><h2 className="panel-title mt-2">Candidate interventions</h2><div className="mt-5 space-y-3">{evidence?.candidates.map((candidate) => <div key={candidate.machine_id} className={`rounded-lg border p-4 ${candidate.eligible ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/50"}`}><div className="flex flex-wrap items-center justify-between gap-2"><strong>{candidate.machine_name}</strong><span className="text-xs font-bold uppercase">{candidate.eligible ? "Eligible" : "Evidence incomplete"}</span></div>{candidate.eligible ? <><p className="mt-2 text-xs text-slate-600">Risk {candidate.calibrated_fault_risk?.toFixed(3)} · causal benefit {candidate.causal_benefit} · distance {candidate.distance_km?.toFixed(2)} km</p><div className="mt-3 grid grid-cols-3 gap-2">{([['cost', 'Cost'], ['downtime', 'Downtime h'], ['duration', 'Tech h']] as const).map(([field, label]) => <label key={field} className="text-[10px] font-bold uppercase text-slate-600">{label}<input type="number" min="0" step="any" className="mt-1 w-full rounded border border-slate-300 bg-white px-2 py-1.5 font-normal" value={inputs[candidate.machine_id]?.[field] ?? ""} onChange={(event) => updateInput(candidate.machine_id, field, event.target.value)} /></label>)}</div></> : <p className="mt-2 text-xs text-amber-900">Missing: {candidate.missing_evidence.join(", ")}</p>}</div>)}{evidence && evidence.candidates.length === 0 && <p className="text-sm text-slate-500">No registered machines are available.</p>}</div></article>
      <article className="panel"><p className="eyebrow !text-teal-700">CONSTRAINTS</p><h2 className="panel-title mt-2">Available resources</h2><form className="mt-5 space-y-3" onSubmit={optimize}>{[["Budget", budget, setBudget], ["Maximum downtime hours", downtime, setDowntime], ["Technician hours", hours, setHours], ["Maximum actions", maxActions, setMaxActions]].map(([label, value, setter]) => <label key={String(label)} className="block text-xs font-bold uppercase text-slate-600">{String(label)}<input type="number" min="1" step="any" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={String(value)} onChange={(event) => (setter as (value: string) => void)(event.target.value)} /></label>)}<button className="primary-button w-full" disabled={busy}>{busy ? "Optimizing..." : "Generate Pareto schedules"}</button></form></article>
    </section>
    {run && <section className="panel"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow !text-teal-700">PARETO FRONT</p><h2 className="panel-title mt-2">{run.status === "completed" ? `${solutions.length} non-dominated options` : "Optimization abstained"}</h2></div><span className="font-mono text-xs text-slate-500">Run {run.id.slice(0, 8)}</span></div>{run.status === "abstained" ? <p className="mt-4 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">{run.results.abstention_reason?.replaceAll("_", " ")}</p> : <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-800 text-xs uppercase text-white"><tr><th className="p-3">Assets</th><th className="p-3">Residual risk</th><th className="p-3">Cost</th><th className="p-3">Downtime</th><th className="p-3">Travel</th><th className="p-3">Benefit</th><th className="p-3">Review</th></tr></thead><tbody>{solutions.map((solution, index) => <tr key={solution.selected_candidate_ids.join("|") || "none"} className="border-b border-slate-100"><td className="p-3">{solution.selected_machine_ids.length ? solution.selected_machine_ids.map((id) => evidence?.candidates.find((item) => item.machine_id === id)?.machine_name ?? id).join(", ") : "No action"}</td><td className="p-3">{solution.objectives.residual_risk.toFixed(3)}</td><td className="p-3">{solution.objectives.cost.toFixed(2)}</td><td className="p-3">{solution.objectives.downtime_hours.toFixed(2)} h</td><td className="p-3">{solution.objectives.travel_km.toFixed(2)} km</td><td className="p-3">{(-solution.objectives.negative_causal_benefit).toFixed(3)}</td><td className="p-3"><button type="button" className="primary-button" disabled={busy} onClick={() => void selectPlan(index)}>Select</button></td></tr>)}</tbody></table></div>}<p className="mt-4 text-xs text-slate-500">Baselines computed in the same run: greedy risk/cost and conventional risk priority. They remain comparison artifacts, not chosen recommendations.</p></section>}
    {plan && <section className="rounded-xl border border-blue-200 bg-blue-50 p-5"><p className="text-xs font-bold uppercase text-blue-700">REVIEW REQUIRED</p><h2 className="mt-1 text-lg font-extrabold text-blue-950">Plan {plan.id.slice(0, 8)} preserved for Phase 9 review</h2><p className="mt-2 text-sm text-blue-900">This record preserves the selected Pareto option and its evidence chain. No maintenance action was created or authorized.</p></section>}
  </div>;
}
