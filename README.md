<a href="https://explosion.ai"><img src="https://explosion.ai/assets/img/logo.svg" width="125" height="125" align="right" /></a>

# spaCy Layout: Process PDFs, Word documents and more with spaCy

This plugin integrates with [Docling](https://ds4sd.github.io/docling/) to bring structured processing of **PDFs**, **Word documents** and other input formats to your [spaCy](https://spacy.io) pipeline. It outputs clean, **structured data** in a text-based format and outputs spaCy's familiar [`Doc`](https://spacy.io/api/doc) objects that let you accessed labelled text spans like sections, headings, or footnotes.

This workflow makes it easy to apply powerful **NLP techniques** to your documents, including linguistic analysis, named entity recognition, text classification and more. It's also great for implementing **chunking for RAG** pipelines.

[![Test](https://github.com/explosion/spacy-layout/actions/workflows/test.yml/badge.svg)](https://github.com/explosion/spacy-layout/actions/workflows/test.yml)
[![Current Release Version](https://img.shields.io/github/release/explosion/spacy-layout.svg?style=flat-square&logo=github&include_prereleases)](https://github.com/explosion/spacy-layout/releases)
[![pypi Version](https://img.shields.io/pypi/v/spacy-layout.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/spacy-layout/)
[![Built with spaCy](https://img.shields.io/badge/built%20with-spaCy-09a3d5.svg?style=flat-square)](https://spacy.io)

## 📝 Usage

> ⚠️ This package requires **Python 3.10** or above.

```bash
pip install spacy-layout
```

After initializing the `spaCyLayout` preprocessor with an `nlp` object for tokenization, you can call it on a document path to convert it to structured data. The resulting `Doc` object includes layout spans that map into the original raw text and expose various attributes, including the content type and layout features.

```python
import spacy
from spacy_layout import spaCyLayout

nlp = spacy.blank("en")
layout = spaCyLayout(nlp)

# Process a document and create a spaCy Doc object
doc = layout("./starcraft.pdf")

# The text-based contents of the document
print(doc.text)
# Document layout including pages and page sizes
print(doc._.layout)

# Layout spans for different sections
for span in doc.spans["layout"]:
    # Document section and token and character offsets into the text
    print(span.text, span.start, span.end, span.start_char, span.end_char)
    # Section type, e.g. "text", "title", "section_header" etc.
    print(span.label_)
    # Layout features of the section, including bounding box
    print(span._.layout)
    # Closest heading to the span (accuracy depends on document structure)
    print(span._.heading)
```

After you've processed the documents, you can [serialize](https://spacy.io/usage/saving-loading#docs) the structured `Doc` objects in spaCy's efficient binary format, so you don't have to re-run the resource-intensive conversion.

spaCy also allows you to call the `nlp` object on an already created `Doc`, so you can easily apply a pipeline of components for [linguistic analysis](https://spacy.io/usage/linguistic-features) or [named entity recognition](https://spacy.io/usage/linguistic-features#named-entities), use [rule-based matching](https://spacy.io/usage/rule-based-matching) or anything else you can do with spaCy.

```python
# Load the transformer-based English pipeline
# Installation: python -m spacy download en_core_web_trf
nlp = spacy.load("en_core_web_trf")
layout = spaCyLayout(nlp)

doc = layout("./starcraft.pdf")
# Apply the pipeline to access POS tags, dependencies, entities etc.
doc = nlp(doc)
```

## 🎛️ API

### Data and extension attributes

```python
layout = spaCyLayout(nlp)
doc = layout("./starcraft.pdf")
print(doc._.layout)
for span in doc.spans["layout"]:
    print(span.label_, span._.layout)
```

| Attribute | Type | Description |
| --- | --- | --- |
| `Doc._.layout` | `DocLayout` | Layout features of the document. |
| `Doc._.pages` | `list[tuple[PageLayout, list[Span]]]` | Pages in the document and the spans they contain. |
| `Doc.spans["layout"]` | `spacy.tokens.SpanGroup` | The layout spans in the document. |
| `Span.label_` | `str` | The type of the extracted layout span, e.g. `"text"` or `"section_header"`. [See here](https://github.com/DS4SD/docling-core/blob/main/docling_core/types/doc/labels.py) for options. |
| `Span.label` | `int` | The integer ID of the span label. |
| `Span.id` | `int` | Running index of layout span. |
| `Span._.layout` | `SpanLayout` | Layout features of a layout span. |
| `Span._.heading` | `Span` / `None` | Closest heading to a span, if available. |

### <kbd>dataclass</kbd> PageLayout

| Attribute | Type | Description |
| --- | --- | --- |
| `page_no` | `int` | The page number (1-indexed). |
| `width` | `float` | Page with in pixels. |
| `height` | `float` | Page height in pixels. |

### <kbd>dataclass</kbd> DocLayout

| Attribute | Type | Description |
| --- | --- | --- |
| `pages` | `list[PageLayout]` | The pages in the document. |

### <kbd>dataclass</kbd> SpanLayout

| Attribute | Type | Description |
| --- | --- | --- |
| `x` | `float` | Horizontal offset of the bounding box in pixels. |
| `y` | `float` | Vertical offset of the bounding box in pixels. |
| `width` | `float` | Width of the bounding box in pixels. |
| `height` | `float` | Height of the bounding box in pixels. |
| `page_no` | `int` | Number of page the span is on. |

### <kbd>class</kbd> `spaCyLayout`

#### <kbd>method</kbd> `spaCyLayout.__init__`

Initialize the document processor.

```python
nlp = spacy.blank("en")
layout = spaCyLayout(nlp)
```

| Argument | Type | Description |
| --- | --- | --- |
| `nlp` | `spacy.language.Language` | The initialized `nlp` object to use for tokenization. |
| `separator` | `str` | Token used to separate sections in the created `Doc` object. The separator won't be part of the layout span. If `None`, no separator will be added. Defaults to `"\n\n"`. |
| `attrs` | `dict[str, str]` | Override the custom spaCy attributes. Can include `"doc_layout"`, `"doc_pages"`, `"span_layout"`, `"span_heading"` and `"span_group"`. |
| `headings` | `list[str]` | Labels of headings to consider for `Span._.heading` detection. Defaults to `["section_header", "page_header", "title"]`. |
| `docling_options` | `dict[InputFormat, FormatOption]` | [Format options](https://ds4sd.github.io/docling/usage/#advanced-options) passed to Docling's `DocumentConverter`. |
| **RETURNS** | `spaCyLayout` | The initialized object. |

#### <kbd>method</kbd> `spaCyLayout.__call__`

Process a document and create a spaCy [`Doc`](https://spacy.io/api/doc) object containing the text content and layout spans, available via `Doc.spans["layout"]` by default.

```python
layout = spaCyLayout(nlp)
doc = layout("./starcraft.pdf")
```

| Argument | Type | Description |
| --- | --- | --- |
| `path` | `str` / `Path` | Path to document to process. |
| **RETURNS** | `Doc` | The processed spaCy `Doc` object. |
