import { Link } from "react-router-dom";
import { Home } from "lucide-react";
import { GlassButton } from "../components/GlassButton";

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center p-5">
      <div className="glass-panel w-full max-w-lg rounded-[28px] p-9 text-center sm:p-12">
        <div className="mx-auto mb-5 grid h-16 w-16 place-items-center rounded-2xl border border-violet-300/15 bg-violet-400/10 text-violet-100">
          <Home size={25} />
        </div>
        <p className="mb-2 font-mono text-sm text-violet-200">404</p>
        <h1 className="text-3xl font-semibold tracking-tight">
          This page wandered off.
        </h1>
        <p className="mx-auto mb-7 mt-3 max-w-sm text-sm leading-relaxed text-secondary">
          The address may have changed, or the page may not exist. Return to the
          home page to continue.
        </p>
        <Link to="/">
          <GlassButton tone="primary">Back to home</GlassButton>
        </Link>
      </div>
    </div>
  );
}
