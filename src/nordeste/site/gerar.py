"""Gerador do site estatico a partir da base publicada, dos relatorios e dos metadados: Inicio, Como chegamos ate
aqui (so com o conteudo historico pronto), Estados, Explorar, Cards, Sobre e Dados.

Nada aqui le o relogio nem a base de trabalho: a mesma base publicada gera o mesmo site, byte a byte. Todo numero de
texto vem de um marcador preenchido pela base (`conteudo.preencher`); fecho e card cuja condicao falha, ou cujo texto
cita um destaque que sumiu da base, nao saem e vao para o `RelatorioSite`.
"""

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import NamedTuple

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from nordeste.caminhos import Caminhos
from nordeste.site.conteudo import (
    Conteudo, Destaque, ErroConteudo, avaliar_condicao, calcular_destaques, carregar_conteudo, destaques_citados,
    pontos_da_selecao, preencher,
)
from nordeste.site.dados import DadosSite
from nordeste.site.explorar import (
    ETIQUETA_DO_TERRITORIO, FAIXAS, INDICADORES_EXPLORAR, NOME_DO_TERRITORIO, POR_CHAVE, TERRITORIOS,
    IndicadorExplorar, dados_explorar, pontos, pontos_do_indicador, referencias, tabela_do_territorio, vistas_estados,
)
from nordeste.site.formatacao import numero
from nordeste.site.graficos import ConfigGrafico, Linha, faixas_em_json, grafico_linhas, minigrafico
from nordeste.site.historia import (
    PESO_MAXIMO_DA_EPOCA,
    PESO_MAXIMO_DO_CARTAO,
    PESO_MAXIMO_DO_MARCO,
    PROPORCAO,
    ROTULO_DA_LICENCA,
    TIPOS,
    Historia,
    ImagemHistorica,
    arquivo_do_cartao,
    carregar_historia,
    medidas_da_webp,
    parcela_do_nordeste,
)
from nordeste.site.imagens import VERSAO_DO_RENDER, AlvoImagem, renderizar

NOME_DO_SITE = "Nordeste em Números"
URL_DO_SITE = "https://nordeste.dnascimento.com.br"
URL_DO_AUTOR = "https://dnascimento.com.br"
LICENCA = "https://creativecommons.org/licenses/by/4.0/"
PASTA_MODELOS = Path(__file__).parent / "modelos"
PASTA_ESTATICOS = Path(__file__).parent / "estaticos"  # estilo, script, fontes, foto e .htaccess, copiados na raiz do site
CONTORNO = ("site", "nordeste-contorno.svg")  # em metadados/; ferramentas/gerar_contorno.py o gera
OG = (1200, 630)  # imagem de compartilhamento das paginas
CARD = (1080, 1350)  # PNG de cada card
FOTO_TAMANHO_MAXIMO = 200_000  # bytes: a foto pesa na primeira tela
FOTO_EXIGIDA = ("credito", "url")  # `foto` e opcional em textos.yaml; se existir, traz tudo isso (Ruling S-Z)
FOTO_ARQUIVO = "foto-abertura.webp"  # em estaticos/; o estilo.css aponta para este nome (fundo da abertura, Ruling S-U)
AUTOR_FOTO = "autor.webp"  # em estaticos/, opcional: a foto do circulo do rodape; sem ela o circulo mostra as iniciais
AUTOR_FOTO_TAMANHO_MAXIMO = 100_000  # bytes: o rodape esta em todas as paginas
AUTOR_MARCA = "marca-autor.svg"  # em estaticos/, opcional: a marca grafica do autor, mostrada no rodape so se existir
LARGO = {"largura": 720}  # os dois tamanhos de cada grafico (Ruling S-O): o CSS mostra um conforme a largura da tela
ESTREITO = {"largura": 360, "altura": 240}
AMPLIADO = {"largura": 1100, "altura": 520}  # o terceiro, do modal "Ampliar" (Ruling S-W): guardado num <template>
MANIFESTO_DE_IMAGENS = "_imagens.json"  # na raiz do site: sha256 das entradas de cada PNG (Ruling S-X); sem dado sensivel
ARQUIVOS_DE_DADOS = ("base_nordeste.csv", "derivados.csv")
EXPLORAR_INICIAL = ("pib_pc", "NE")  # a vista que ja vem desenhada no HTML: indicador e territorio
TEXTOS_EXIGIDOS = {  # seção de textos.yaml: chaves lidas pelo gerador e pelos modelos
    "abertura": {"eyebrow", "titulo", "destaque", "intro"},
    "faixa": {"rotulo", "id", "numeros", "texto", "nota"},  # + `condicao`, opcional (Ruling S-V)
    "ampliar": {"botao", "rotulo", "fechar", "gire", "quebra"},
    "por_que": {"titulo", "paragrafos"}, "como_ler": {"titulo", "itens"}, "o_que_falta": {"titulo", "itens"},
    "dataset": {"nome", "descricao"}, "fontes": {"titulo", "intro"}, "formulas": {"titulo", "intro", "blocos"},
    "arquivos": {"titulo", "intro"}, "dados": {"titulo", "intro", "conferir", "arquivos"},
    "estados": {
        "titulo", "intro", "titulo_mapa", "titulo_ranking", "escala_pior", "escala_melhor", "nota_do_mapa", "rolagem",
        "tabela", "fonte", "sem_dados",
    },
    "explorar": {
        **dict.fromkeys(("titulo", "intro", "nota", "tabela", "fonte", "sem_dados", "sem_periodo", "erro")),
        "zoom": {"grupo", "de", "ate", "inicio", "fim", "ampliar", "todo", "ajuda"},
    },
    "cards": {"titulo", "intro", "sera", "baixar", "voltar"},
    "autor": {  # + `formacao`, opcional (lista de itens)
        **dict.fromkeys(("nome", "titulo", "fechar", "link", "formacao_titulo", "formacao_vazia")),
        "quem_sou": {"titulo", "texto"}, "motivacao": {"titulo", "texto"},
    },
}
FRASE_DA_DATA = "na data desta publicação"
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")


class Pagina(NamedTuple):
    chave: str  # tambem a chave em textos.yaml (paginas) e o nome da imagem OpenGraph
    modelo: str
    arquivo: str
    rota: str
    rotulo: str  # no menu


