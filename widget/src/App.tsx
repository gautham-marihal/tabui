import { ChatBotProvider } from "react-chatbotify";
import { useState } from "react";
import { RoomContext } from "@livekit/components-react";

import { Room } from "livekit-client";

import "./App.scss";

import type { WidgetProps } from "./util/types";
import MMBot from "./components/MMBot";
import NewMMBot from "./components/new-ui/NewMMBot";

export function App(props: WidgetProps) {
  const [room] = useState(
    () =>
      new Room({
        // Optimize video quality for each participant's screen
        adaptiveStream: true,
        // Enable automatic audio/video quality optimization
        dynacast: true,
      })
  );

  return (
    <>
      <ChatBotProvider>
        <RoomContext.Provider value={room}>
          <MMBot {...props} room={room} />
        </RoomContext.Provider>
      </ChatBotProvider>
    </>
  );
}

export function NewApp(props: WidgetProps) {
  return <NewMMBot {...props} />;
}
