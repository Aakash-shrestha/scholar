from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

from scholar.corpus.db import Paper, get_engine


class CorpusRepository:
    """
    Corpus Repository is the class that controls the access to the database for entire
    codebase. It is the central control of the database
    """

    def __init__(self, engine: Engine) -> None:
        """constructor initializes the repository with a database engine"""
        self.engine = engine

    def add(self, paper: Paper) -> None:
        """Adds a paper to the database."""
        with Session(self.engine) as session:
            session.add(paper)
            session.commit()

    def get(self, arxiv_id: str) -> Paper | None:
        """Gets a paper from the database by its arxiv_id. Returns None if not found."""
        with Session(self.engine) as session:
            return session.get(Paper, arxiv_id)  # using get is better here because working with
            # arxiv_id which is a pk

    def list_all(self) -> list[Paper]:
        """Lists all papers in the database in descending order of ingested_at time"""
        with Session(self.engine) as session:
            stmt = select(Paper).order_by(Paper.ingested_at.desc())
            return list(session.scalars(stmt))
