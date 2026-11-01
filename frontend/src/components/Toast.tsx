import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CheckCircle2, XCircle, X } from "lucide-react";

type ToastType = "success" | "error" | "info";

interface ToastProps {
  message: string;
  type: ToastType;
  onClose: () => void;
}

export function Toast({ message, type, onClose }: ToastProps) {
  const reducedMotion = useReducedMotion();
  const [isVisible, setIsVisible] = useState(true);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(() => onCloseRef.current(), 300);
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  const bgColors = {
    success: "border-safe/25 text-safe",
    error: "border-critical/25 text-critical",
    info: "border-violet-300/25 text-violet-100",
  };

  const icons = {
    success: <CheckCircle2 size={20} />,
    error: <XCircle size={20} />,
    info: <CheckCircle2 size={20} />,
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          role={type === "error" ? "alert" : "status"}
          aria-live={type === "error" ? "assertive" : "polite"}
          initial={reducedMotion ? false : { opacity: 0, y: 12, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8 }}
          transition={{ duration: reducedMotion ? 0 : 0.22 }}
          className={`toast-glass fixed bottom-4 right-4 z-50 w-[min(24rem,calc(100vw-2rem))] rounded-2xl p-4 ${bgColors[type]}`}
        >
          <div className="flex items-start gap-3">
            {icons[type]}
            <p className="flex-1 text-sm text-text">{message}</p>
            <button
              aria-label="Dismiss notification"
              onClick={() => {
                setIsVisible(false);
                setTimeout(() => onCloseRef.current(), 220);
              }}
              className="rounded-lg p-1 text-secondary transition hover:bg-white/10 hover:text-white"
            >
              <X size={16} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
