"use client";

import React from "react";
import Image from "next/image";

import type { TABWidgetProps } from "../../lib/types";

declare global {
  interface Window {
    mountTABWidget?: (containerId: string, properties: any) => void;
    unmountTABWidget?: (containerId: string) => void;
  }
}

const regex = /^S\d{7}D$/i;
const replaceText = "S*******D";

export default function TABWidget({
  agentId,
  livekitURL,
  chatTextDisplayFilterEnabled,
}: TABWidgetProps) {
  const [showTABWidget, setShowTABWidget] = React.useState(false);

  React.useEffect(() => {
    const properties = {
      agentId: agentId || "nimbus-care",
      livekitURL: livekitURL || "",
      // Empty means same-origin Showcase API endpoints (/api/bots and /api/token).
      authTokenAPI: "",
      width: 340,
      height: 495,
      chatTextDisplayFilter: {
        enabled: chatTextDisplayFilterEnabled,
        test: (text: string) => {
          return regex.test(text);
        },
        replace: (text: string) => {
          return text.replace(regex, replaceText);
        },
      },
    };

    if (window.mountTABWidget) {
      window.mountTABWidget("demo-widget-container", properties);
    } else {
      console.error("ERROR: Could not mount TAB Widget");
    }

    return () => {
      if (window.unmountTABWidget) {
        window.unmountTABWidget("demo-widget-container");
      }
    };
  }, []);

  const toggleTABWidget = () => {
    setShowTABWidget((prevState) => !prevState);
  };

  return (
    <div>
      <div
        id="demo-widget-container"
        style={{
          zIndex: 100,
          visibility: showTABWidget ? "visible" : "hidden",
        }}
      >
        &nbsp;
      </div>

      <div
        id="tab-icon"
        onClick={toggleTABWidget}
        style={{
          backgroundColor: "#732b90",
          borderRadius: "50%",
          padding: 9,
          cursor: "pointer",
          position: "fixed",
          right: 20,
          bottom: 20,
          display: "grid",
          placeItems: "center",
        }}
      >
        <Image
          src="/images/chat-icon.webp"
          alt="Launch Tetherfi MX Bot"
          height={30}
          width={30}
        />
      </div>
    </div>
  );
}
