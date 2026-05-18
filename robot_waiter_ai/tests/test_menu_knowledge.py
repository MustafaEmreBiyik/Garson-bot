from pathlib import Path

from robot_waiter_ai.assistant.menu_knowledge import MenuKnowledge


def test_menu_loads_items():
    base_dir = Path(__file__).resolve().parents[1]
    menu = MenuKnowledge(base_dir / "data" / "menu.yaml")
    menu.load()
    assert len(menu.items) > 0


def test_list_categories():
    base_dir = Path(__file__).resolve().parents[1]
    menu = MenuKnowledge(base_dir / "data" / "menu.yaml")
    menu.load()
    categories = menu.list_categories()
    assert "Çorba" in categories
