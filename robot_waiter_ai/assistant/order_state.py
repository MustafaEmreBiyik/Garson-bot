from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class OrderItem:
    id: str
    name: str
    price: float
    quantity: int = 1


@dataclass
class OrderState:
    items: Dict[str, OrderItem] = field(default_factory=dict)

    def add_item(self, item_id: str, name: str, price: float, quantity: int = 1) -> None:
        if item_id in self.items:
            self.items[item_id].quantity += quantity
        else:
            self.items[item_id] = OrderItem(item_id, name, price, quantity)

    def remove_item(self, item_id: str) -> bool:
        return self.items.pop(item_id, None) is not None

    def update_quantity(self, item_id: str, quantity: int) -> bool:
        if item_id not in self.items:
            return False
        if quantity <= 0:
            self.remove_item(item_id)
            return True
        self.items[item_id].quantity = quantity
        return True

    def clear(self) -> None:
        self.items.clear()

    def has_items(self) -> bool:
        return bool(self.items)

    def summarize(self) -> str:
        if not self.items:
            return "Siparişiniz şu an boş."
        lines: List[str] = []
        total = 0.0
        for item in self.items.values():
            line_total = item.price * item.quantity
            total += line_total
            lines.append(f"{item.quantity} x {item.name} = {line_total:.2f} TL")
        lines.append(f"Toplam: {total:.2f} TL")
        return "\n".join(lines)

    def total_price(self) -> float:
        return sum(item.price * item.quantity for item in self.items.values())
