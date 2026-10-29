import { Button } from "react-chatbotify";
import type { Params } from "react-chatbotify";
import {
  MdClear,
  MdVideocam,
  MdVideocamOff,
  MdScreenShare,
  MdStopScreenShare,
} from "react-icons/md";

export default function composeBotProps(
  handleUpload: (params: Params) => void,
  width: number,
  height: number,
  botAvatar: string,
  disconnectFromAgent: () => void,
  showVideoScreen: () => void,
  showVideoPane: boolean,
  showScreenShareScreen: () => void,
  showScreenSharePane: boolean
) {
  const botFlow = {
    start: {
      message: "",
      path: "start",
      file: (params: Params) => handleUpload(params),
    },
  };

  const botStyles = {
    notificationIconStyle: { fill: "yellow" },
    chatWindowStyle: { width: width, height: height },
  };

  const botSettings = {
    general: {
      embedded: true,
      primaryColor: "#4682B4",
      secondaryColor: "#732b90",
    },
    emoji: {
      disabled: true,
    },
    fileAttachment: {
      disabled: false,
    },
    voice: {
      disabled: false,
      defaultToggledOn: true,
      sendAsAudio: true, // Don't transalte to text before sending
    },
    chatWindow: {
      showMessagePrompt: false,
      showTypingIndicator: false,
    },
    chatInput: {
      disabled: false,
      showCharacterCount: true,
      characterLimit: 500,
    },
    event: {
      rcbToggleVoice: true,
      rcbUserSubmitText: true,
      rcbUserUploadFile: true,
    },
    chatHistory: {
      disabled: true,
    },
    header: {
      title: "Tetherfi Assist Bot",
      showAvatar: true,
      avatar: botAvatar,
      buttons: [
        <button
          onClick={disconnectFromAgent}
          style={{
            cursor: "pointer",
            border: "none",
            backgroundColor: "transparent",
            color: "white",
            fontSize: 25,
            display: "grid",
            placeItems: "center",
          }}
        >
          <MdClear />
        </button>,
      ],
    },
    footer: {
      text: "",
      buttons: [
        Button.FILE_ATTACHMENT_BUTTON,
        <span
          onClick={showVideoScreen}
          className="rcb-attach-button-disabled"
          style={{
            cursor: "pointer",
            border: "none",
            backgroundColor: "transparent",
            color: showVideoPane ? "red" : "#aaa",
            fontSize: 24,
            padding: "0px 10px",
            display: "grid",
            placeItems: "center",
            opacity: showVideoPane ? 1 : 0.5,
          }}
        >
          {showVideoPane ? <MdVideocam /> : <MdVideocamOff />}
        </span>,
        <span
          onClick={showScreenShareScreen}
          className="rcb-attach-button-disabled"
          style={{
            cursor: "pointer",
            border: "none",
            backgroundColor: "transparent",
            color: showScreenSharePane ? "red" : "#aaa",
            fontSize: 24,
            padding: "0px 10px",
            display: "grid",
            placeItems: "center",
            opacity: showScreenSharePane ? 1 : 0.5,
          }}
        >
          {showScreenSharePane ? <MdStopScreenShare /> : <MdScreenShare />}
        </span>,
      ],
    },
    notification: { disabled: true },
  };

  return { botFlow, botSettings, botStyles };
}
