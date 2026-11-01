import { Link } from 'react-router-dom';
import { Github, CheckCircle, Shield, Cpu, GitBranch } from 'lucide-react';
import { landingConfig } from '../config/landing';

export default function Landing() {
  return (
    <div className="min-h-screen bg-page text-text">
      {/* Hero */}
      <section className="py-20 px-4 text-center">
        <h1 className="text-5xl font-bold mb-4 text-brand">SentinelCode</h1>
        <p className="text-xl text-secondary mb-8 max-w-2xl mx-auto">
          Multi-agent AI code review powered by local LLMs
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            to="/app/new"
            className="bg-brand hover:bg-brand/90 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Try a Review
          </Link>
          <a
            href="https://github.com/dhanalaxmi875/sentinel-multiagent-code-reviewer"
            target="_blank"
            rel="noopener noreferrer"
            className="border border-border hover:border-brand text-text px-6 py-3 rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <Github size={20} />
            GitHub
          </a>
        </div>
      </section>

      {/* Pipeline Diagram */}
      <section className="py-16 px-4 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold mb-8 text-center uppercase tracking-wider text-secondary">
          Pipeline
        </h2>
        <div className="bg-panel border border-border rounded-lg p-8">
          <svg viewBox="0 0 800 200" className="w-full h-auto">
            {/* Orchestrator */}
            <rect x="50" y="80" width="100" height="40" rx="4" fill="#161B22" stroke="#8B5CF6" strokeWidth="2" />
            <text x="100" y="105" textAnchor="middle" fill="#E6EDF3" fontSize="12">Orchestrator</text>

            {/* Arrow */}
            <line x1="150" y1="100" x2="200" y2="100" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)" />

            {/* Specialists in parallel */}
            <rect x="200" y="30" width="80" height="35" rx="4" fill="#161B22" stroke="#21262D" strokeWidth="1" />
            <text x="240" y="52" textAnchor="middle" fill="#E6EDF3" fontSize="10">Bug</text>

            <rect x="200" y="75" width="80" height="35" rx="4" fill="#161B22" stroke="#21262D" strokeWidth="1" />
            <text x="240" y="97" textAnchor="middle" fill="#E6EDF3" fontSize="10">Security</text>

            <rect x="200" y="120" width="80" height="35" rx="4" fill="#161B22" stroke="#21262D" strokeWidth="1" />
            <text x="240" y="142" textAnchor="middle" fill="#E6EDF3" fontSize="10">Quality</text>

            <rect x="200" y="165" width="80" height="35" rx="4" fill="#161B22" stroke="#21262D" strokeWidth="1" />
            <text x="240" y="187" textAnchor="middle" fill="#E6EDF3" fontSize="10">Test</text>

            {/* Semgrep in parallel */}
            <rect x="200" y="15" width="80" height="15" rx="2" fill="#161B22" stroke="#58A6FF" strokeWidth="1" />
            <text x="240" y="26" textAnchor="middle" fill="#58A6FF" fontSize="8">Semgrep</text>

            {/* Arrow */}
            <line x1="280" y1="100" x2="330" y2="100" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)" />

            {/* Verifier */}
            <rect x="330" y="80" width="80" height="40" rx="4" fill="#161B22" stroke="#8B5CF6" strokeWidth="2" />
            <text x="370" y="105" textAnchor="middle" fill="#E6EDF3" fontSize="12">Verifier</text>

            {/* Arrow */}
            <line x1="410" y1="100" x2="460" y2="100" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)" />

            {/* Summarizer */}
            <rect x="460" y="80" width="100" height="40" rx="4" fill="#161B22" stroke="#8B5CF6" strokeWidth="2" />
            <text x="510" y="105" textAnchor="middle" fill="#E6EDF3" fontSize="12">Summarizer</text>

            {/* Arrow */}
            <line x1="560" y1="100" x2="610" y2="100" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)" />

            {/* Verdict */}
            <rect x="610" y="80" width="80" height="40" rx="4" fill="#161B22" stroke="#3FB950" strokeWidth="2" />
            <text x="650" y="105" textAnchor="middle" fill="#3FB950" fontSize="12">Verdict</text>

            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#8B949E" />
              </marker>
            </defs>
          </svg>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-4 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold mb-8 text-center uppercase tracking-wider text-secondary">
          Features
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-panel border border-border rounded-lg p-6">
            <Shield className="w-8 h-8 text-brand mb-4" />
            <h3 className="font-semibold mb-2">Multi-Agent Specialization</h3>
            <p className="text-secondary text-sm">
              Specialized agents for bugs, security, code quality, and test coverage work in parallel
            </p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6">
            <CheckCircle className="w-8 h-8 text-brand mb-4" />
            <h3 className="font-semibold mb-2">Semgrep Hybrid</h3>
            <p className="text-secondary text-sm">
              Combines AI analysis with deterministic static security scanning for accuracy
            </p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6">
            <Shield className="w-8 h-8 text-brand mb-4" />
            <h3 className="font-semibold mb-2">Verification Layer</h3>
            <p className="text-secondary text-sm">
              Removes false positives through evidence-based validation
            </p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6">
            <Cpu className="w-8 h-8 text-brand mb-4" />
            <h3 className="font-semibold mb-2">Local LLMs</h3>
            <p className="text-secondary text-sm">
              Runs on local models via Ollama - no data leaves your infrastructure
            </p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6">
            <GitBranch className="w-8 h-8 text-brand mb-4" />
            <h3 className="font-semibold mb-2">GitHub Actions Ready</h3>
            <p className="text-secondary text-sm">
              Drop-in CI/CD integration for automated PR reviews
            </p>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="py-16 px-4 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold mb-8 text-center uppercase tracking-wider text-secondary">
          Team
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {landingConfig.team.map((member, i) => (
            <div key={i} className="bg-panel border border-border rounded-lg p-6 text-center">
              <div className="w-12 h-12 bg-brand/20 rounded-full mx-auto mb-4 flex items-center justify-center text-brand font-bold">
                {member.name.charAt(0)}
              </div>
              <h3 className="font-semibold">{member.name}</h3>
              <p className="text-secondary text-sm">{member.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-16 px-4 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold mb-8 text-center uppercase tracking-wider text-secondary">
          Tech Stack
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-panel border border-border rounded-lg p-6 text-center">
            <h3 className="font-semibold mb-2">Frontend</h3>
            <p className="text-secondary text-sm">React + TypeScript + Vite</p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6 text-center">
            <h3 className="font-semibold mb-2">Backend</h3>
            <p className="text-secondary text-sm">Python + FastAPI</p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6 text-center">
            <h3 className="font-semibold mb-2">AI</h3>
            <p className="text-secondary text-sm">Ollama + Local LLMs</p>
          </div>
          <div className="bg-panel border border-border rounded-lg p-6 text-center">
            <h3 className="font-semibold mb-2">Security</h3>
            <p className="text-secondary text-sm">Semgrep + SAST</p>
          </div>
        </div>
      </section>
    </div>
  );
}
