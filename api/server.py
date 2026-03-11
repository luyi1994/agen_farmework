from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.chat import router as chat_router
from api.routes.memory import router as memory_router

app = FastAPI(
    title="Agent Framework API",
    description="通用 Python Agent 框架 REST API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, tags=["Chat"])
app.include_router(memory_router, tags=["Memory & Tools"])


@app.get("/health")
def health():
    return {"status": "ok"}
