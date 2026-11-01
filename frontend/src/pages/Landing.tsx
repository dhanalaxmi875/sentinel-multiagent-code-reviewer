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

      {Object.values(landingConfig.stats).some(value => value !== null) && (
        <section className="px-4 pb-12 max-w-5xl mx-auto" aria-label="Project statistics">
          <div className="grid sm:grid-cols-3 gap-4">
            {Object.entries(landingConfig.stats).filter((entry): entry is [string, number] => typeof entry[1] === 'number').map(([label, value]) => (
              <div key={label} className="bg-panel border border-border rounded-lg p-5"><div className="text-2xl font-bold">{value}</div><div className="text-sm text-secondary">{label.replace(/[A-Z]/g, letter => ` ${letter}`).trim()}</div></div>
            ))}
          </div>
        </section>
      )}

      <section className="px-4 py-12 max-w-5xl mx-auto" aria-labelledby="problem-title">
        <div className="bg-panel border border-border rounded-lg p-6 md:p-8">
          <h2 id="problem-title" className="text-xl font-semibold mb-3">Code review needs more than one perspective</h2>
          <p className="text-secondary leading-relaxed">A single pass can miss security flaws, behavioral bugs, and gaps in test coverage. SentinelCode coordinates focused reviewers, checks security patterns with Semgrep, and verifies findings before producing a concise report.</p>
        </div>
      </section>

      {/* Pipeline Diagram */}
      <section className="py-16 px-4 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold mb-8 text-center uppercase tracking-wider text-secondary">
          Pipeline
        </h2>
        <div className="bg-panel border border-border rounded-lg p-8">
          <svg role="img" aria-label="Review pipeline: Orchestrator coordinates Bug, Security, Quality, Test Coverage and Semgrep; findings pass through Verifier and Summarizer" viewBox="0 0 900 340" className="w-full h-auto">
            <defs><marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#8B949E" /></marker></defs>
            <rect x="20" y="142" width="130" height="56" rx="8" fill="#161B22" stroke="#8B5CF6" strokeWidth="2" />
            <text x="85" y="176" textAnchor="middle" fill="#E6EDF3" fontSize="14">Orchestrator</text>
            <path d="M150 170 H184 V48 H210 M184 170 V104 H210 M184 170 V160 H210 M184 170 V216 H210 M184 170 V272 H210" fill="none" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)" />
            <g fill="#161B22" stroke="#21262D"><rect x="210" y="28" width="150" height="40" rx="8"/><rect x="210" y="84" width="150" height="40" rx="8"/><rect x="210" y="140" width="150" height="40" rx="8"/><rect x="210" y="196" width="150" height="40" rx="8"/><rect x="210" y="252" width="150" height="40" rx="8"/></g>
            <g fill="#E6EDF3" fontSize="13" textAnchor="middle"><text x="285" y="53">Bug</text><text x="285" y="109">Security</text><text x="285" y="165">Quality</text><text x="285" y="221">Test Coverage</text><text x="285" y="277">Semgrep</text></g>
            <path d="M360 48 H398 V170 H430 M360 104 H398 M360 160 H398 M360 216 H398 M360 272 H398 V170" fill="none" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)" />
            <rect x="430" y="142" width="130" height="56" rx="8" fill="#161B22" stroke="#8B5CF6" strokeWidth="2"/><text x="495" y="176" textAnchor="middle" fill="#E6EDF3" fontSize="14">Verifier</text>
            <line x1="560" y1="170" x2="650" y2="170" stroke="#8B949E" strokeWidth="2" markerEnd="url(#arrowhead)"/>
            <rect x="650" y="142" width="160" height="56" rx="8" fill="#161B22" stroke="#8B5CF6" strokeWidth="2"/><text x="730" y="176" textAnchor="middle" fill="#E6EDF3" fontSize="14">Summarizer</text>

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

      {landingConfig.team.length > 0 && <section className="py-16 px-4 max-w-6xl mx-auto">
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
      </section>}

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
