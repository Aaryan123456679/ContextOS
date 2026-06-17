from fastapi import Request, HTTPException
from core.config import settings

# Routes that are fully public (no auth check at all)
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


async def auth_middleware(request: Request, call_next):
    """
    MVP auth: no mandatory server-side token.
    The user provides their own LLM API key in the request body — validated
    downstream by the LLM provider.

    This middleware is a placeholder for future JWT / Supabase Auth integration.
    It currently allows all requests through and only blocks if an
    X-Admin-Token header is present but wrong (for future admin routes).
    """
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    admin_token = request.headers.get("X-Admin-Token")
    if admin_token and admin_token != settings.RENDER_HEALTHCHECK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    return await call_next(request)
