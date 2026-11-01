import { lazy } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Route, Routes, useLocation } from "react-router-dom";

const Landing = lazy(() => import("../pages/Landing"));
const Dashboard = lazy(() => import("../pages/Dashboard"));
const NewReview = lazy(() => import("../pages/NewReview"));
const ReviewResult = lazy(() => import("../pages/ReviewResult"));
const History = lazy(() => import("../pages/History"));
const NotFound = lazy(() => import("../pages/NotFound"));

export function AnimatedRoutes() {
  const location = useLocation();
  const reducedMotion = useReducedMotion();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: reducedMotion ? 0 : 0.2 }}
      >
        <Routes location={location}>
          <Route path="/" element={<Landing />} />
          <Route path="/app" element={<Dashboard />} />
          <Route path="/app/new" element={<NewReview />} />
          <Route path="/app/reviews/:id" element={<ReviewResult />} />
          <Route path="/app/history" element={<History />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}
