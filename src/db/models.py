from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Integer, String, TIMESTAMP, Boolean, ForeignKey
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Link(Base):
    __tablename__ = "link"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_url: Mapped[str] = mapped_column(String, nullable=False)
    short_code: Mapped[str] = mapped_column(String, nullable=False)
    creation_date: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0)
    last_usage_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User] = relationship()
