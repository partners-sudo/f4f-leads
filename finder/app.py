from fastapi import FastAPI
from finder.tasks import validate_domain

app = FastAPI()

@app.get("/ping")
def ping():
    return {"ok": True}

@app.post("/validate")
def trigger(domain: str):
    result = validate_domain.delay(domain)
    return {"task_id": result.id}
