from pathlib import Path

import pytest
import spacy
import srsly
from docling_core.types.doc.base import BoundingBox, CoordOrigin
from docling_core.types.doc.labels import DocItemLabel
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from spacy.tokens import DocBin

from spacy_layout import spaCyLayout
from spacy_layout.layout import TABLE_PLACEHOLDER, get_bounding_box
from spacy_layout.types import DocLayout, PageLayout, SpanLayout

PDF_STARCRAFT = Path(__file__).parent / "data" / "starcraft.pdf"
PDF_SIMPLE = Path(__file__).parent / "data" / "simple.pdf"
DOCX_SIMPLE = Path(__file__).parent / "data" / "simple.docx"
PDF_SIMPLE_BYTES = PDF_SIMPLE.open("rb").read()
PDF_TABLE = Path(__file__).parent / "data" / "table.pdf"


@pytest.fixture
def nlp():
    return spacy.blank("en")


@pytest.fixture
def span_labels():
    return [label.value for label in DocItemLabel]


@pytest.mark.parametrize("path", [PDF_STARCRAFT, PDF_SIMPLE, PDF_SIMPLE_BYTES])
def test_general(path, nlp, span_labels):
    layout = spaCyLayout(nlp)
    doc = layout(path)
    assert isinstance(doc._.get(layout.attrs.doc_layout), DocLayout)
    for span in doc.spans[layout.attrs.span_group]:
        assert span.text
        assert span.label_ in span_labels
        assert isinstance(span._.get(layout.attrs.span_layout), SpanLayout)

@pytest.mark.parametrize("path, pg_no", [(PDF_STARCRAFT, 6), (PDF_SIMPLE, 1)])
def test_pages(path, pg_no, nlp):
    layout = spaCyLayout(nlp)
    doc = layout(path)
    # This should not raise a KeyError when accessing `pages` dict
    # Key Error would mean a mismatched pagination on document layout and span layout
    result = layout.get_pages(doc)
    assert len(result) == pg_no
    assert result[0][0].page_no == 1
    if pg_no == 6:
        # there should be 18 spans on the pg_no 1
        assert len(result[0][1]) == 18
    elif pg_no == 1:
        # there should be 4 spans on pg_no 1
        assert len(result[0][1]) == 4


@pytest.mark.parametrize("path", [PDF_SIMPLE, DOCX_SIMPLE])
@pytest.mark.parametrize("separator", ["\n\n", ""])
def test_simple(path, separator, nlp):
    layout = spaCyLayout(nlp, separator=separator)
    doc = layout(path)
    assert len(doc.spans[layout.attrs.span_group]) == 4
    assert doc.text.startswith(f"Lorem ipsum dolor sit amet{separator}")
    assert doc.spans[layout.attrs.span_group][0].text == "Lorem ipsum dolor sit amet"


def test_simple_pipe(nlp):
    layout = spaCyLayout(nlp)
    for doc in layout.pipe([PDF_SIMPLE, DOCX_SIMPLE]):
        assert len(doc.spans[layout.attrs.span_group]) == 4


def test_fix_text(nlp):
    def fix_text(text):
        return text.replace("Lorem", "LOREM")

    layout = spaCyLayout(nlp, fix_text=fix_text)
    doc = layout(PDF_SIMPLE)
    assert doc.text.startswith("LOREM ipsum dolor sit amet")


def test_table(nlp):
    layout = spaCyLayout(nlp)
    doc = layout(PDF_TABLE)
    assert len(doc._.get(layout.attrs.doc_tables)) == 1
    table = doc._.get(layout.attrs.doc_tables)[0]
    assert table.text == TABLE_PLACEHOLDER
    df = table._.get(layout.attrs.span_data)
    assert df.columns.tolist() == ["Name", "Type", "Place of birth"]
    assert df.to_dict(orient="list") == {
        "Name": ["Ines", "Matt", "Baikal", "Stanislav Petrov"],
        "Type": ["human", "human", "cat", "cat"],
        "Place of birth": [
            "Cologne, Germany",
            "Sydney, Australia",
            "Berlin, Germany",
            "Chernihiv, Ukraine",
        ],
    }
    markdown = (
        "| Name             | Type   | Place of birth     |\n"
        "|------------------|--------|--------------------|\n"
        "| Ines             | human  | Cologne, Germany   |\n"
        "| Matt             | human  | Sydney, Australia  |\n"
        "| Baikal           | cat    | Berlin, Germany    |\n"
        "| Stanislav Petrov | cat    | Chernihiv, Ukraine |\n"
    )
    assert markdown in doc._.get(layout.attrs.doc_markdown)


