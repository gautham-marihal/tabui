import * as React from "react";
import type {
  MessageFormatter,
  ReceivedChatMessage,
} from "@livekit/components-react";
// import { cn } from '@/lib/utils';
import { useChatMessage } from "./hooks/utils";

export interface ChatEntryProps extends React.HTMLAttributes<HTMLLIElement> {
  /** The chat massage object to display. */
  entry: ReceivedChatMessage;
  /** Hide sender name. Useful when displaying multiple consecutive chat messages from the same person. */
  hideName?: boolean;
  /** Hide message timestamp. */
  hideTimestamp?: boolean;
  /** An optional formatter for the message body. */
  messageFormatter?: MessageFormatter;
}

export const ChatEntry = ({
  entry,
  messageFormatter,
  hideName,
  hideTimestamp,
  className,
  ...props
}: ChatEntryProps) => {
  const { message, hasBeenEdited, time, locale, name } = useChatMessage(
    entry,
    messageFormatter
  );

  const isUser = entry.from?.isLocal ?? false;
  const messageOrigin = isUser ? "remote" : "local";

  return (
    <li
      data-lk-message-origin={messageOrigin}
      title={time.toLocaleTimeString(locale, { timeStyle: "full" })}
      {...props}
    >
      {(!hideTimestamp || !hideName || hasBeenEdited) && (
        <span>
          {!hideName && <strong className="mt-2">{name}</strong>}

          {!hideTimestamp && (
            <span>
              {hasBeenEdited && "*"}
              {time.toLocaleTimeString(locale, { timeStyle: "short" })}
            </span>
          )}
        </span>
      )}

      <span
        style={{
          maxWidth: "80%",
          borderRadius: "20px",
          padding: "0.5rem",
        }}
      >
        {message}
      </span>
    </li>
  );
};
