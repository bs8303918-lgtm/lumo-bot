from pydantic import BaseModel, Field


class GrantListItem(BaseModel):
    id: int
    flag: str
    location: str
    title: str
    description: str
    deadline: str
    features: list[str]
    isPremium: bool
    isLocked: bool = False
    premiumContent: dict | None = None


class PremiumContent(BaseModel):
    applicationUrl: str | None = None
    messageLink: str | None = None
    requirements: str | None = None
    documentTemplates: list[str] = Field(default_factory=list)
    sourceChannelName: str | None = None


class GrantDetail(GrantListItem):
    premiumContent: PremiumContent | None = None


class ExpertServiceItem(BaseModel):
    id: int
    title: str
    price: str


class CourseItem(BaseModel):
    id: int
    title: str
    description: str
    price: str


class BannerResponse(BaseModel):
    title: str
    subtitle: str
    ctaLabel: str
    ctaUrl: str


class SiteMetaResponse(BaseModel):
    title: str
    subtitle: str
    communityHandle: str
    communityUrl: str
    supportContact: str


class ContactRequest(BaseModel):
    contact: str = Field(min_length=3, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=2000)
    grantId: int | None = None


class PurchaseRequest(BaseModel):
    contact: str = Field(min_length=3, max_length=255)
    courseId: int | None = None
    serviceId: int | None = None


class MessageResponse(BaseModel):
    ok: bool = True
    message: str
