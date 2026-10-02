from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)


class CompanyRole(StrEnum):
    TARGET = "TARGET"
    COMPETITOR = "COMPETITOR"


class EventSource(StrEnum):
    GNEWS = "GNEWS"
    X = "X"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    companies: Mapped[list[AnalysisCompany]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    website: Mapped[str] = mapped_column(String(500))
    search_term: Mapped[str | None] = mapped_column(String(240))
    market: Mapped[str | None] = mapped_column(Text)
    products: Mapped[str | None] = mapped_column(Text)
    audience: Mapped[str | None] = mapped_column(Text)
    analyses: Mapped[list[AnalysisCompany]] = relationship(back_populates="company")
    events: Mapped[list[Event]] = relationship(back_populates="company")

    @property
    def effective_search_term(self) -> str:
        return self.search_term or self.name


class AnalysisCompany(Base):
    __tablename__ = "analysis_companies"
    __table_args__ = (
        Index(
            "uq_analysis_target",
            "analysis_id",
            unique=True,
            postgresql_where=text("role = 'TARGET'"),
            sqlite_where=text("role = 'TARGET'"),
        ),
    )

    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[CompanyRole] = mapped_column(
        Enum(CompanyRole, native_enum=False, length=16), nullable=False
    )
    analysis: Mapped[Analysis] = relationship(back_populates="companies")
    company: Mapped[Company] = relationship(back_populates="analyses")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("company_id", "source", "url", name="uq_event_company_source_url"),
        Index("ix_event_timeline", "published_at", "collected_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    source: Mapped[EventSource] = mapped_column(Enum(EventSource, native_enum=False, length=16))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000))
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime] = mapped_column(UTCDateTime())
    collected_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=lambda: datetime.now(UTC))
    company: Mapped[Company] = relationship(back_populates="events")
