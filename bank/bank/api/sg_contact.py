"""Singapore AACC (hand-overs into skill queues) and the fax server."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Market
from .common import hand_over, json_body, send_fax

router = APIRouter(tags=["Singapore: AACC and fax"])


@router.post("/sg/aacc/transfer")
def transfer(request: Request, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return hand_over(db, Market.SG, body, dict(request.headers))


@router.post("/sg/fax/send")
def fax(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return send_fax(db, Market.SG, body)
