from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.database import Database

from src.core.config import settings

mongo_client: MongoClient | None = None


def build_mongo_uri() -> str:
    raw_url = settings.db_url.strip()
    encoded_user = quote_plus(settings.db_user)
    encoded_password = quote_plus(settings.db_password)

    if raw_url.startswith(("mongodb://", "mongodb+srv://")):
        if "@" in raw_url:
            return raw_url

        scheme, remainder = raw_url.split("://", 1)
        return f"{scheme}://{encoded_user}:{encoded_password}@{remainder}"

    return f"mongodb+srv://{encoded_user}:{encoded_password}@{raw_url}"


def connect_to_mongo() -> Database:
    global mongo_client

    if mongo_client is None:
        mongo_client = MongoClient(build_mongo_uri(), serverSelectionTimeoutMS=5000)

    return mongo_client[settings.db_name]


def get_database() -> Database:
    if mongo_client is None:
        return connect_to_mongo()

    return mongo_client[settings.db_name]


def ping_database() -> None:
    database = get_database()
    database.command("ping")


def ensure_indexes() -> None:
    database = get_database()
    database["users"].create_index("user_id", unique=True)
    database["users"].create_index("email", unique=True)
    database["sources"].create_index("id", unique=True)
    database["sources"].create_index("user_id")
    database["linkedin_scrape_raw"].create_index("user_id")
    database["linkedin_scrape_raw"].create_index("source_url")
    database["linkedin_author_bylines"].create_index("user_id")
    database["linkedin_author_bylines"].create_index("source_url")
    database["linkedin_author_bylines"].create_index([("user_id", 1), ("status", 1)])
    database["linkedin_author_bylines"].create_index([("user_id", 1), ("created_at", -1)])


def close_mongo_connection() -> None:
    global mongo_client

    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
