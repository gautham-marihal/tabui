// import { useMessages, useTextArea } from "react-chatbotify";
import { useState } from "react";
import {
  useTracks,
  useVoiceAssistant,
  BarVisualizer,
  LayoutContextProvider,
  LiveKitRoom,
  ParticipantTile,
  RoomAudioRenderer,
  TrackLoop,
} from "@livekit/components-react";

import type { WidgetState } from "@livekit/components-react";

import { Room, Track } from "livekit-client";

import StartScreen from "../StartScreen";

import ChatInputBox from "./chatInputBox";
import ChatBox from "./chatBox";

import { CustomControlBar } from "./customControlBar";
import RegisterChatHandler from "./registerHandler";

import "../../App.scss";
import "@livekit/components-styles";

import type { WidgetProps } from "../../util/types";

export default function NewMMBot(props: WidgetProps) {
  const {
    agentId,
    livekitURL,
    authTokenAPI,
    width,
    height,
  } = props;

  const [connectedToAgent, setConnectedToAgent] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [room] = useState(new Room());

  const [token, setToken] = useState<string | undefined>(undefined);

  const [widgetState, setWidgetState] = useState<WidgetState>({
    showChat: false,
    unreadMessages: 0,
  });

  const connectToAgent = async (event: React.SyntheticEvent) => {
    event.preventDefault(); // Don't refresh the page

    if (isConnecting) return;

    setIsConnecting(true);

    try {
      // TODO: Need to make API calling secure with access tokens
      const { accessToken } = await fetch(
        `${authTokenAPI}/api/token?agentId=${agentId}`
      ).then((res) => res.json());

      setToken(accessToken);

      setConnectedToAgent(true);

      setIsConnecting(false);
    } catch (error) {
      setIsConnecting(false);
      console.error("Error:", error);
    }
  };

  const disconnectFromAgent = async () => {
    setConnectedToAgent(false);
  };

  return (
    <div>
      {connectedToAgent ? (
        <div
          data-lk-theme="default"
          style={{
            width: width,
            height: height,
            borderRadius: 10,
            position: "relative",
            backgroundColor: "white",
          }}
        >
          <LiveKitRoom
            room={room}
            video={false}
            audio={true}
            token={token}
            connect={connectedToAgent}
            serverUrl={livekitURL}
            onMediaDeviceFailure={(e) => {
              console.error(e);
              alert(
                "Error acquiring camera or microphone permissions. Please make sure you grant the necessary permissions in your browser and reload the tab"
              );
            }}
            onDisconnected={() => disconnectFromAgent()}
          >
            <LayoutContextProvider onWidgetChange={setWidgetState}>
              <RegisterChatHandler room={room} />

              {!widgetState.showChat && <SimpleVoiceAssistant />}

              <div style={{}}>
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

              <Stage />

              <RoomAudioRenderer />
            </LayoutContextProvider>
          </LiveKitRoom>
        </div>
      ) : (
        <StartScreen
          width={width}
          height={height}
          connectToAgent={connectToAgent}
          isConnecting={isConnecting}
        />
      )}
    </div>
  );
}

function SimpleVoiceAssistant() {
  const { state, audioTrack } = useVoiceAssistant();
  return (
    <BarVisualizer
      state={state}
      barCount={7}
      options={{ minHeight: 5 }}
      trackRef={audioTrack}
      style={{ width: "100%", gap: "0.5rem" }}
    />
  );
}

function Stage() {
  const cameraTracks = useTracks([Track.Source.Camera]);
  const screenShareTrackRef = useTracks([Track.Source.ScreenShare])[0];

  return (
    <div style={{}}>
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
