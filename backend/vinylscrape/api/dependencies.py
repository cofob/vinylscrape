from fastapi import Header, HTTPException

from vinylscrape.config import Config


async def verify_admin_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    config = Config()
    if x_api_key != config.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key
