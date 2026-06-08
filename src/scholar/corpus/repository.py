from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

from scholar.corpus.db import Citation, Paper, Reference


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


class CitationRepository:
    """
    Citation Repository is the class that controls the access to the citations table in the database.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, source_arxiv_id: str, cited_arxiv_id: str) -> Citation | None:
        with Session(self.engine) as session:
            return session.get(Citation, (source_arxiv_id, cited_arxiv_id))

    def add(self, source_arxiv_id: str, cited_arxiv_id: str) -> None:
        if self.get(source_arxiv_id, cited_arxiv_id) is not None:
            return
        citation = Citation(
            source_arxiv_id=source_arxiv_id,
            cited_arxiv_id=cited_arxiv_id,
        )
        with Session(self.engine) as session:
            session.add(citation)
            session.commit()

    def get_cited_by(self, arxiv_id: str) -> list[Paper]:
        """returns all the papers cited by arxiv_id"""
        with Session(self.engine) as session:
            stmt = (
                select(Paper)
                .join(Citation, Paper.arxiv_id == Citation.cited_arxiv_id)
                .where(Citation.source_arxiv_id == arxiv_id)
            )
            return list(session.scalars(stmt))

    def list_all(self) -> list[Citation]:
        with Session(self.engine) as session:
            return list(session.scalars(select(Citation)))


class ReferenceRepository:
    """
    Reference Repository is the class that controls the access to the references table
    in the database.
    """

    def __init__(self, engine: Engine) -> None:
        """constructor initializes the repository with a database engine"""
        self.engine = engine

    def add(self, source_arxiv_id: str, title: str, arxiv_id: str | None) -> None:
        if source_arxiv_id is None or title is None:
            raise ValueError("source_arxiv_id and title cannot be None")

        reference = Reference(
            source_arxiv_id=source_arxiv_id,
            title=title,
            arxiv_id=arxiv_id,
        )
        with Session(self.engine) as session:
            session.merge(reference)
            session.commit()

    def get_by_source(self, source_arxiv_id: str) -> list[Reference]:
        if source_arxiv_id is None:
            raise ValueError("source_arxiv_id cannot be None")
        with Session(self.engine) as session:
            stmt = select(Reference).where(Reference.source_arxiv_id == source_arxiv_id)
            return list(session.scalars(stmt))

    def update_arxiv_id(self, source_arxiv_id: str, title: str, arxiv_id: str) -> None:
        if source_arxiv_id is None:
            raise ValueError("source_arxiv_id cannot be None")
        with Session(self.engine) as session:
            ref = session.get(Reference, (source_arxiv_id, title))
            if ref:
                ref.arxiv_id = arxiv_id
                session.commit()
