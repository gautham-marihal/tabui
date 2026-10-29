#!/bin/sh
# nginx's own image runs every executable script in /docker-entrypoint.d/ before starting, in
# order - this fills in index.html's placeholders from the environment on every container start
# (not baked in at build time), so changing the bot/server just needs a restart, not a rebuild.
set -eu

: "${ADA_AGENT_ID:?ADA_AGENT_ID must be set}"
: "${ADA_LIVEKIT_URL:?ADA_LIVEKIT_URL must be set}"
: "${ADA_AUTH_TOKEN_API:?ADA_AUTH_TOKEN_API must be set}"

sed -i \
  -e "s#__ADA_AGENT_ID__#${ADA_AGENT_ID}#g" \
  -e "s#__ADA_LIVEKIT_URL__#${ADA_LIVEKIT_URL}#g" \
  -e "s#__ADA_AUTH_TOKEN_API__#${ADA_AUTH_TOKEN_API}#g" \
  /usr/share/nginx/html/index.html