PAGINAS = (  # as paginas de sempre; a da historia entra depois do Inicio so quando o conteudo dela esta pronto
    Pagina("index", "inicio.html", "index.html", "/", "Início"),
    Pagina("estados", "estados.html", "estados/index.html", "/estados/", "Estados"),
    Pagina("explorar", "explorar.html", "explorar/index.html", "/explorar/", "Explorar"),
    Pagina("cards", "cards.html", "cards/index.html", "/cards/", "Cards"),
    Pagina("sobre", "sobre.html", "sobre/index.html", "/sobre/", "Sobre os dados"),
    Pagina("dados", "dados.html", "dados/index.html", "/dados/", "Dados"),
)
PAGINA_HISTORIA = Pagina("como-chegamos", "como_chegamos.html", "como-chegamos/index.html", "/como-chegamos/", "Como chegamos aqui")
PAGINAS_COM_DATASET = ("index", "dados")
PASTA_IMAGENS_HISTORIA = "/historia/"  # estaticos/historia/ do pacote, copiada na raiz do site so com a pagina
AVISO_DA_PREVIA = "Prévia: texto provisório"


def paginas_do_site(com_historia: bool) -> tuple[Pagina, ...]:
    """As paginas do menu, na ordem dele: a da historia entre Inicio e Estados quando ela e gerada."""
    return (PAGINAS[0], PAGINA_HISTORIA, *PAGINAS[1:]) if com_historia else PAGINAS


@dataclass
class RelatorioSite:
    paginas: list[str]
    # ids das perguntas que ficaram sem fecho ou sairam inteiras e da faixa de numeros da abertura, se saiu (abertura_numeros)
    fechos_suprimidos: list[str]
    cards_suprimidos: list[str]
    # historia.yaml com `provisoria: true`: a pagina Como chegamos nao sai (so em previa, com incluir_provisoria)
    historia_provisoria: bool = False


# --- datas e textos ---

def data_por_extenso(aaaa_mm_dd: str) -> str:
    """`2026-11-01` -> `1º de novembro de 2026`."""
    ano, mes, dia = aaaa_mm_dd.split("-")
    return f"{int(dia)}{'º' if int(dia) == 1 else ''} de {MESES[int(mes) - 1]} de {ano}"


def mes_por_extenso(aaaa_mm: str) -> str:
    """`2027-02` -> `fevereiro de 2027`."""
    ano, mes = aaaa_mm.split("-")
    return f"{MESES[int(mes) - 1]} de {ano}"


