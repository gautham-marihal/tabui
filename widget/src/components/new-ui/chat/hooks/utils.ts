import * as React from "react";
import { Room } from "livekit-client";

import type {
  MessageFormatter,
  ReceivedChatMessage,
  TextStreamData,
} from "@livekit/components-react";

export const useChatMessage = (
  entry: ReceivedChatMessage,
  messageFormatter?: MessageFormatter
) => {
  const formattedMessage = React.useMemo(() => {
    return messageFormatter ? messageFormatter(entry.message) : entry.message;
  }, [entry.message, messageFormatter]);
  const hasBeenEdited = !!entry.editTimestamp;
  const time = new Date(entry.timestamp);
  const locale =
    typeof navigator !== "undefined" ? navigator.language : "en-US";

  const name =
    entry.from?.name && entry.from.name !== ""
      ? entry.from.name
      : entry.from?.identity;

  return { message: formattedMessage, hasBeenEdited, time, locale, name };
};

export function transcriptionToChatMessage(
  textStream: TextStreamData,
  room: Room
): ReceivedChatMessage {
  return {
    id: textStream.streamInfo.id,
    timestamp: textStream.streamInfo.timestamp,
    message: textStream.text,
    from:
      textStream.participantInfo.identity === room.localParticipant.identity
        ? room.localParticipant
        : Array.from(room.remoteParticipants.values()).find(
            (p) => p.identity === textStream.participantInfo.identity
          ),
  };
}
