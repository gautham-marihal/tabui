import useChatAndTranscription from "@/hooks/useChatAndTranscription";
import { Room } from "livekit-client";
import { useEffect } from "react";

interface RegisterChatHandlerProps {
  room: Room;
}

function RegisterChatHandler({ room }: RegisterChatHandlerProps) {
  const { send } = useChatAndTranscription();
  useEffect(() => {
    if (!room) return;
    room.registerTextStreamHandler(
      "city",
      async (reader: any, participantInfo: any) => {
        const info = reader.info;
        console.log(
          `Received text stream from ${participantInfo.identity}\n` +
            `  Topic: ${info.topic}\n` +
            `  Timestamp: ${info.timestamp}\n` +
            `  ID: ${info.id}\n` +
            `  Size: ${info.size}`
        );

        const text = await reader.readAll();
        const obj = JSON.parse(text);
        console.log(`Received text: ${text}`);
        console.log(`Display Massage: ${obj.chatDisplayMessage}`);
        send(obj.chatDisplayMessage, { topic: "" });
      }
    );
    return () => {
      room.unregisterTextStreamHandler("city");
    };
  }, [room]);

  return null;
}

export default RegisterChatHandler;
