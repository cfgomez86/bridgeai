from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CodeFile(Base):
    __tablename__ = "code_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_modified: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lines_of_code: Mapped[int] = mapped_column(Integer, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
