"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { GeoAsset, GeospatialAnalysisRun, maintenanceApi } from "../services/api";

type Distance = { machine_id: string; machine_name: string; distance_km: number };
type Cluster = { cluster_id: number; centroid: { latitude: number; longitude: number }; machine_names: string[]; event_ids: string[]; asset_count: number; fault_event_count: number };

export function GeoWorkspace() {
  const [assets, setAssets] = useState<GeoAsset[]>([]);
  const [latitude, setLatitude] = useState("12.9716");
  const [longitude, setLongitude] = useState("77.5946");
  const [epsilon, setEpsilon] = useState("1");
  const [lookback, setLookback] = useState("30");
  const [distanceRun, setDistanceRun] = useState<GeospatialAnalysisRun>();
  const [hotspotRun, setHotspotRun] = useState<GeospatialAnalysisRun>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { maintenanceApi.geoAssets().then(setAssets).catch(() => setError("Geospatial evidence could not be loaded.")); }, []);
  const bounds = useMemo(() => ({
    minLat: assets.length ? Math.min(...assets.map((asset) => asset.latitude)) : 0,
    maxLat: assets.length ? Math.max(...assets.map((asset) => asset.latitude)) : 1,
    minLon: assets.length ? Math.min(...assets.map((asset) => asset.longitude)) : 0,
    maxLon: assets.length ? Math.max(...assets.map((asset) => asset.longitude)) : 1,
  }), [assets]);
  const distances = (distanceRun?.result.distances ?? []) as Distance[];
  const clusters = (hotspotRun?.result.clusters ?? []) as Cluster[];

  async function calculateDistances(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { setDistanceRun(await maintenanceApi.geoDistances(Number(latitude), Number(longitude))); }
    catch { setError("Distances could not be calculated. Check the origin coordinates."); }
    finally { setBusy(false); }
  }

  async function detectHotspots(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { setHotspotRun(await maintenanceApi.geoHotspots(Number(epsilon), 2, Number(lookback))); }
    catch { setError("Hotspot analysis could not be completed with these settings."); }
    finally { setBusy(false); }
  }

  return <div className="space-y-7">
    <section className="page-hero"><p className="eyebrow">GEOSPATIAL EVIDENCE</p><h1>Locate assets and inspect fault proximity.</h1><p>Distances use the Haversine great-circle method. DBSCAN hotspots summarize recorded fault locations and never imply that location caused a fault.</p></section>
    {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <section className="grid gap-5 lg:grid-cols-[1.2fr_.8fr]">
      <article className="panel"><p className="eyebrow !text-teal-700">COORDINATE PLOT</p><h2 className="panel-title mt-2">Mapped assets</h2><div className="relative mt-5 h-80 overflow-hidden rounded-xl border border-slate-200 bg-slate-50" role="img" aria-label="Relative coordinate plot of registered assets">{assets.map((asset) => { const x = 5 + 90 * (asset.longitude - bounds.minLon) / Math.max(bounds.maxLon - bounds.minLon, 0.000001); const y = 95 - 90 * (asset.latitude - bounds.minLat) / Math.max(bounds.maxLat - bounds.minLat, 0.000001); return <div key={asset.machine_id} title={`${asset.machine_name}: ${asset.latitude}, ${asset.longitude}`} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${x}%`, top: `${y}%` }}><span className={`block h-4 w-4 rounded-full border-2 border-white shadow ${asset.fault_event_count ? "bg-rose-500" : "bg-teal-500"}`} /><span className="mt-1 block whitespace-nowrap rounded bg-white/90 px-1 text-[10px] font-bold">{asset.machine_name}</span></div>; })}{assets.length === 0 && <p className="p-8 text-center text-sm text-slate-500">No assets have complete coordinates. Add latitude and longitude in the asset registry.</p>}</div><p className="mt-3 text-xs text-slate-500">Relative coordinate view; use computed distances for measurement. Red markers have recorded faults.</p></article>
      <article className="panel"><p className="eyebrow !text-teal-700">ASSET PROVENANCE</p><h2 className="panel-title mt-2">Recorded locations</h2><div className="mt-5 space-y-2">{assets.map((asset) => <div key={asset.machine_id} className="rounded-lg border border-slate-200 p-3"><div className="flex justify-between gap-3"><strong>{asset.machine_name}</strong><span className="text-xs text-slate-500">{asset.fault_event_count} faults</span></div><p className="mt-1 font-mono text-xs text-slate-600">{asset.latitude.toFixed(5)}, {asset.longitude.toFixed(5)}</p><p className="text-xs text-slate-500">Latest: {asset.latest_fault_type ?? "none recorded"}</p></div>)}</div></article>
    </section>
    <section className="grid gap-5 lg:grid-cols-2">
      <article className="panel"><p className="eyebrow !text-teal-700">HAVERSINE DISTANCE</p><h2 className="panel-title mt-2">Distance from response origin</h2><form onSubmit={calculateDistances} className="mt-5 grid grid-cols-2 gap-3"><label className="text-xs font-bold uppercase text-slate-600">Latitude<input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" type="number" step="any" min="-90" max="90" value={latitude} onChange={(event) => setLatitude(event.target.value)} /></label><label className="text-xs font-bold uppercase text-slate-600">Longitude<input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" type="number" step="any" min="-180" max="180" value={longitude} onChange={(event) => setLongitude(event.target.value)} /></label><button disabled={busy} className="primary-button col-span-2">Calculate and preserve run</button></form><ol className="mt-5 space-y-2">{distances.map((item) => <li key={item.machine_id} className="flex justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"><span>{item.machine_name}</span><strong>{item.distance_km.toFixed(2)} km</strong></li>)}</ol></article>
      <article className="panel"><p className="eyebrow !text-teal-700">DBSCAN HOTSPOTS</p><h2 className="panel-title mt-2">Recent spatial patterns</h2><form onSubmit={detectHotspots} className="mt-5 grid grid-cols-2 gap-3"><label className="text-xs font-bold uppercase text-slate-600">Radius (km)<input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" type="number" step="any" min="0.001" value={epsilon} onChange={(event) => setEpsilon(event.target.value)} /></label><label className="text-xs font-bold uppercase text-slate-600">Lookback days<input className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 font-normal" type="number" min="1" value={lookback} onChange={(event) => setLookback(event.target.value)} /></label><button disabled={busy} className="primary-button col-span-2">Detect and preserve hotspots</button></form>{hotspotRun && <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">{String(hotspotRun.result.warning)}</div>}<div className="mt-3 space-y-2">{clusters.map((cluster) => <div key={cluster.cluster_id} className="rounded-lg border border-slate-200 p-3 text-sm"><strong>Cluster {cluster.cluster_id + 1}</strong><p>{cluster.machine_names.join(", ")} · {cluster.fault_event_count} events</p><p className="mt-1 text-xs text-slate-500">Provenance: {cluster.event_ids.join(", ")}</p></div>)}{hotspotRun && clusters.length === 0 && <p className="text-sm text-slate-500">No cluster met the minimum of two distinct assets.</p>}</div></article>
    </section>
  </div>;
}
