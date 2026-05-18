from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    base_dir: Path
    menu_path: Path
    restaurant_info_path: Path
    language: str = "tr"


def default_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parents[1]
    return AppConfig(
        base_dir=base_dir,
        menu_path=base_dir / "data" / "menu.yaml",
        restaurant_info_path=base_dir / "data" / "restaurant_info.yaml",
        language="tr",
    )
