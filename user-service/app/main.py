import logging
from contextlib import asynccontextmanager

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = Field(alias="MONGODB_URI")
    db_name: str = Field(default="userdb", alias="DB_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


settings = Settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("user-service")


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr


def _serialize_user(doc: dict) -> UserOut:
    return UserOut(id=str(doc["_id"]), name=doc["name"], email=doc["email"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongodb_uri)
    app.state.mongo_client = client
    app.state.db = client[settings.db_name]
    app.state.users = app.state.db["users"]
    logger.info("Connected to MongoDB")
    try:
        yield
    finally:
        client.close()
        logger.info("MongoDB connection closed")


app = FastAPI(title="user-service", version="1.0.0", lifespan=lifespan)


@app.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate):
    users = app.state.users
    doc = payload.model_dump()
    result = await users.insert_one(doc)
    created = await users.find_one({"_id": result.inserted_id})
    return _serialize_user(created)


@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: str):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    users = app.state.users
    doc = await users.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(doc)
