export interface TokenResult {
  identity: string;
  accessToken: string;
  livekitURL: string;
}

export interface TABWidgetProps {
  agentId: string;
  livekitURL: string;
  chatTextDisplayFilterEnabled: boolean;
}
