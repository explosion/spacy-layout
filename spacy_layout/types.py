from dataclasses import asdict, dataclass

from docling_core.types.doc.document import (
    ListItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
)

DoclingItem = ListItem | SectionHeaderItem | TextItem | TableItem


@dataclass
class Attrs:
    """Custom atributes used to extend spaCy"""

    doc_layout: str
    doc_pages: str
    doc_tables: str
    span_layout: str
    span_data: str
    span_heading: str
    span_group: str
    doc_layout_internal: str = "_doc_layout"
    span_layout_internal: str = "_span_layout"
    span_data_internal: str = "_span_data"


@dataclass
class PageLayout:
    page_no: int
    width: float
    height: float

    def to_dict(self) -> dict:
        return {"page_no": self.page_no, "width": self.width, "height": self.height}


@dataclass
class DocLayout:
    """Document layout features added to Doc object"""

    pages: list[PageLayout]

    @classmethod
    def from_dict(cls, data: dict) -> "DocLayout":
        return cls(pages=[PageLayout(**page) for page in data["pages"]])


@dataclass
class SpanLayout:
    """Text span layout features added to Span object"""

    x: float
    y: float
    width: float
    height: float
    page_no: int

    @classmethod
    def from_dict(cls, data: dict) -> "SpanLayout":
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)
