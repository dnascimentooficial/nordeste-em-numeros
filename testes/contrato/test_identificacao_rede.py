"""O IBID baixa do endereço oficial do INPI com a identificação do projeto (marcador `rede`).

O gov.br respondia 403 à identificação padrão da biblioteca HTTP; com o User-Agent do projeto, a planilha vem.
"""

from pathlib import Path

import pytest

from nordeste.coletores.http import baixar
from nordeste.fichas import carregar_fichas

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.rede


def test_ibid_baixa_do_endereco_oficial_com_o_user_agent_do_projeto():
    serie = carregar_fichas(RAIZ_REPOSITORIO / "metadados" / "indicadores")["ibid"].serie("serie_historica")
    assert serie.parametros["url"].startswith("https://www.gov.br/inpi/")
    conteudo = baixar(serie.parametros["url"], tentativas_extras=1)
    assert conteudo[:2] == b"PK" and len(conteudo) > 100_000  # xlsx (zip), não a página de erro
