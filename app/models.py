from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


class IngestResponse(BaseModel):
    status: str
    chunks_count: int
