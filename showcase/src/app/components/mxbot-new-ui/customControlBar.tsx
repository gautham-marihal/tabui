import React from "react";
import { Track } from "livekit-client";
import {
  ChatIcon,
  ChatToggle,
  DisconnectButton,
  LeaveIcon,
  MediaDeviceMenu,
  StartMediaButton,
  TrackToggle,
  useLocalParticipantPermissions,
  usePersistentUserChoices,
} from "@livekit/components-react";
import { supportsScreenSharing } from "@livekit/components-core";
import ButtonUpload from "./buttonUpload";

export function CustomControlBar() {
  const showIcon = true;
  const showText = false;

  const localPermissions = useLocalParticipantPermissions();
  const browserSupportsScreenSharing = supportsScreenSharing();

  const {
    saveAudioInputEnabled,
    saveVideoInputEnabled,
    saveAudioInputDeviceId,
    saveVideoInputDeviceId,
  } = usePersistentUserChoices({ preventSave: false });

  const microphoneOnChange = (enabled: boolean, isUserInitiated: boolean) => {
    if (isUserInitiated) saveAudioInputEnabled(enabled);
  };

  const cameraOnChange = (enabled: boolean, isUserInitiated: boolean) => {
    if (isUserInitiated) saveVideoInputEnabled(enabled);
  };

  return (
    <div className="lk-control-bar" style={{ borderTop: "0px" }}>
      {/* Microphone */}
      {localPermissions?.canPublish && (
        <div className="lk-button-group">
          <TrackToggle
            source={Track.Source.Microphone}
            showIcon={showIcon}
            onChange={microphoneOnChange}
          >
            {showText && "Microphone"}
          </TrackToggle>
          <div className="lk-button-group-menu">
            <MediaDeviceMenu
              kind="audioinput"
              onActiveDeviceChange={(_, deviceId) =>
                saveAudioInputDeviceId(deviceId ?? "default")
              }
            />
          </div>
        </div>
      )}

      {/* Camera */}
      {localPermissions?.canPublish && (
        <div className="lk-button-group">
          <TrackToggle
            source={Track.Source.Camera}
            showIcon={showIcon}
            onChange={cameraOnChange}
          >
            {showText && "Camera"}
          </TrackToggle>
          <div className="lk-button-group-menu">
            <MediaDeviceMenu
              kind="videoinput"
              onActiveDeviceChange={(_, deviceId) =>
                saveVideoInputDeviceId(deviceId ?? "default")
              }
            />
          </div>
        </div>
      )}

      {/* Screen Share */}
      {localPermissions?.canPublish && browserSupportsScreenSharing && (
        <TrackToggle source={Track.Source.ScreenShare} showIcon={showIcon}>
          {showText && "Share screen"}
        </TrackToggle>
      )}

      {/* Chat */}
      {localPermissions?.canPublishData && (
        <ChatToggle>
          {showIcon && <ChatIcon />}
          {showText && "Chat"}
        </ChatToggle>
      )}

      {/* Upload Button */}
      {localPermissions?.canPublishData && <ButtonUpload />}

      {/* Leave Button */}
      <DisconnectButton>
        {showIcon && <LeaveIcon />}
        {showText && "Leave"}
      </DisconnectButton>

      {/* Start Media */}
      <StartMediaButton />
    </div>
  );
}
