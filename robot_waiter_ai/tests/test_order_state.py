from robot_waiter_ai.assistant.order_state import OrderState


def test_add_and_summarize_order():
    state = OrderState()
    state.add_item("m1", "Izgara Tavuk Salata", 200, 2)
    summary = state.summarize()
    assert "Izgara Tavuk Salata" in summary
    assert "Toplam" in summary


def test_update_and_remove():
    state = OrderState()
    state.add_item("b1", "Ayran", 45, 1)
    state.update_quantity("b1", 3)
    assert state.items["b1"].quantity == 3
    state.remove_item("b1")
    assert "b1" not in state.items
