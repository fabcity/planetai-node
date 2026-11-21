"""HTTP front of core.py: GET /health, POST /forecast. The model loads once, at startup."""
from fastapi import Body, FastAPI, HTTPException

import core

app = FastAPI()
core.load()


@app.get("/health")
def health():
    return core.health()


@app.post("/forecast")
def forecast(body: dict = Body(...)):
    if core.PIPE is None:
        raise HTTPException(503, core.health()["error"])
    why = core.problem(body)
    if why:
        raise HTTPException(400, why)
    return core.answer(body)
