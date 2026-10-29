import React from "react";
import type { StartScreenProps } from "../util/types";

const StartScreen: React.FC<StartScreenProps> = ({
  width,
  height,
  connectToAgent,
  isConnecting,
  connectionError = "",
  agents = [],
  selectedAgentKey = "",
  onAgentChange = () => undefined,
  isLoadingAgents = false,
  agentsError = "",
}) => {
  const statusText = isConnecting ? "Connecting..." : connectionError;

  return (
    <div
      style={{
        width,
        height,
        borderRadius: 10,
        backgroundColor: "#ffffff",
        display: "grid",
        placeItems: "center",
        outline: "solid lightgrey 1px",
        position: "relative",
        boxSizing: "border-box",
        padding: 18,
      }}
    >
      <div style={{ position: "absolute", top: 22, left: 18, right: 18 }}>
        <label htmlFor="weave-agent-select" style={{ display: "block", color: "#333", fontSize: 13, fontWeight: 600, marginBottom: 7 }}>
          Agent from Weave Studio
        </label>
        <select
          id="weave-agent-select"
          value={selectedAgentKey}
          onChange={(event) => onAgentChange(event.target.value)}
          disabled={isConnecting || isLoadingAgents || agents.length === 0}
          style={{ width: "100%", minHeight: 38, padding: "7px 9px", borderRadius: 7, border: "1px solid #c9c9c9", background: "white", color: "#252525", fontSize: 13 }}
        >
          {isLoadingAgents ? (
            <option value={selectedAgentKey}>Loading deployed agents…</option>
          ) : agents.map((agent) => (
            <option key={`${agent.id}::${agent.ref}`} value={`${agent.id}::${agent.ref}`}>
              {agent.name} · {agent.ref} · v{agent.version}
            </option>
          ))}
        </select>
        {agentsError && (
          <p role="status" style={{ margin: "6px 0 0", color: "#9a5a00", fontSize: 11, lineHeight: 1.35 }}>
            {agentsError}
          </p>
        )}
      </div>

      <button
        onClick={connectToAgent}
        disabled={isConnecting || (agents.length === 0 && Boolean(agentsError))}
        style={{
          width: 200,
          height: 42,
          backgroundColor: "#732b90",
          opacity: isConnecting || (agents.length === 0 && Boolean(agentsError)) ? 0.55 : 1,
          color: "white",
          border: "none",
          borderRadius: 10,
          fontSize: 16,
          fontWeight: "bolder",
          cursor: isConnecting || (agents.length === 0 && Boolean(agentsError)) ? "progress" : "pointer",
          marginTop: 25,
        }}
      >
        Connect
      </button>

      {statusText && (
        <div
          role={connectionError ? "alert" : "status"}
          style={{
            position: "absolute",
            left: "5%",
            right: "5%",
            bottom: 18,
            color: connectionError ? "#c62828" : "#732b90",
            textAlign: "center",
            fontSize: connectionError ? 12 : 16,
            lineHeight: 1.35,
            overflowWrap: "anywhere",
          }}
        >
          {statusText}
        </div>
      )}
    </div>
  );
};

export default StartScreen;
