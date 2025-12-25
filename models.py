from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, NonNegativeInt, conint, constr


# Core identifiers and common fields
class Provider(str, Enum):
    sendgrid = "sendgrid"
    # extend with other providers e.g., mailgun = "mailgun"


class MessageStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    delivered = "delivered"
    bounced = "bounced"
    dropped = "dropped"
    deferred = "deferred"
    complained = "complained"
    failed = "failed"
    unknown = "unknown"


class Variant(str, Enum):
    A = "A"
    B = "B"
    C = "C"


# Audience and Segmentation
class AudienceMember(BaseModel):
    recipient_id: constr(strip_whitespace=True, min_length=1)
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    # consent flags
    subscribed: bool = True
    suppressed: bool = False
    # arbitrary profile traits used for segmentation/personalization
    traits: Dict[str, Any] = Field(default_factory=dict)


class SegmentRule(BaseModel):
    # Simple rule expression or a structured rule representation
    # Example: expression="traits.plan == 'pro' and traits.mau > 100"
    expression: str = Field(..., description="Boolean expression evaluated against AudienceMember context")
    name: Optional[str] = None


class Segment(BaseModel):
    segment_id: constr(strip_whitespace=True, min_length=1)
    name: Optional[str] = None
    description: Optional[str] = None
    rules: List[SegmentRule] = Field(default_factory=list)


# Campaign and Experimentation
class ABTestConfig(BaseModel):
    variants: List[Variant] = Field(default_factory=lambda: [Variant.A, Variant.B])
    splits: List[int] = Field(default_factory=lambda: [50, 50], description="Percentage split across variants (must sum to 100)")
    sticky_salt: str = Field("default", description="Salt for consistent hashing assignment")

    @property
    def distribution(self) -> Dict[Variant, int]:
        return {v: self.splits[i] for i, v in enumerate(self.variants)}

    def validate_distribution(self) -> None:
        if len(self.variants) != len(self.splits):
            raise ValueError("variants and splits length mismatch")
        if sum(self.splits) != 100:
            raise ValueError("A/B splits must sum to 100")
        if any(s < 0 for s in self.splits):
            raise ValueError("A/B splits must be non-negative")


class Campaign(BaseModel):
    campaign_id: constr(strip_whitespace=True, min_length=1)
    name: Optional[str] = None
    provider: Provider = Provider.sendgrid
    subject_templates: Dict[Variant, str]
    body_templates: Dict[Variant, str]
    from_email: EmailStr
    from_name: Optional[str] = None
    reply_to: Optional[EmailStr] = None
    list_unsubscribe: Optional[HttpUrl] = None
    ab_test: Optional[ABTestConfig] = None
    categories: List[str] = Field(default_factory=list)
    custom_args: Dict[str, str] = Field(default_factory=dict)


# Personalization
class PersonalizedMessage(BaseModel):
    campaign_id: str
    recipient: AudienceMember
    variant: Variant = Variant.A
    subject: str
    html_body: str
    text_body: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    custom_args: Dict[str, str] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)


# Delivery
class DeliveryRequest(BaseModel):
    campaign_id: str
    variant: Variant
    recipient: AudienceMember
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_email: EmailStr
    from_name: Optional[str] = None
    reply_to: Optional[EmailStr] = None
    list_unsubscribe: Optional[HttpUrl] = None
    categories: List[str] = Field(default_factory=list)
    custom_args: Dict[str, str] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)


class DeliveryResult(BaseModel):
    campaign_id: str
    recipient_id: str
    email: EmailStr
    variant: Variant
    provider: Provider
    status: MessageStatus
    message_id: Optional[str] = None
    provider_status_code: Optional[int] = None
    error: Optional[str] = None
    retryable: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Reporting
class EventType(str, Enum):
    processed = "processed"
    delivered = "delivered"
    open = "open"
    click = "click"
    bounce = "bounce"
    dropped = "dropped"
    spamreport = "spamreport"
    unsubscribe = "unsubscribe"


class DeliveryEvent(BaseModel):
    event: EventType
    campaign_id: str
    recipient_id: str
    email: EmailStr
    variant: Variant
    provider: Provider
    message_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    meta: Dict[str, Any] = Field(default_factory=dict)


class SegmentReport(BaseModel):
    segment_id: str
    counts: Dict[str, int] = Field(default_factory=dict)  # e.g., {"sent": 100, "open": 40}
    variant_breakdown: Dict[Variant, Dict[str, int]] = Field(default_factory=dict)


class CampaignReport(BaseModel):
    campaign_id: str
    totals: Dict[str, int] = Field(default_factory=dict)
    segments: List[SegmentReport] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# Pagination / batching helpers
class BatchConfig(BaseModel):
    batch_size: conint(gt=0) = 100
    max_concurrency: conint(gt=0) = 5
    rate_limit_per_minute: Optional[NonNegativeInt] = None


# Utility models
class ValidationIssue(BaseModel):
    recipient_id: Optional[str] = None
    email: Optional[str] = None
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"


class ValidationReport(BaseModel):
    campaign_id: str
    issues: List[ValidationIssue] = Field(default_factory=list)
    valid_count: int = 0
    invalid_count: int = 0


__all__ = [
    "Provider",
    "MessageStatus",
    "Variant",
    "AudienceMember",
    "SegmentRule",
    "Segment",
    "ABTestConfig",
    "Campaign",
    "PersonalizedMessage",
    "DeliveryRequest",
    "DeliveryResult",
    "EventType",
    "DeliveryEvent",
    "SegmentReport",
    "CampaignReport",
    "BatchConfig",
    "ValidationIssue",
    "ValidationReport",
]
