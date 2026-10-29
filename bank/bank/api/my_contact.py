"""Malaysia contact centre: hand-overs to people, call-backs and surveys."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Market
from .common import hand_over, json_body, open_callback, request_callback, take_survey

router = APIRouter(prefix="/my/contact", tags=["Malaysia: contact centre"])
MY = Market.MY


@router.post("/transfer")
def transfer(request: Request, body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return hand_over(db, MY, body, dict(request.headers))


@router.get("/callbacks/{phone}")
def callback_open(phone: str, db: Session = Depends(get_session)):
    return open_callback(db, MY, phone)


@router.post("/callbacks")
def callback(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return request_callback(db, MY, body)


@router.post("/surveys")
def survey(body: dict = Depends(json_body), db: Session = Depends(get_session)):
    return take_survey(db, MY, body)
