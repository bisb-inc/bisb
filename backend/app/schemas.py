from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import (
    AnalysisEngine,
    CompanyRole,
    CompetitiveImpact,
    EventAnalysisCategory,
    EventSentiment,
    EventSource,
)


class CompanyInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    website: str = Field(min_length=1, max_length=500)
    search_term: str | None = Field(default=None, max_length=240)
    market: str | None = None
    products: str | None = None
    audience: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome da empresa é obrigatório")
        return value

    @field_validator("website")
    @classmethod
    def strip_website(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O site da empresa é obrigatório")
        return value


class AnalysisCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    target: CompanyInput
    competitors: list[CompanyInput] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome da análise é obrigatório")
        return value


class CompanyRead(CompanyInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    effective_search_term: str


class AnalysisCompanyRead(BaseModel):
    role: CompanyRole
    company: CompanyRead


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime
    companies: list[AnalysisCompanyRead]


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    source: EventSource
    title: str
    description: str | None
    url: str
    is_mock: bool
    published_at: datetime
    collected_at: datetime


class EventAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    summary: str
    category: EventAnalysisCategory
    competitive_impact: CompetitiveImpact
    sentiment: EventSentiment
    relevance_score: int = Field(ge=0, le=100)
    justification: str
    provider: AnalysisEngine
    model: str
    is_mock: bool
    created_at: datetime
    updated_at: datetime


class CollectionRequest(BaseModel):
    from_date: date
    to_date: date

    @model_validator(mode="after")
    def validate_range(self):
        if self.from_date > self.to_date:
            raise ValueError("A data inicial deve ser anterior ou igual à data final")
        return self


class ProviderOutcome(BaseModel):
    source: EventSource
    company_id: int
    status: str
    fetched: int = 0
    persisted: int = 0
    error: str | None = None


class CollectionResult(BaseModel):
    status: str
    providers: list[ProviderOutcome]
    fetched: int
    persisted: int
