# TAB Widget (Tetherfi Assist Bot) - Walkthrough

Written for: engineers who need to understand, run, or deploy this widget.

## 1. What this project is

The TAB widget is an embeddable, floating voice/chat assistant. A host website drops a
script and stylesheet onto the page, and a chat-bubble icon appears in the corner. Clicking it
opens a small panel where the user connects to an AI agent running in a LiveKit room. The user
can talk to the agent by voice, type messages, attach files, turn on the camera, and share the
screen. The agent's speech is played back, and both sides' speech is transcribed into the chat.

It ships as a single self-contained bundle (`tab-widget.iife.js` + `tab-widget.css`) so it can be
dropped into any web page without a framework.

The `widget/` folder is the widget itself. The sibling `showcase/` folder is a Next.js demo site
that hosts the widget and provides the token endpoint (see section 9).

## 2. Tech stack

| Concern | Technology |
| --- | --- |
| UI framework | React 19 (`react`, `react-dom`) |
| Language | TypeScript ~5.8 |
| Build tool | Vite 7 (library mode, IIFE output) |
| Real-time media | LiveKit: `livekit-client` 2.x, `@livekit/components-react` 2.x, `@livekit/components-styles` |
| Chat UI | `react-chatbotify` 2.x |
| Icons | `react-icons` (Material Design set, `react-icons/md`) |
| Styling | SCSS (`sass`), plus LiveKit's default component styles |
| Lint | ESLint 9 with typescript-eslint and react-hooks / react-refresh plugins |
| Production web server | nginx 1.27 (alpine), inside Docker |
| Build image | node:20-slim |

### Dependencies (from `widget/package.json`)

Runtime:

- `@livekit/components-react` ^2.9.14 - React hooks and components for LiveKit (`useTracks`, `useChat`, `LiveKitRoom`, `VideoTrack`, etc.)
- `@livekit/components-styles` ^1.2.0 - default LiveKit CSS for the prebuilt components
- `livekit-client` ^2.15.4 - core LiveKit SDK (`Room`, tracks, participants, data streams)
- `react` / `react-dom` ^19.1.0
- `react-chatbotify` ^2.2.0 - the chat window, message flow, and footer buttons
- `react-icons` ^5.5.0

Dev only: `vite`, `@vitejs/plugin-react`, `typescript`, `sass`, `eslint` and its plugins,
`@types/*`.

### Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Vite dev server. Uses the root `index.html` and `src/main.tsx` with the dev harness. |
| `npm run build` | `tsc -b` type-check, then `vite build` to `dist/` |
| `npm run preview` | Build, then serve `dist/` locally |
| `npm run lint` | ESLint over the project |

## 3. Folder map

```
widget/
├── index.html                  # Dev-mode host page (used by `npm run dev`)
├── public/
│   ├── index.html              # Production host page: the icon + mount logic (copied to dist/)
│   ├── brightgrid-bg.png       # Background image for the host page
│   └── favicon.png
├── dist/                       # Build output (tab-widget.iife.js, tab-widget.css, index.html)
├── docker-entrypoint.d/
│   └── 40-substitute-ada-env.sh  # Injects runtime env into index.html at container start
├── Dockerfile                  # Two-stage: Vite build -> nginx
├── setup-docs/
│   ├── README.md               # How to integrate the widget into another site
│   └── TABWidget.txt           # Example React/Next.js wrapper component
├── vite.config.ts              # Library-mode build config
├── .env.example                # Dev env variables
└── src/
    ├── main.tsx                # Entry point: dev render OR window.mount* globals
    ├── App.tsx                 # Creates the LiveKit Room; wraps MMBot in providers
    ├── DevHarness.tsx          # Dev-only wrapper around the widget
    ├── App.scss / index.scss   # Global styles
    ├── util/
    │   ├── types.ts            # WidgetProps, StartScreenProps
    │   └── composeBotProps.tsx # react-chatbotify config: flow, settings, styles, footer buttons
    ├── hooks/
    │   └── useMultibandTrackVolume.tsx  # Frequency bands for the mic visualizer
    └── components/
        ├── MMBot.tsx           # The main "classic" UI: connection, events, media controls
        ├── StartScreen.tsx     # Pre-connect screen with the Connect button
        ├── VideoScreen.tsx     # Overlay that shows the camera or screen-share track
        ├── CustomAudioVisualizer.tsx  # 9-bar mic level meter
        └── new-ui/             # Newer LiveKit-components-based UI (see §11)
            ├── NewMMBot.tsx
            ├── customControlBar.tsx, chatBox.tsx, chatInputBox.tsx, chatBox, chat-*
            ├── buttonUpload.tsx, registerHandler.tsx
            └── chat/hooks/useChatAndTranscription.ts
```

