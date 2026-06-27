from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from data import ACCESS_TOKEN, BANNER, COURSES, GRANTS, META, SERVICES
from lumo_catalog import catalog_status, get_opportunity, list_categories, list_opportunities, match_opportunities

app = FastAPI(title="AI Startify Grants API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContactRequest(BaseModel):
    contact: str = Field(min_length=3, max_length=255)
    name: str | None = None
    message: str | None = None
    grantId: int | None = None


class PurchaseRequest(BaseModel):
    contact: str = Field(min_length=3, max_length=255)
    courseId: int | None = None
    serviceId: int | None = None


class MatchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    limit: int = Field(default=12, ge=1, le=30)


def _has_access(authorization: str | None) -> bool:
    if not authorization:
        return False
    token = authorization.removeprefix("Bearer ").strip()
    return token == ACCESS_TOKEN


def _public_grant(grant: dict, *, unlocked: bool) -> dict:
    item = {k: v for k, v in grant.items() if k != "premiumContent"}
    if grant["isPremium"] and not unlocked:
        item["isLocked"] = True
        item["premiumContent"] = None
    else:
        item["isLocked"] = False
        item["premiumContent"] = grant["premiumContent"]
    return item


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def get_meta() -> dict:
    return META


@app.get("/api/banner")
def get_banner() -> dict:
    return BANNER


@app.get("/api/grants")
def list_grants(q: str | None = Query(default=None)) -> list[dict]:
    items = GRANTS
    if q:
        needle = q.lower()
        items = [
            g
            for g in GRANTS
            if needle in g["title"].lower() or needle in g["location"].lower()
        ]
    return [_public_grant(g, unlocked=False) for g in items]


@app.get("/api/grants/{grant_id}")
def get_grant(grant_id: int, authorization: str | None = Header(default=None)) -> dict:
    grant = next((g for g in GRANTS if g["id"] == grant_id), None)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    return _public_grant(grant, unlocked=_has_access(authorization))


@app.get("/api/services")
def list_services() -> list[dict]:
    return SERVICES


@app.get("/api/courses")
def list_courses() -> list[dict]:
    return COURSES


@app.post("/api/leads/contact")
def submit_contact(payload: ContactRequest) -> dict:
    return {"ok": True, "message": "Заявка принята. Мы свяжемся с вами в Telegram."}


@app.post("/api/leads/purchase")
def submit_purchase(payload: PurchaseRequest) -> dict:
    if not payload.courseId and not payload.serviceId:
        raise HTTPException(status_code=422, detail="Specify courseId or serviceId")
    return {"ok": True, "message": "Запрос отправлен. Менеджер напишет вам в Telegram."}


@app.get("/api/lumo/status")
def lumo_status() -> dict:
    return catalog_status()


@app.get("/api/lumo/categories")
def lumo_categories() -> list[dict]:
    try:
        return list_categories()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/lumo/opportunities")
def lumo_opportunities(
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> dict:
    try:
        return list_opportunities(category=category, q=q, page=page, page_size=page_size)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/lumo/opportunities/{item_id}")
def lumo_opportunity(item_id: int) -> dict:
    try:
        item = get_opportunity(item_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return item


@app.post("/api/lumo/match")
def lumo_match(payload: MatchRequest) -> dict:
    try:
        return match_opportunities(payload.query, limit=payload.limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
