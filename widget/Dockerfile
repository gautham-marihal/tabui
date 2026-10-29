# Static build (Vite lib mode -> tab-widget.iife.js/.css + the icon-toggle host page in
# public/index.html), served by nginx. agentId/livekitURL/authTokenAPI are NOT build args -
# they're substituted into index.html at container start (see docker-entrypoint.d/), so
# reconfiguring which bot/server this points at is a restart, not a rebuild. Contrast with
# showcase's Next.js build, where NEXT_PUBLIC_* really is build-time only.

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker-entrypoint.d/40-substitute-ada-env.sh /docker-entrypoint.d/40-substitute-ada-env.sh
RUN chmod +x /docker-entrypoint.d/40-substitute-ada-env.sh

EXPOSE 80