## 4. Entry point and how the widget is mounted

`src/main.tsx` has two modes, chosen by `VITE_ENVIRONMENT`:

**Local / dev mode** (`VITE_ENVIRONMENT=local`). It renders `<App>` straight into
`#tabui-development-app-root` inside `<DevHarness>`. Config comes from `VITE_AGENT_ID`,
`VITE_LIVEKIT_URL`, and `VITE_LIVEKIT_TOKEN_API`. It also masks a 7-digit + "D" pattern (looks
like a Singapore NRIC-style ID) in typed text before display.

**Widget / production mode** (anything else). It doesn't render on load. Instead it exposes
global functions on `window` for a host page to call:

| Global | Purpose |
| --- | --- |
| `window.mountTABWidget(containerId, props)` | Renders `<App {...props}>` into the element with that id |
| `window.unmountTABWidget(containerId)` | Unmounts that React root |
| `window.mountNewTABWidget(containerId, props)` | Same as above (see the caveat in §11) |
| `window.unmountNewTABWidget(containerId)` | Same as above |

`props` is a `WidgetProps` object:

```ts
interface WidgetProps {
  agentId: string;        // Which bot to talk to; passed to the token API
  livekitURL: string;     // LiveKit server WebSocket URL, e.g. wss://...
  authTokenAPI: string;   // Base URL of the token server, e.g. https://host:8090
  width: number;          // Pixel width of the panel
  height: number;         // Pixel height of the panel
  room?: any;             // Internal, set by MMBot
  chatTextDisplayFilter?: {
    enabled: boolean;
    test: (text: string) => boolean;
    replace: (text: string) => string;
  };
}
```

`mount` checks that `livekitURL`, `width`, `height`, and `agentId` are all set. If any is
missing, it logs `Missing required Widget Properties.` and renders nothing.

### The production host page (`public/index.html`)

This page is what the Docker image serves. It:

1. Loads `tab-widget.css` and `tab-widget.iife.js`.
2. Declares the three config values as placeholders: `__ADA_AGENT_ID__`, `__ADA_LIVEKIT_URL__`, `__ADA_AUTH_TOKEN_API__`.
3. Shows a fixed purple chat button (`#tab-icon`) at bottom-right.
4. On the first click, calls `mountTABWidget("tab-widget-container", {...width: 360, height: 520})`. It mounts only once. Later clicks just show or hide the container.

## 5. The main component: `MMBot`

`App.tsx` creates one LiveKit `Room` per widget instance:

```ts
new Room({ adaptiveStream: true, dynacast: true })
```

- `adaptiveStream` lowers the resolution of video the browser doesn't need to render.
- `dynacast` pauses video layers nobody is subscribed to.

The `Room` is passed to `RoomContext.Provider`, so LiveKit hooks work inside it. The Room is
passed to `MMBot` as a prop too, so MMBot can call `connect` and `disconnect` directly.

`MMBot` holds the UI state:

| State | Meaning |
| --- | --- |
| `connectedToAgent` | `false` shows `StartScreen`, `true` shows the chat |
| `isConnecting` | Disables the Connect button while the token request is in flight |
| `showVideoPane` / `showScreenSharePane` | Whether the camera or screen overlay is open |
| `cameraFacingMode` | `"environment"` (rear, default) or `"user"` (front) |
| `isMute` | Mirrors the mic toggle, drives the visualizer colour |

