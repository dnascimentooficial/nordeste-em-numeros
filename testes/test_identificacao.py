"""Toda coleta se identifica com o mesmo User-Agent, definido num lugar so (nordeste.coletores.http)."""

import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

from nordeste import automacao
from nordeste.caminhos import Caminhos
from nordeste.coletores import coletar_serie
from nordeste.coletores.http import USER_AGENT, baixar, baixar_para_arquivo
from nordeste.fichas import Ficha, Serie, carregar_fichas

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]

ESPERADO = "nordeste-em-numeros/1.0 (+https://nordeste.dnascimento.com.br)"


class _Servidor:
    """Responde 200 so a quem se identifica com USER_AGENT (como o gov.br, que da 403 ao python-requests)."""

    def __init__(self):
        self.agentes: list[str | None] = []
        servidor = self

        class Tratador(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - nome da API do http.server
                agente = self.headers.get("User-Agent")
                servidor.agentes.append(agente)
                status, corpo = (200, b"conteudo") if agente == ESPERADO else (403, b"proibido")
                self.send_response(status)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *_args):
                pass

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Tratador)
        threading.Thread(target=self._http.serve_forever, daemon=True).start()

    def url(self, caminho: str) -> str:
        return f"http://127.0.0.1:{self._http.server_port}{caminho}"

    def fechar(self) -> None:
        self._http.shutdown()
        self._http.server_close()


@pytest.fixture
def servidor():
    s = _Servidor()
    yield s
    s.fechar()


def test_o_user_agent_e_o_do_projeto_e_a_automacao_usa_o_mesmo():
    assert USER_AGENT == ESPERADO
    assert automacao.USER_AGENT is USER_AGENT and automacao.CABECALHOS == {"User-Agent": ESPERADO}


def test_baixar_envia_o_user_agent_sem_sessao(servidor):
    assert baixar(servidor.url("/a.xlsx"), tentativas_extras=0) == b"conteudo"
    assert servidor.agentes == [ESPERADO]


def test_baixar_envia_o_user_agent_mesmo_com_sessao_de_fora(servidor):
    sessao = requests.Session()  # identificacao padrao da biblioteca: o servidor recusaria
    assert baixar(servidor.url("/a.xlsx"), tentativas_extras=0, sessao=sessao) == b"conteudo"
    assert servidor.agentes == [ESPERADO]


def test_baixar_para_arquivo_envia_o_user_agent(servidor, tmp_path):
    destino = tmp_path / "a.zip"
    _, tamanho = baixar_para_arquivo(servidor.url("/a.zip"), destino, tentativas_extras=0)
    assert tamanho == len(b"conteudo") and destino.read_bytes() == b"conteudo"
    assert servidor.agentes == [ESPERADO]


def test_coletar_serie_de_arquivo_se_identifica(servidor, tmp_path):
    raiz = tmp_path / "projeto"
    (raiz / "metadados").mkdir(parents=True)
    caminhos = Caminhos(raiz=raiz)
    ibid = carregar_fichas(RAIZ_REPOSITORIO / "metadados" / "indicadores")["ibid"]
    serie = ibid.serie("serie_historica")
    local = Serie(**{**serie.__dict__, "parametros": {**serie.parametros, "url": servidor.url("/ibid.xlsx")}})
    ficha = Ficha(**{**ibid.__dict__, "series": (local,)})
    coleta = coletar_serie(ficha, local, caminhos, offline=False, hoje=date(2026, 11, 3))
    assert (raiz / coleta.arquivo).read_bytes() == b"conteudo"
    assert servidor.agentes == [ESPERADO]
