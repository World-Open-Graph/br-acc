from pydantic import BaseModel, Field


class InvestigationCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class InvestigationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)


class InvestigationResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    created_at: str
    updated_at: str
    entity_ids: list[str] = []
    share_token: str | None = None
    share_expires_at: str | None = None


class InvestigationListResponse(BaseModel):
    investigations: list[InvestigationResponse]
    total: int


class Annotation(BaseModel):
    id: str
    entity_id: str
    investigation_id: str
    text: str
    created_at: str


class AnnotationCreate(BaseModel):
    entity_id: str
    text: str = Field(max_length=5000)


class Tag(BaseModel):
    id: str
    investigation_id: str
    name: str
    color: str


class TagCreate(BaseModel):
    name: str = Field(max_length=50)
    color: str = Field(default="#E07A2F", max_length=7)
