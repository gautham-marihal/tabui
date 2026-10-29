# Tetherfi Assist Bot (TAB) User Interface

This repository contains two projects: `Widget` and `Showcase`.

## Widget

The source code for the TAB Widget, designed to be integrated into any website is in `\widget` folder.

## Showcase

The source code for a website showcasing the features and functionalities of the TAB Widget is in `\showcase` folder.


## Local Weave Studio + TAB widget setup

See [RUN_WIDGET.md](RUN_WIDGET.md). The widget runs on `http://localhost:5174` so Weave Studio can stay on `http://localhost:5173`. Paste only the LiveKit URL, API key, and API secret into `showcase/.env.local`.

## Bank and CRM

The `\bank` folder holds a made-up bank in a PostgreSQL database and its API, including a CRM. The Showcase shows it at `/crm` and serves it to other apps at `/api/crm` (with `CRM_API_KEY`); in Weave Studio, connect it under Integrations → CRM to check it, browse its records, and give agents tools to look callers up, verify them and hand them over. See [bank/README.md](bank/README.md).
