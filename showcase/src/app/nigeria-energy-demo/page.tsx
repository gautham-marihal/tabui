"use client";

import React, { useEffect, useState } from "react";
import {
  LiveKitRoom,
  setLogLevel,
  RoomAudioRenderer,
  ControlBar,
  LayoutContextProvider,
  WidgetState,
  BarVisualizer,
  useVoiceAssistant,
  ParticipantTile,
  useTracks,
  TrackLoop,
} from "@livekit/components-react";

import "react-tabs/style/react-tabs.css";
import styles from "./page.module.scss";
import ChatInputBox from "../components/mxbot-new-ui/chatInputBox";
import ButtonUpload from "../components/mxbot-new-ui/buttonUpload";
import ChatBox from "../components/mxbot-new-ui/chatBox";
import { Room, Track } from "livekit-client";
import { CustomControlBar } from "../components/mxbot-new-ui/customControlBar";
import RegisterChatHandler from "../components/mxbot-new-ui/registerHandler";

// Ada (NigeriaEnergyBot) demo page. Same mxbot-new-ui chat UI as sc-bank-new-ui, but wired to
// the standalone AuthTokenAPI service (../../Demo/AuthTokenAPI) instead of this app's own
// per-bot NEXT_PUBLIC_<AGENTID>_LIVEKIT_URL env var scheme - Ada shares one LiveKit server with
// explicit agent-name dispatch (same server SIP already runs on), not a dedicated project.

function SimpleVoiceAssistant() {
  const { state, audioTrack } = useVoiceAssistant();
  return (
    <BarVisualizer
      state={state}
      barCount={7}
      options={{ minHeight: 5 }}
      trackRef={audioTrack}
      style={{ width: "100%", height: "550px", gap: "0.5rem" }}
    />
  );
}

export default function NigeriaEnergyDemo() {
  setLogLevel("debug", { liveKitClientLogLevel: "info" });
  const [widgetState, setWidgetState] = useState<WidgetState>({
    showChat: false,
    unreadMessages: 0,
  });

  const [shouldConnect, setShouldConnect] = useState(false);
  const [token, setToken] = useState<string | undefined>(undefined);
  const [room] = useState(new Room());

  useEffect(() => {
    const getToken = async () => {
      try {
        const { accessToken } = await fetch(
          `${process.env.NEXT_PUBLIC_LK_TOKEN_ENDPOINT}/api/token?agentId=nigeria-energy-bot`
        ).then((res) => res.json());
        setToken(accessToken);
      } catch (err) {
        console.error("Error fetching token:", err);
      }
    };

    getToken();
  }, []);

  return (
    <div className={styles.page}>
      <div data-lk-theme="default">
        <LiveKitRoom
          room={room}
          video={false}
          audio={true}
          token={token}
          connect={shouldConnect}
          serverUrl={process.env.NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL}
          onMediaDeviceFailure={(e) => {
            console.error(e);
            alert(
              "Error acquiring camera or microphone permissions. Please make sure you grant the necessary permissions in your browser and reload the tab"
            );
          }}
          onDisconnected={() => setShouldConnect(false)}
        >
          <div>
            {shouldConnect ? (
              <LayoutContextProvider onWidgetChange={setWidgetState}>
                <RegisterChatHandler room={room} />
                {!widgetState.showChat && <SimpleVoiceAssistant />}
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    position: "fixed",
                    bottom: 0,
                    left: "50%",
                    transform: "translateX(-50%)",
                    justifyContent: "center",
                    alignItems: "center",
                    zIndex: 50,
                    padding: "35px 0px",
                    width: "100%",
                    backgroundColor: "rgba(17, 17, 17)",
                  }}
                >
                  {widgetState.showChat && (
                    <ChatInputBox style={{ width: "50%" }} />
                  )}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <CustomControlBar />
                  </div>
                </div>
                <ChatBox {...widgetState} />
              </LayoutContextProvider>
            ) : (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  height: "100vh",
                  alignItems: "center",
                  gap: "12px",
                }}
              >
                <p>Chat live with Ada, BrightGrid Electricity&apos;s voice AI agent</p>
                <button
                  className="lk-button"
                  style={{
                    padding: "10px 100px",
                    borderRadius: "20px",
                    backgroundColor: "#19AAC7",
                  }}
                  onClick={() => setShouldConnect(true)}
                >
                  START CALL
                </button>
              </div>
            )}
          </div>
          {shouldConnect && <Stage />}
          <RoomAudioRenderer />
        </LiveKitRoom>
      </div>
    </div>
  );
}

function Stage() {
  const cameraTracks = useTracks([Track.Source.Camera]);
  const screenShareTrackRef = useTracks([Track.Source.ScreenShare])[0];

  return (
    <div
      style={{
        position: "fixed",
        display: "flex",
        width: "20%",
        height: "20%",
        bottom: 20,
        right: 20,
        zIndex: 90,
      }}
    >
      {screenShareTrackRef && (
        <ParticipantTile trackRef={screenShareTrackRef} />
      )}
      {cameraTracks && (
        <TrackLoop tracks={cameraTracks}>
          <ParticipantTile />
        </TrackLoop>
      )}
    </div>
  );
}
