"""Project-wide path configuration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path = Path(__file__).resolve().parent.parent

    @property
    def data_raw(self) -> Path:
        return self.root / "data" / "raw"

    @property
    def data_processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def data_quarantine(self) -> Path:
        return self.root / "data" / "quarantine"

    @property
    def reports_data_dictionary(self) -> Path:
        return self.root / "reports" / "data_dictionary"

    @property
    def reports_figures(self) -> Path:
        return self.root / "reports" / "figures"


PROJECT_PATHS = ProjectPaths()
