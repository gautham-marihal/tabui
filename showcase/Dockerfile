# Next.js standalone build. NEXT_PUBLIC_* vars are baked in at build time (browser code can't
# read them at runtime), so they're build ARGs here, not just environment/compose values - pass
# the server's real public address when building, e.g.:
#   docker build \
#     --build-arg NEXT_PUBLIC_LK_TOKEN_ENDPOINT=https://your-domain:8090 \
#     --build-arg NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL=wss://mxbot.cimbpoc.tetherfi.cloud \
#     -t tab-showcase .
# Rebuild the image whenever either value changes - editing .env on the running container does
# nothing for these two.
#
# node:20-slim (Debian/glibc), not node:20-alpine: Next.js's SWC compiler ships a native
# @next/swc-linux-x64-gnu binary that needs glibc: Alpine (musl) can't load it and next build
# fails with unrelated-looking "Module not found" errors. glibc also matches an Ubuntu target.

FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG NEXT_PUBLIC_LK_TOKEN_ENDPOINT
ARG NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL
ENV NEXT_PUBLIC_LK_TOKEN_ENDPOINT=$NEXT_PUBLIC_LK_TOKEN_ENDPOINT
ENV NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL=$NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL

RUN npm run build

FROM node:20-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
