import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

interface ModalProps {
  title: string;
  wide?: boolean;
  onClose: () => void;
  children: ReactNode;
}

export default function Modal({ title, wide, onClose, children }: ModalProps) {
  const [phase, setPhase] = useState<"entering" | "visible" | "leaving">("entering");
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    timerRef.current = setTimeout(() => setPhase("visible"), 250);
    return () => clearTimeout(timerRef.current);
  }, []);

  const startClose = useCallback(() => {
    if (phase === "leaving") return;
    setPhase("leaving");
    timerRef.current = setTimeout(onClose, 200);
  }, [onClose, phase]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") startClose();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [startClose]);

  const overlayClass =
    phase === "entering" ? "overlay entering" :
    phase === "leaving" ? "overlay leaving" :
    "overlay entering";

  return (
    <div className={overlayClass} onClick={startClose}>
      <div
        className={`modal${wide ? " wide" : ""}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="modal-close" onClick={startClose}>
            &times;
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
