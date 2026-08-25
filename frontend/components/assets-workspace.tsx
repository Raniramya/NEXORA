"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Machine, maintenanceApi, SensorReading, SignalWindow } from "../services/api";

const emptyReading = { vibration_rms: "", temperature: "", current: "", rpm: "" };
const measurementLabels: Record<keyof typeof emptyReading, string> = {
  vibration_rms: "Vibration RMS",
  temperature: "Temperature",
  current: "Current",
  rpm: "RPM",
};

export function AssetsWorkspace() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selected, setSelected] = useState<Machine>();
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [signalWindows, setSignalWindows] = useState<SignalWindow[]>([]);
  const [machineName, setMachineName] = useState("");
  const [reading, setReading] = useState(emptyReading);
  const [sampleRate, setSampleRate] = useState("1000");
  const [signalSamples, setSignalSamples] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const items = await maintenanceApi.machines();
    setMachines(items);
    setSelected((current) => current ? items.find((item) => item.id === current.id) : items[0]);
  }, []);

  useEffect(() => { refresh().catch(() => setError("The maintenance API is unavailable. Start the backend on port 8000.")); }, [refresh]);
  useEffect(() => {
    if (!selected) { setReadings([]); setSignalWindows([]); return; }
    Promise.all([maintenanceApi.readings(selected.id), maintenanceApi.signalWindows(selected.id)])
      .then(([measurementItems, windowItems]) => { setReadings(measurementItems); setSignalWindows(windowItems); })
      .catch(() => setError("Recorded evidence could not be loaded."));
  }, [selected]);

  async function createMachine(event: FormEvent) {
    event.preventDefault();
    if (!machineName.trim()) return;
    setBusy(true); setError("");
    try { const machine = await maintenanceApi.createMachine({ name: machineName.trim(), asset_type: "motor" }); setMachineName(""); await refresh(); setSelected(machine); }
    catch { setError("The asset could not be registered."); }
    finally { setBusy(false); }
  }

  async function recordReading(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const values = Object.values(reading);
    if (values.every((value) => value === "")) { setError("Enter at least one measured sensor value."); return; }
    setBusy(true); setError("");
    try {
      const payload = Object.fromEntries(Object.entries(reading).map(([key, value]) => [key, value === "" ? null : Number(value)]));
      await maintenanceApi.recordReading(selected.id, { recorded_at: new Date().toISOString(), ...payload } as Omit<SensorReading, "id" | "machine_id" | "features">);
      setReading(emptyReading);
      setReadings(await maintenanceApi.readings(selected.id));
    } catch { setError("The measurement could not be recorded. Check the entered values."); }
    finally { setBusy(false); }
  }

  async function processSignal(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    const samples = signalSamples.split(/[\s,;]+/).filter(Boolean).map(Number);
    if (samples.length < 8 || samples.some((value) => !Number.isFinite(value))) { setError("Provide at least 8 finite samples separated by commas or spaces."); return; }
    const rate = Number(sampleRate);
    if (!Number.isFinite(rate) || rate <= 0) { setError("Sample rate must be positive."); return; }
    setBusy(true); setError("");
    try {
      await maintenanceApi.recordSignalWindow(selected.id, { recorded_at: new Date().toISOString(), sample_rate_hz: rate, channel: "vibration_x", unit: "g", samples, source: "dashboard_replay" });
      setSignalSamples("");
      setSignalWindows(await maintenanceApi.signalWindows(selected.id));
    } catch { setError("The signal window could not be processed."); }
    finally { setBusy(false); }
  }

  const latest = readings[0];
  return <div className="space-y-7">
    <section className="page-hero"><p className="eyebrow">EDGE–CLOUD FOUNDATION</p><h1>Connect physical assets to evidence.</h1><p>Register motors and ingest vibration, temperature, current, and RPM measurements. Values shown here are recorded observations—not predictions.</p></section>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <section className="grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">ASSET REGISTRY</p><h2 className="panel-title mt-2">Machines</h2><form className="mt-5 flex gap-2" onSubmit={createMachine}><label className="sr-only" htmlFor="machine-name">Machine name</label><input id="machine-name" className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2" value={machineName} onChange={(event) => setMachineName(event.target.value)} placeholder="Motor 01" maxLength={120} /><button className="primary-button" disabled={busy}>Register</button></form><div className="mt-5 space-y-2">{machines.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-500">No assets registered yet.</p>}{machines.map((machine) => <button type="button" key={machine.id} onClick={() => setSelected(machine)} className={`w-full rounded-lg border px-4 py-3 text-left ${selected?.id === machine.id ? "border-teal-400 bg-teal-50" : "border-slate-200"}`}><span className="block font-bold">{machine.name}</span><span className="text-xs text-slate-500">{machine.asset_type} · {machine.status}</span></button>)}</div></article>
      <article className="panel"><p className="eyebrow !text-teal-700">MULTIMODAL TELEMETRY</p><h2 className="panel-title mt-2">{selected ? `Record evidence for ${selected.name}` : "Select an asset"}</h2><p className="panel-copy">Use physical measurements from the ESP32 or test bench. Blank channels remain explicitly missing.</p><form className="mt-5 grid grid-cols-2 gap-3" onSubmit={recordReading}>{Object.entries(reading).map(([key, value]) => { const measurement = key as keyof typeof emptyReading; return <label key={key} className="text-xs font-bold uppercase tracking-wide text-slate-600">{measurementLabels[measurement]}<input type="number" min={measurement === "temperature" ? undefined : 0} step="any" disabled={!selected || busy} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" value={value} onChange={(event) => setReading((current) => ({ ...current, [key]: event.target.value }))} /></label>; })}<button className="primary-button col-span-2 mt-2" disabled={!selected || busy}>{busy ? "Saving evidence..." : "Record sensor reading"}</button></form></article>
    </section>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[["Vibration RMS", latest?.vibration_rms], ["Temperature", latest?.temperature], ["Current", latest?.current], ["RPM", latest?.rpm]].map(([label, value]) => <article className="metric-card" key={String(label)}><p className="metric-label">{label}</p><div className="metric-value">{value == null ? "—" : Number(value).toLocaleString()}</div><p className="metric-note">{latest ? `Observed ${new Date(latest.recorded_at).toLocaleString()}` : "No recorded evidence"}</p></article>)}</section>
    <section className="grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">SIGNAL WINDOW REPLAY</p><h2 className="panel-title mt-2">Process raw vibration samples</h2><p className="panel-copy">Paste ESP32 or test-bench samples. NEXORA preserves the raw window and computes deterministic features server-side.</p><form className="mt-5 space-y-3" onSubmit={processSignal}><label className="block text-xs font-bold uppercase tracking-wide text-slate-600">Sample rate (Hz)<input type="number" min="0.001" step="any" value={sampleRate} onChange={(event) => setSampleRate(event.target.value)} disabled={!selected || busy} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm font-normal" /></label><label className="block text-xs font-bold uppercase tracking-wide text-slate-600">Raw samples<textarea rows={6} value={signalSamples} onChange={(event) => setSignalSamples(event.target.value)} disabled={!selected || busy} placeholder="0.0, 0.31, 0.59, 0.81, ..." className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm font-normal" /></label><button className="primary-button w-full" disabled={!selected || busy}>{busy ? "Processing..." : "Store and extract features"}</button></form></article>
      <article className="panel"><p className="eyebrow !text-teal-700">DERIVED EVIDENCE</p><h2 className="panel-title mt-2">Latest computed feature set</h2>{signalWindows[0] ? <><p className="panel-copy">Extractor {signalWindows[0].feature_set.extractor_version} · source window {signalWindows[0].id.slice(0, 8)}</p><dl className="mt-5 grid grid-cols-2 gap-3">{Object.entries(signalWindows[0].feature_set.features).map(([name, value]) => <div key={name} className="rounded-lg border border-slate-200 bg-slate-50 p-3"><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{name.replaceAll("_", " ")}</dt><dd className="mt-1 text-lg font-extrabold text-slate-800">{value.toLocaleString(undefined, { maximumFractionDigits: 5 })}</dd></div>)}</dl></> : <p className="mt-5 rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-500">No raw signal window has been processed for this asset.</p>}</article>
    </section>
    <section className="panel overflow-hidden !p-0"><div className="border-b border-slate-200 px-5 py-4"><p className="eyebrow !text-teal-700">PROVENANCE LOG</p><h2 className="panel-title mt-1">Recorded observations</h2></div><div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-800 text-xs uppercase tracking-wide text-white"><tr><th className="px-5 py-3">Recorded at</th><th className="px-5 py-3">Vibration RMS</th><th className="px-5 py-3">Temperature</th><th className="px-5 py-3">Current</th><th className="px-5 py-3">RPM</th></tr></thead><tbody>{readings.map((item) => <tr key={item.id} className="border-b border-slate-100"><td className="px-5 py-3">{new Date(item.recorded_at).toLocaleString()}</td><td className="px-5 py-3">{item.vibration_rms ?? "—"}</td><td className="px-5 py-3">{item.temperature ?? "—"}</td><td className="px-5 py-3">{item.current ?? "—"}</td><td className="px-5 py-3">{item.rpm ?? "—"}</td></tr>)}</tbody></table>{readings.length === 0 && <p className="p-6 text-center text-sm text-slate-500">No sensor evidence recorded for this asset.</p>}</div></section>
  </div>;
}
