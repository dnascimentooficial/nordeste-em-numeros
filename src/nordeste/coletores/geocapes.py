"""Coletor da API JSON do GeoCAPES (geocapes.capes.gov.br), a mesma que o mapa do site consulta.

Nao e API documentada nem arquivo de dados abertos: sao as chamadas que a pagina `geocapes/` faz (lidas no
`geocapes.js` do proprio site em 2026-11-03). Por isso o coletor confere o que pode e falha alto se algo mudar:

1. `GET /rest/fotosDados/?indicador=<id>` lista as "fotos" do indicador, uma por ano-base, com o `id` da foto (que muda a
   cada republicacao), o ano e o indicador (descricao e o aviso de metodo). A descricao tem de ser a da ficha, e cada ano
   da serie tem de ter exatamente uma foto;
2. para cada ano, `PUT /rest/fotosDados/<foto>/dadosSumarizados?referencial=quantidade&sumarizador=<campos>` com corpo
   `{}` devolve as contagens somadas pelos campos (por exemplo, `iduf`, ou `uf,grau,fluxo`).

O arquivo bruto da serie e um JSON montado aqui, com as chaves e listas em ordem fixa (o mesmo conteudo da fonte da o
mesmo sha256): a URL da lista, o indicador (id, descricao, aviso) e, por ano, a foto usada e as contagens. Nome de
usuario e consulta SQL que a lista traz nao sao guardados.
"""

import json
from urllib.parse import urlencode

import requests

from nordeste.coletores.erros import ErroColeta
from nordeste.coletores.http import baixar

BASE = "https://geocapes.capes.gov.br/geocapes/rest"


def url_geocapes(parametros: dict) -> str:
    """URL registrada da coleta: a lista de fotos do indicador."""
    indicador = parametros.get("indicador")
    if not isinstance(indicador, int) or isinstance(indicador, bool):
        raise ErroColeta("parametros do coletor geocapes sem o indicador (número inteiro)")
    return f"{BASE}/fotosDados/?indicador={indicador}"


def _json(conteudo: bytes, url: str):
    try:
        return json.loads(conteudo)
    except ValueError as erro:
        raise ErroColeta(f"GeoCAPES: resposta ilegível em {url} ({erro})") from erro


def baixar_geocapes(parametros: dict, inicio: int, fim: int, sessao: requests.Session | None = None) -> bytes:
    """JSON da serie, de `inicio` a `fim`; qualquer mudanca na lista de fotos (descricao, ano sem foto ou com duas) e
    ErroColeta."""
    for chave in ("descricao", "sumarizador"):
        if not isinstance(parametros.get(chave), str) or not parametros[chave]:
            raise ErroColeta(f"parametros do coletor geocapes sem {chave}")
    url = url_geocapes(parametros)
    fotos = _json(baixar(url, sessao=sessao), url)
    if not isinstance(fotos, list) or not all(isinstance(f, dict) for f in fotos):
        raise ErroColeta(f"GeoCAPES: a lista de fotos de {url} não é uma lista de objetos")
    indicadores = {json.dumps(f.get("indicador", {}).get("id")) for f in fotos}
    descricoes = {f.get("indicador", {}).get("descricao") for f in fotos}
    if indicadores != {json.dumps(parametros["indicador"])} or descricoes != {parametros["descricao"]}:
        raise ErroColeta(
            f"GeoCAPES: o indicador {parametros['indicador']} mudou (descrições {sorted(map(str, descricoes))}, "
            f"esperava {parametros['descricao']!r})")
    por_ano: dict[int, list[dict]] = {}
    for foto in fotos:
        por_ano.setdefault(foto.get("ano"), []).append(foto)
    problemas = [f"{ano}: {len(por_ano.get(ano, []))} fotos" for ano in range(inicio, fim + 1)
                 if len(por_ano.get(ano, [])) != 1]
    if problemas:
        raise ErroColeta(f"GeoCAPES: cada ano da série precisa de uma foto ({'; '.join(problemas)})")
    indicador = fotos[0]["indicador"]
    anos = {}
    consulta = urlencode({"referencial": "quantidade", "sumarizador": parametros["sumarizador"]})
    for ano in range(inicio, fim + 1):
        foto = por_ano[ano][0]["id"]
        endereco = f"{BASE}/fotosDados/{foto}/dadosSumarizados?{consulta}"
        dados = _json(baixar(endereco, sessao=sessao, put_json={}), endereco)
        if not isinstance(dados, list) or not all(isinstance(d, dict) for d in dados):
            raise ErroColeta(f"GeoCAPES: {endereco} não devolveu uma lista de objetos")
        ordenados = sorted(dados, key=lambda d: json.dumps(d, sort_keys=True, ensure_ascii=False))
        anos[str(ano)] = {"foto": foto, "dados": ordenados}
    bruto = {
        "fonte": url,
        "indicador": {"id": indicador.get("id"), "descricao": indicador.get("descricao"),
                      "mensagem": indicador.get("mensagem")},
        "sumarizador": parametros["sumarizador"],
        "anos": anos,
    }
    return (json.dumps(bruto, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
