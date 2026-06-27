from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    interest_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    interest_categories_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    interest_preferences_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user_channels: Mapped[list["UserChannel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    processed_pairs: Mapped[list["ProcessedPair"]] = relationship(back_populates="user")
    sent_matches: Mapped[list["SentMatch"]] = relationship(back_populates="user")
    events: Mapped[list["Event"]] = relationship(back_populates="user")
    feedback_entries: Mapped[list["UserFeedback"]] = relationship(back_populates="user")
    opportunity_submissions: Mapped[list["OpportunitySubmission"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SeedChannel(Base):
    __tablename__ = "seed_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_identifier: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserChannel(Base):
    __tablename__ = "user_channels"
    __table_args__ = (UniqueConstraint("user_id", "channel_identifier", name="uq_user_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    channel_identifier: Mapped[str] = mapped_column(String(255), index=True)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="user_channels")


class MonitoredChannel(Base):
    __tablename__ = "monitored_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_identifier: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    telegram_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_checked_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    source_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    raw_messages: Mapped[list["RawMessage"]] = relationship(
        back_populates="monitored_channel",
        passive_deletes=True,
    )


class RawMessage(Base):
    __tablename__ = "raw_messages"
    __table_args__ = (
        UniqueConstraint("monitored_channel_id", "telegram_message_id", name="uq_channel_message"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitored_channel_id: Mapped[int] = mapped_column(
        ForeignKey("monitored_channels.id", ondelete="CASCADE"), index=True
    )
    telegram_message_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(Text)
    message_link: Mapped[str] = mapped_column(String(512))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    monitored_channel: Mapped["MonitoredChannel"] = relationship(back_populates="raw_messages")
    processed_pairs: Mapped[list["ProcessedPair"]] = relationship(back_populates="raw_message")
    sent_matches: Mapped[list["SentMatch"]] = relationship(back_populates="raw_message")
    catalog_opportunity: Mapped["CatalogOpportunity | None"] = relationship(
        back_populates="raw_message", uselist=False
    )


class ProcessedPair(Base):
    __tablename__ = "processed_pairs"
    __table_args__ = (UniqueConstraint("user_id", "raw_message_id", name="uq_processed_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    raw_message_id: Mapped[int] = mapped_column(ForeignKey("raw_messages.id", ondelete="CASCADE"), index=True)
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    llm_response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="processed_pairs")
    raw_message: Mapped["RawMessage"] = relationship(back_populates="processed_pairs")


class SentMatch(Base):
    __tablename__ = "sent_matches"
    __table_args__ = (UniqueConstraint("user_id", "raw_message_id", name="uq_sent_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    raw_message_id: Mapped[int] = mapped_column(ForeignKey("raw_messages.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    opportunity_type: Mapped[str] = mapped_column(String(64))
    deadline: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_channel_name: Mapped[str] = mapped_column(String(255))
    message_link: Mapped[str] = mapped_column(String(512))
    application_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sent_matches")
    raw_message: Mapped["RawMessage"] = relationship(back_populates="sent_matches")


class CatalogOpportunity(Base):
    """Классифицированный пост — один раз через LLM, раздаётся пользователям по категориям."""

    __tablename__ = "catalog_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_message_id: Mapped[int] = mapped_column(
        ForeignKey("raw_messages.id", ondelete="CASCADE"), unique=True, index=True
    )
    opportunity_type: Mapped[str] = mapped_column(String(64), index=True)
    tags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    deadline: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_channel_name: Mapped[str] = mapped_column(String(255))
    message_link: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", index=True)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    raw_message: Mapped["RawMessage"] = relationship(back_populates="catalog_opportunity")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped["User | None"] = relationship(back_populates="events")


class SystemState(Base):
    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Grant(Base):
    __tablename__ = "grants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag: Mapped[str] = mapped_column(String(16), default="🌍")
    location: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(512), index=True)
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[str] = mapped_column(String(128))
    features_json: Mapped[str] = mapped_column(Text, default="[]")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    application_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    message_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_templates_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_channel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpertService(Base):
    __tablename__ = "expert_services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    price_display: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    price_display: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


class UserFeedback(Base):
    """Баги и идеи от пользователей (Mini App / бот)."""

    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), default="mini_app", server_default="mini_app")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped["User | None"] = relationship(back_populates="feedback_entries")


class OpportunitySubmission(Base):
    """Пользовательская заявка на добавление возможности (модерация)."""

    __tablename__ = "opportunity_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_mode: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    opportunity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(128), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_opportunities.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="opportunity_submissions")


class InterestReviewRequest(Base):
    """Запрос админу: новая категория или вопросы по профилю пользователя."""

    __tablename__ = "interest_review_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    interest_query: Mapped[str] = mapped_column(Text)
    proposed_domains_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    questions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending", index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()


class PromoCampaignDelivery(Base):
    """Кому уже отправили промо-кампанию (без дублей)."""

    __tablename__ = "promo_campaign_deliveries"

    campaign_slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tier: Mapped[str] = mapped_column(String(16), default="default", server_default="default")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()


class TrainingSample(Base):
    """Сэмплы для будущего обучения / fine-tuning моделей Lumo."""

    __tablename__ = "training_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String(32), index=True)
    raw_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_opportunities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_channel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_json: Mapped[str] = mapped_column(Text)
    output_json: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ContactLead(Base):
    __tablename__ = "contact_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact: Mapped[str] = mapped_column(String(255))
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    grant_id: Mapped[int | None] = mapped_column(ForeignKey("grants.id", ondelete="SET NULL"), nullable=True)
    lead_type: Mapped[str] = mapped_column(String(32), default="contact", server_default="contact")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
