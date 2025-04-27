import motor.motor_asyncio
import asyncio

MONGO_URI = "mongodb://mongodb:27017?retryWrites=true&w=majority"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

db = client.get_database("app")
users = db.get_collection("users")


async def user_create(username: str, password: str):
    return await users.insert_one(
        {
            "username": username,
            "password": password,
            "stats": [0, 0, 0],
        }
    )


async def user_find(username):
    return await users.find_one({"username": username})


async def user_stats_get(username: str):
    user = await users.find_one({"username": username})
    return user["stats"] if user else None


async def user_stats_update(username: str, new_stats: dict):
    return await users.update_one(
        {"username": username}, {"$set": {"stats": new_stats}}
    )


async def top_users_get():
    top_users = await users.find().sort({"stats.0": -1}).to_list(length=10)
    return top_users
