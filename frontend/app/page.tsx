import { Hero } from "./components/Hero";
import { About } from "./components/About";
import { Dashboard } from "./components/Dashboard";

export default function Home() {
  return (
    <div className="space-y-12">
      <Hero />
      <Dashboard />
      <About />
    </div>
  );
}

