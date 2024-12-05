from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterable, Iterator

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from docling_core.types.doc.base import CoordOrigin
from docling_core.types.doc.labels import DocItemLabel
from pandas import DataFrame
from spacy.tokens import Doc, Span, SpanGroup

from .types import Attrs, DocLayout, DoclingItem, PageLayout, SpanLayout

if TYPE_CHECKING:
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import ConversionResult, FormatOption
    from docling_core.types.doc.base import BoundingBox
    from spacy.language import Language


TABLE_PLACEHOLDER = "TABLE"


class spaCyLayout:
    def __init__(
        self,
        nlp: "Language",
        separator: str | None = "\n\n",
        attrs: dict[str, str] = {},
        headings: list[str] = [
            DocItemLabel.SECTION_HEADER,
            DocItemLabel.PAGE_HEADER,
            DocItemLabel.TITLE,
        ],
        display_table: Callable[[DataFrame], str] | str = TABLE_PLACEHOLDER,
        docling_options: dict["InputFormat", "FormatOption"] | None = None,
    ) -> None:
        """Initialize the layout parser and Docling converter."""
        self.nlp = nlp
        self.sep = separator
        self.attrs = Attrs(
            doc_layout=attrs.get("doc_layout", "layout"),
            doc_pages=attrs.get("doc_pages", "pages"),
            doc_tables=attrs.get("doc_tables", "tables"),
            span_layout=attrs.get("span_layout", "layout"),
            span_heading=attrs.get("span_heading", "heading"),
            span_data=attrs.get("span_data", "data"),
            span_group=attrs.get("span_group", "layout"),
        )
        self.headings = headings
        self.display_table = display_table
        self.converter = DocumentConverter(format_options=docling_options)
        # Set spaCy extension attributes for custom data
        Doc.set_extension(self.attrs.doc_layout_internal, default=None, force=True)
        Doc.set_extension(self.attrs.doc_layout, getter=self.get_doc_layout, force=True)
        Doc.set_extension(self.attrs.doc_pages, getter=self.get_pages, force=True)
        Doc.set_extension(self.attrs.doc_tables, getter=self.get_tables, force=True)
        Span.set_extension(self.attrs.span_layout_internal, default=None, force=True)
        Span.set_extension(
            self.attrs.span_layout, getter=self.get_span_layout, force=True
        )
        Span.set_extension(self.attrs.span_data_internal, default=None, force=True)
        Span.set_extension(self.attrs.span_data, getter=self.get_span_data, force=True)
        Span.set_extension(self.attrs.span_heading, getter=self.get_heading, force=True)

    def __call__(self, source: str | Path | bytes) -> Doc:
        """Call parser on a path to create a spaCy Doc object."""
        result = self.converter.convert(self._get_source(source))
        return self._result_to_doc(result)

    def pipe(self, sources: Iterable[str | Path | bytes]) -> Iterator[Doc]:
        """Process multiple documents and create spaCy Doc objects."""
        data = (self._get_source(source) for source in sources)
        results = self.converter.convert_all(data)
        for result in results:
            yield self._result_to_doc(result)

    def _get_source(self, source: str | Path | bytes) -> str | Path | DocumentStream:
        if isinstance(source, (str, Path)):
            return source
        return DocumentStream(name="source", stream=BytesIO(source))

    def _result_to_doc(self, result: "ConversionResult") -> Doc:
        inputs = []
        pages = {
            (page.page_no + 1): PageLayout(
                page_no=page.page_no + 1,
                width=page.size.width if page.size else 0,
                height=page.size.height if page.size else 0,
            )
            for page in result.pages
        }
        text_items = {item.self_ref: item for item in result.document.texts}
        table_items = {item.self_ref: item for item in result.document.tables}
        # We want to iterate over the tree to get different elements in order
        for node, _ in result.document.iterate_items():
            if node.self_ref in text_items:
                item = text_items[node.self_ref]
                if item.text == "":
                    continue
                inputs.append((item.text, item))
            elif node.self_ref in table_items:
                item = table_items[node.self_ref]
                if isinstance(self.display_table, str):
                    table_text = self.display_table
                else:
                    table_text = self.display_table(item.export_to_dataframe())
                inputs.append((table_text, item))
        doc = self._texts_to_doc(inputs, pages)
        page_layout = {"pages": [p.to_dict() for p in pages.values()]}
        doc._.set(self.attrs.doc_layout_internal, page_layout)
        return doc

    def _texts_to_doc(
        self, inputs: list[tuple[str, DoclingItem]], pages: dict[int, PageLayout]
    ) -> Doc:
        """Convert Docling structure to spaCy Doc."""
        words = []
        spaces = []
        span_data = []
        token_idx = 0
        # Tokenize the span because we can't rely on the document parsing to
        # give us items that are not split across token boundaries
        with self.nlp.select_pipes(disable=self.nlp.pipe_names):
            for span_doc, item in self.nlp.pipe(inputs, as_tuples=True):
                words += [token.text for token in span_doc]
                spaces += [bool(token.whitespace_) for token in span_doc]
                # Add separator token and don't include it in the layout span
                if self.sep:
                    words.append(self.sep)
                    spaces[-1] = False
                    spaces.append(False)
                end = token_idx + len(span_doc)
                span_data.append((item, token_idx, end))
                token_idx += len(span_doc) + (1 if self.sep else 0)
        doc = Doc(self.nlp.vocab, words=words, spaces=spaces)
        spans = []
        for i, (item, start, end) in enumerate(span_data):
            span = Span(doc, start=start, end=end, label=item.label, span_id=i)
            layout = self._get_span_layout(item, pages)
            span._.set(self.attrs.span_layout_internal, layout)
            if item.label == DocItemLabel.TABLE:
                df = item.export_to_dataframe()
                span._.set(self.attrs.span_data_internal, df.to_dict())
            spans.append(span)
        doc.spans[self.attrs.span_group] = SpanGroup(
            doc, name=self.attrs.span_group, spans=spans
        )
        return doc

    def _get_span_layout(
        self, item: DoclingItem, pages: dict[int, PageLayout]
    ) -> dict | None:
        if item.prov:
            prov = item.prov[0]
            page = pages[prov.page_no]
            if page.width and page.height:
                x, y, width, height = get_bounding_box(prov.bbox, page.height)
                bounding_box = SpanLayout(
                    x=x, y=y, width=width, height=height, page_no=prov.page_no
                )
                return bounding_box.to_dict()

    def get_pages(self, doc: Doc) -> list[tuple[PageLayout, list[Span]]]:
        """Get all pages and their layout spans."""
        layout = doc._.get(self.attrs.doc_layout)
        pages = {page.page_no: page for page in layout.pages}
        page_spans = {page.page_no: [] for page in layout.pages}
        for span in doc.spans[self.attrs.span_group]:
            span_layout = span._.get(self.attrs.span_layout)
            page_spans[span_layout.page_no].append(span)
        return [(pages[i], page_spans[i]) for i in page_spans]

    def get_heading(self, span: Span) -> Span | None:
        """Get the closest heading for a span."""
        spans = list(span.doc.spans[self.attrs.span_group])
        if span.label_ not in self.headings:
            # Go through previous layout spans in reverse and find first match
            for candidate in spans[: span.id][::-1]:
                if candidate.label_ in self.headings:
                    return candidate

    def get_tables(self, doc: Doc) -> list[Span]:
        """Get all tables in the document."""
        return [
            span
            for span in doc.spans[self.attrs.span_group]
            if span.label_ == DocItemLabel.TABLE
        ]

    def get_doc_layout(self, doc: Doc) -> DocLayout:
        return DocLayout.from_dict(doc._.get(self.attrs.doc_layout_internal))

    def get_span_layout(self, span: Span) -> SpanLayout:
        return SpanLayout.from_dict(span._.get(self.attrs.span_layout_internal))

    def get_span_data(self, span: Span) -> DataFrame:
        return DataFrame(span._.get(self.attrs.span_data_internal))


def get_bounding_box(
    bbox: "BoundingBox", page_height: float
) -> tuple[float, float, float, float]:
    is_bottom = bbox.coord_origin == CoordOrigin.BOTTOMLEFT
    y = page_height - bbox.t if is_bottom else bbox.t
    height = bbox.t - bbox.b if is_bottom else bbox.b - bbox.t
    width = bbox.r - bbox.l
    return (bbox.l, y, width, height)
