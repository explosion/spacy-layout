import dataclasses
from typing import TYPE_CHECKING, Any, Callable

from docling_core.types.doc.base import CoordOrigin
from pandas import DataFrame

from .types import DocLayout, PageLayout, SpanLayout

if TYPE_CHECKING:
    from docling_core.types.doc.base import BoundingBox

TYPE_ATTR = "__type__"
OBJ_TYPES = {"SpanLayout": SpanLayout, "DocLayout": DocLayout, "PageLayout": PageLayout}


def encode_obj(obj: Any, chain: Callable | None = None) -> Any:
    """Convert custom dataclass to dict for serialization."""
    if isinstance(obj, tuple(OBJ_TYPES.values())):
        result = dataclasses.asdict(obj)
        result[TYPE_ATTR] = type(obj).__name__
        return result
    return obj if chain is None else chain(obj)


def decode_obj(obj: Any, chain: Callable | None = None) -> Any:
    """Load custom dataclass from serialized dict."""
    if isinstance(obj, dict) and obj.get(TYPE_ATTR) in OBJ_TYPES:
        obj_type = obj.pop(TYPE_ATTR)
        return OBJ_TYPES[obj_type].from_dict(obj)
    return obj if chain is None else chain(obj)


def encode_df(obj: Any, chain: Callable | None = None) -> Any:
    """Convert pandas.DataFrame for serialization."""
    if isinstance(obj, DataFrame):
        # ensure unique column names, as data will be lost otherwise
        df = _ensure_unique_columns(obj)
        return {"data": df.to_dict(), TYPE_ATTR: "DataFrame"}
    return obj if chain is None else chain(obj)


def _ensure_unique_columns(df: DataFrame) -> DataFrame:
    seen_cols = {}
    new_cols = []
    for col_name in df.columns:
        if col_name not in seen_cols:
            seen_cols[col_name] = 1
            new_cols.append(col_name)
        else:
            seen_cols[col_name] += 1
            new_cols.append(f"{col_name} ({seen_cols[col_name]})")
    df.columns = new_cols
    return df


def decode_df(obj: Any, chain: Callable | None = None) -> Any:
    """Load pandas.DataFrame from serialized data."""
    if isinstance(obj, dict) and obj.get(TYPE_ATTR) == "DataFrame":
        return DataFrame(obj["data"])
    return obj if chain is None else chain(obj)


def get_bounding_box(
    bbox: "BoundingBox", page_height: float
) -> tuple[float, float, float, float]:
    is_bottom = bbox.coord_origin == CoordOrigin.BOTTOMLEFT
    y = page_height - bbox.t if is_bottom else bbox.t
    height = bbox.t - bbox.b if is_bottom else bbox.b - bbox.t
    width = bbox.r - bbox.l
    return (bbox.l, y, width, height)