def test_table_placeholder(nlp):
    def display_table(df):
        return f"Table with columns: {', '.join(df.columns.tolist())}"

    layout = spaCyLayout(nlp, display_table=display_table)
    doc = layout(PDF_TABLE)
    table = doc._.get(layout.attrs.doc_tables)[0]
    assert table.text == "Table with columns: Name, Type, Place of birth"


@pytest.mark.parametrize(
    "box,page_height,expected",
    [
        (
            (200.0, 50.0, 100.0, 400.0, CoordOrigin.BOTTOMLEFT),
            1000.0,
            (100.0, 800.0, 300.0, 150.0),
        ),
        (
            (200.0, 250.0, 100.0, 400.0, CoordOrigin.TOPLEFT),
            1000.0,
            (100.0, 200.0, 300.0, 50.0),
        ),
        (
            (
                648.3192749023438,
                633.4112548828125,
                155.50897216796875,
                239.66929626464844,
                CoordOrigin.BOTTOMLEFT,
            ),
            792.0,
            (
                155.50897216796875,
                143.68072509765625,
                84.16032409667969,
                14.90802001953125,
            ),
        ),
    ],
)
def test_bounding_box(box, page_height, expected):
    top, bottom, left, right, origin = box
    bbox = BoundingBox(t=top, b=bottom, l=left, r=right, coord_origin=origin)
    assert get_bounding_box(bbox, page_height) == expected


def test_serialize_objects():
    span_layout = SpanLayout(x=10, y=20, width=30, height=40, page_no=1)
    doc_layout = DocLayout(pages=[PageLayout(page_no=1, width=500, height=600)])
    bytes_data = srsly.msgpack_dumps({"span": span_layout, "doc": doc_layout})
    data = srsly.msgpack_loads(bytes_data)
    assert isinstance(data, dict)
    assert data["span"] == span_layout
    assert data["doc"] == doc_layout
    df = DataFrame(data={"col1": [1, 2], "col2": [3, 4]})
    bytes_data = srsly.msgpack_dumps({"df": df})
    data = srsly.msgpack_loads(bytes_data)
    assert isinstance(data, dict)
    assert_frame_equal(df, data["df"])


@pytest.mark.parametrize("path", [PDF_SIMPLE, PDF_TABLE])
def test_serialize_roundtrip(path, nlp):
    layout = spaCyLayout(nlp)
    doc = layout(path)
    doc_bin = DocBin(store_user_data=True)
    doc_bin.add(doc)
    bytes_data = doc_bin.to_bytes()
    new_doc_bin = DocBin().from_bytes(bytes_data)
    new_doc = list(new_doc_bin.get_docs(nlp.vocab))[0]
    layout_spans = new_doc.spans[layout.attrs.span_group]
    assert len(layout_spans) == len(doc.spans[layout.attrs.span_group])
    assert all(
        isinstance(span._.get(layout.attrs.span_layout), SpanLayout)
        for span in layout_spans
    )
    assert isinstance(new_doc._.get(layout.attrs.doc_layout), DocLayout)
    tables = doc._.get(layout.attrs.doc_tables)
    new_tables = new_doc._.get(layout.attrs.doc_tables)
    for before, after in zip(tables, new_tables):
        table_before = before._.get(layout.attrs.span_data)
        table_after = after._.get(layout.attrs.span_data)
        assert_frame_equal(table_before, table_after)
