import { useState } from "react";
import { MdChat, MdClose } from "react-icons/md";

// Local dev-mode only: mirrors the icon-toggle pattern setup-docs/TABWidget.txt expects the
// *host page* to provide when embedding via mountTABWidget - the widget itself has no built-in
// launcher. Toggles visibility only; the widget (and its LiveKit room) stays mounted underneath,
// so opening/closing never drops the call.
export default function DevHarness({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div
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
