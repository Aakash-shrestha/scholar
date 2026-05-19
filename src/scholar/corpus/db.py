import datetime
from pathlib import Path

from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):  # declarative base is a parent class that tells anything that inherits
    # me is a sql table
    pass  # pass means this class is left intentionally empty, only purpose is so that other subclass
    # can inherit from this parent base class


class Paper(Base):
    """A research paper that has been ingested into the corpus."""

    __tablename__ = "papers"
    arxiv_id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    short_citation: Mapped[str]
    year: Mapped[int]
    abstract: Mapped[str]
    pdf_path: Mapped[str]  # relative path like data/papers/1706.01392
    persist_dir: Mapped[str]  # relative path like data/chroma/..
    ingested_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.UTC)
    )


def get_engine(db_path: Path = Path("data/scholar.db")) -> Engine:
    """Returns a SQLAlchemy engine connected to the specified SQLite database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine: Engine) -> None:
    """Initializes the database by creating the papers table if it doesn't exist."""
    Base.metadata.create_all(engine)
