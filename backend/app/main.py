from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, course, me
from app.core.config import settings

app = FastAPI(
    title="Ariadne API",
    description="Gamified, adaptive tutor for graphs and depth-first search (COS750).",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, me.router, course.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
