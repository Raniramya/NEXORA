"use client";

import { useEffect, useState } from "react";
import { AnomalyModelRun, AnomalyScore, FaultExplanation, FaultModelRun, FaultPrediction, FaultReliabilityRun, Machine, maintenanceApi, SelectivePrediction, SignalFaultLabel, SignalWindow } from "../services/api";

export function FaultModelWorkspace() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [machineId, setMachineId] = useState("");
  const [windows, setWindows] = useState<SignalWindow[]>([]);
  const [labels, setLabels] = useState<SignalFaultLabel[]>([]);
  const [runs, setRuns] = useState<FaultModelRun[]>([]);
  const [faultClass, setFaultClass] = useState("normal");
  const [prediction, setPrediction] = useState<FaultPrediction>();
  const [explanation, setExplanation] = useState<FaultExplanation>();
  const [anomalyRuns, setAnomalyRuns] = useState<AnomalyModelRun[]>([]);
  const [anomalyScore, setAnomalyScore] = useState<AnomalyScore>();
  const [reliabilityRuns, setReliabilityRuns] = useState<FaultReliabilityRun[]>([]);
  const [selective, setSelective] = useState<SelectivePrediction>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { Promise.all([maintenanceApi.machines(), maintenanceApi.faultModelRuns(), maintenanceApi.anomalyModelRuns(), maintenanceApi.reliabilityRuns()]).then(([assets, modelRuns, anomalyModelRuns, reliabilityModelRuns]) => { setMachines(assets); setRuns(modelRuns); setAnomalyRuns(anomalyModelRuns); setReliabilityRuns(reliabilityModelRuns); setMachineId(assets[0]?.id ?? ""); }).catch(() => setError("Fault-model services are unavailable.")); }, []);
  useEffect(() => { if (!machineId) return; Promise.all([maintenanceApi.signalWindows(machineId), maintenanceApi.labels(machineId)]).then(([items, labelItems]) => { setWindows(items); setLabels(labelItems); }).catch(() => setError("Training evidence could not be loaded.")); }, [machineId]);

  async function label(windowId: string) {
    setBusy(true); setError("");
    try { await maintenanceApi.labelWindow(windowId, faultClass.trim()); setLabels(await maintenanceApi.labels(machineId)); }
    catch { setError("The controlled-experiment label could not be stored."); }
    finally { setBusy(false); }
  }

  async function train() {
    setBusy(true); setError(""); setPrediction(undefined); setExplanation(undefined);
    try { const run = await maintenanceApi.trainFaultModel(machineId); setRuns((current) => [run, ...current]); }
    catch { setError("Training requires at least 8 confirmed windows, two classes, and two examples per class."); }
    finally { setBusy(false); }
  }

  async function predict() {
    const run = runs.find((item) => item.machine_id === machineId && item.status === "completed");
    if (!run || !windows[0]) return;
    setBusy(true); setError("");
    try { setPrediction(await maintenanceApi.predictFault(run.id, windows[0].id)); setExplanation(undefined); }
    catch { setError("The latest feature set is incompatible with this model run."); }
    finally { setBusy(false); }
  }

  async function explain() {
    if (!prediction) return;
    setBusy(true); setError("");
    try { setExplanation(await maintenanceApi.explainFault(prediction.id)); }
    catch { setError("The prediction could not be explained from its model provenance."); }
    finally { setBusy(false); }
  }

  async function trainAndScoreAnomaly() {
    if (!machineId || !windows[0]) return;
    setBusy(true); setError("");
    try {
      let run = anomalyRuns.find((item) => item.machine_id === machineId && item.status === "completed");
      if (!run) { run = await maintenanceApi.trainAnomalyModel(machineId); setAnomalyRuns((current) => [run as AnomalyModelRun, ...current]); }
      setAnomalyScore(await maintenanceApi.scoreAnomaly(run.id, windows[0].id));
    } catch { setError("Anomaly training requires at least 8 confirmed normal windows."); }
    finally { setBusy(false); }
  }

  async function calibrateAndEvaluate() {
    if (!latestRun || !prediction) { setError("Create a prediction before reliability evaluation."); return; }
    setBusy(true); setError("");
    try {
      let run = reliabilityRuns.find((item) => item.fault_model_run_id === latestRun.id);
      if (!run) { run = await maintenanceApi.calibrateFaultModel(latestRun.id); setReliabilityRuns((current) => [run as FaultReliabilityRun, ...current]); }
      setSelective(await maintenanceApi.evaluateReliability(run.id, prediction.id, anomalyScore?.id));
    } catch { setError("Reliability evaluation could not be completed from independent calibration evidence."); }
    finally { setBusy(false); }
  }

  const labelByWindow = new Map(labels.map((item) => [item.signal_window_id, item]));
  const latestRun = runs.find((item) => item.machine_id === machineId && item.status === "completed");
  const reliabilityPanel = <article className="panel"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow !text-teal-700">CALIBRATED SELECTIVE PREDICTION</p><h2 className="panel-title mt-2">ACT / MONITOR / ABSTAIN</h2><p className="panel-copy">Uses an independent calibration partition, conformal prediction set, and optional anomaly evidence.</p></div><button type="button" className="primary-button" disabled={busy || !prediction} onClick={() => void calibrateAndEvaluate()}>{busy ? "Evaluating..." : "Calibrate / evaluate"}</button></div>{selective && <div className={`mt-5 rounded-lg p-4 ${selective.action === "ACT" ? "bg-emerald-50 text-emerald-900" : selective.action === "MONITOR" ? "bg-amber-50 text-amber-900" : "bg-rose-50 text-rose-900"}`}><p className="text-xs font-bold uppercase tracking-wide">{selective.action}</p><p className="mt-1 text-xl font-extrabold">Prediction set: {selective.prediction_set.length ? selective.prediction_set.join(", ") : "empty"}</p><div className="mt-2 flex flex-wrap gap-2">{Object.entries(selective.calibrated_probabilities).map(([name, value]) => <span className="rounded-full bg-white/70 px-2.5 py-1 text-xs font-bold" key={name}>{name} {(value * 100).toFixed(1)}%</span>)}</div><p className="mt-3 text-sm">{String(selective.details.interpretation ?? (selective.details.reasons as string[] | undefined)?.join(" ") ?? "Evidence gate evaluated.")}</p></div>}</article>;
  return <section className="space-y-5">
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <div className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">CONTROLLED LABELS</p><h2 className="panel-title mt-2">Build the fault dataset</h2><p className="panel-copy">Only confirmed test-bench labels enter training.</p><select className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2" value={machineId} onChange={(event) => setMachineId(event.target.value)}>{machines.map((machine) => <option value={machine.id} key={machine.id}>{machine.name}</option>)}</select><div className="mt-3 flex gap-2"><input className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2" value={faultClass} onChange={(event) => setFaultClass(event.target.value)} placeholder="normal / imbalance" /><span className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-bold">{labels.length} labelled</span></div><div className="mt-4 max-h-72 space-y-2 overflow-auto">{windows.map((window) => { const existing = labelByWindow.get(window.id); return <div key={window.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 p-3"><span className="min-w-0 text-sm"><b className="block truncate">{window.channel} · {window.samples.length} samples</b><span className="text-xs text-slate-500">{existing ? `${existing.fault_class} · confirmed` : "unlabelled"}</span></span><button type="button" className="shrink-0 rounded-lg border border-teal-600 px-3 py-1.5 text-xs font-bold text-teal-700" disabled={busy || !faultClass.trim()} onClick={() => void label(window.id)}>Label</button></div>; })}</div></article>
      <article className="panel"><p className="eyebrow !text-teal-700">REPRODUCIBLE TRAINING</p><h2 className="panel-title mt-2">Fault classifier comparison</h2><p className="panel-copy">A seeded stratified split compares Random Forest, SVM, and XGBoost when installed.</p><button type="button" className="primary-button mt-5 w-full" disabled={busy || !machineId} onClick={() => void train()}>{busy ? "Working..." : "Train fault models"}</button>{latestRun ? <div className="mt-5"><div className="rounded-lg bg-emerald-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Winning candidate</p><p className="mt-1 text-xl font-extrabold text-emerald-900">{latestRun.winning_model}</p><p className="mt-1 text-xs text-emerald-800">{latestRun.results.train_size} train / {latestRun.results.test_size} test · seed 42</p></div><div className="mt-3 space-y-2">{Object.entries(latestRun.results.models ?? {}).map(([name, metrics]) => <div key={name} className="flex justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm"><b>{name}</b><span>F1 {Number(metrics.f1_weighted ?? 0).toFixed(3)}</span></div>)}</div>{Object.keys(latestRun.results.unavailable_models ?? {}).length > 0 && <p className="mt-3 text-xs text-amber-700">Unavailable: {Object.keys(latestRun.results.unavailable_models ?? {}).join(", ")}. No substitute was used.</p>}<button type="button" className="mt-4 w-full rounded-lg border border-teal-600 px-4 py-2 font-bold text-teal-700" disabled={busy || windows.length === 0} onClick={() => void predict()}>Predict latest window</button></div> : <p className="mt-5 rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-500">No completed physical fault-model run for this asset.</p>}</article>
    </div>
    {prediction && <article className="panel border-amber-300"><p className="eyebrow !text-amber-700">UNCALIBRATED PREDICTION</p><div className="mt-2 flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-2xl font-extrabold">{prediction.predicted_class}</h2><p className="text-sm text-slate-500">Model probability {prediction.confidence == null ? "unavailable" : `${(prediction.confidence * 100).toFixed(1)}%`}</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold uppercase text-amber-800">{prediction.reliability_status}</span></div><p className="mt-3 text-sm text-amber-800">This output is predictive evidence only. It is not calibrated, causal, or a maintenance recommendation.</p><button type="button" className="mt-4 rounded-lg border border-amber-600 px-4 py-2 font-bold text-amber-800" disabled={busy} onClick={() => void explain()}>{busy ? "Computing..." : "Explain this prediction"}</button></article>}
    {explanation && <article className="panel"><p className="eyebrow !text-teal-700">PERMUTATION SHAP</p><h2 className="panel-title mt-2">Contributions toward {explanation.explained_class}</h2><p className="panel-copy">Base probability {explanation.base_value.toFixed(4)} → explained output {explanation.output_value.toFixed(4)}. Positive values support this class; negative values oppose it.</p><div className="mt-4 space-y-2">{Object.entries(explanation.contributions).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).map(([name, value]) => <div className="grid grid-cols-[1fr_auto] gap-4 rounded-lg border border-slate-200 px-3 py-2 text-sm" key={name}><span>{name.replaceAll("_", " ")}</span><b className={value >= 0 ? "text-emerald-700" : "text-rose-700"}>{value >= 0 ? "+" : ""}{value.toFixed(5)}</b></div>)}</div><p className="mt-4 text-xs text-slate-500">SHAP explains model behavior. It does not establish that changing a feature will change the physical outcome.</p></article>}
    <article className="panel"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow !text-teal-700">UNKNOWN-CONDITION DETECTION</p><h2 className="panel-title mt-2">Isolation Forest normal envelope</h2><p className="panel-copy">Train only on confirmed normal windows, then score the latest signal without assigning a fault class.</p></div><button type="button" className="primary-button" disabled={busy || !machineId || windows.length === 0} onClick={() => void trainAndScoreAnomaly()}>{busy ? "Working..." : "Train / score latest"}</button></div>{anomalyScore && <div className={`mt-5 rounded-lg p-4 ${anomalyScore.is_anomaly ? "bg-rose-50 text-rose-900" : "bg-emerald-50 text-emerald-900"}`}><p className="text-xs font-bold uppercase tracking-wide">{anomalyScore.interpretation.replaceAll("_", " ")}</p><p className="mt-1 text-xl font-extrabold">Decision score {anomalyScore.decision_score.toFixed(5)}</p><p className="mt-2 text-sm">{anomalyScore.is_anomaly ? "The window is outside the learned normal envelope. Its fault type remains unknown." : "The window is within the learned normal envelope."}</p></div>}</article>
    {reliabilityPanel}
  </section>;
}
