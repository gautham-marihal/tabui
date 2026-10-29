import type { TrackReference } from "@livekit/components-react";
import { useMultibandTrackVolume } from "../hooks/useMultibandTrackVolume";

type CustomAudioVisualizer = {
  localMicTrack: TrackReference | undefined;
  isMute: boolean;
};
const minBarHeight = 5;
const maxBarHeight = 35;

export default function CustomAudioVisualizer({
  localMicTrack,
  isMute,
}: CustomAudioVisualizer) {
  const localMultibandVolumeFrequencies: Float32Array[] | number[][] =
    useMultibandTrackVolume(localMicTrack?.publication.audioTrack, 9);

  const summedFrequencies = localMultibandVolumeFrequencies.map(
    (bandFrequencies) => {
      const sum = bandFrequencies.reduce((a, b) => a + b, 0);
      return Math.sqrt(sum / bandFrequencies.length);
    }
  );

  return (
    <div
      style={{
        width: 90,
        height: 35,
        display: "grid",
        gridTemplateColumns: "repeat(9, 1fr)", // 9 Bars
        gridGap: 2,
        alignItems: "center",
        backgroundColor: "transparent",
        position: "absolute",
        bottom: 10,
        right: 25,
      }}
    >
      {summedFrequencies.map((localMultibandVolumeFrequencies, i) => {
        return (
          <div
            key={"frequency-" + i}
            style={{
              height: isMute
                ? 5
                : minBarHeight +
                  localMultibandVolumeFrequencies *
                    (maxBarHeight - minBarHeight),
              width: 5,
              backgroundColor: isMute ? "darkgrey" : "tomato",
              borderRadius: isMute ? 0 : 3,
            }}
          ></div>
        );
      })}
    </div>
  );
}
