import ChatBot, { useMessages, useTextArea } from "react-chatbotify";
import type { Params, RcbToggleVoiceEvent, RcbUserSubmitTextEvent } from "react-chatbotify";
import { useState, useEffect, useRef, useMemo } from "react";
import {
  useChat,
  useTracks,
  useLocalParticipant,
  useTrackTranscription,
} from "@livekit/components-react";

import {
  RoomEvent,
  RemoteTrack,
  TrackPublication,
  Participant,
  LocalParticipant,
  Room,
  Track,
} from "livekit-client";

import StartScreen from "./StartScreen";
import VideoScreen from "./VideoScreen";
import CustomAudioVisualizer from "./CustomAudioVisualizer";
import composeBotProps from "../util/composeBotProps";

import botAvatar from "../assets/botAvatar.png";

import "../App.scss";

import type { SelectableAgent, WidgetProps } from "../util/types";

// App always hands MMBot the LiveKit room it provides to the tree
export default function MMBot(props: WidgetProps & { room: Room }) {
  const {
    agentId,
    agentRef = "development",
    livekitURL,
    authTokenAPI,
    width,
    height,
    room,
    chatTextDisplayFilter,
  } = props;

  const [showVideoPane, setShowVideoPane] = useState(false);
  const [showScreenSharePane, setShowScreenSharePane] = useState(false);
  const [connectedToAgent, setConnectedToAgent] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const fallbackAgent = useMemo<SelectableAgent>(() => ({
    id: agentId || "nimbus-care",
    name: agentId || "nimbus-care",
    ref: agentRef || "development",
    version: "configured fallback",
  }), [agentId, agentRef]);
  const [availableAgents, setAvailableAgents] = useState<SelectableAgent[]>([fallbackAgent]);
  const [selectedAgentKey, setSelectedAgentKey] = useState(`${fallbackAgent.id}::${fallbackAgent.ref}`);
  const [isLoadingAgents, setIsLoadingAgents] = useState(true);
  const [agentsError, setAgentsError] = useState("");
  const connectionCleanupRef = useRef<(() => void) | null>(null);
  // Rear camera by default - callers showing a meter or breaker box need it far more often than
  // a selfie-style front camera.
  const [cameraFacingMode, setCameraFacingMode] = useState<"user" | "environment">("environment");

  const [isMute, setIsMute] = useState(false);

  const tracks = useTracks();
  const localTracks = tracks.filter(
    ({ participant }) => participant instanceof LocalParticipant
  );
  const localMicTrack = localTracks.find(
    ({ source }) => source === Track.Source.Microphone
  );

  const localCameraTrack = localTracks.find(
    ({ source }) => source === Track.Source.Camera
  );

  const localScreenShareTrack = localTracks.find(
    ({ source }) => source === Track.Source.ScreenShare
  );

  const { send } = useChat();

  const { streamMessage, endStreamMessage, injectMessage } = useMessages();

  const localParticipant = useLocalParticipant();

  const localMessages = useTrackTranscription({
    publication: localParticipant.microphoneTrack,
    source: Track.Source.Microphone,
    participant: localParticipant.localParticipant,
  });

  const { setTextAreaValue } = useTextArea();

  useEffect(() => {
    let cancelled = false;
    const apiBase = (authTokenAPI || "").replace(/\/+$/, "");

    const loadAgents = async () => {
      setIsLoadingAgents(true);
      setAgentsError("");
      try {
        const response = await fetch(`${apiBase}/api/bots`, { cache: "no-store" });
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(payload?.error || `Agent list request failed (${response.status}).`);
        }
        if (!Array.isArray(payload?.agents)) {
          throw new Error(payload?.error || "The bot API did not return an agents array.");
        }
        const agents = (payload.agents as SelectableAgent[]).filter(
          (item) => item && typeof item.id === "string" && typeof item.ref === "string"
        );
        if (agents.length === 0) {
          throw new Error(payload?.error || "No deployed agents were returned by GET /bots.");
        }
        if (cancelled) return;
        setAvailableAgents(agents);
        const preferred = agents.find((item) => item.id === agentId && item.ref === agentRef)
          || agents.find((item) => item.id === agentId)
          || agents.find((item) => item.id === "nimbus-care" && item.ref === "development")
          || agents[0];
        setSelectedAgentKey(`${preferred.id}::${preferred.ref}`);
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Unable to load agents from Weave Studio.";
        setAgentsError(`${message} Using the configured fallback agent.`);
        setAvailableAgents([fallbackAgent]);
        setSelectedAgentKey(`${fallbackAgent.id}::${fallbackAgent.ref}`);
        console.error("Failed to load agents from Weave Studio:", error);
      } finally {
        if (!cancelled) setIsLoadingAgents(false);
      }
    };

    void loadAgents();
    return () => { cancelled = true; };
  }, [authTokenAPI, agentId, agentRef, fallbackAgent]);

  useEffect(() => {
    // Add event listners on component mount
    window.addEventListener("rcb-toggle-voice", handleVoiceToggle);
    window.addEventListener("rcb-user-submit-text", handleTextInput);

    return () => {
      // Remove event listners on component unmount
      window.removeEventListener("rcb-toggle-voice", handleVoiceToggle);
      window.removeEventListener("rcb-user-submit-text", handleTextInput);
    };
  }, []); //Empty dependency array means this useEffect runs only once

  useEffect(() => {
    const s = localMessages.segments.at(-1);
    if (s?.final) {
      injectMessage(`${s.text}`, "user");
    }
  }, [localMessages.segments]);

  useEffect(() => {
    // The browser's own "Stop sharing" bar can end the track without going through our button;
    // keep the pane/button state in sync either way.
    if (!localScreenShareTrack && showScreenSharePane) {
      setShowScreenSharePane(false);
    }
  }, [localScreenShareTrack, showScreenSharePane]);

  const handleVoiceToggle = (event: RcbToggleVoiceEvent) => {
    // Event to toggle audio input. i.e., to mute and unmute
    console.info("Audio Muted? ", event.data.currState);

    setIsMute(event.data.currState);

    room.localParticipant.setMicrophoneEnabled(!event.data.currState);
  };

  const handleTextInput = (event: RcbUserSubmitTextEvent) => {
    const text = event.data.inputText;

    send(text);

    // Process any custom display text logic
    if (chatTextDisplayFilter?.enabled && chatTextDisplayFilter.test(text)) {
      event.preventDefault();

      injectMessage(chatTextDisplayFilter.replace(text), "user");
      setTextAreaValue("");
    }
  };

  const handleUpload = async (params: Params) => {
    const files = params.files ?? [];
    // handle files logic here
    const file = files[0];
    if (!file) return;
    const info = await room.localParticipant.sendFile(file, {
      mimeType: file.type,
      topic: "image-upload",
    });
    console.log("Files uploaded:", files);
    console.log(`Files sent with stream ID: ${info.id}`);
  };

  const connectToAgent = async (event: React.SyntheticEvent) => {
    event.preventDefault();
    if (isConnecting) return;

    setIsConnecting(true);
    setConnectionError("");

    let joinTimeout: number | undefined;
    let agentJoined = false;

    const clearJoinTimeout = () => {
      if (joinTimeout) {
        window.clearTimeout(joinTimeout);
        joinTimeout = undefined;
      }
    };

    // Clear leftovers from a previous failed attempt before registering new handlers.
    connectionCleanupRef.current?.();
    connectionCleanupRef.current = null;

    try {
      const tokenApiBase = (authTokenAPI || "").replace(/\/+$/, "");
      const selectedAgent = availableAgents.find(
        (item) => `${item.id}::${item.ref}` === selectedAgentKey
      ) || fallbackAgent;
      const tokenQuery = new URLSearchParams({
        agentId: selectedAgent.id,
        botId: selectedAgent.id,
        ref: selectedAgent.ref,
      });
      const tokenEndpoint = `${tokenApiBase}/api/token?${tokenQuery}`;
      const tokenResponse = await fetch(tokenEndpoint);
      const tokenPayload = await tokenResponse.json().catch(() => null);

      if (!tokenResponse.ok) {
        throw new Error(
          tokenPayload?.error || `Token API request failed (${tokenResponse.status}).`
        );
      }

      const accessToken = tokenPayload?.accessToken as string | undefined;
      const tokenLivekitURL = tokenPayload?.livekitURL as string | undefined;
      const connectionURL = tokenLivekitURL || livekitURL;

      if (!accessToken) {
        throw new Error("The token API response did not contain an accessToken.");
      }
      if (!connectionURL) {
        throw new Error(
          "The LiveKit URL is missing. Set LIVEKIT_URL in showcase/.env.local."
        );
      }

      const onParticipantConnected = (participant: Participant) => {
        if (participant.identity === room.localParticipant.identity) return;
        agentJoined = true;
        clearJoinTimeout();
        setConnectedToAgent(true);
        setIsConnecting(false);
        setConnectionError("");
      };

      const onTrackSubscribed = (
        track: RemoteTrack,
        _publication: TrackPublication,
        participant: Participant
      ) => {
        if (participant.identity !== room.localParticipant.identity) {
          setConnectedToAgent(true);
          setIsConnecting(false);
        }

        if (track.kind === "audio") {
          console.log(`Subscribed to audio track from ${participant.identity}`);
          const audioElement = track.attach();
          audioElement.autoplay = true;
          audioElement.controls = false;
          audioElement.style.display = "none";
          document.body.appendChild(audioElement);
        }
      };

      const cleanupListeners = () => {
        clearJoinTimeout();
        room.off(RoomEvent.ParticipantConnected, onParticipantConnected);
        room.off(RoomEvent.TrackSubscribed, onTrackSubscribed);
        room.unregisterTextStreamHandler("lk.transcription");
      };

      // Register listeners BEFORE room.connect so early participant/track events are not missed.
      room.on(RoomEvent.ParticipantConnected, onParticipantConnected);
      room.on(RoomEvent.TrackSubscribed, onTrackSubscribed);
      connectionCleanupRef.current = cleanupListeners;

      room.registerTextStreamHandler(
        "lk.transcription",
        async (reader, participantInfo) => {
          let text = "";
          for await (const chunk of reader) {
            text += chunk;
            if (participantInfo.identity !== room.localParticipant.identity) {
              await streamMessage(text);
            }
          }
          if (participantInfo.identity !== room.localParticipant.identity) {
            await endStreamMessage();
          }
        }
      );

      await room.connect(connectionURL, accessToken);
      await room.localParticipant.setMicrophoneEnabled(true);

      // Some agents join after the user's LiveKit connection has completed.
      // If no remote participant arrives, show a useful error instead of spinning forever.
      if (!agentJoined) {
        joinTimeout = window.setTimeout(() => {
          if (agentJoined) return;
          connectionCleanupRef.current?.();
          connectionCleanupRef.current = null;
          setConnectedToAgent(false);
          setIsConnecting(false);
          setConnectionError(
            "Connected to LiveKit, but no agent joined within 25 seconds. Check that agent-builder-runtime is running and that the bot metadata is correct."
          );
          void room.disconnect().catch((disconnectError: unknown) => {
            console.error("Failed to disconnect after agent timeout:", disconnectError);
          });
        }, 25000);
      }
    } catch (error) {
      clearJoinTimeout();
      connectionCleanupRef.current?.();
      connectionCleanupRef.current = null;
      setIsConnecting(false);
      setConnectedToAgent(false);
      setConnectionError(
        error instanceof Error ? error.message : "Unable to connect to the agent."
      );
      console.error("Failed to connect to the agent:", error);
      try {
        await room.disconnect();
      } catch {
        // The room may not have connected; there is nothing further to clean up.
      }
    }
  };

  const disconnectFromAgent = async () => {
    setShowVideoPane(false);
    setShowScreenSharePane(false);
    connectionCleanupRef.current?.();
    connectionCleanupRef.current = null;
    await room.disconnect();
    setConnectedToAgent(false);
    setIsConnecting(false);
    setConnectionError("");
  };

  const showVideoScreen = async () => {
    await room.localParticipant.setCameraEnabled(true, {
      facingMode: cameraFacingMode,
    });

    setShowVideoPane((prevState) => !prevState);
  };

  const closeVideoScreen = async () => {
    setShowVideoPane(false);
  };

  const flipCamera = async () => {
    const nextMode = cameraFacingMode === "environment" ? "user" : "environment";
    setCameraFacingMode(nextMode);

    // setCameraEnabled(true, ...) is a no-op on an already-published track (it just unmutes and
    // ignores the new constraints) - restartTrack is what actually re-acquires the camera.
    const publication = room.localParticipant.getTrackPublication(Track.Source.Camera);
    if (publication?.track) {
      await publication.track.restartTrack({ facingMode: nextMode });
    } else {
      await room.localParticipant.setCameraEnabled(true, { facingMode: nextMode });
    }
  };

  const showScreenShareScreen = async () => {
    if (showScreenSharePane) {
      await room.localParticipant.setScreenShareEnabled(false);
      setShowScreenSharePane(false);
      return;
    }

    try {
      await room.localParticipant.setScreenShareEnabled(true);
      setShowScreenSharePane(true);
    } catch (error) {
      // The user cancelled the browser's own share picker - nothing to recover from.
      console.error("Screen share was not started:", error);
    }
  };

  const closeScreenShareScreen = async () => {
    await room.localParticipant.setScreenShareEnabled(false);
    setShowScreenSharePane(false);
  };

  const { botFlow, botSettings, botStyles } = composeBotProps(
    handleUpload,
    width,
    height,
    botAvatar,
    disconnectFromAgent,
    showVideoScreen,
    showVideoPane,
    showScreenShareScreen,
    showScreenSharePane
  );

  return (
    <div>
      {connectedToAgent ? (
        <div
          style={{
            width: width,
            height: height,
            borderRadius: 10,
            position: "relative",
          }}
        >
          <ChatBot settings={botSettings} flow={botFlow} styles={botStyles} />

          {showVideoPane && (
            <VideoScreen
              track={localCameraTrack}
              closeVideoScreen={closeVideoScreen}
              onFlipCamera={flipCamera}
            />
          )}

          {showScreenSharePane && (
            <VideoScreen
              track={localScreenShareTrack}
              closeVideoScreen={closeScreenShareScreen}
            />
          )}

          <CustomAudioVisualizer
            localMicTrack={localMicTrack}
            isMute={isMute}
          />
        </div>
      ) : (
        <StartScreen
          width={width}
          height={height}
          connectToAgent={connectToAgent}
          isConnecting={isConnecting}
          connectionError={connectionError}
          agents={availableAgents}
          selectedAgentKey={selectedAgentKey}
          onAgentChange={setSelectedAgentKey}
          isLoadingAgents={isLoadingAgents}
          agentsError={agentsError}
        />
      )}
    </div>
  );
}