`MMBot` also uses `useTracks()` and `useLocalParticipant()` to find the user's own mic, camera,
and screen-share tracks, and `useChat()` / `useMessages()` from react-chatbotify to push text
into the chat.

## 6. How the widget connects to LiveKit

This is the full connection path, from the Connect button to audio playing.

### Step 1: Get a token from the token server

```ts
const { accessToken } = await fetch(
  `${authTokenAPI}/api/token?agentId=${agentId}`
).then((res) => res.json());
```

The widget does not hold any LiveKit API secret. It asks the backend to mint a short-lived JWT.
The backend (see §9) returns `{ identity, accessToken }`.

### Step 2: Join the room

```ts
await room.connect(livekitURL, accessToken);
room.localParticipant.setMicrophoneEnabled(true);
```

`livekitURL` is the server, and `accessToken` says which room to join and with what permissions.
The token grants `roomJoin`, `canPublish`, `canPublishData`, `canSubscribe`, and
`canUpdateOwnMetadata`, all for a room named `tab-XXXX-XXXX` that is generated per connection. So
every click on Connect creates a new room. The microphone is turned on right away.

### Step 3: Listen for the agent's audio

```ts
room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
  if (track.kind === "audio") {
    const audioElement = track.attach();
    audioElement.autoplay = true;
    audioElement.style.display = "none";
    document.body.appendChild(audioElement);
    setConnectedToAgent(true);
  }
  setIsConnecting(false);
});
```

When the agent publishes an audio track, the widget subscribes to it automatically, attaches it to
a hidden `<audio>` element, and flips the UI to the chat view.

### Step 4: Receive the agent's transcript

The agent sends its speech-to-text output over LiveKit's **data stream** API, on topic
`lk.transcription`:

```ts
room.registerTextStreamHandler("lk.transcription", async (reader, participantInfo) => {
  let text = "";
  for await (const chunk of reader) {
    text += chunk;
    if (participantInfo.identity !== room.localParticipant.identity) {
      await streamMessage(text);      // Partial text, shown as it arrives
    }
  }
  if (participantInfo.identity !== room.localParticipant.identity) {
    await endStreamMessage();          // Final text
  }
});
```

Each chunk extends the same message bubble until the stream closes. Messages from the local user
are ignored here because they come from the mic (see step 5).

### Step 5: Send the user's speech

The mic is published as an audio track, and the agent does the speech recognition on the server.
The widget also runs `useTrackTranscription` on the local mic track. When a final segment comes
back, it is injected into the chat as a user message:

```ts
useEffect(() => {
  const s = localMessages.segments.at(-1);
  if (s?.final) injectMessage(`${s.text}`, "user");
}, [localMessages.segments]);
```

### Step 6: Typed messages

react-chatbotify raises a DOM event when the user types and submits. The widget listens for it
and sends the text over the LiveKit chat channel:

```ts
window.addEventListener("rcb-user-submit-text", handleTextInput);
// handleTextInput -> send(text)   (from useChat)
```

### Step 7: Mute and unmute

The chatbot footer emits `rcb-toggle-voice`. The handler calls
`room.localParticipant.setMicrophoneEnabled(!muted)`.

### Step 8: Files and images

`react-chatbotify`'s file-attachment button calls `handleUpload`, which sends the file as a
LiveKit byte stream on topic `image-upload`:

```ts
await room.localParticipant.sendFile(file, { mimeType: file.type, topic: "image-upload" });
```

The agent side must listen on that topic.

### Step 9: Camera and screen share

- **Camera.** `showVideoScreen` calls `setCameraEnabled(true, { facingMode })` and opens
  `VideoScreen`, which renders the local camera track with `<VideoTrack>`. The flip button calls
  `restartTrack({ facingMode })` on the existing track, because `setCameraEnabled` does not apply
  new constraints to a track that is already published.
