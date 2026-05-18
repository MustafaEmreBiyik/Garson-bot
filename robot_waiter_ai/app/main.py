from robot_waiter_ai.app.config import default_config
from robot_waiter_ai.assistant.dialogue_manager import DialogueManager


def run_cli() -> None:
    config = default_config()
    manager = DialogueManager(config.menu_path, config.restaurant_info_path)

    restaurant_name = manager.restaurant_info.get("restaurant", {}).get("name", "Restoranımıza")

    print("=" * 50)
    print(f"Hoş geldiniz! {restaurant_name} GarsonBot asistanınız hazır.")
    print("Size nasıl yardımcı olabilirim?")
    print("Örnek komutlar:")
    print("  - Menüde neler var?")
    print("  - 2 Ayran istiyorum.")
    print("  - Siparişi özetle.")
    print("  - Çıkmak için 'çıkış' yazabilirsiniz.")
    print("=" * 50)

    while True:
        try:
            user_text = input("\nSiz: ").strip()
            if not user_text:
                continue
            if user_text.casefold() in {"cikis", "çıkış", "quit", "exit"}:
                print("GarsonBot: Afiyet olsun, görüşmek üzere!")
                break
            response = manager.handle_message(user_text)
            print(f"GarsonBot: {response}")
        except KeyboardInterrupt:
            print("\nGarsonBot: Afiyet olsun, görüşmek üzere!")
            break
        except Exception as exc:
            print(f"\nGarsonBot: Bir hata oluştu: {exc}")
            break


if __name__ == "__main__":
    run_cli()
