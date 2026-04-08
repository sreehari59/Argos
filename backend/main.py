"""FastAPI application entry point for Agnes Network Intelligence."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Agnes Network Intelligence",
    description="AI-powered sourcing decision-support for CPG raw materials",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


from routes import router
app.include_router(router)
