import { notFound } from "next/navigation";
import { PlaceholderPage } from "../../components/placeholder-page";
import { DataWorkspace } from "../../components/data-workspace";
import { AnalyticsWorkspace } from "../../components/analytics-workspace";
import { MLLab } from "../../components/ml-lab";
import { CausalLab } from "../../components/causal-lab";
import { DecisionsWorkspace } from "../../components/decisions-workspace";
import { InvestigatorWorkspace } from "../../components/investigator-workspace";

const sections: Record<string, { title: string; description: string }> = {
  data: { title: "Data", description: "Connect and validate decision datasets before analysis." },
  analytics: { title: "Analytics", description: "Inspect descriptive evidence without causal claims." },
  "ml-lab": { title: "ML Lab", description: "Predictive modelling workspace; results will be computed and versioned." },
  "causal-lab": { title: "Causal Lab", description: "Causal identification and treatment-effect analysis workspace." },
  scenarios: { title: "Scenarios", description: "Counterfactual scenario analysis will surface feasible, evidence-bounded options." },
  "ai-investigator": { title: "AI Investigator", description: "AI explanations will be grounded exclusively in validated evidence." },
  decisions: { title: "Decisions", description: "Decision recommendations will include provenance and abstention states." },
  experiments: { title: "Experiments", description: "Reproducible baseline and system evaluations will be tracked here." },
};

export function generateStaticParams() {
  return Object.keys(sections).map((section) => ({ section }));
}

export default async function SectionPage({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params;
  const page = sections[section];
  if (!page) notFound();
  if (section === "data") return <DataWorkspace />;
  if (section === "analytics") return <AnalyticsWorkspace />;
  if (section === "ml-lab") return <MLLab />;
  if (section === "causal-lab" || section === "scenarios") return <CausalLab />;
  if (section === "decisions") return <DecisionsWorkspace />;
  if (section === "ai-investigator") return <InvestigatorWorkspace />;
  return <PlaceholderPage {...page} />;
}
