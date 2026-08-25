export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <div className="max-w-4xl">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">NEXORA-CDI</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">{title}</h1>
      <div className="mt-8 rounded-2xl border border-[#22314a] bg-[#101b2d] p-7 shadow-2xl shadow-black/10">
        <p className="text-slate-300">{description}</p>
        <p className="mt-4 text-sm text-slate-500">No analytical evidence has been loaded yet.</p>
      </div>
    </div>
  );
}
