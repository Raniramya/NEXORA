"use client";

import { FormEvent, useEffect, useState } from "react";
import { Decision, DecisionEvidenceGraph, DecisionReview, decisionsApi, Evidence, MaintenancePlan, maintenanceApi } from "../services/api";

export function DecisionsWorkspace() {
  const [decisions, setDecisions] = useState<Decision[]>([]), [plans, setPlans] = useState<MaintenancePlan[]>([]);
  const [selected, setSelected] = useState<Decision>(), [evidence, setEvidence] = useState<Evidence[]>([]), [graph, setGraph] = useState<DecisionEvidenceGraph>(), [reviews, setReviews] = useState<DecisionReview[]>([]);
  const [planId, setPlanId] = useState(""), [question, setQuestion] = useState("Should the selected evidence-backed maintenance plan proceed?");
  const [reviewer, setReviewer] = useState(""), [notes, setNotes] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false);

  async function refresh() {
    const [decisionItems, planItems] = await Promise.all([decisionsApi.list(), maintenanceApi.maintenancePlans()]);
    setDecisions(decisionItems); setPlans(planItems); setPlanId((current) => current || planItems[0]?.id || "");
  }
  useEffect(() => { refresh().catch(() => setError("The integrated decision service is unavailable.")); }, []);

  async function open(decision: Decision) {
    setError("");
    try {
      const detail = await decisionsApi.detail(decision.id);
      const [records, reviewItems] = await Promise.all([decisionsApi.evidence(decision.id), decisionsApi.reviews(decision.id)]);
      let evidenceGraph: DecisionEvidenceGraph | undefined;
      try { evidenceGraph = await decisionsApi.graph(decision.id); } catch { evidenceGraph = undefined; }
      setSelected(detail); setEvidence(records); setReviews(reviewItems); setGraph(evidenceGraph);
    } catch { setError("Decision evidence could not be loaded."); }
  }

  async function createDecision(event: FormEvent) {
    event.preventDefault(); if (!planId || !question.trim()) return; setBusy(true); setError("");
    try { const decision = await decisionsApi.createIntegrated(planId, question.trim()); await refresh(); await open(decision); }
    catch { setError("The plan may already have a decision, or its provenance is unavailable."); }
    finally { setBusy(false); }
  }

  async function review(outcome: "approved" | "rejected") {
    if (!selected || !reviewer.trim()) { setError("Enter the name of the accountable reviewer."); return; }
    setBusy(true); setError("");
    try { await decisionsApi.review(selected.id, { reviewer: reviewer.trim(), outcome, notes: notes.trim() || undefined }); await refresh(); await open(await decisionsApi.detail(selected.id)); }
    catch { setError("Only an evidence-complete, unreviewed decision can be approved or rejected."); }
    finally { setBusy(false); }
  }

  return <div className="space-y-7">
    <section className="page-hero"><p className="eyebrow">INTEGRATED DECISION WORKFLOW</p><h1>Review the complete evidence chain before action.</h1><p>Recommendations are generated mechanically from selected maintenance plans. Missing predictive, explanatory, reliability, causal, spatial, or optimization evidence forces abstention.</p></section>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <section className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">PLAN INTAKE</p><h2 className="panel-title mt-2">Create integrated decision</h2><form className="mt-5 space-y-3" onSubmit={createDecision}><label className="block text-xs font-bold uppercase text-slate-600">Review-required plan<select className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={planId} onChange={(event) => setPlanId(event.target.value)}><option value="">Select a plan</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.id.slice(0, 8)} · {plan.solution.selected_machine_ids.length} assets</option>)}</select></label><label className="block text-xs font-bold uppercase text-slate-600">Decision question<textarea rows={3} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" value={question} onChange={(event) => setQuestion(event.target.value)} /></label><button className="primary-button w-full" disabled={busy || !planId}>{busy ? "Checking evidence..." : "Build evidence graph"}</button></form></article>
      <article className="panel"><p className="eyebrow !text-teal-700">DECISION REGISTER</p><h2 className="panel-title mt-2">Recorded outcomes</h2><div className="mt-5 space-y-2">{decisions.map((decision) => <button type="button" onClick={() => void open(decision)} className={`flex w-full items-center justify-between gap-3 rounded-lg border p-3 text-left ${selected?.id === decision.id ? "border-teal-400 bg-teal-50" : "border-slate-200"}`} key={decision.id}><span><strong className="block">{decision.question}</strong><span className="text-xs text-slate-500">{new Date(decision.created_at).toLocaleString()}</span></span><span className="rounded bg-slate-800 px-2 py-1 text-xs font-bold text-white">{decision.reliability_status}</span></button>)}{!decisions.length && <p className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-500">No integrated decision has been created.</p>}</div></article>
    </section>
    {selected && <><section className="grid gap-5 lg:grid-cols-[1.1fr_.9fr]"><article className="panel"><p className="eyebrow !text-teal-700">READINESS RESULT</p><h2 className="panel-title mt-2">{selected.reliability_status}</h2>{selected.recommendation ? <p className="mt-4 text-lg font-bold text-slate-800">{selected.recommendation}</p> : <p className="mt-4 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">Recommendation withheld: {selected.abstention_reason}</p>}<dl className="mt-5 grid grid-cols-2 gap-3">{Object.entries((selected.reliability_details.selected_solution_objectives ?? {}) as Record<string, number>).map(([name, value]) => <div className="rounded-lg bg-slate-50 p-3" key={name}><dt className="text-xs font-bold uppercase text-slate-500">{name.replaceAll("_", " ")}</dt><dd className="mt-1 font-extrabold">{Number(value).toFixed(3)}</dd></div>)}</dl></article><article className="panel"><p className="eyebrow !text-teal-700">HUMAN ACCOUNTABILITY</p><h2 className="panel-title mt-2">Named review</h2>{reviews.length ? <div className="mt-4 rounded-lg bg-slate-50 p-4"><strong>{reviews[0].outcome.toUpperCase()}</strong><p className="text-sm">{reviews[0].reviewer} · {new Date(reviews[0].created_at).toLocaleString()}</p><p className="mt-2 text-xs text-slate-500">{reviews[0].created_action_ids.length} planned actions created</p></div> : <div className="mt-4 space-y-3"><input className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Reviewer full name" value={reviewer} onChange={(event) => setReviewer(event.target.value)} /><textarea className="w-full rounded-lg border border-slate-300 px-3 py-2" placeholder="Review notes" value={notes} onChange={(event) => setNotes(event.target.value)} /><div className="grid grid-cols-2 gap-2"><button className="primary-button" disabled={busy || selected.reliability_status !== "REVIEW"} onClick={() => void review("approved")}>Approve plan</button><button className="rounded-lg border border-rose-300 px-4 py-2 font-bold text-rose-700" disabled={busy || selected.reliability_status !== "REVIEW"} onClick={() => void review("rejected")}>Reject</button></div></div>}<p className="mt-4 text-xs text-slate-500">Approval creates planned maintenance records only. Execution and observed benefit remain separate physical evidence.</p></article></section>
    <section className="panel"><p className="eyebrow !text-teal-700">PROVENANCE GRAPH</p><h2 className="panel-title mt-2">{graph?.nodes.length ?? 0} evidence nodes · {graph?.edges.length ?? 0} links</h2>{graph?.missing_links.length ? <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Missing: {graph.missing_links.join(", ")}</p> : <p className="mt-3 text-sm text-emerald-700">Complete required evidence chain.</p>}<div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{graph?.nodes.map((node) => <div key={node.key} className="rounded-lg border border-slate-200 p-3"><strong className="text-xs uppercase text-slate-600">{node.resource_type.replaceAll("_", " ")}</strong><p className="mt-1 truncate font-mono text-xs text-slate-500">{node.resource_id}</p></div>)}</div><details className="mt-4"><summary className="cursor-pointer text-sm font-bold">Evidence payloads</summary>{evidence.map((record) => <pre key={record.id} className="mt-2 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(record.payload, null, 2)}</pre>)}</details></section></>}
  </div>;
}
