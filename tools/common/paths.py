"""Where a unit's files live. Shared by every pipeline step.

Folders are organised by source; the first segment of a unit ID says which:
  ukpga/1988/52/section/172  -> raw/legislation/ukpga/1988/52/section/172/
                                data/legislation/ukpga/1988/52/section-172/
  govuk/speeding-penalties   -> raw/govuk/speeding-penalties/
                                data/govuk/speeding-penalties/
  sentencing/guidelines/speeding-revised-2017
                             -> raw/sentencing/guidelines/speeding-revised-2017/ (and data/...)
"""
from pathlib import Path

RAW_ROOT = Path("raw")
DATA_ROOT = Path("data")
RAW = RAW_ROOT / "legislation"
DATA = DATA_ROOT / "legislation"
OWN_FOLDER = {"govuk", "sentencing"}  # sources whose ID prefix is already the folder name


def _segments(uri: str) -> list[str]:
    """ukpga/1988/52/section/172 -> ukpga/1988/52/section-172; uksi/2000/2792/schedule stays as is."""
    parts = uri.split("/")
    if len(parts) >= 5:
        parts = parts[:3] + [f"{parts[3]}-{parts[4]}"] + parts[5:]
    return parts


def raw_dir(uri: str) -> Path:
    if uri.split("/")[0] in OWN_FOLDER:
        return RAW_ROOT.joinpath(*uri.split("/"))
    return RAW.joinpath(*uri.split("/"))


def data_dir(uri: str) -> Path:
    if uri.split("/")[0] in OWN_FOLDER:
        return DATA_ROOT.joinpath(*uri.split("/"))
    return DATA.joinpath(*_segments(uri))
