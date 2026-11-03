import { StrictMode } from "react";
import ReactDOM from "react-dom/client";
import GuidePage from "./GuidePage.tsx";

// The dev page's guide (index.html), beside the widget's own entry (src/main.tsx).
const root = document.getElementById("tabui-guide-root");
if (root)
  ReactDOM.createRoot(root).render(
    <StrictMode>
      <GuidePage />
    </StrictMode>
  );
