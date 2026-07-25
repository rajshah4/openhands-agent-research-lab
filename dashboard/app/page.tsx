import snapshot from "../data/snapshot.json";
import { ResearchDashboard } from "./research-dashboard";

export default function Home() {
  return <ResearchDashboard snapshot={snapshot} />;
}
