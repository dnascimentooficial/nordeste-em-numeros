"""O mapa do Inicio "Onde a renda mais cresceu desde 2012?": as 27 UFs em quadrados do mesmo tamanho, cada um na
posicao aproximada do estado (o "tile grid map"), em duas vistas: quanto a renda cresceu (variacao real do primeiro ao
ultimo ano) e quanto ela e hoje (R$ do ultimo ano). Tudo sai pronto do Python: a grade do Inicio (botoes, sem estilo
inline) e o SVG do card. O site.js so troca a vista e mostra o valor do estado apontado.
"""

import math

from nordeste.site.conteudo import ComparacaoDasUfs
from nordeste.site.formatacao import numero

# (coluna, linha) de cada UF na grade de 6 colunas e 8 linhas: o Norte a oeste, o Nordeste em bloco a leste, o Sul embaixo
GRADE = {
    "RR": (1, 0), "AP": (2, 0),
    "AM": (1, 1), "PA": (2, 1), "MA": (3, 1), "CE": (4, 1), "RN": (5, 1),
    "AC": (0, 2), "RO": (1, 2), "TO": (2, 2), "PI": (3, 2), "PE": (4, 2), "PB": (5, 2),
    "MT": (1, 3), "GO": (2, 3), "BA": (3, 3), "SE_UF": (4, 3), "AL": (5, 3),
    "MS": (1, 4), "DF": (2, 4), "MG": (3, 4), "ES": (4, 4),
    "PR": (1, 5), "SP": (2, 5), "RJ": (3, 5),
    "SC": (1, 6),
    "RS": (1, 7),
}
COLUNAS, LINHAS = 6, 8
CLASSES = 6  # tons da escala sequencial (nn-mapa-q0 a nn-mapa-q5, o mais escuro e o maior valor)
PASSOS = (1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000)
VISTAS = ("cresceu", "hoje")
TOPO = 5  # quantos estados em cada ponta do ranking


def sigla(uf: str) -> str:
    return "SE" if uf == "SE_UF" else uf


def faixas(valores: list[float], classes: int = CLASSES) -> list[float]:
    """Os limites das faixas da legenda, em passos redondos (1, 2, 2,5, 5 vezes uma potencia de 10): o menor passo que
    cobre do menor ao maior valor em no maximo `classes` faixas. `[10, 20, ..., 70]` sao seis faixas."""
    baixo, alto = min(valores), max(valores)
    for passo in PASSOS:
        inicio, fim = math.floor(baixo / passo) * passo, math.ceil(alto / passo) * passo
        if fim == inicio:
            fim += passo
        if round((fim - inicio) / passo) <= classes:
            return [inicio + i * passo for i in range(round((fim - inicio) / passo) + 1)]
    raise ValueError(f"valores fora da escala do mapa: {baixo} a {alto}")


def faixa_do_valor(valor: float, limites: list[float]) -> int:
    """O indice da faixa (0 a len(limites) - 2); o maior valor fica na ultima."""
    for i in range(len(limites) - 1):
        if valor < limites[i + 1]:
            return i
    return len(limites) - 2


def tom(indice: int, faixas_usadas: int) -> int:
    """A faixa espalhada pelos tons da escala: com quatro faixas, os tons 0, 2, 3 e 5 (o primeiro e o ultimo sempre)."""
    if faixas_usadas <= 1:
        return CLASSES - 1
    return round(indice * (CLASSES - 1) / (faixas_usadas - 1))


def _variacao_em_texto(valor: float, casas: int = 1) -> str:
    texto = numero(valor, casas)
    return ("+" + texto if round(valor, casas) > 0 else texto) + "%"


def _legenda(limites: list[float], casas: int, sufixo: str) -> list[dict]:
    faixas_usadas = len(limites) - 1
    return [
        {"tom": tom(i, faixas_usadas), "texto": f"{numero(limites[i], casas)}–{numero(limites[i + 1], casas)}{sufixo}"}
        for i in range(faixas_usadas)
    ]


