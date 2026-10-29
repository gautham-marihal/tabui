import { StrictMode } from "react";
import ReactDOM from "react-dom/client";

import type { WidgetProps } from "./util/types";

import { App } from "./App.tsx";
import DevHarness from "./DevHarness.tsx";

import "./index.scss";

// the element a widget is mounted in, keeping its React root so the widget can be unmounted later
type RootHost = HTMLElement & { __root?: ReactDOM.Root };

declare global {
  interface Window {
    mountTABWidget: (containerId: string, props?: WidgetProps) => void;
    unmountTABWidget: (containerId: string) => void;
    mountNewTABWidget: (containerId: string, props?: WidgetProps) => void;
    unmountNewTABWidget: (containerId: string) => void;
  }
}

if (import.meta.env.VITE_ENVIRONMENT === "local") {
  // Code for local testing during development

  const regex = /^S\d{7}D$/i;
  const replaceText = "S*******D";

  ReactDOM.createRoot(
    document.getElementById("tabui-development-app-root")!
  ).render(
    <StrictMode>
      <DevHarness>
        <App
          agentId={import.meta.env.VITE_AGENT_ID || "nimbus-care"}
          agentRef={import.meta.env.VITE_AGENT_REF || "development"}
          livekitURL={import.meta.env.VITE_LIVEKIT_URL}
          authTokenAPI={import.meta.env.VITE_LIVEKIT_TOKEN_API}
          width={340}
          height={495}
          chatTextDisplayFilter={{
            enabled: true,
            test: (text) => {
              return regex.test(text);
            },
            replace: (text) => {
              return text.replace(regex, replaceText);
            },
          }}
        />
      </DevHarness>
    </StrictMode>
  );
} else {
  // Code that runs in "widget" mode aka prod build
  window.mountTABWidget = (containerId: string, props?: WidgetProps) => {
    const container = document.getElementById(containerId);

    if (container) {
      const root = ReactDOM.createRoot(container);

      if (
        props &&
        props.width &&
        props.height &&
        props.agentId
      ) {
        // The token API returns the actual LiveKit URL, so the host page need not
        // duplicate or expose it in widget initialization props.
        root.render(<App {...props} livekitURL={props.livekitURL || ""} authTokenAPI={props.authTokenAPI ?? ""} />);
      } else {
        console.error("Missing required Widget Properties.");
      }

      (container as RootHost).__root = root; // store root for unmounting later
    }
  };

  window.unmountTABWidget = (containerId: string) => {
    const container = document.getElementById(containerId);

    const root = (container as RootHost | null)?.__root;

    if (root) {
      root.unmount();
    }
  };

  window.mountNewTABWidget = (containerId: string, props?: WidgetProps) => {
    const container = document.getElementById(containerId);

    if (container) {
      const root = ReactDOM.createRoot(container);

      if (
        props &&
        props.width &&
        props.height &&
        props.agentId
      ) {
        // The token API returns the actual LiveKit URL, so the host page need not
        // duplicate or expose it in widget initialization props.
        root.render(<App {...props} livekitURL={props.livekitURL || ""} authTokenAPI={props.authTokenAPI ?? ""} />);
      } else {
        console.error("Missing required Widget Properties.");
      }

      (container as RootHost).__root = root; // store root for unmounting later
    }
  };

  window.unmountNewTABWidget = (containerId: string) => {
    const container = document.getElementById(containerId);

    const root = (container as RootHost | null)?.__root;

    if (root) {
      root.unmount();
    }
  };
}
