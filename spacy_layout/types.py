from dataclasses import dataclass
from typing import TYPE_CHECKING

from docling_core.types.doc.document import (
    ListItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)

if TYPE_CHECKING:
    from pandas import DataFrame

DoclingItem = ListItem | SectionHeaderItem | TextItem | TableItem


@dataclass
class Attrs:
    """Custom atributes used to extend spaCy"""

    doc_layout: str
    doc_pages: str
    doc_tables: str
    span_layout: str
    span_heading: str
    span_group: str


@dataclass
class PageLayout:
    page_no: int
    width: float
    height: float


@dataclass
class DocLayout:
    """Document layout features added to Doc object"""

    pages: list[PageLayout]


@dataclass
class SpanLayout:
    """Text span layout features added to Span object"""

    x: float
    y: float
    width: float
    height: float
    page_no: int


@dataclass
class Table:
    """Tabular data in the document."""

    df: "DataFrame"
    layout: SpanLayout | None
