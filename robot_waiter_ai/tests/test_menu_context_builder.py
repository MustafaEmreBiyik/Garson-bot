from __future__ import annotations

from pathlib import Path

from robot_waiter_ai.inference.menu_context_builder import build_menu_context


def test_build_menu_context_includes_menu_and_restaurant_info(tmp_path: Path) -> None:
    menu_path = tmp_path / "menu.yaml"
    menu_path.write_text(
        """
menu:
  - id: s1
    name: Test Corba
    category: Corba
    price: 50
  - id: d1
    name: Test Tatli
    category: Tatli
    price: 70
""".strip()
        + "\n",
        encoding="utf-8",
    )

    restaurant_info_path = tmp_path / "restaurant_info.yaml"
    restaurant_info_path.write_text(
        """
restaurant:
  opening_hours: "09:00 - 21:00"
  payment_methods:
    - nakit
    - kart
  allergy_policy:
    - Mutfakla teyit edin
""".strip()
        + "\n",
        encoding="utf-8",
    )

    context = build_menu_context(menu_path, restaurant_info_path)

    assert "Menü kategorileri" in context
    assert "Corba" in context
    assert "Test Corba" in context
    assert "50.00 TL" in context
    assert "Çalışma saatleri" in context
    assert "nakit" in context
    assert "Alerji politikası" in context


def test_build_menu_context_gracefully_handles_missing_restaurant_info(tmp_path: Path) -> None:
    menu_path = tmp_path / "menu.yaml"
    menu_path.write_text(
        """
menu:
  - name: Ayran
    category: İçecek
    price: 45
""".strip()
        + "\n",
        encoding="utf-8",
    )

    context = build_menu_context(menu_path, tmp_path / "restaurant_info.yaml")

    assert "Ayran" in context
    assert "45.00 TL" in context
