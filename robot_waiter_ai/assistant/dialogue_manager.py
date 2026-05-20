from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import safety_rules
from .menu_knowledge import MenuKnowledge, MenuItem, normalize_text
from .order_state import OrderState
from .persona import Persona, default_persona


MAIN_DISH_ALIASES = (
    "ana yemek",
    "ana yemekler",
    "yemek",
    "yemekler",
    "yemekleri",
)


class DialogueManager:
    def __init__(
        self,
        menu_path: Path,
        restaurant_info_path: Path,
        persona: Optional[Persona] = None,
    ) -> None:
        self.persona = persona or default_persona()
        self.menu = MenuKnowledge(menu_path)
        self.menu.load()
        self.order = OrderState()
        self.restaurant_info = self._load_restaurant_info(restaurant_info_path)

    def _load_restaurant_info(self, path: Path) -> Dict:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def handle_message(self, text: str) -> str:
        user_text = text.strip()
        if not user_text:
            return "Yardımcı olmam için bir şey yazabilir misiniz?"

        lower = normalize_text(user_text)

        if self._is_greeting(lower):
            return self.persona.greeting

        if self._is_thanks(lower):
            return self.persona.closing

        if self._is_ask_hours(lower):
            return self._respond_hours()

        if self._is_restaurant_info_question(lower):
            return self._respond_restaurant_info(lower)

        if self._is_recommendation(lower):
            return self._respond_recommendation(lower)

        if self._is_category_listing_question(lower):
            return self._respond_category_items(lower)

        if self._is_ask_categories(lower):
            return self._respond_categories()

        if self._is_allergy(lower):
            item = self._extract_item(lower)
            if item and self._is_item_allergy_question(lower):
                return self._respond_item_allergy(item)
            return "Alerji konusunda dikkatli olalım. Menü alerjenlerini kontrol edip mutfakla teyit edebilirim."

        if self._is_confirm_order(lower):
            return self._respond_confirm_order()

        if self._is_summary(lower):
            return self.order.summarize() + "\nOnaylamak ister misiniz?"

        if self._is_clear_order(lower):
            self.order.clear()
            return "Siparişiniz temizlendi. Başka bir isteğiniz var mı?"

        if self._is_remove_order(lower):
            return self._respond_remove_order(user_text)

        if self._is_add_order(lower):
            return self._respond_add_order(user_text)

        if self._is_update_order(lower):
            return self._respond_update_order(user_text)

        if self._is_price_question(lower):
            item = self._extract_item(lower)
            if not item:
                return "Hangi ürünün fiyatını öğrenmek istersiniz?"
            return self._respond_item_price(item, lower)

        if self._is_ingredient_question(lower):
            item = self._extract_item(lower)
            if not item:
                return self._respond_categories()
            return self._respond_item_detail(item)

        if self._is_menu_question(lower):
            item = self._extract_item(lower)
            if not item:
                return self._respond_categories()
            return self._respond_item_detail(item)

        return "Bu konuda yardımcı olamıyorum. Menü veya siparişle ilgili sorabilir misiniz?"

    def _respond_hours(self) -> str:
        info = self.restaurant_info.get("restaurant", {})
        hours = info.get("opening_hours")
        if not hours:
            return self._respond_missing_demo_info("Çalışma saatleri")
        return f"Çalışma saatlerimiz: {hours}."

    def _respond_restaurant_info(self, lower: str) -> str:
        info = self.restaurant_info.get("restaurant", {})

        if self._is_restaurant_name_question(lower):
            name = str(info.get("name") or info.get("restaurant_name") or "").strip()
            if not name:
                return self._respond_missing_demo_info("Restoran adı")
            return f"Restoran adı: {name}."

        if self._is_payment_question(lower):
            methods = [str(method).strip() for method in info.get("payment_methods", []) if str(method).strip()]
            if not methods:
                return self._respond_missing_demo_info("Ödeme seçenekleri")
            return "Ödeme seçenekleri: " + ", ".join(methods) + "."

        if self._is_allergen_policy_question(lower):
            policy = [str(note).strip() for note in info.get("allergy_policy", []) if str(note).strip()]
            if not policy:
                return self._respond_missing_demo_info("Alerjen politikası")
            return "Alerjen bilgisi için: " + " ".join(policy)

        if self._is_vegetarian_info_question(lower):
            note = str(info.get("vegetarian_note") or "").strip()
            if not note:
                return self._respond_missing_demo_info("Vejetaryen seçenek bilgisi")
            return note

        if self._is_delivery_question(lower):
            notes = [str(note).strip() for note in info.get("service_notes", []) if str(note).strip()]
            if notes:
                return "Servis notu: " + " ".join(notes)
            return self._respond_missing_demo_info("Paket servis bilgisi")

        if self._is_location_question(lower):
            note = str(info.get("location_note") or "").strip()
            if not note:
                return self._respond_missing_demo_info("Konum bilgisi")
            return note

        return self._respond_missing_demo_info("Bu bilgi")

    def _respond_missing_demo_info(self, topic: str) -> str:
        return f"{topic} bu demo ortamında tanımlı değildir. Menü veya siparişle ilgili yardımcı olabilirim."

    def _respond_categories(self) -> str:
        categories = self.menu.list_categories()
        if not categories:
            return safety_rules.no_invention_response()
        return "Kategoriler: " + ", ".join(categories)

    def _respond_recommendation(self, lower: str) -> str:
        category = self._extract_category(lower)
        if category:
            items = self.menu.list_available_items(category)
            if not items:
                return f"{category} için uygun bir önerim yok. Başka bir kategori belirtir misiniz?"
            names = self._format_name_list([item.name for item in items])
            return f"{category} olarak {names} önerebilirim."

        tags = []
        if "hafif" in lower:
            tags.append("light")
        if "vejetaryen" in lower or "vegetarian" in lower:
            tags.append("vegetarian")
        if "protein" in lower:
            tags.append("high-protein")
        if not tags:
            tags = ["traditional"]
        items = self.menu.recommend_by_tag(tags)
        if not items:
            return "Size uygun bir önerim yok. Bir kategori belirtir misiniz?"
        names = ", ".join(item.name for item in items)
        return f"Öneri olarak şunları sunabilirim: {names}."

    def _format_name_list(self, names: List[str]) -> str:
        cleaned = [name.strip() for name in names if name.strip()]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} veya {cleaned[1]}"
        return ", ".join(cleaned[:-1]) + f" veya {cleaned[-1]}"

    def _respond_item_price(self, item: MenuItem, lower: str) -> str:
        if False and "fiyat" in lower:
            return f"{item.name} fiyatı {item.price:.2f} TL."
        return f"{item.name} {item.price:.2f} TL."

    def _respond_item_detail(self, item: MenuItem) -> str:
        allergen_note = (
            safety_rules.allergy_warning(item.allergens) if item.allergens else "Alerjen bilgisi bulunamadı."
        )
        return f"{item.name}: {item.description} Fiyat: {item.price:.2f} TL. {allergen_note}"

    def _respond_item_allergy(self, item: MenuItem) -> str:
        return f"{item.name} için kayıtlı alerjen bilgisi: {safety_rules.allergy_warning(item.allergens)}"

    def _respond_category_items(self, lower: str) -> str:
        category = self._extract_category(lower)
        if not category:
            return self._respond_categories()
        items = self.menu.list_available_items(category)
        if not items:
            return safety_rules.no_invention_response()
        names = ", ".join(item.name for item in items)
        return f"{category} seçeneklerimiz: {names}."

    def _respond_add_order(self, text: str) -> str:
        added = self._add_items_from_text(text)
        if not added:
            return "Siparişe eklemek istediğiniz ürünü yazar mısınız?"
        added_summary = ", ".join(f"{quantity} x {item.name}" for item, quantity in added)
        return f"Ekledim: {added_summary}. Başka bir isteğiniz var mı?"

    def _respond_remove_order(self, text: str) -> str:
        removed = self._remove_items_from_text(text)
        if not removed:
            return "Hangi ürünü çıkarmak istersiniz?"
        removed_names = ", ".join(item.name for item in removed)
        return f"Çıkardım: {removed_names}. Başka bir isteğiniz var mı?"

    def _respond_update_order(self, text: str) -> str:
        updated = self._update_items_from_text(text)
        if not updated:
            return "Hangi ürünün miktarını güncellemek istersiniz?"
        updated_summary = ", ".join(f"{quantity} x {item.name}" for item, quantity in updated)
        return f"Güncelledim: {updated_summary}. Başka bir isteğiniz var mı?"

    def _respond_confirm_order(self) -> str:
        if not self.order.has_items():
            return "Onaylanacak aktif bir siparişiniz görünmüyor. Önce siparişinize bir ürün ekleyebilir misiniz?"
        summary = self.order.summarize()
        return (
            "Siparişinizi onaylıyorum.\n"
            f"{summary}\n"
            "Not: Bu yalnızca MVP/demo onayıdır; gerçek restoran gönderimi yapılmaz."
        )

    def _add_items_from_text(self, text: str) -> List[tuple[MenuItem, int]]:
        added: List[tuple[MenuItem, int]] = []
        for item in self.menu.find_mentions(text):
            qty = self._extract_quantity(text, item.name)
            self.order.add_item(item.id, item.name, item.price, qty)
            added.append((item, qty))
        return added

    def _remove_items_from_text(self, text: str) -> List[MenuItem]:
        removed: List[MenuItem] = []
        for item in self.menu.find_mentions(text):
            if self.order.remove_item(item.id):
                removed.append(item)
        return removed

    def _update_items_from_text(self, text: str) -> List[tuple[MenuItem, int]]:
        updated: List[tuple[MenuItem, int]] = []
        for item in self.menu.find_mentions(text):
            qty = self._extract_quantity(text, item.name)
            if self.order.update_quantity(item.id, qty):
                updated.append((item, qty))
        return updated

    def _extract_quantity(self, text: str, name: str) -> int:
        word_to_num = {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5}
        normalized_text = normalize_text(text)
        
        matched_name = name
        item = self.menu.get_item_by_name(name)
        if item:
            if normalize_text(item.name) not in normalized_text:
                for alias in item.aliases:
                    if normalize_text(alias) in normalized_text:
                        matched_name = alias
                        break
                        
        normalized_name = normalize_text(matched_name)
        num_pattern = r"(\d+|bir|iki|uc|dort|bes)"

        p1 = rf"{num_pattern}\s*(?:x|adet|tane)?\s*{re.escape(normalized_name)}"
        m1 = re.search(p1, normalized_text, flags=re.IGNORECASE)
        if m1:
            val = m1.group(1).lower()
            return int(val) if val.isdigit() else word_to_num.get(val, 1)

        p2 = rf"{re.escape(normalized_name)}.*?(?:{num_pattern})\s*(?:x|adet|tane)"
        m2 = re.search(p2, normalized_text, flags=re.IGNORECASE)
        if m2:
            val = m2.group(1).lower()
            return int(val) if val.isdigit() else word_to_num.get(val, 1)

        p3 = rf"{re.escape(normalized_name)}\s*{num_pattern}"
        m3 = re.search(p3, normalized_text, flags=re.IGNORECASE)
        if m3:
            val = m3.group(1).lower()
            return int(val) if val.isdigit() else word_to_num.get(val, 1)

        m4 = re.search(rf"{num_pattern}\s*(?:x|adet|tane)", normalized_text, flags=re.IGNORECASE)
        if m4:
            val = m4.group(1).lower()
            return int(val) if val.isdigit() else word_to_num.get(val, 1)

        return 1

    def _extract_item(self, lower: str) -> Optional[MenuItem]:
        items = self.menu.find_mentions(lower)
        return items[0] if items else None

    def _extract_category(self, lower: str) -> Optional[str]:
        for category in self.menu.list_categories():
            if normalize_text(category) in lower:
                return category
        if any(alias in lower for alias in MAIN_DISH_ALIASES):
            for category in self.menu.list_categories():
                if normalize_text(category) == "ana yemek":
                    return category
        return None

    def _is_greeting(self, lower: str) -> bool:
        return any(word in lower for word in ["merhaba", "selam", "iyi gunler"])

    def _is_thanks(self, lower: str) -> bool:
        return any(word in lower for word in ["tesekkur", "sag olun"])

    def _is_ask_hours(self, lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in [
                "kacta aciliyorsunuz",
                "kacta kapaniyorsunuz",
                "calisma saatleriniz",
                "calisma saatleri",
                "kacta acik",
                "kacta kapaniyor",
                "saat kacta acik",
                "saat kacta kapaniyor",
            ]
        )

    def _is_ask_categories(self, lower: str) -> bool:
        return "kategori" in lower or any(
            phrase in lower
            for phrase in [
                "menude neler var",
                "menunuzde neler var",
                "menu neler",
                "menunuz neler",
                "menude ne var",
                "menunuzde ne var",
                "menu secenekleri",
            ]
        )

    def _is_category_listing_question(self, lower: str) -> bool:
        if self._extract_item(lower) is not None:
            return False
        category = self._extract_category(lower)
        if not category:
            return False
        return any(
            phrase in lower
            for phrase in ["secenek", "neler", "ne var", "hangi", "liste", "cesit", "mevcut", "say", " ne"]
        )

    def _is_recommendation(self, lower: str) -> bool:
        words = lower.split()
        return any(
            any(w.startswith(prefix) for prefix in ["oner", "tavsiye"])
            for w in words
            if not w.startswith("doner")
        )

    def _is_restaurant_info_question(self, lower: str) -> bool:
        return any(
            checker(lower)
            for checker in [
                self._is_restaurant_name_question,
                self._is_payment_question,
                self._is_allergen_policy_question,
                self._is_vegetarian_info_question,
                self._is_delivery_question,
                self._is_location_question,
            ]
        )

    def _is_restaurant_name_question(self, lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in ["restoranin adi", "restoran adi", "mekanin adi", "restoranin ismi", "adiniz ne"]
        )

    def _is_payment_question(self, lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in ["kart geciyor", "kredi karti geciyor", "odeme secenekleri", "odeme yontemleri", "temassiz"]
        )

    def _is_allergen_policy_question(self, lower: str) -> bool:
        return "alerjen bilgisi" in lower and any(
            phrase in lower for phrase in ["guvenilir", "dogru", "teyit", "emin"]
        )

    def _is_vegetarian_info_question(self, lower: str) -> bool:
        return "vejetaryen" in lower and "secenek" in lower

    def _is_delivery_question(self, lower: str) -> bool:
        return any(phrase in lower for phrase in ["paket servis", "teslimat", "kurye"])

    def _is_location_question(self, lower: str) -> bool:
        return any(phrase in lower for phrase in ["adres", "nerede", "konum"])

    def _is_allergy(self, lower: str) -> bool:
        return any(
            word in lower
            for word in [
                "alerji",
                "alerjim",
                "glutensiz",
                "laktoz",
                "laktozsuz",
                "sut urunu",
                "sut urunleri",
                "dairy",
                "findik",
                "fistik",
                "yer fistigi",
                "gluten",
            ]
        )

    def _is_item_allergy_question(self, lower: str) -> bool:
        return self._extract_item(lower) is not None and self._is_allergy(lower)

    def _is_confirm_order(self, lower: str) -> bool:
        return any(
            phrase in lower
            for phrase in [
                "onayliyorum",
                "siparisi onayla",
                "siparisimi onayla",
                "tamam siparisi onayliyorum",
                "tamam siparisimi onayliyorum",
                "evet onayliyorum",
                "evet onayla",
                "evet dogru",
                "bu siparis dogru",
                "siparisimi ver",
            ]
        )

    def _is_menu_question(self, lower: str) -> bool:
        if self._extract_item(lower) is not None:
            return True
        return any(word in lower for word in ["fiyat", "icerik", "icinde", "nedir"])

    def _is_price_question(self, lower: str) -> bool:
        if self._extract_item(lower) is None:
            return False
        return any(phrase in lower for phrase in ["fiyat", "ne kadar", "kac tl", "fiyati ne"])

    def _is_ingredient_question(self, lower: str) -> bool:
        if self._extract_item(lower) is None:
            return False
        return any(
            phrase in lower
            for phrase in [
                "icerik",
                "icinde ne var",
                "hangi malzeme",
                "hangi malzemelerle",
                "hazirlaniyor",
            ]
        )

    def _is_add_order(self, lower: str) -> bool:
        if self._extract_item(lower) is not None and "daha" in lower:
            return True
        if self._extract_item(lower) is not None and re.search(
            r"\b(\d+|bir|iki|uc|dort|bes)\b",
            lower,
            flags=re.IGNORECASE,
        ):
            return True
        return bool(
            re.search(
                r"\b(istiyorum|alabilir|siparis|ekle|isterim|alayim)\b",
                lower,
                flags=re.IGNORECASE,
            )
        )

    def _is_remove_order(self, lower: str) -> bool:
        return any(word in lower for word in ["iptal", "cikar", "sil"])

    def _is_update_order(self, lower: str) -> bool:
        return "adet" in lower or "tane" in lower

    def _is_summary(self, lower: str) -> bool:
        return any(phrase in lower for phrase in ["ozet", "toplam", "siparisim ne"])

    def _is_clear_order(self, lower: str) -> bool:
        return any(phrase in lower for phrase in ["temizle", "tumunu iptal"])
