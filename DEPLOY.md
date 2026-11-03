# Deploying tabui with Docker

For whoever puts tabui on a server (an AWS EC2 instance, say). The **showcase** is the site people use: its pages,
the chat widget built into it, and the routes the widget needs (`/api/bots` for the list of agents, `/api/token` for
a call). Everything runs from this folder with Docker Compose.

## What it needs

- A Linux server with **Docker** and the **Docker Compose plugin**. 2 GB of memory and 10 GB of disk are plenty
  (the build itself needs about 2 GB of memory).
- A **domain** pointing at the server, for HTTPS. Browsers give a page the microphone only over HTTPS, so voice calls
  need it.
- The server can reach **LiveKit**, the **Agent Builder API** (`http://16.79.174.151:8100`) and the **bank database**
  (`http://16.79.174.151:3322`).
- The LiveKit address, key and secret, and the Agent Builder API key.

## 1. Copy the folder and fill in the settings

Copy this folder to the server (without `node_modules`, `.next` or `dist`). Then:

```sh
cp .env.example .env
nano .env        # LiveKit, the Agent Builder address and key, the bank database, the domain
```

Set `SHOWCASE_DOMAIN` to the domain, and add `https://<that domain>` to `ALLOWED_ORIGINS_TO_CALL_API`. `.env` holds
the secrets: it stays on the server and is read when the container starts. Only the `NEXT_PUBLIC_*` values are built
into the image (rebuild after changing one); the main pages don't need them.

## 2. Start it

Open ports **80 and 443** in the server's security group (not 3000), then:

```sh
docker compose --profile https up --build -d     # https://SHOWCASE_DOMAIN
```

Caddy gets and renews the HTTPS certificate itself. Without the `https` profile the showcase is on port 3000 over plain
HTTP: fine for trying it, but voice calls won't get the microphone.

The guide page (the page to try the agents on, with the live table of test customers) runs too, on port 5174. It
is the widget's own dev server, so keep it for trying things out; on a server, set `GUIDE_ALLOWED_HOSTS` to the name it
is opened on and `GUIDE_TOKEN_API` to the showcase's https address.

Optional: the widget's own host page (an nginx page that embeds the widget), on port 8081:

```sh
docker compose --profile widget up --build -d    # set ADA_AUTH_TOKEN_API in .env to the showcase's address
```

## 3. Check it

```sh
docker compose ps                                  # showcase: Up
curl -s https://<domain>/api/bots | head -c 300    # {"agents":[ … the deployed agents … ]}
docker compose logs showcase | tail
```

Open `https://<domain>`, open the chat, choose an agent and talk to it.

## Updating and stopping

```sh
docker compose --profile https up --build -d     # after copying new files: rebuilds and restarts
docker compose --profile https down              # stops it (certificates are kept)
```

## When Weave Studio runs on the same server

Both projects' HTTPS fronts want ports 80 and 443, and only one can have them: run tabui with HTTPS and the studio
private (its DEPLOY.md, option A), or give them separate servers.
