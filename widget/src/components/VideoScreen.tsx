import React from "react";

import { VideoTrack } from "@livekit/components-react";

import type { TrackReference } from "@livekit/components-react";

import { MdCameraswitch, MdHighlightOff } from "react-icons/md";

const VideoScreen: React.FC<{
  track: TrackReference | undefined;
  closeVideoScreen: () => void;
  onFlipCamera?: () => void;
}> = ({ track, closeVideoScreen, onFlipCamera }) => {
  const [videoRectangle, setVideoRectangle] = React.useState({
    vTop: 0,
    vLeft: 0,
    vHeight: 0,
    vWidth: 0,
  });

  React.useLayoutEffect(() => {
    const chatBodyContainer =
      document.getElementsByClassName("rcb-chat-body-container") &&
      (document.getElementsByClassName(
        "rcb-chat-body-container"
      )[0] as HTMLElement);

    if (chatBodyContainer)
      setVideoRectangle({
        vTop: chatBodyContainer.offsetTop,
        vLeft: chatBodyContainer.offsetLeft,
        vHeight: chatBodyContainer.clientHeight,
        vWidth: chatBodyContainer.clientWidth,
      });
  }, []); // Run once on component mount

  const closeButtonClick = () => {
    closeVideoScreen();
  };

  return track ? (
    <div
      style={{
        backgroundColor: "lightyellow",
        height: videoRectangle.vHeight,
        width: videoRectangle.vWidth,
        position: "absolute",
        top: videoRectangle.vTop,
        left: videoRectangle.vLeft,
      }}
    >
      <div style={{ position: "relative", height: "100%" }}>
        <VideoTrack style={{ width: "100%" }} trackRef={track} />

        <div
          style={{
            display: "flex",
            gap: 6,
            alignItems: "center",
            position: "absolute",
            top: 0,
            right: 0,
            padding: 7,
          }}
        >
          {onFlipCamera && (
            <MdCameraswitch
              onClick={onFlipCamera}
              aria-label="Switch camera"
              style={{
                cursor: "pointer",
                fontSize: 20,
                backgroundColor: "white",
                borderRadius: "50%",
                padding: 2,
              }}
            />
          )}
          <MdHighlightOff
            onClick={closeButtonClick}
            style={{
              cursor: "pointer",
              fontSize: 20,
              backgroundColor: "white",
              borderRadius: "50%",
            }}
          />
        </div>
      </div>
    </div>
  ) : null;
};

export default VideoScreen;
