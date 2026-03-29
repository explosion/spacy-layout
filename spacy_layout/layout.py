from io import BytesIO
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterable,
    Iterator,
    Literal,
    TypeVar,
    cast,
    overload,
)

import srsly
from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument, ContentLayer
from docling_core.types.doc.labels import DocItemLabel
from spacy.tokens import Doc, Span, SpanGroup

from .types import Attrs, DocLayout, DoclingItem, PageLayout, SpanLayout
from .util import decode_df, decode_obj, encode_df, encode_obj, get_bounding_box

if TYPE_CHECKING:
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import FormatOption
    from pandas import DataFrame
    from spacy.language import Language

# Type variable for contexts piped with documents
_AnyContext = TypeVar("_AnyContext")

TABLE_PLACEHOLDER = "TABLE"
TABLE_ITEM_LABELS = [DocItemLabel.TABLE, DocItemLabel.DOCUMENT_INDEX]

# Register msgpack encoders and decoders for custom types
srsly.msgpack_encoders.register("spacy-layout.dataclass", func=encode_obj)
srsly.msgpack_decoders.register("spacy-layout.dataclass", func=decode_obj)
srsly.msgpack_encoders.register("spacy-layout.dataframe", func=encode_df)
srsly.msgpack_decoders.register("spacy-layout.dataframe", func=decode_df)


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
        display_table: Callable[["DataFrame"], str] | str = TABLE_PLACEHOLDER,
        docling_options: dict["InputFormat", "FormatOption"] | None = None,
        content_layer_options: set[ContentLayer] = [ContentLayer.BODY],
    ) -> None:
        """Initialize the layout parser and Docling converter."""
        self.nlp = nlp
        self.sep = separator
        self.attrs = Attrs(
            doc_layout=attrs.get("doc_layout", "layout"),
            doc_pages=attrs.get("doc_pages", "pages"),
            doc_tables=attrs.get("doc_tables", "tables"),
            doc_markdown=attrs.get("doc_markdown", "markdown"),
            span_layout=attrs.get("span_layout", "layout"),
            span_heading=attrs.get("span_heading", "heading"),
            span_data=attrs.get("span_data", "data"),
            span_group=attrs.get("span_group", "layout"),
        )
        self.headings = headings
        self.display_table = display_table
        self.converter = DocumentConverter(format_options=docling_options)
        self.content_layer_options = content_layer_options
        # Set spaCy extension attributes for custom data
        Doc.set_extension(self.attrs.doc_layout, default=None, force=True)
        Doc.set_extension(self.attrs.doc_pages, getter=self.get_pages, force=True)
        Doc.set_extension(self.attrs.doc_tables, getter=self.get_tables, force=True)
        Doc.set_extension(self.attrs.doc_markdown, default=None, force=True)
        Span.set_extension(self.attrs.span_layout, default=None, force=True)
        Span.set_extension(self.attrs.span_data, default=None, force=True)
        Span.set_extension(self.attrs.span_heading, getter=self.get_heading, force=True)

    def __call__(self, source: str | Path | bytes | DoclingDocument) -> Doc:
        """Call parser on a path to create a spaCy Doc object."""
        if isinstance(source, DoclingDocument):
            result = source
        else:
            result = self.converter.convert(self._get_source(source)).document
        return self._result_to_doc(result)

    @overload
    def pipe(
        self,
        sources: Iterable[str | Path | bytes],
        as_tuples: Literal[False] = ...,
    ) -> Iterator[Doc]: ...

    @overload
    def pipe(
        self,
        sources: Iterable[tuple[str | Path | bytes, _AnyContext]],
        as_tuples: Literal[True] = ...,
    ) -> Iterator[tuple[Doc, _AnyContext]]: ...

    def pipe(
        self,
        sources: (
            Iterable[str | Path | bytes]
            | Iterable[tuple[str | Path | bytes, _AnyContext]]
        ),
        as_tuples: bool = False,
    ) -> Iterator[Doc] | Iterator[tuple[Doc, _AnyContext]]:
        """Process multiple documents and create spaCy Doc objects."""
        if as_tuples:
            sources = cast(Iterable[tuple[str | Path | bytes, _AnyContext]], sources)
            data = (self._get_source(source) for source, _ in sources)
            contexts = (context for _, context in sources)
            results = self.converter.convert_all(data)
            for result, context in zip(results, contexts):
                yield (self._result_to_doc(result.document), context)
        else:
            sources = cast(Iterable[str | Path | bytes], sources)
            data = (self._get_source(source) for source in sources)
            results = self.converter.convert_all(data)
            for result in results:
                yield self._result_to_doc(result.document)

    def _get_source(self, source: str | Path | bytes) -> str | Path | DocumentStream:
        if isinstance(source, (str, Path)):
            return source
        return DocumentStream(name="source", stream=BytesIO(source))

    def _result_to_doc(self, document: DoclingDocument) -> Doc:
        inputs = []
        pages = {
            (page.page_no): PageLayout(
                page_no=page.page_no,
                width=page.size.width if page.size else 0,
                height=page.size.height if page.size else 0,
            )
            for _, page in document.pages.items()
        }
        text_items = {item.self_ref: item for item in document.texts}
        table_items = {item.self_ref: item for item in document.tables}
        # We want to iterate over the tree to get different elements in order
        for node, _ in document.iterate_items(
            included_content_layers=self.content_layer_options
        ):
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
        doc._.set(self.attrs.doc_layout, DocLayout(pages=[p for p in pages.values()]))
        doc._.set(self.attrs.doc_markdown, document.export_to_markdown())
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
            span._.set(self.attrs.span_layout, layout)
            if item.label in TABLE_ITEM_LABELS:
                span._.set(self.attrs.span_data, item.export_to_dataframe())
            spans.append(span)
        doc.spans[self.attrs.span_group] = SpanGroup(
            doc, name=self.attrs.span_group, spans=spans
        )
        return doc

    def _get_span_layout(
        self, item: DoclingItem, pages: dict[int, PageLayout]
    ) -> SpanLayout | None:
        if item.prov:
            prov = item.prov[0]
            page = pages[prov.page_no]
            if page.width and page.height:
                x, y, width, height = get_bounding_box(prov.bbox, page.height)
                return SpanLayout(
                    x=x, y=y, width=width, height=height, page_no=prov.page_no
                )

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
            if span.label_ in TABLE_ITEM_LABELS
        ]
