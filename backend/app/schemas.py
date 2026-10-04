"""请求体 Pydantic 模型。"""
from pydantic import BaseModel, Field


class QuoteIn(BaseModel):
    # 创建时 id 为空（None）；保存修订时可携带已有引文 id（前端不强制使用）
    id: int | None = None
    audio_id: int
    speaker: str = Field("", max_length=200)
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)
    quote_text: str = Field("", max_length=5000)


class EventIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    event_date: str = Field(min_length=8, max_length=10)  # YYYY-MM-DD
    description: str = Field("", max_length=10000)
    quotes: list[QuoteIn] = Field(default_factory=list)
    # 乐观锁：编辑时必须携带当前 revision，服务端据此检测并发冲突
    base_revision: int | None = None


class PublishIn(BaseModel):
    note: str = Field("", max_length=500)
