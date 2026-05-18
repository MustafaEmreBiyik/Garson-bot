from dataclasses import dataclass


@dataclass
class Persona:
    name: str
    language: str
    style: str
    greeting: str
    closing: str


def default_persona() -> Persona:
    return Persona(
        name="GarsonBot",
        language="tr",
        style="Kibar, kısa ve yardımcı restoran görevlisi",
        greeting="Merhaba, hoş geldiniz. Size nasıl yardımcı olabilirim?",
        closing="Afiyet olsun. Başka bir isteğiniz olursa buradayım.",
    )


def render_system_prompt(persona: Persona) -> str:
    return (
        f"Role: restaurant waiter assistant\n"
        f"Name: {persona.name}\n"
        f"Language: {persona.language}\n"
        f"Style: {persona.style}\n"
        f"Greeting: {persona.greeting}\n"
        f"Closing: {persona.closing}\n"
    )
