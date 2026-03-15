"""SQLAlchemy ORM models."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    # private_email: supplied by the caller (personal/private inbox)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # corporate_email: derived as name.surname@b2.com
    corporate_email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    private_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    temp_password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    line_manager: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
