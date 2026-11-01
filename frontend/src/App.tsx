import { lazy, Suspense } from "react";
import { BrowserRouter } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";

const AnimatedRoutes = lazy(() =>
  import("./components/AnimatedRoutes").then((module) => ({
    default: module.AnimatedRoutes,
  })),
);

function LoadingScreen() {
  return (
    <div className="grid min-h-screen place-items-center px-5">
      <div
        className="skeleton-glass h-48 w-full max-w-3xl rounded-[28px]"
        aria-label="Loading page"
      />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Suspense fallback={<LoadingScreen />}>
          <AnimatedRoutes />
        </Suspense>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

export default App;
