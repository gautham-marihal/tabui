# Run the TAB widget and load agents from Weave Studio

This project fetches deployed agents from the Weave Studio `GET /bots` API, displays the available bot/deployment pairs in the widget, and dispatches the selected one through LiveKit using metadata in the form `{ "bot": "<id>", "ref": "<deployment>" }`.

## 1. Paste the three LiveKit values

Open `showcase/.env.local` and replace only these three placeholder values:

```env
LIVEKIT_URL=wss://YOUR_LIVEKIT_URL
LIVEKIT_API_KEY=YOUR_API_KEY
LIVEKIT_API_SECRET=YOUR_API_SECRET
```

Do not place the API secret in `widget/.env.local` or in any `VITE_` variable.

## 2. Keep Weave Studio running

The screenshot you supplied showed the Weave Studio UI at `http://localhost:5173/#/bots`. Based on that, `showcase/.env.local` is preconfigured with:

```env
WEAVE_API_BASE_URL=http://localhost:5173/api
```

The app will call `GET http://localhost:5173/api/bots`: Weave Studio's dev server passes `/api` on to the Agent Builder API and adds its key there, so no key is needed here. If `/bots` is served by a separate backend host or port, change `WEAVE_API_BASE_URL` to that API server's base URL (a path in it is kept). A browser address with a hash route identifies the UI origin, but cannot by itself prove the API is served by the same origin; the `/api/bots` endpoint reports a clear error if it gets HTML instead of JSON.

Weave Studio remains on port 5173. This project's standalone widget runs on port 5174 to avoid a port conflict.

## 3. Install dependencies

In a terminal opened at the `tabui` project root:

```bash
cd widget
npm install
```

Then in a second terminal:

```bash
cd showcase
npm install
npm run dev
```

The Showcase startup script builds the widget bundle from `widget/src`, copies it into `showcase/public/tab-widget`, and starts Next.js on `http://localhost:3000`. This keeps the embedded site in sync with the current widget code. Open one of the existing Showcase demo pages such as `/autocompany-demo`, `/sh`, or `/singapore-health-demo` to test the embedded widget.

To run the widget's standalone local harness instead, run `npm run dev` inside `widget` in another terminal and open `http://localhost:5174`.

## 4. Verify dynamic agent discovery

Open `http://localhost:3000/api/bots`. A successful response contains an `agents` array. Each option includes an agent ID, name, deployment `ref`, and deployed version. Draft-only agents with no deployed environment are intentionally omitted.

If it errors with `HTML page, not JSON`, `WEAVE_API_BASE_URL` currently points to the Studio UI rather than the API. Set it to the actual host and port that serves `GET /bots`.

## 5. How dispatch works

When a user chooses an item and clicks Connect, the widget calls `/api/token` with the selected bot ID and ref. The backend creates a LiveKit access token and dispatches `agent-builder-runtime` with metadata similar to:

```json
{ "bot": "nimbus-care", "ref": "development" }
```

The bot list reflects whatever environments GET /bots reports. The separate `agent-builder-runtime` service must be running, registered with the same LiveKit project, and programmed to interpret the metadata. LiveKit credentials alone cannot start that service.

## External hosting note

For a truly remote deployment, `WEAVE_API_BASE_URL` must be a reachable API URL from the deployed backend; `localhost` refers to the machine hosting the application, not your laptop. The widget's API endpoints must also be hosted or configured to point to the deployed Showcase backend. Never ship the LiveKit API secret to the browser.