def montar_mapa(comparacao: ComparacaoDasUfs, nomes: dict[str, str], regioes: dict[str, str], leitura: str) -> dict:
    """O mapa pronto para o modelo: os quadrados (posicao, tom de cada vista, valores e o rotulo acessivel), a legenda
    de cada vista e os rankings (os `TOPO` de cada ponta). `leitura` e o modelo do rotulo de cada estado, com
    [nome], [variacao], [ano0], [ano1], [v0] e [v1]."""
    ufs = [uf for uf in GRADE if uf in comparacao.valores]
    variacao = {uf: comparacao.variacao(uf) for uf in ufs}
    hoje = {uf: comparacao.valores[uf][1] for uf in ufs}
    limites = {"cresceu": faixas(list(variacao.values())), "hoje": faixas(list(hoje.values()))}
    valores = {"cresceu": variacao, "hoje": hoje}

    def tons(uf: str) -> dict[str, int]:
        return {v: tom(faixa_do_valor(valores[v][uf], limites[v]), len(limites[v]) - 1) for v in VISTAS}

    def rotulo(uf: str) -> str:
        inicial, final = comparacao.valores[uf]
        trocas = {
            "[nome]": nomes[uf], "[variacao]": _variacao_em_texto(variacao[uf]), "[ano0]": str(comparacao.ano_inicial),
            "[ano1]": str(comparacao.ano_final), "[v0]": numero(inicial, 0), "[v1]": numero(final, 0),
        }
        texto = leitura
        for marcador, valor in trocas.items():
            texto = texto.replace(marcador, valor)
        return texto

    quadrados = [
        {
            "uf": uf, "sigla": sigla(uf), "nome": nomes[uf], "coluna": GRADE[uf][0], "linha": GRADE[uf][1],
            "ne": regioes[uf] == "NE", "tons": tons(uf), "rotulo": rotulo(uf),
            "valores": {"cresceu": _variacao_em_texto(variacao[uf], 0), "hoje": numero(hoje[uf], 0)},
        }
        for uf in ufs
    ]

    def ranking(vista: str, formato) -> dict:
        ordem = sorted(ufs, key=lambda uf: (-valores[vista][uf], uf))
        item = lambda posicao, uf: {  # noqa: E731
            "posicao": posicao, "uf": uf, "nome": nomes[uf], "ne": regioes[uf] == "NE", "valor": formato(valores[vista][uf]),
        }
        return {
            "mais": [item(i, uf) for i, uf in enumerate(ordem[:TOPO], 1)],
            "menos": [item(i, uf) for i, uf in enumerate(ordem, 1)][-TOPO:],
        }

    return {
        "ano_inicial": comparacao.ano_inicial, "ano_final": comparacao.ano_final,
        "quadrados": quadrados,
        "legendas": {"cresceu": _legenda(limites["cresceu"], 0, "%"), "hoje": _legenda(limites["hoje"], 0, "")},
        "rankings": {"cresceu": ranking("cresceu", _variacao_em_texto), "hoje": ranking("hoje", lambda v: numero(v, 0))},
        "tabela": [
            {"nome": nomes[uf], "ne": regioes[uf] == "NE", "regiao": regioes[uf], "v0": numero(comparacao.valores[uf][0], 0),
             "v1": numero(hoje[uf], 0), "variacao": _variacao_em_texto(variacao[uf])}
            for uf in sorted(ufs, key=lambda uf: (-variacao[uf], uf))
        ],
    }


# --- o SVG do card (o PNG de 1080 x 1350 e a pagina do card): os quadrados da vista "quanto cresceu" ---

LADO, VAO = 44, 4  # px do quadrado e do vao no viewBox


def mapa_svg(mapa: dict, titulo: str) -> str:
    """O mapa da vista "quanto cresceu" em SVG, para o card: cada quadrado com a sigla e a variacao arredondada; os do
    Nordeste com o contorno laranja. Cores por classe (estilo.css), nada de estilo inline."""
    largura = COLUNAS * LADO + (COLUNAS - 1) * VAO
    altura = LINHAS * LADO + (LINHAS - 1) * VAO
    partes = [
        f'<svg class="nn-mapa-svg" viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}" role="img" '
        f'aria-label="{_attr(titulo)}">'
    ]
    for q in mapa["quadrados"]:
        x, y = q["coluna"] * (LADO + VAO), q["linha"] * (LADO + VAO)
        classe = f"nn-mapa-svg-uf nn-mapa-q{q['tons']['cresceu']}" + (" nn-mapa-svg-ne" if q["ne"] else "")
        partes.append(
            f'<g class="{classe}"><rect x="{x + 1.5}" y="{y + 1.5}" width="{LADO - 3}" height="{LADO - 3}" rx="5"/>'
            f'<text x="{x + LADO / 2}" y="{y + 19}" class="nn-mapa-svg-sigla">{q["sigla"]}</text>'
            f'<text x="{x + LADO / 2}" y="{y + 34}" class="nn-mapa-svg-valor">{_attr(q["valores"]["cresceu"])}</text></g>'
        )
    partes.append("</svg>")
    return "".join(partes)


def _attr(texto: str) -> str:
    return texto.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
