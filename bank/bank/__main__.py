"""Runs the mock bank API:  python -m bank   (PORT, default 4300; MOCK_BANK_KEY for a private address)."""

import uvicorn

from .config import settings

if __name__ == "__main__":
    where = f"http://localhost:{settings.port}{'/' + settings.access_key if settings.access_key else ''}"
    print(f"Mock bank API on {where}  (GET {where}/ for the test customers, {where}/activity for what the agents did)")
    uvicorn.run("bank.app:app", host="0.0.0.0", port=settings.port, log_level="info")
