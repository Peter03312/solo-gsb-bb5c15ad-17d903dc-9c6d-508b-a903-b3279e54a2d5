import re

from pydantic import BaseModel, Field, field_validator

DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


class QuoteIn(BaseModel):
    media_id: int = Field(gt=0)
    speaker: str | None = Field(default=None, max_length=256)
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)
    text: str = ""


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    event_date: str
    description: str = ""
    location: str = Field(default="", max_length=256)
    revision: int | None = Field(default=None, ge=1)  # required on update, ignored on create
    quotes: list[QuoteIn] = Field(default_factory=list)

    @field_validator("title", "event_date")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("不能为空")
        return v

    @field_validator("event_date")
    @classmethod
    def _check_date(cls, v: str) -> str:
        if not DATE_RE.match(v):
            raise ValueError("日期格式应为 YYYY、YYYY-MM 或 YYYY-MM-DD")
        parts = v.split("-")
        if len(parts) >= 2 and not (1 <= int(parts[1]) <= 12):
            raise ValueError("月份超出合法范围")
        if len(parts) == 3 and not (1 <= int(parts[2]) <= 31):
            raise ValueError("日期超出合法范围")
        return v


class PublishIn(BaseModel):
    label: str = Field(min_length=1, max_length=256)
    note: str = ""

    @field_validator("label")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("版本名称不能为空")
        return v
