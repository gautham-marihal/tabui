"""The mock bank API: every bank system the agents call, the tester's overview (/) and the audit log (/activity).

Each system is a path prefix the agents' connections point at:
  Singapore  /sg/as400 (logins, CIF, PIN change, cheque status and stop-payment, rates)   /sg/soa (balances, history,
             statements, incoming funds, cheque deposits and books, fixed-deposit rates, one-time passwords)
             /sg/siebel (account login, NRIC check, service requests, cases)   /sg/cmm (caller preferences, VIPs, service
             codes, promotions, forms, branches, bank codes, appointments, call-backs, surveys)   /sg/aacc   /sg/fax
  Malaysia   /my/core (logins, accounts, transfers, payments, direct debits, cheques, cards, rates, branches, forms, fax)
             /my/contact (hand-overs, call-backs, surveys)
With an access key, everything answers only under /<key>: a private address only those who have it can use.
"""

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from .api import ROUTERS
from .api.common import BodyNotJson
from .api.policy import MissingReference
from .config import MOCK_OTP, settings
from .db import get_session
from .models import Account, AuditEvent, Customer, Person


def create_app(access_key: str | None = None) -> FastAPI:
    key = settings.access_key if access_key is None else access_key
    app = FastAPI(title="Mock bank API", summary="The made-up bank behind the business-banking phone agents", docs_url=None, redoc_url=None)
    for router in ROUTERS:
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    def overview(db: Session = Depends(get_session)):
        count = lambda model: db.scalar(select(func.count(model.id)))  # noqa: E731
        return {**OVERVIEW, "people": count(Person), "customers": count(Customer), "accounts": count(Account)}

    @app.get("/activity", include_in_schema=False)
    def activity(db: Session = Depends(get_session)):
        rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id))
        return {"items": [{"at": e.at.isoformat(), "kind": e.kind, **({"market": e.market.value} if e.market else {}), **e.details} for e in rows]}

    @app.exception_handler(BodyNotJson)
    async def not_json(request: Request, _error: BodyNotJson):
        return JSONResponse({"error": "body_is_not_json"}, status_code=400)

    @app.exception_handler(MissingReference)
    async def missing_reference(request: Request, error: MissingReference):
        # the bank's reference data lacks a setting, tariff or country the route needs: fix the data (or run the seed)
        return JSONResponse({"error": "reference_data_missing", "missing": str(error)}, status_code=500)

    @app.exception_handler(HTTPException)
    async def not_found(request: Request, error: HTTPException):
        # an unknown path, or a known path with the wrong method, is simply not there (as the bank's gateway answers)
        if error.status_code in (404, 405):
            return JSONResponse({"error": "not_found", "path": request.url.path}, status_code=404)
        return JSONResponse({"error": error.detail}, status_code=error.status_code)

    return PrivateAddress(app, key) if key else app


class PrivateAddress:
    """Answers only under /<key>, with the key taken off before routing. Any other address, / included, is a 404."""

    def __init__(self, app, key: str):
        self.app, self.prefix = app, f"/{key}"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path != self.prefix and not path.startswith(f"{self.prefix}/"):
            response = JSONResponse({"error": "not_found"}, status_code=404)
            return await response(scope, receive, send)
        inner = path[len(self.prefix) :] or "/"
        await self.app({**scope, "path": inner, "raw_path": inner.encode()}, receive, send)


# What a tester needs: the systems, and where the made-up customers and their logins are listed.
OVERVIEW = {
    "name": "Mock bank API for the business-banking phone agents",
    "activity": "/activity lists what the agents changed (service requests, bookings, call-backs, surveys, hand-overs, payments, faxes)",
    "one_time_password": MOCK_OTP,
    "test_logins": "bank/README.md lists every made-up person and how they log in",
    "systems": {
        "both countries": ["/hub (who is calling, a person's accounts, balances, history; /hub/reference: lines, hours, holidays, prices)", "/crm"],
        "singapore": ["/sg/as400", "/sg/soa", "/sg/siebel", "/sg/cmm", "/sg/aacc", "/sg/fax"],
        "malaysia": ["/my/core", "/my/contact"],
    },
}

app = create_app()
