from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2200)

class Source(BaseModel):
    document: str
    page: int | None = None
    score: float
    source_url: str | None = None

class ChatResponse(BaseModel):
    answer: str
    sources_found: bool
    sources: list[Source]
    response_time_ms: int

class HealthResponse(BaseModel):
    status: str
    knowledge_base_available: bool
    llm_name: str
