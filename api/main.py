import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "port": os.getenv("PORT", "8080")}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "working"}
