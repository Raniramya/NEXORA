"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [["Executive overview", "/"], ["Data foundation", "/data"], ["Analytics", "/analytics"], ["ML studio", "/ml-lab"], ["Causal lab", "/causal-lab"], ["Scenarios", "/scenarios"], ["AI investigator", "/ai-investigator"], ["Decision register", "/decisions"], ["Experiments", "/experiments"]] as const;

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  return <div className="min-h-screen bg-[#f4f7fb] text-[#101828] md:grid md:grid-cols-[278px_1fr]"><aside className="app-sidebar"><Link href="/" className="brand"><span className="brand-mark">N</span><span>NEXORA <small>CDI</small></span></Link><p className="brand-caption">Evidence-calibrated decision intelligence</p><nav aria-label="Primary navigation">{navigation.map(([label, href], index) => <Link key={href} href={href} className={pathname === href ? "nav-link active" : "nav-link"}><span className="nav-index">{String(index + 1).padStart(2, "0")}</span>{label}</Link>)}</nav><div className="sidebar-foot"><span className="status-dot" />Evidence-first workspace</div><a href="https://github.com/Bharat0264/NEXORA---CDI" target="_blank" rel="noreferrer" className="github-link">View project source <span aria-hidden="true">-&gt;</span></a></aside><main className="app-main"><header className="app-topbar"><div><span className="topbar-kicker">RESEARCH WORKSPACE</span><span className="topbar-title">Decision intelligence platform</span></div><div className="topbar-user"><span className="topbar-avatar">N</span><span>Local workspace</span></div></header><section className="app-content">{children}</section></main></div>;
}