- **Screen share.** `setScreenShareEnabled(true)` opens the browser's picker. If the user stops
  sharing from the browser's own bar, an effect syncs the button state.

Both overlays are positioned over the chat body by measuring `.rcb-chat-body-container`.

### Step 10: Disconnect

`disconnectFromAgent` closes any video panes, unregisters the `lk.transcription` handler, calls
`room.disconnect()`, and goes back to the StartScreen.

### Connection flow at a glance

```
Host page                 Token server (showcase /api/token)       LiveKit server
   |  click Connect            |                                          |
   |-- GET /api/token?agentId->|  mint JWT (room tab-XXXX-XXXX)           |
   |<-- { accessToken } -------|                                          |
   |-------------------------- room.connect(url, token) ------------------>|
   |<------------------------- joined; agent joins same room -------------|
   |<------------------------- agent audio track (TrackSubscribed) -------|
   |<------------------------- data stream lk.transcription (text) -------|
   |-------------------------- mic audio track ------------------------->|
   |-------------------------- chat / sendFile (image-upload) ----------->|
```

## 7. UI pieces

- **`StartScreen`** - the white card with the purple Connect button. Shows "Connecting..." while
  the token request runs.
- **`react-chatbotify` (`ChatBot`)** - the chat window. `composeBotProps.tsx` configures it:
  header with a close (disconnect) button, footer with file attach, camera toggle, and
  screen-share toggle, voice on by default, 500-character input limit, emoji and chat history off.
- **`CustomAudioVisualizer`** - nine bars at bottom-right, driven by
  `useMultibandTrackVolume` on the local mic. Goes grey when muted.
- **`VideoScreen`** - the camera or screen-share overlay, with a camera-flip and close icon.

## 8. Running it locally

1. `cd widget`
2. `npm ci`
3. Copy `.env.example` to `.env.local` and set:
   ```
   VITE_ENVIRONMENT=local
   VITE_LIVEKIT_URL=wss://your-livekit-host
   VITE_LIVEKIT_TOKEN_API=http://localhost:3000     # the showcase app, or your token server
   VITE_AGENT_ID=your-agent-id
   ```
4. `npm run dev` and open the URL Vite prints.

To test the production bundle locally: set `VITE_ENVIRONMENT=production`, run `npm run build`,
and open `dist/index.html` through a web server. (Opening it directly with `file://` won't work
because of module loading.)

## 9. The token server

The widget depends on a backend that issues LiveKit JWTs. In this repo that is
`showcase/src/app/api/token/route.ts`:

- It reads `agentId` from the query string and looks up the LiveKit API key and secret for that
  agent in `getEnvVariables(agentId)`. Those secrets must **never** be in the widget bundle.
- It generates a random room name and identity, builds an `AccessToken` with the
  `livekit-server-sdk` package, and returns `{ identity, accessToken }` as JSON.
- It sets CORS headers from `allowedOriginsToCallAPI`, so only listed sites can call it from a
  browser.

If you deploy the widget somewhere else, you need an equivalent endpoint that returns the same
JSON shape, and you must set its CORS allow-list to your host page's origin.

## 10. Build and deployment

### Build artifacts

`npm run build` runs `tsc -b`, then Vite in library mode (`vite.config.ts`). It emits
`dist/tab-widget.iife.js` (one IIFE bundle, with React and LiveKit inside) and
`dist/tab-widget.css`. `process.env.NODE_ENV` is fixed to `"production"`.

### Docker image (the production deployment)

`widget/Dockerfile` is two stages:

1. **build** (`node:20-slim`): `npm ci`, copy the source, `npm run build`.
2. **runtime** (`nginx:1.27-alpine`): copies `dist/` to `/usr/share/nginx/html` and installs
   `40-substitute-ada-env.sh` into nginx's `/docker-entrypoint.d/`. Exposes port **80**.

The runtime env is not baked in. `40-substitute-ada-env.sh` runs at every container start and
replaces the three placeholders in `index.html` with the env values. Changing the agent or server
means restarting the container, not rebuilding.