def _textos(obj: object) -> Iterator[str]:
    """Todos os textos do conteudo, menos as condicoes (que nao sao texto de leitura)."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for chave, valor in obj.items():
            if chave != "condicao":
                yield from _textos(valor)
    elif isinstance(obj, list):
        for valor in obj:
            yield from _textos(valor)


def _cita_so_o_que_existe(obj: object, destaques: dict[str, Destaque]) -> bool:
    return all(destaques_citados(t) <= destaques.keys() for t in _textos(obj))


def _resolver(obj: object, destaques: dict[str, Destaque], data: str) -> object:
    """Preenche os marcadores dos textos fixos e a data da publicacao. Item de lista que cita destaque ausente sai."""
    if isinstance(obj, str):
        return preencher(obj, destaques).replace(FRASE_DA_DATA, f"em {data}")
    if isinstance(obj, list):
        return [_resolver(item, destaques, data) for item in obj if _cita_so_o_que_existe(item, destaques)]
    if isinstance(obj, dict):
        return {chave: _resolver(valor, destaques, data) for chave, valor in obj.items()}
    return obj


# --- graficos ---

def _linhas(dados: DadosSite, grafico: dict) -> list[Linha]:
    return [
        Linha(l["rotulo"], l["rotulo_curto"], pontos_da_selecao(dados, l), l["destaque"]) for l in grafico["linhas"]
    ]


def _config(grafico: dict, destaques: dict[str, Destaque]) -> ConfigGrafico:
    descricao = grafico.get("descricao") or grafico.get("titulo") or grafico["id"]
    return ConfigGrafico(
        titulo=preencher(descricao, destaques),
        casas=grafico["casas"],
        sufixo=grafico.get("sufixo", ""),
        min0=grafico.get("min0", False),
        ref100=grafico.get("ref100", False),
        quebras=tuple((q["ano"], q["rotulo"]) for q in grafico.get("quebras", [])),
    )


def _tabela(linhas: list[Linha], cfg: ConfigGrafico, nome: str) -> list[dict]:
    """Os valores do grafico em ordem de ano. Linha com mais de uma serie leva a serie no nome: nunca se emendam."""
    linhas_da_tabela = []
    for ordem, linha in enumerate(linhas):
        varias = len({p.serie for p in linha.pontos}) > 1
        for p in linha.pontos:
            rotulo = f"{linha.rotulo} ({p.serie})" if varias else linha.rotulo
            linhas_da_tabela.append((p.ano, ordem, p.serie, nome, rotulo, f"{numero(p.valor, cfg.casas)}{cfg.sufixo}"))
    return [
        {"grafico": nome, "ano": ano, "serie": rotulo, "valor": valor}
        for ano, _, _, nome, rotulo, valor in sorted(linhas_da_tabela, key=lambda t: t[:3])
    ]


def _desenhar(linhas: list[Linha], cfg: ConfigGrafico, governos: pd.DataFrame) -> tuple[str, str]:
    """O grafico nas duas larguras (Ruling S-O); vazio quando nenhuma linha tem ponto no eixo."""
    largo = grafico_linhas(linhas, cfg, governos, **LARGO)
    return (largo, grafico_linhas(linhas, cfg, governos, **ESTREITO)) if largo else ("", "")


def _montar_grafico(dados: DadosSite, destaques: dict[str, Destaque], grafico: dict) -> dict | None:
    """O grafico nas tres larguras (a do modal tambem), a tabela dos numeros e o que o modal mostra do grafico
    (notas de quebra e atualizacoes dos seus indicadores); None quando nenhuma linha tem ponto no eixo."""
    linhas, cfg = _linhas(dados, grafico), _config(grafico, destaques)
    largo, estreito = _desenhar(linhas, cfg, dados.governos)
    if not largo:
        return None
    nome = preencher(grafico.get("titulo") or grafico.get("descricao") or grafico["id"], destaques)
    indicadores = list(dict.fromkeys(l["indicador"] for l in grafico["linhas"]))
    return {
        "id": grafico["id"].replace("_", "-"),
        "titulo": preencher(grafico["titulo"], destaques) if "titulo" in grafico else None,
        "subtitulo": preencher(grafico["subtitulo"], destaques) if "subtitulo" in grafico else None,
        "largo": largo,
        "estreito": estreito,
        "ampliado": grafico_linhas(linhas, cfg, dados.governos, **AMPLIADO),
        "quebras": [{"ano": q["ano"], "rotulo": q["rotulo"]} for q in grafico.get("quebras", [])],
        "atualizacoes": _atualizacoes(dados, indicadores),
        "tabela": _tabela(linhas, cfg, nome),
    }


# --- perguntas e cards ---

def _atualizacoes(dados: DadosSite, indicadores: list[str]) -> list[dict]:
    """Por indicador: nome, data da ultima coleta e proxima publicacao esperada (None quando nao ha previsao)."""
    atualizacoes = []
    for indicador in indicadores:
        ficha = dados.fichas.get(indicador)
        if ficha is None:
            continue
        try:
            atualizado = data_por_extenso(dados.atualizado_em(indicador))
        except KeyError:
            continue
        proximo = dados.proxima_publicacao(indicador)
        atualizacoes.append(
            {"nome": ficha.nome, "atualizado": atualizado, "proximo": mes_por_extenso(proximo) if proximo else None}
        )
    return atualizacoes


def _pergunta(dados: DadosSite, destaques: dict[str, Destaque], p: dict, com_fecho: bool) -> dict:
    graficos = [g for g in (_montar_grafico(dados, destaques, g) for g in p["graficos"]) if g is not None]
    indicadores = list(dict.fromkeys(l["indicador"] for g in p["graficos"] for l in g["linhas"]))
    return {
        "id": p["id"],
        "rotulo": preencher(p["rotulo"], destaques),
        "frase_feita": preencher(p["frase_feita"], destaques),
        "explicacao": preencher(p["explicacao"], destaques) if "explicacao" in p else None,
        "lide": preencher(p["lide"], destaques),
        "graficos": graficos,
        "tabela": [linha for g in graficos for linha in g["tabela"]],
        "fecho": preencher(p["fecho"]["texto"], destaques) if com_fecho else None,
        "alerta": preencher(p["alerta"], destaques) if "alerta" in p else None,
        "fonte": [preencher(f, destaques) for f in p["fonte"]],
        "atualizacoes": _atualizacoes(dados, indicadores),
    }


def _perguntas(dados: DadosSite, destaques: dict[str, Destaque], conteudo: Conteudo) -> tuple[list[dict], list[str]]:
    """Perguntas publicaveis e os ids das que perderam o fecho ou sairam inteiras.

    O corpo (lide, explicacao, alerta, fonte, graficos) que cita destaque ausente tira a pergunta toda; o fecho cuja
    condicao e falsa, ou cujo texto cita destaque ausente, tira so o fecho.
    """
    publicadas, suprimidas = [], []
    for p in conteudo.perguntas:
        corpo = {k: v for k, v in p.items() if k != "fecho"}
        if not _cita_so_o_que_existe(corpo, destaques):
            suprimidas.append(p["id"])
            continue
        fecho = p["fecho"]
        com_fecho = avaliar_condicao(fecho["condicao"], destaques) and _cita_so_o_que_existe(fecho["texto"], destaques)
        if not com_fecho:
            suprimidas.append(p["id"])
        publicadas.append(_pergunta(dados, destaques, p, com_fecho))
    return publicadas, suprimidas


def _cards_suprimidos(conteudo: Conteudo, destaques: dict[str, Destaque]) -> list[str]:
    """Ids dos cards cuja condicao e falsa ou cujo texto cita destaque ausente da base."""
    return [
        c["id"] for c in conteudo.cards
        if not (avaliar_condicao(c["condicao"], destaques) and _cita_so_o_que_existe(c, destaques))
    ]


# --- Estados, Explorar e Cards ---

def _contexto_dos_estados(dados: DadosSite) -> dict:
    vistas = vistas_estados(dados)
    for vista in vistas:
        vista["atualizacoes"] = _atualizacoes(dados, [vista["indicador_id"]])
    return {"estados": vistas, "faixas": [f"nn-f{i}" for i in range(FAIXAS)]}


def _vista_explorar(dados: DadosSite, ind: IndicadorExplorar, por_territorio: dict, territorio: str) -> dict:
    """O titulo, o grafico (as duas larguras) e a tabela do territorio escolhido.

    Territorio sem nenhum ponto no indicador: `grafico` fica None e a pagina mostra o aviso. As linhas de referencia
    (Brasil, Nordeste) nao aparecem sozinhas, para nao parecerem a serie do territorio.
    """
    vista = {
        "titulo": f"{ind.nome}: {NOME_DO_TERRITORIO[territorio]} ({ind.unidade})", "grafico": None, "tabela": [],
    }
    if not por_territorio[territorio]:
        return vista
    linhas = [
        Linha(NOME_DO_TERRITORIO[t], ETIQUETA_DO_TERRITORIO[t], pontos(por_territorio[t]), t == territorio)
        for t in (*referencias(territorio), territorio)
    ]
    cfg = ConfigGrafico(titulo=f"{ind.nome}, {NOME_DO_TERRITORIO[territorio]}", casas=ind.casas, sufixo=ind.sufixo)
    largo, estreito = _desenhar(linhas, cfg, dados.governos)
    if largo:
        vista["grafico"] = {"id": "g-explorar", "largo": largo, "estreito": estreito}
        vista["tabela"] = tabela_do_territorio(ind, por_territorio[territorio], territorio)
    return vista


def vista_explorar_em_html(dados: DadosSite, textos: dict, indicador: str, territorio: str) -> str:
    """O HTML da vista do Explorar de um indicador e territorio: grafico e tabela, ou o aviso de que nao ha dados."""
    ind = POR_CHAVE[indicador]
    vista = _vista_explorar(dados, ind, pontos_do_indicador(dados, ind), territorio)
    return str(_ambiente().get_template("_vista_explorar.html").module.vista(vista, textos["explorar"]))


def _contexto_do_explorar(dados: DadosSite, por_indicador: dict[str, dict[str, list[list]]]) -> dict:
    chave, territorio = EXPLORAR_INICIAL
    vista = _vista_explorar(dados, POR_CHAVE[chave], por_indicador[chave], territorio)
    return {
        "explorar": {
            "indicadores": INDICADORES_EXPLORAR,
            "territorios": [{"id": id_, "nome": nome, "etiqueta": etiqueta} for id_, nome, etiqueta in TERRITORIOS],
            "inicial": {"indicador": chave, "territorio": territorio},
            "vista": vista,
            "governos": faixas_em_json(dados.governos),
        }
    }


def _cartao(dados: DadosSite, destaques: dict[str, Destaque], card: dict) -> dict:
    """O card pronto para o modelo: textos preenchidos, minigrafico e o resumo das previas de compartilhamento."""
    de, para = preencher(card["de"], destaques), preencher(card["para"], destaques)
    frase, fecho = preencher(card["frase"], destaques), preencher(card["fecho"], destaques)
    frase_feita = preencher(card["frase_feita"], destaques)
    return {
        "id": card["id"], "rotulo": preencher(card["rotulo"], destaques), "frase_feita": frase_feita,
        "titulo_sem_aspas": frase_feita.strip("“”"), "de": de, "para": para, "frase": frase, "fecho": fecho,
        "fonte": preencher(card["fonte"], destaques), "longo": card.get("longo", False),
        "mini": minigrafico(_linhas(dados, card["grafico"])),
        "resumo": f"{de} → {para} {frase} {fecho}",
    }


# --- Como chegamos ate aqui ---

def _medidas_da_imagem(arquivo: str, peso_maximo: int, falta: str | None = None) -> tuple[int, int]:
    """Largura e altura do arquivo em estaticos/historia/ (vao para o width e o height do HTML, sem salto de layout).

    Recusa arquivo que falta (com a mensagem `falta`, quando dada), que passa do peso ou que nao esta em 21:9 (recorte
    feito no arquivo, nao pelo navegador).
    """
    caminho = PASTA_ESTATICOS / "historia" / arquivo
    if not caminho.is_file():
        raise ErroConteudo(falta or f"historia.yaml cita {arquivo}, que não está em estaticos/historia/ do pacote.")
    if caminho.stat().st_size > peso_maximo:
        raise ErroConteudo(f"{arquivo}: {caminho.stat().st_size} bytes, acima de {peso_maximo}.")
    largura, altura = medidas_da_webp(caminho)
    base, alto = PROPORCAO
    if abs(largura * alto - altura * base) > base:  # folga de 1 px na altura
        raise ErroConteudo(f"{arquivo}: {largura} x {altura}, fora da proporção {base}:{alto}.")
    return largura, altura


def _credito(imagem: ImagemHistorica, peso_maximo: int = PESO_MAXIMO_DA_EPOCA) -> dict:
    largura, altura = _medidas_da_imagem(imagem.arquivo, peso_maximo)
    return {
        "src": PASTA_IMAGENS_HISTORIA + imagem.arquivo, "alt": imagem.alt, "titulo": imagem.titulo,
        "autor": imagem.autor, "data": imagem.data, "licenca": ROTULO_DA_LICENCA[imagem.licenca], "url": imagem.url,
        "largura": largura, "altura": altura,
    }


def _imagem_da_epoca(imagem: ImagemHistorica) -> dict:
    """O credito da imagem da epoca (artigo e modal) e a miniatura do cartao, arquivo proprio por convencao.

    O cartao usa so a miniatura (ate 25 000 bytes): as 8 da faixa cabem no limite de 1 MB da pagina sem modal aberto.
    """
    nome = arquivo_do_cartao(imagem.arquivo)
    largura, altura = _medidas_da_imagem(
        nome, PESO_MAXIMO_DO_CARTAO,
        falta=f"{imagem.arquivo} não tem a miniatura do cartão: falta {nome} em estaticos/historia/ do pacote "
              f"(o mesmo recorte reduzido, até {PESO_MAXIMO_DO_CARTAO} bytes).",
    )
    return {**_credito(imagem), "cartao": {"src": PASTA_IMAGENS_HISTORIA + nome, "largura": largura, "altura": altura}}


def _marcos(epoca) -> list[dict]:
    return [
        {"ano": m.ano, "titulo": m.titulo, "texto": m.texto,
         "imagem": None if m.imagem is None else _credito(m.imagem, PESO_MAXIMO_DO_MARCO)}
        for m in epoca.marcos
    ]


def _abertura_da_historia(historia: Historia, governos: pd.DataFrame) -> dict:
    """Os numeros grandes (primeiro e ultimo censo), o grafico dos censos nas duas larguras e a tabela dos valores.

    A parcela vem sempre de `parcela_do_nordeste` (censos.csv), nunca de texto. O grafico usa as funcoes dos outros
    graficos com um eixo proprio (do primeiro ao ultimo censo), a linha emendada (os censos nao sao anuais) e nenhuma
    faixa de governo (`governos` vazio, com as colunas de sempre).
    """
    parcelas = parcela_do_nordeste(historia)
    primeiro, ultimo = parcelas[0], parcelas[-1]
    linhas = [Linha("Nordeste", "Nordeste", parcelas, True)]
    cfg = ConfigGrafico(
        titulo=f"Parcela da população brasileira que vivia no Nordeste, por censo, de {primeiro.ano} a {ultimo.ano}",
        casas=1, sufixo="%", min0=True,
    )
    eixo = (primeiro.ano, ultimo.ano + 1)
    numeros = [{"valor": f"{numero(p.valor, 1)}%", "ano": p.ano} for p in dict.fromkeys((primeiro, ultimo))]
    return {
        "numeros": numeros,
        "grafico": {
            "id": "g-censos",
            "largo": grafico_linhas(linhas, cfg, governos, **LARGO, eixo=eixo, emendar=True),
            "estreito": grafico_linhas(linhas, cfg, governos, **ESTREITO, eixo=eixo, emendar=True),
        },
        "tabela": [
            {"ano": ano, "nordeste": numero(nordeste, 0), "brasil": numero(brasil, 0),
             "parcela": f"{numero(p.valor, 1)}%", "fonte": fonte}
            for (ano, nordeste, brasil, fonte), p in zip(historia.censos, parcelas)
        ],
    }


def _epocas(historia: Historia) -> list[dict]:
    """Cada epoca pronta para o cartao da linha do tempo e para o artigo do modal, com a anterior e a proxima."""
    epocas = historia.epocas
    return [
        {
            "id": e.id, "periodo": f"{e.inicio}–{e.fim}", "nome": e.nome, "resumo": e.resumo,
            "paragrafos": [p.strip() for p in e.texto.split("\n\n") if p.strip()],
            "marcos": _marcos(e),
            "numeros": [
                {"valor": n.valor, "legenda": n.legenda, "tipo": n.tipo, "rotulo": TIPOS[n.tipo], "fonte": n.fonte}
                for n in e.numeros
            ],
            "o_que_ficou": e.o_que_ficou, "interpretacao": TIPOS["interpretacao"],
            "fontes": [{"texto": f["texto"], "url": f.get("url")} for f in e.fontes],
            "imagem": None if e.imagem is None else _imagem_da_epoca(e.imagem),
            "anterior": epocas[i - 1].id if i > 0 else None,
            "proxima": epocas[i + 1].id if i + 1 < len(epocas) else None,
        }
        for i, e in enumerate(epocas)
    ]


def _contexto_da_historia(historia: Historia, governos: pd.DataFrame) -> dict:
    return {
        "historia": {
            "previa": AVISO_DA_PREVIA if historia.provisoria else None, "abertura": historia.abertura, "fecho": historia.fecho,
            **_abertura_da_historia(historia, governos), "epocas": _epocas(historia),
        }
    }


def _creditos_da_historia(historia: Historia) -> list[dict]:
    """A lista de creditos das imagens da pagina, para Sobre os dados: cada epoca com imagem e, logo depois, cada marco
    dela com imagem."""
    creditos = []
    for e in historia.epocas:
        if e.imagem is not None:
            creditos.append({"epoca": e.nome, **_credito(e.imagem)})
        creditos += [
            {"epoca": f"{e.nome}, marco de {m.ano}", **_credito(m.imagem, PESO_MAXIMO_DO_MARCO)}
            for m in e.marcos if m.imagem is not None
        ]
    return creditos


# --- paginas ---

def _anos_da_base(dados: DadosSite) -> tuple[int, int]:
    com_valor = dados.base.loc[dados.base["valor"].notna() & (dados.base["tipo_dado"] != "indisponivel"), "ano"]
    return int(com_valor.min()), int(com_valor.max())


def _tamanho(n_bytes: int) -> str:
    return f"{numero(n_bytes / 1e6, 1)} MB" if n_bytes >= 1e6 else f"{numero(n_bytes / 1e3, 0)} kB"


def _arquivos_de_dados(caminhos: Caminhos, textos: dict) -> list[dict]:
    arquivos = []
    for nome in ARQUIVOS_DE_DADOS:
        conteudo = (caminhos.base / nome).read_bytes()
        arquivos.append({
            "nome": nome, "rota": f"/dados/{nome}", "url": f"{URL_DO_SITE}/dados/{nome}",
            "descricao": textos["dados"]["arquivos"][nome],
            "sha256": hashlib.sha256(conteudo).hexdigest(), "tamanho": _tamanho(len(conteudo)),
        })
    return arquivos


def _json_ld(dados: DadosSite, textos: dict, anos: tuple[int, int], arquivos: list[dict]) -> str:
    ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": textos["dataset"]["nome"],
        "description": textos["dataset"]["descricao"],
        "url": f"{URL_DO_SITE}/dados/",
        "inLanguage": "pt-BR",
        "creator": {"@type": "Person", "name": "Júlio Diógenes", "url": URL_DO_AUTOR},
        "license": LICENCA,
        "temporalCoverage": f"{anos[0]}/{anos[1]}",
        "spatialCoverage": "Nordeste, Brasil",
        "dateModified": dados.data_base,
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "text/csv", "name": a["nome"], "contentUrl": a["url"]}
            for a in arquivos
        ],
    }
    return json.dumps(ld, ensure_ascii=False, indent=2).replace("<", "\\u003c")  # nunca fecha o <script>


def _fontes(dados: DadosSite) -> list[dict]:
    """Uma entrada por indicador, com uma linha por serie, na ordem das fichas (por id)."""
    return [
        {
            "nome": f.nome, "orgao": f.orgao,
            "series": [{"fonte": s.fonte, "url": s.url, "base_origem": s.base_origem} for s in f.series],
        }
        for f in dados.fichas.values()
    ]


def _ambiente() -> Environment:
    return Environment(
        loader=FileSystemLoader(PASTA_MODELOS), autoescape=True, undefined=StrictUndefined,
        trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True,
    )


def _contorno(caminhos: Caminhos) -> dict:
    """O viewBox e o caminho do contorno do Nordeste (metadados/site/nordeste-contorno.svg), para a imagem OpenGraph."""
    svg = ET.fromstring((caminhos.metadados.joinpath(*CONTORNO)).read_text(encoding="utf-8"))
    caminho = next(e for e in svg.iter() if e.tag.endswith("}path"))
    return {"viewbox": svg.attrib["viewBox"], "d": caminho.attrib["d"]}


def _texto_og(chave: str, textos: dict) -> dict:
    """O titulo da imagem de uma pagina: a pergunta da abertura (com o destaque) no Inicio, o nome da pagina nas demais."""
    if chave == "index":
        return {"linhas": textos["abertura"]["titulo"], "destaque": textos["abertura"]["destaque"]}
    return {"linhas": [textos["paginas"][chave]["titulo"].split(" · ")[0]], "destaque": None}


def _hash_dos_recursos(saida: Path) -> str:
    """Resumo do estilo, das fontes e da foto que as paginas de apoio carregam: o que, alem do HTML, entra na imagem."""
    resumo = hashlib.sha256()
    recursos = [saida / "estilo.css", *sorted(p for p in (saida / "fontes").rglob("*") if p.is_file())]
    foto = saida / FOTO_ARQUIVO
    if foto.is_file():
        recursos.append(foto)
    for recurso in recursos:
        resumo.update(recurso.relative_to(saida).as_posix().encode("utf-8") + b"\0")
        resumo.update(hashlib.sha256(recurso.read_bytes()).digest())
    return resumo.hexdigest()


def _entrada_da_imagem(alvo: AlvoImagem, recursos: str) -> str:
    """sha256 do que produz o PNG: tamanho, versao do procedimento de render, recursos e o HTML de apoio."""
    cabeca = f"{alvo.largura}x{alvo.altura}\0{VERSAO_DO_RENDER}\0{recursos}\0"
    return hashlib.sha256(cabeca.encode("utf-8") + alvo.html.read_bytes()).hexdigest()


def _ler_manifesto(pasta: Path | None) -> dict[str, str]:
    """O manifesto de imagens de uma saida anterior; ausente ou ilegivel vale como vazio (tudo e renderizado de novo)."""
    if pasta is None:
        return {}
    try:
        manifesto = json.loads((pasta / MANIFESTO_DE_IMAGENS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return manifesto if isinstance(manifesto, dict) else {}


def _gerar_imagens(
    saida: Path, ambiente: Environment, comum: dict, cards: list[dict], contorno: dict, anterior: Path | None,
    paginas: tuple[Pagina, ...] = PAGINAS,
) -> None:
    """og/<pagina>.png (1200x630) para cada pagina que nao e de card e cards/<id>.png (1080x1350) para cada card.

    As paginas de card ja apontam o og:image para o PNG do proprio card. O Chromium fotografa paginas de apoio
    (modelos/og.html) escritas em `_imagens/`, que somem ao fim, com o estilo e as fontes locais do site.

    O PNG de uma imagem so e refeito se a entrada mudou em relacao a `anterior` (o manifesto dela guarda o sha256 da
    entrada de cada imagem): o Chromium nao gera os mesmos bytes entre versoes, e a publicacao semanal nao pode
    mudar so por isso (Ruling S-X). O manifesto desta saida e gravado ao fim.
    """
    apoio = saida / "_imagens"
    apoio.mkdir()
    alvos = []
    try:
        for p in paginas:
            nome = f"og-{p.chave}.html"
            _escrever(
                ambiente, apoio, "og.html", nome, titulo=NOME_DO_SITE, card=None, contorno=contorno,
                og=_texto_og(p.chave, comum["textos"]), **comum,
            )
            alvos.append(AlvoImagem(apoio / nome, saida / "og" / f"{p.chave}.png", *OG))
        for card in cards:
            nome = f"card-{card['id']}.html"
            _escrever(ambiente, apoio, "og.html", nome, titulo=card["frase_feita"], card=card, contorno=None, og=None, **comum)
            alvos.append(AlvoImagem(apoio / nome, saida / "cards" / f"{card['id']}.png", *CARD))
        recursos = _hash_dos_recursos(saida)
        manifesto = {a.png.relative_to(saida).as_posix(): _entrada_da_imagem(a, recursos) for a in alvos}
        anteriores = _ler_manifesto(anterior)
        pendentes = []
        for alvo in alvos:
            chave = alvo.png.relative_to(saida).as_posix()
            velho = None if anterior is None else anterior / chave
            if anteriores.get(chave) == manifesto[chave] and velho is not None and velho.is_file():
                alvo.png.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(velho, alvo.png)
            else:
                pendentes.append(alvo)
        if pendentes:
            renderizar(pendentes, raiz=saida)
        texto = json.dumps(manifesto, indent=2, sort_keys=True) + "\n"
        (saida / MANIFESTO_DE_IMAGENS).write_bytes(texto.encode("utf-8"))
    finally:
        shutil.rmtree(apoio)


def _validar_saida(caminhos: Caminhos, saida: Path, anterior: Path | None = None) -> None:
    """A saida e apagada: nunca a base publicada, os relatorios ou os metadados, nem uma pasta que os contenha ou
    que esteja dentro deles. A saida anterior (de onde se copiam os PNG) tambem nao pode ser apagada por isso."""
    destino = saida.resolve()
    if anterior is not None and (anterior.resolve() == destino or destino in anterior.resolve().parents):
        raise ValueError(f"A saída anterior {anterior} é a própria saída {saida} (ou está dentro dela): ela seria apagada antes de ser lida.")
    for protegida in (caminhos.base, caminhos.relatorios, caminhos.metadados):
        protegida = protegida.resolve()
        if destino == protegida or destino in protegida.parents or protegida in destino.parents:
            raise ValueError(f"A pasta de saída {saida} mexeria em {protegida}: escolha outra, fora da base e dos metadados.")


def _exigir(parte: object, spec: set | dict, caminho: str) -> None:
    """`spec` e um conjunto de chaves ou um mapa chave -> spec (None: so a chave); falta vira ErroConteudo."""
    if not isinstance(parte, dict):
        raise ErroConteudo(f"textos.yaml: falta a seção {caminho}.")
    for chave in sorted(spec):
        if chave not in parte:
            raise ErroConteudo(f"textos.yaml: falta {caminho}.{chave}.")
        if isinstance(spec, dict) and spec[chave] is not None:
            _exigir(parte[chave], spec[chave], f"{caminho}.{chave}")


def _validar_textos(textos: object, paginas: tuple[Pagina, ...] = PAGINAS) -> None:
    """As chaves de textos.yaml que o gerador e os modelos leem; faltando uma, ErroConteudo em vez de KeyError."""
    exigidos = {
        **TEXTOS_EXIGIDOS,
        "paginas": {p.chave: {"titulo", "descricao"} for p in paginas},
        "dados": {**dict.fromkeys(TEXTOS_EXIGIDOS["dados"] - {"arquivos"}), "arquivos": set(ARQUIVOS_DE_DADOS)},
    }
    _exigir(textos, exigidos, "textos")
    if "foto" in textos:
        _validar_foto(textos["foto"])
    _validar_autor(textos["autor"])


def _validar_foto(foto: object) -> None:
    """`foto: {credito, url}` (Rulings S-Q e S-Z): o credito aponta para a pagina da licenca, e a foto e o
    estaticos/foto-abertura.webp do pacote, o nome que o estilo.css usa."""
    _exigir(foto, set(FOTO_EXIGIDA), "textos.foto")
    if not all(isinstance(foto[chave], str) and foto[chave].strip() for chave in FOTO_EXIGIDA):
        raise ErroConteudo("textos.yaml: foto.credito e foto.url são textos, não vazios.")
    arquivo = PASTA_ESTATICOS / FOTO_ARQUIVO
    if not arquivo.is_file():
        raise ErroConteudo(f"textos.yaml tem foto, mas {FOTO_ARQUIVO} não está em estaticos/ do pacote.")
    if arquivo.stat().st_size > FOTO_TAMANHO_MAXIMO:
        raise ErroConteudo(f"{FOTO_ARQUIVO} passa de {FOTO_TAMANHO_MAXIMO // 1000} KB.")


def _validar_autor(autor: dict) -> None:
    """Os textos do autor sao textos nao vazios; `link` aparece em quem_sou.texto e em formacao_vazia (e o trecho que
    vira link para o site do autor); `formacao`, se vier, e uma lista de textos nao vazios (nula ou vazia vale ausente)."""
    textos = {
        "nome": autor["nome"], "titulo": autor["titulo"], "fechar": autor["fechar"], "link": autor["link"],
        "formacao_titulo": autor["formacao_titulo"], "formacao_vazia": autor["formacao_vazia"],
        **{f"{secao}.{campo}": autor[secao][campo] for secao in ("quem_sou", "motivacao") for campo in ("titulo", "texto")},
    }
    for nome, texto in textos.items():
        if not isinstance(texto, str) or not texto.strip():
            raise ErroConteudo(f"textos.yaml: autor.{nome} é um texto, não vazio.")
    for nome, texto in (("quem_sou.texto", autor["quem_sou"]["texto"]), ("formacao_vazia", autor["formacao_vazia"])):
        if autor["link"] not in texto:
            raise ErroConteudo(f"textos.yaml: autor.{nome} não cita autor.link ({autor['link']!r}), o trecho que vira link.")
    formacao = autor.get("formacao")
    if formacao is not None and (
        not isinstance(formacao, list) or not all(isinstance(i, str) and i.strip() for i in formacao)
    ):
        raise ErroConteudo("textos.yaml: autor.formacao é uma lista de textos não vazios.")


def _com_link(texto: str, ancora: str) -> dict:
    """O texto cortado no trecho que vira link: antes, a ancora e depois (o modelo monta o <a> sem repetir o texto)."""
    antes, _, depois = texto.partition(ancora)
    return {"antes": antes, "ancora": ancora, "depois": depois}


def _foto_do_autor() -> dict | None:
    """`estaticos/autor.webp`, se existir: o src e o width/height do arquivo (sem salto de layout). Recusa o que nao
    e WebP ou passa do peso."""
    arquivo = PASTA_ESTATICOS / AUTOR_FOTO
    if not arquivo.is_file():
        return None
    if arquivo.stat().st_size > AUTOR_FOTO_TAMANHO_MAXIMO:
        raise ErroConteudo(f"{AUTOR_FOTO} passa de {AUTOR_FOTO_TAMANHO_MAXIMO // 1000} KB.")
    largura, altura = medidas_da_webp(arquivo)
    return {"src": f"/{AUTOR_FOTO}", "largura": largura, "altura": altura}


def _contexto_do_autor(autor: dict) -> dict:
    """O que os modelos leem do autor (rodape, modal e secao de Sobre): nome, iniciais, foto e marca (se existirem) e
    as tres secoes, com o link do site do autor ja marcado nos textos que o citam."""
    palavras = autor["nome"].split()
    formacao = autor.get("formacao") or []
    return {
        "nome": autor["nome"], "iniciais": (palavras[0][0] + palavras[-1][0]).upper(), "url": URL_DO_AUTOR,
        "titulo": autor["titulo"], "fechar": autor["fechar"], "link": autor["link"],
        "foto": _foto_do_autor(),
        "marca": f"/{AUTOR_MARCA}" if (PASTA_ESTATICOS / AUTOR_MARCA).is_file() else None,
        "quem_sou": {"titulo": autor["quem_sou"]["titulo"], "texto": _com_link(autor["quem_sou"]["texto"], autor["link"])},
        "motivacao": autor["motivacao"],
        "formacao": {
            "titulo": autor["formacao_titulo"], "itens": formacao,
            "vazio": _com_link(autor["formacao_vazia"], autor["link"]),
        },
    }


def _paragrafos_da_abertura(itens: list, destaques: dict[str, Destaque]) -> tuple[list[str], list[str]]:
    """Textos dos paragrafos da abertura que valem e os ids dos que sairam.

    Como no fecho, sai o paragrafo cuja condicao e falsa ou cujo texto cita destaque ausente da base.
    """
    textos, suprimidos = [], []
    for item in itens:
        if not isinstance(item, dict) or not {"id", "texto"} <= item.keys() or item.keys() - {"id", "texto", "condicao"}:
            raise ErroConteudo(f"textos.yaml, abertura.intro: cada parágrafo tem id e texto, e pode ter condicao: {item!r}.")
        vale = _cita_so_o_que_existe(item["texto"], destaques)
        if vale and "condicao" in item:
            vale = avaliar_condicao(item["condicao"], destaques)
        if vale:
            textos.append(item["texto"])
        else:
            suprimidos.append(item["id"])
    return textos, suprimidos


def _faixa(faixa: dict, destaques: dict[str, Destaque]) -> tuple[dict, list[str]]:
    """A faixa de numeros da abertura pronta para preencher e os ids que sairam (`[]` ou o id da faixa).

    Os numeros grandes e o paragrafo valem juntos: saem se a condicao e falsa ou se algum texto cita destaque ausente
    da base. A nota (de onde vem o dado, o que as faixas de governo nao dizem) nao tem numero e fica sempre.
    """
    numeros = faixa["numeros"]
    formato_ok = isinstance(numeros, list) and numeros and all(
        isinstance(n, dict) and n.keys() == {"valor", "rotulo", "ano"} for n in numeros
    )
    if not formato_ok or faixa.keys() - {*TEXTOS_EXIGIDOS["faixa"], "condicao"}:
        raise ErroConteudo("textos.yaml, faixa: numeros é uma lista de valor, rotulo e ano; as demais chaves são "
                           "rotulo, id, texto, nota e, se houver, condicao.")
    vale = _cita_so_o_que_existe([faixa["texto"], numeros], destaques)
    if vale and "condicao" in faixa:
        vale = avaliar_condicao(faixa["condicao"], destaques)
    pronta = {"rotulo": faixa["rotulo"], "nota": faixa["nota"], "texto": None, "numeros": []}
    if not vale:
        return pronta, [faixa["id"]]
    return {**pronta, "texto": faixa["texto"], "numeros": numeros}, []


def _copiar_estaticos(saida: Path, com_foto: bool, com_historia: bool) -> None:
    """Estilo, script, fontes (com a licenca OFL) e .htaccess, na raiz do site; cache do Python fica de fora.

    A foto da abertura so vai quando textos.yaml tem a chave `foto` (e o credito): foto no site sem credito nao sai.
    As imagens das epocas e dos marcos (historia/) so vao quando a pagina Como chegamos e gerada.
    """
    ignorar = ["__pycache__", "*.pyc"] + ([] if com_foto else [FOTO_ARQUIVO]) + ([] if com_historia else ["historia"])
    shutil.copytree(PASTA_ESTATICOS, saida, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*ignorar))


def _escrever(ambiente: Environment, saida: Path, modelo: str, arquivo: str, **contexto: object) -> None:
    destino = saida / arquivo
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(ambiente.get_template(modelo).render(**contexto).encode("utf-8"))


def _pagina(
    chave: str, rota: str, titulo: str, descricao: str, imagem: str, json_ld: str | None = None, noindex: bool = False,
) -> dict:
    return {
        "chave": chave, "rota": rota, "url": URL_DO_SITE + rota, "titulo": titulo, "descricao": descricao,
        "imagem": imagem, "json_ld": json_ld, "noindex": noindex,
    }


def gerar_site(
    caminhos: Caminhos, saida: Path, *, imagens: bool = True, anterior: Path | None = None,
    incluir_provisoria: bool = False,
) -> RelatorioSite:
    """Apaga e recria `saida` com as paginas do site e as copias dos CSVs; devolve o que foi suprimido.

    `anterior` e a saida da geracao anterior (uma pasta de fora de `saida`): os PNG cuja entrada nao mudou sao
    copiados dela em vez de renderizados de novo.

    A pagina Como chegamos ate aqui sai quando `historia.yaml` existe e nao e provisorio. `incluir_provisoria` (so
    para previa local; a automacao semanal nunca usa) gera a pagina com o conteudo provisorio, com o aviso de previa
    e fora dos buscadores (`noindex`).
    """
    _validar_saida(caminhos, saida, anterior)
    dados = DadosSite.carregar(caminhos)
    conteudo = carregar_conteudo(caminhos.metadados / "site")
    historia = carregar_historia(caminhos.metadados / "site")
    com_historia = historia is not None and (not historia.provisoria or incluir_provisoria)
    paginas_do_menu = paginas_do_site(com_historia)
    _validar_textos(conteudo.textos, paginas_do_menu)
    destaques = calcular_destaques(dados, conteudo)
    data = data_por_extenso(dados.data_base)
    abertura, paragrafos_suprimidos = _paragrafos_da_abertura(conteudo.textos["abertura"]["intro"], destaques)
    faixa, faixa_suprimida = _faixa(conteudo.textos["faixa"], destaques)
    com_abertura = {
        **conteudo.textos, "abertura": {**conteudo.textos["abertura"], "intro": abertura}, "faixa": faixa,
    }
    textos = _resolver(com_abertura, destaques, data)
    perguntas, fechos_suprimidos = _perguntas(dados, destaques, conteudo)
    cards_fora = _cards_suprimidos(conteudo, destaques)
    cards = [_cartao(dados, destaques, c) for c in conteudo.cards if c["id"] not in cards_fora]
    explorar = dados_explorar(dados)
    anos = _anos_da_base(dados)
    arquivos = _arquivos_de_dados(caminhos, textos)
    comum = {
        "menu": [{"chave": p.chave, "rota": p.rota, "rotulo": p.rotulo} for p in paginas_do_menu],
        "data_base": data, "sha256_base": dados.sha256_base, "licenca": LICENCA, "autor_url": URL_DO_AUTOR,
        "foto": textos.get("foto"), "autor": _contexto_do_autor(textos["autor"]),
        "textos": textos, "selo": f"{textos['abertura']['eyebrow']} · {anos[0]} a {anos[1]}",
        "perguntas": perguntas, "fontes": _fontes(dados), "arquivos": arquivos, "cards": cards,
        "data_curta": "/".join(reversed(dados.data_base.split("-"))),
        "creditos_historia": _creditos_da_historia(historia) if com_historia else [],
    }
    por_pagina = {"estados": _contexto_dos_estados(dados), "explorar": _contexto_do_explorar(dados, explorar)}
    if com_historia:
        por_pagina[PAGINA_HISTORIA.chave] = _contexto_da_historia(historia, dados.governos.iloc[:0])

    if saida.exists():
        shutil.rmtree(saida)
    (saida / "dados").mkdir(parents=True)
    (saida / "explorar" / "dados").mkdir(parents=True)
    _copiar_estaticos(saida, com_foto=comum["foto"] is not None, com_historia=com_historia)
    ambiente = _ambiente()
    for p in paginas_do_menu:
        pagina = _pagina(
            p.chave, p.rota, textos["paginas"][p.chave]["titulo"], textos["paginas"][p.chave]["descricao"],
            f"{URL_DO_SITE}/og/{p.chave}.png",
            _json_ld(dados, textos, anos, arquivos) if p.chave in PAGINAS_COM_DATASET else None,
            noindex=p is PAGINA_HISTORIA and historia.provisoria,
        )
        _escrever(ambiente, saida, p.modelo, p.arquivo, pagina=pagina, **comum, **por_pagina.get(p.chave, {}))
    for card in cards:
        rota = f"/cards/{card['id']}/"
        pagina = _pagina(
            "cards", rota, f"{card['frase_feita']} · {NOME_DO_SITE}", card["resumo"],
            f"{URL_DO_SITE}/cards/{card['id']}.png",
        )
        _escrever(ambiente, saida, "card.html", f"cards/{card['id']}/index.html", pagina=pagina, card=card, **comum)
    for nome in ARQUIVOS_DE_DADOS:
        shutil.copyfile(caminhos.base / nome, saida / "dados" / nome)
    for chave, por_territorio in explorar.items():
        texto = json.dumps(por_territorio, ensure_ascii=False, separators=(",", ":")) + "\n"
        (saida / "explorar" / "dados" / f"{chave}.json").write_bytes(texto.encode("utf-8"))

    paginas = [p.arquivo for p in paginas_do_menu] + [f"cards/{c['id']}/index.html" for c in cards]
    if imagens:
        _gerar_imagens(saida, ambiente, comum, cards, _contorno(caminhos), anterior, paginas_do_menu)
    return RelatorioSite(
        paginas, [*paragrafos_suprimidos, *faixa_suprimida, *fechos_suprimidos], cards_fora,
        historia_provisoria=historia is not None and historia.provisoria,
    )


def relatorio_em_json(relatorio: RelatorioSite) -> str:
    return json.dumps(asdict(relatorio), ensure_ascii=False, indent=2) + "\n"
