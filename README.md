# Tetherfi Assist Bot (TAB) User Interface

This repository contains two projects: `Widget` and `Showcase`.

## Run with Docker

`cp .env.example .env`, fill it in, then `docker compose up --build -d`: the guide page to try the agents on http://localhost:5174, and the showcase (it serves the chat's agents and tokens) on http://localhost:3000. On a server with HTTPS (needed for voice), see [DEPLOY.md](DEPLOY.md).

## Widget

The source code for the TAB Widget, designed to be integrated into any website is in `\widget` folder.

## Showcase

The source code for a website showcasing the features and functionalities of the TAB Widget is in `\showcase` folder.


## Local Weave Studio + TAB widget setup

See [RUN_WIDGET.md](RUN_WIDGET.md). The widget runs on `http://localhost:5174` so Weave Studio can stay on `http://localhost:5173`. Paste only the LiveKit URL, API key, and API secret into `showcase/.env.local`.

## Bank and CRM

The bank behind the phone agents is Ashwin's customer, account and transaction database (Region DB2), reached with `POST /TetherfiDbRestApi/dboperations`. The Showcase shows it at `/crm` (set `BANK_API_URL` in `showcase/.env.local`), and the widget's guide page lists its test customers. In Weave Studio it is connected under Integrations → REST API.