Required environment variables at runtime:

| Variable | Example | Used for |
| --- | --- | --- |
| `ADA_AGENT_ID` | `selfcarebanking` | Passed to the token API as `agentId` |
| `ADA_LIVEKIT_URL` | `wss://mxbot.example.com` | LiveKit server URL the browser connects to |
| `ADA_AUTH_TOKEN_API` | `https://your-showcase-host:8090` | Base URL of the token server |

The entrypoint exits with an error if any of them is unset, so the container won't start with a
blank config.

Example run:

```bash
docker build -t tab-widget ./widget

docker run -d --name tab-widget \
  -p 8080:80 \
  -e ADA_AGENT_ID=selfcarebanking \
  -e ADA_LIVEKIT_URL=wss://your-livekit-host \
  -e ADA_AUTH_TOKEN_API=https://your-token-server \
  --restart unless-stopped \
  tab-widget
```

Then open `http://<host>:8080`.

### Integrating into another site

See `setup-docs/README.md`. In short: copy `tab-widget.css` and `tab-widget.iife.js` from `dist/`
into the target project, then either use the vanilla `public/index.html` pattern or the React
wrapper in `setup-docs/TABWidget.txt`. In the React wrapper, the placeholder values (`agentId`,
`livekitURL`, `authTokenAPI`) must be replaced with real ones.

## 11. Things to know

- **The "new UI" is not wired in.** `main.tsx` exposes `mountNewTABWidget`, but it renders the same
  `App` as `mountTABWidget`. `App.tsx` exports `NewApp`, which renders `NewMMBot`, but nothing
  imports `NewApp`. So `components/new-ui/` is currently unreachable from either mount function.
  If you want it live, change `mountNewTABWidget` to render `NewApp`.
- **`NewMMBot` uses a different connection model.** It creates the Room inside `LiveKitRoom`,
  stores the token in state, and relies on the component's `connect` prop. Its chat and
  transcription come from `useChatAndTranscription()`, which combines `useTranscriptions()` and
  `useChat()`. It also uses `useVoiceAssistant()` for the bar visualizer.
- **Listeners are added on every Connect.** In `MMBot.connectToAgent`, `room.on(TrackSubscribed, ...)`
  is called each time, and the listener is never removed. Reconnecting in one session stacks
  handlers. Consider registering it once, or calling `room.off` in `disconnectFromAgent`.
- **The token endpoint has no authentication.** The code has a `TODO` about it. Anyone who knows an
  `agentId` can mint tokens. Treat the token server as a public endpoint and rate-limit it.
- **Audio elements are appended to `<body>`** on every track subscription and are not removed on
  disconnect.
- **Dev-only text masking.** The `chatTextDisplayFilter` in `main.tsx` is set only in local mode.
  The production build relies on the caller to pass a filter.
- **`setup-docs/TABWidget.txt` is a Next.js example** with placeholder values and a `@ts-expect-error`
  workaround. Replace the placeholders before use.
- **The README says `/dis/index.html`.** The correct path is `dist/index.html`.
- **`widget/dist/` is local build output.** It is gitignored, so it only exists on machines where
  someone has run `npm run build`. The Docker build creates its own copy.

## 12. Quick reference

| Question | Where to look |
| --- | --- |
| Where does the widget start? | `src/main.tsx` |
| Where is the LiveKit room created? | `src/App.tsx` |
| Where does Connect happen? | `src/components/MMBot.tsx` -> `connectToAgent` |
| Where is the token fetched? | `MMBot.tsx` (fetch), `showcase/src/app/api/token/route.ts` (server) |
| Where does agent text come in? | `registerTextStreamHandler("lk.transcription", ...)` in `MMBot.tsx` |
| Where are the footer buttons? | `src/util/composeBotProps.tsx` |
| Where are the runtime env vars applied? | `docker-entrypoint.d/40-substitute-ada-env.sh` |
| Where is the production host page? | `public/index.html` |
