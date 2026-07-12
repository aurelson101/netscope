from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.core.config import settings
from app.db.init import init_db
from app.core.logging import configure_logging
import logging
import time
from fastapi import Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(); yield


configure_logging()
logger=logging.getLogger("netscope.api")
app=FastAPI(title=settings.app_name,version="0.0.2",lifespan=lifespan,docs_url="/api/docs",openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_list,allow_credentials=True,allow_methods=["GET","POST","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type","X-MFA-Code"])
app.include_router(router)


@app.middleware("http")
async def request_log(request:Request,call_next):
    started=time.perf_counter()
    try:
        response=await call_next(request)
    except Exception:
        logger.exception("unhandled_request_error",extra={"method":request.method,"path":request.url.path,"duration_ms":round((time.perf_counter()-started)*1000,2)})
        raise
    logger.info("request",extra={"method":request.method,"path":request.url.path,"status":response.status_code,"duration_ms":round((time.perf_counter()-started)*1000,2)})
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="no-referrer"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"]="no-store" if request.url.path.startswith("/api/") else response.headers.get("Cache-Control","no-cache")
    return response


@app.get("/health")
async def health(): return {"status":"ok","service":"api"}
