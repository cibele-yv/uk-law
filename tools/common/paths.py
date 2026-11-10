"""Where a unit's files live. Shared by every pipeline step."""
from pathlib import Path

RAW = Path("raw/legislation")
DATA = Path("data/legislation")


def _segments(uri: str) -> list[str]:
    """ukpga/1988/52/section/172 -> ukpga/1988/52/section-172; uksi/2000/2792/schedule stays as is."""
    parts = uri.split("/")
    if len(parts) >= 5:
        parts = parts[:3] + [f"{parts[3]}-{parts[4]}"] + parts[5:]
    return parts


def raw_dir(uri: str) -> Path:
    return RAW.joinpath(*uri.split("/"))


def data_dir(uri: str) -> Path:
    return DATA.joinpath(*_segments(uri))
