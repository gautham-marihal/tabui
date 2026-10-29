import type { Room } from "livekit-client";
import type { RcbToggleVoiceEvent, RcbUserSubmitTextEvent } from "react-chatbotify";

// react-chatbotify sends these on window; naming them here lets addEventListener give handlers their real event types
declare global {
  interface WindowEventMap {
    "rcb-toggle-voice": RcbToggleVoiceEvent;
    "rcb-user-submit-text": RcbUserSubmitTextEvent;
  }
}

export interface WidgetProps {
  agentId: string;
  agentRef?: string;
  livekitURL: string;
  authTokenAPI: string | "";
  width: number;
  height: number;
  room?: Room;
  chatTextDisplayFilter?: {
    enabled: boolean;
    test: (text: string) => boolean;
    replace: (text: string) => string;
  };
}

export interface SelectableAgent {
  id: string;
  name: string;
  ref: string;
  version: string;
}

export interface StartScreenProps {
  width: number;
  height: number;
  connectToAgent: (event: React.SyntheticEvent) => Promise<void>;
  isConnecting: boolean;
  connectionError?: string;
  agents?: SelectableAgent[];
  selectedAgentKey?: string;
  onAgentChange?: (key: string) => void;
  isLoadingAgents?: boolean;
  agentsError?: string;
}
