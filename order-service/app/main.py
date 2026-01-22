import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = Field(alias="MONGODB_URI")
    db_name: str = Field(default="orderdb", alias="DB_NAME")
    user_service_url: str = Field(default="http://user-service:4000", alias="USER_SERVICE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    request_timeout_seconds: float = Field(default=3.0, alias="REQUEST_TIMEOUT_SECONDS")


settings = Settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("order-service")


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str


class OrderItem(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    qty: int = Field(ge=1, le=1000)


class OrderCreate(BaseModel):
    user_id: str = Field(min_length=1)
    items: List[OrderItem] = Field(min_length=1)
    total: float = Field(gt=0)


class OrderOut(BaseModel):
    id: str
    user_id: str
    items: List[OrderItem]
    total: float
    created_at: str


def _serialize_order(doc: dict) -> OrderOut:
    return OrderOut(
        id=str(doc["_id"]),
        user_id=doc["user_id"],
        items=doc["items"],
        total=doc["total"],
        created_at=doc["created_at"],
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_client = AsyncIOMotorClient(settings.mongodb_uri)
    app.state.mongo_client = mongo_client
    app.state.db = mongo_client[settings.db_name]
    app.state.orders = app.state.db["orders"]

    http_client = httpx.AsyncClient(
        base_url=settings.user_service_url,
        timeout=httpx.Timeout(settings.request_timeout_seconds),
    )
    app.state.http = http_client

    logger.info("Connected to MongoDB and initialized HTTP client")
    try:
        yield
    finally:
        await http_client.aclose()
        mongo_client.close()
        logger.info("Closed HTTP client and MongoDB connection")


app = FastAPI(title="order-service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _fetch_user(user_id: str) -> Optional[dict]:
    try:
        resp = await app.state.http.get(f"/users/{user_id}")
    except httpx.RequestError as exc:
        logger.exception("User service unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="User service unavailable")

    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        logger.error("Unexpected user-service response %s: %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="User validation failed")

    return resp.json()


# Frontend must talk only to order-service: proxy user endpoints.
@app.post("/users", response_model=UserOut, status_code=201)
async def proxy_create_user(payload: UserCreate):
    try:
        resp = await app.state.http.post("/users", json=payload.model_dump())
    except httpx.RequestError as exc:
        logger.exception("User service unavailable: %s", exc)
        raise HTTPException(status_code=503, detail="User service unavailable")

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@app.get("/users/{user_id}", response_model=UserOut)
async def proxy_get_user(user_id: str):
    user = await _fetch_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/orders", response_model=OrderOut, status_code=201)
async def create_order(payload: OrderCreate):
    user = await _fetch_user(payload.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Cannot create order: user not found")

    try:
        # Validate it's an ObjectId-shaped string early (not required but helps consistency).
        ObjectId(payload.user_id)
    except Exception:
        # user-service might accept only ObjectId ids; keep message consistent.
        raise HTTPException(status_code=400, detail="Invalid user id")

    doc = {
        "user_id": payload.user_id,
        "items": [item.model_dump() for item in payload.items],
        "total": payload.total,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    orders = app.state.orders
    result = await orders.insert_one(doc)
    created = await orders.find_one({"_id": result.inserted_id})
    return _serialize_order(created)


@app.get("/orders", response_model=List[OrderOut])
async def list_orders():
    orders = app.state.orders
    results: List[OrderOut] = []
    async for doc in orders.find({}).sort("_id", -1):
        results.append(_serialize_order(doc))
    return results
