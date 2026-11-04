"""Formatacao de numeros no idioma da geracao em curso: o padrao brasileiro (1.234,5) no portugues, o americano
(1,234.5) no ingles."""

from nordeste.site.idioma import idioma_atual

ORDINAIS_EN = {1: "st", 2: "nd", 3: "rd"}


def numero(valor: float, casas: int, idioma: str | None = None) -> str:
    """`1234.5, 1` -> `"1.234,5"` (em ingles, `"1,234.5"`): separador de milhares e de decimais do idioma, sem zero
    negativo."""
    arredondado = round(valor, casas) or 0.0  # -0.0 e 0.0 viram 0.0: nunca "-0,0"
    texto = f"{arredondado:,.{casas}f}"
    if (idioma or idioma_atual()) == "en":
        return texto
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


def escala_auto(valor: float, idioma: str | None = None) -> str:
    """Valor grande em escala curta: `2186521 -> "2,19 mi"` (de 1 milhao em diante), `403431 -> "403 mil"`; em
    ingles, `"2.19 million"` e `"403 thousand"`."""
    idioma = idioma or idioma_atual()
    milhao, mil = ("million", "thousand") if idioma == "en" else ("mi", "mil")
    if abs(valor) >= 1e6:
        return f"{numero(valor / 1e6, 2, idioma)} {milhao}"
    return f"{numero(valor / 1e3, 0, idioma)} {mil}"


def ordinal(n: int, idioma: str | None = None) -> str:
    """`1 -> "1º"`; em ingles, `1st`, `2nd`, `3rd`, `4th`, `11th`, `21st`."""
    if (idioma or idioma_atual()) != "en":
        return f"{n}º"
    sufixo = "th" if 10 <= n % 100 <= 20 else ORDINAIS_EN.get(n % 10, "th")
    return f"{n}{sufixo}"
