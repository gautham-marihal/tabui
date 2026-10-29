import { useRemoteParticipants } from "@livekit/components-react";
import useChatAndTranscription from "@/hooks/useChatAndTranscription";
import { ChatInput } from "./chat/chat-input";
import { useState } from "react";

type Props = {
  style?: React.CSSProperties;
};

const ChatInputBox = ({ style }: Props) => {
  const participants = useRemoteParticipants();
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const isAgentAvailable = participants.some((p) => p.isAgent);
  const isInputDisabled = !isAgentAvailable || isSendingMessage;
  const { send } = useChatAndTranscription();

  const handleSendMessage = async (message: string) => {
    setIsSendingMessage(true);
    try {
      await onSendMessage?.(message);
    } finally {
      setIsSendingMessage(false);
    }
  };

  async function onSendMessage(message: string) {
    await send(message);
  }

  return (
    <div style={style}>
      <ChatInput
        onSend={handleSendMessage}
        disabled={isInputDisabled}
        style={{ width: "100%" }}
      />
    </div>
  );
};

export default ChatInputBox;
