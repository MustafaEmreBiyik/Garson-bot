from typing import Iterable


def allergy_warning(allergens: Iterable[str]) -> str:
    if not allergens:
        return "Alerjen bilgisi yok. Lütfen mutfakla teyit ediniz."
    items = ", ".join(allergens)
    return f"Alerjenler: {items}. Lütfen mutfakla teyit ediniz."


def unknown_info_response() -> str:
    return "Bu bilgiye şu an erişemiyorum. Mutfak veya personel ile teyit edebilirim."


def no_invention_response() -> str:
    return "Menü bilgisi eksik. Uydurma bilgi vermek istemem; lütfen personelden teyit edelim."
