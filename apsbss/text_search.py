"""
Support text search of ESAFs and Proposals using the Whoosh package.

.. autosummary::
    ~SearchEngine
"""

import logging

from whoosh.fields import DATETIME
from whoosh.fields import NUMERIC
from whoosh.fields import TEXT
from whoosh.fields import Schema
from whoosh.filedb.filestore import RamStorage
from whoosh.index import FileIndex
from whoosh.qparser import QueryParser

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Search ESAFs & Proposals for text.

    .. autosummary::
        ~index_esafs
        ~index_proposals
        ~search
    """

    def __init__(self):
        """
        Setup the Whoosh index.
        """
        # Items marked as 'stored=True' will appear in results dictionaries.
        self.schema = Schema(
            type=TEXT(stored=True),
            id=NUMERIC(stored=True),
            pi=TEXT(stored=True),
            run=TEXT(stored=True),
            title=TEXT(stored=True),
            full=TEXT,
            startDate=DATETIME,
            endDate=DATETIME,
            users=TEXT,
        )
        storage = RamStorage()  # RAM, not file, storage of the index.
        self.idx = FileIndex.create(storage, self.schema, "MAIN")

    def _index(self, _type: str, members: list) -> None:
        """Index the list of content."""
        writer = self.idx.writer()
        for item in members:
            writer.add_document(
                type=_type,
                id=getattr(item, f"{_type.lower()}_id"),
                endDate=item.endDate,
                full=str(item._raw),
                pi=item.pi,
                run=item.run,
                startDate=item.startDate,
                title=item.title,
                users=", ".join([str(u) for u in item._users]),
            )
        writer.commit()

    def index_esafs(self, esafs: list) -> None:
        """Index a list of ESAFs."""
        self._index("ESAF", esafs)

    def index_proposals(self, proposals: list) -> None:
        """Index a **list** of proposals."""
        self._index("proposal", proposals)

    def search(self, query, default_key="full") -> list:
        """Return a list of hits matching the query."""
        with self.idx.searcher() as searcher:
            parser = QueryParser(default_key, self.idx.schema)
            if isinstance(query, str):
                query = parser.parse(query)
            return [dict(hit) for hit in searcher.search(query)]
