# The showcase (Next.js standalone) with the chat widget built into it. Built from the tabui folder, because the
# showcase's build also builds ../widget and copies it into public/tab-widget:
#   docker compose up --build -d        (from the tabui folder; see docker-compose.yml and .env.example)
#   docker build -f showcase/Dockerfile -t tab-showcase .     (the same, by hand, from the tabui folder)
# Server settings (LiveKit, the Agent Builder API, the bank database) are read when the container starts. Only the
# NEXT_PUBLIC_* values are baked in at build time (browser code can't read them later); rebuild when one changes.
#
# node:22-slim (Debian/glibc), not alpine: Next.js's SWC compiler ships a native @next/swc-linux-x64-gnu binary that
# needs glibc; on Alpine (musl) next build fails with unrelated-looking "Module not found" errors.

FROM node:22-slim AS deps
WORKDIR /app
COPY widget/package.json widget/package-lock.json ./widget/
COPY showcase/package.json showcase/package-lock.json ./showcase/
RUN cd widget && npm ci --no-audit --no-fund && cd ../showcase && npm ci --no-audit --no-fund

FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/widget/node_modules ./widget/node_modules
COPY --from=deps /app/showcase/node_modules ./showcase/node_modules
COPY widget ./widget
COPY showcase ./showcase

ARG NEXT_PUBLIC_LK_TOKEN_ENDPOINT
ARG NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL
ARG NEXT_PUBLIC_AUSBANK_LIVEKIT_URL
ARG NEXT_PUBLIC_AUTOCOMPANY_LIVEKIT_URL
ARG NEXT_PUBLIC_SCBANK_DATA_API
ARG NEXT_PUBLIC_SELFCAREBANK_LIVEKIT_URL
ARG NEXT_PUBLIC_SH_LIVEKIT_URL
ARG NEXT_PUBLIC_SINGHEALTH_LIVEKIT_URL
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_LK_TOKEN_ENDPOINT=$NEXT_PUBLIC_LK_TOKEN_ENDPOINT \
    NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL=$NEXT_PUBLIC_NIGERIA_ENERGY_BOT_LIVEKIT_URL \
    NEXT_PUBLIC_AUSBANK_LIVEKIT_URL=$NEXT_PUBLIC_AUSBANK_LIVEKIT_URL \
    NEXT_PUBLIC_AUTOCOMPANY_LIVEKIT_URL=$NEXT_PUBLIC_AUTOCOMPANY_LIVEKIT_URL \
    NEXT_PUBLIC_SCBANK_DATA_API=$NEXT_PUBLIC_SCBANK_DATA_API \
    NEXT_PUBLIC_SELFCAREBANK_LIVEKIT_URL=$NEXT_PUBLIC_SELFCAREBANK_LIVEKIT_URL \
    NEXT_PUBLIC_SH_LIVEKIT_URL=$NEXT_PUBLIC_SH_LIVEKIT_URL \
    NEXT_PUBLIC_SINGHEALTH_LIVEKIT_URL=$NEXT_PUBLIC_SINGHEALTH_LIVEKIT_URL \
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app/showcase
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build /app/showcase/public ./public
COPY --from=build /app/showcase/.next/standalone ./
COPY --from=build /app/showcase/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
