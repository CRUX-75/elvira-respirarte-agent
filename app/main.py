from fastapi import FastAPI
from app.models.message import IncomingMessage
from app.graph.graph import process_message
from app.services.tracing import traced_process_message

app = FastAPI(
    title="Elvira Respirarte Agent",
    version="0.2.0",
    description="Core conversacional determinístico para Respirarte.",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "elvira-respirarte-agent",
        "version": "0.2.0",
    }


@app.post("/test/message")
def test_message(message: IncomingMessage):
    result = traced_process_message(process_message, message)
    return result.model_dump()