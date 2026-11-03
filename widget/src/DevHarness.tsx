import { useEffect, useRef, useState } from "react";
import { MdChat, MdClose } from "react-icons/md";

// Local dev-mode only: mirrors the icon-toggle pattern setup-docs/TABWidget.txt expects the
// *host page* to provide when embedding via mountTABWidget - the widget itself has no built-in
// launcher. Toggles visibility only; the widget (and its LiveKit room) stays mounted underneath,
// so opening/closing never drops the call.
export default function DevHarness({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  // the guide page's "Open the chat" buttons
  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener("tab-open-chat", show);
    return () => window.removeEventListener("tab-open-chat", show);
  }, []);
  // the panel fades in as it opens (not for people who ask for less motion); opacity only, because a transform would move
  // anything fixed inside the widget. Closing stays instant, so the call's controls never linger.
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = panel.current;
    if (!open || !el?.animate || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    el.animate(
      [{ opacity: 0 }, { opacity: 1 }],
      { duration: 220, easing: "cubic-bezier(0.16, 1, 0.3, 1)" },
    );
  }, [open]);

  return (
    <>
      <div
        ref={panel}
        style={{
          display: open ? "block" : "none",
          position: "fixed",
          bottom: 90,
          right: 20,
          zIndex: 100,
        }}
      >
        {children}
      </div>

      <button
        onClick={() => setOpen((prev) => !prev)}
        aria-label={open ? "Close chat" : "Open chat"}
        style={{
          position: "fixed",
          bottom: 20,
          right: 20,
          zIndex: 101,
          width: 56,
          height: 56,
          borderRadius: "50%",
          border: "none",
          cursor: "pointer",
          backgroundColor: "#732b90",
          display: "grid",
          placeItems: "center",
          boxShadow: "0 2px 10px rgba(0, 0, 0, 0.3)",
        }}
      >
        {open ? (
          <MdClose size={26} color="white" />
        ) : (
          <MdChat size={26} color="white" />
        )}
      </button>
    </>
  );
}
