import argparse
import asyncio
import logging
import uuid

from neo4j import AsyncGraphDatabase

from bracc.config import settings
from bracc.services import auth_service
from bracc.services.neo4j_service import execute_query_single

logger = logging.getLogger(__name__)


async def create_dev_user(email: str, password: str) -> None:
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        async with driver.session(database=settings.neo4j_database) as session:
            existing = await auth_service.authenticate_user(session, email, password)
            if existing:
                logger.debug(f"User {email} already exists.")
                return
            try:
                user = await auth_service.register_user(
                    session,
                    email=email,
                    password=password,
                    invite_code=settings.invite_code
                )
                logger.debug(f"User created successfully: {user.email} (ID: {user.id})")
            except ValueError as e:
                if str(e) == "Invalid invite code":

                    password_hash = auth_service.hash_password(password)
                    record = await execute_query_single(
                        session,
                        "user_create",
                        {"id": str(uuid.uuid4()), "email": email, "password_hash": password_hash},
                    )
                    if record:
                        logger.debug(
                            f"User created successfully (bypassing invite code): "
                            f"{record['email']} (ID: {record['id']})"
                        )
                    else:
                        logger.error("Failed to create user (no record returned)")
                else:
                    raise e
    finally:
        await driver.close()

async def run_cli() -> None:
    parser = argparse.ArgumentParser(description="Create a development user for BRACC")
    parser.add_argument("--email", default="admin@bracc.dev", help="User email")
    parser.add_argument("--password", default="password123", help="User password")

    args = parser.parse_args()

    await create_dev_user(args.email, args.password)

def main() -> None:
    asyncio.run(run_cli())

if __name__ == "__main__":
    main()
