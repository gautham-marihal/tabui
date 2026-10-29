import { ChatEntry } from "@livekit/components-react";
import type {
  ReceivedChatMessage,
  WidgetState,
} from "@livekit/components-react";
import React from "react";
import useChatAndTranscription from "./chat/hooks/useChatAndTranscription";
import { ChatMessageView } from "./chat/chat-message-view";

const ChatBox: React.FC<WidgetState> = (widgetState) => {
  const { messages } = useChatAndTranscription();

  return (
    <div
      style={{
        display: widgetState.showChat ? "grid" : "none",
      }}
    >
      <ChatMessageView
        style={{
          marginLeft: "auto",
          marginRight: "auto",
          minHeight: "100svh",
          width: "100%",
          maxWidth: "42rem",
          paddingLeft: "0.75rem",
          paddingRight: "0.75rem",
          paddingTop: "8rem",
          paddingBottom: "10rem",
          transition: "opacity 300ms ease-out, transform 300ms ease-out",
          transform: "translateY(0)",
          opacity: 1,
          transitionDelay: "200ms",
        }}
      >
        <div style={{ whiteSpace: "pre-wrap" }}>
          {messages.map((message: ReceivedChatMessage, index: number) => (
            <ChatEntry
              style={{ marginTop: index === 0 ? 0 : "12px" }}
              hideName
              key={message.id}
              entry={message}
            />
          ))}
        </div>
      </ChatMessageView>
    </div>
  );
};

export default ChatBox;
