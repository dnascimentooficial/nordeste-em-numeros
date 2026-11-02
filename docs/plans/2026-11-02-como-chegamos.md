# Página "Como chegamos até aqui" — Plano de implementação

> **Para agentes:** SUB-SKILL OBRIGATÓRIA: use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para executar este plano tarefa a tarefa. Os passos usam checkbox (`- [ ]`).

**Objetivo:** acrescentar ao site a página `/como-chegamos/`, uma linha do tempo histórica do Nordeste em 8 épocas, com modal por época, abertura com a parcela da população nos censos de 1872 a 2022 e imagens históricas de domínio público.

**Arquitetura:** conteúdo em `metadados/site/historia.yaml` e `metadados/site/historia/censos.csv`, carregado e validado por um módulo novo `nordeste.site.historia`; o gerador existente monta a página com um modelo Jinja2 novo; a linha do tempo e o modal são uma camada de JavaScript sobre HTML que já traz todo o conteúdo; estilos com escopo na classe da página.

**Tecnologia:** a do site (Python ≥ 3.12, pandas, pyyaml, Jinja2, Playwright/Chromium nos testes de navegador, axe-core); fonte serifada EB Garamond (OFL) local; Pillow só para converter imagens (já no extra `dev`).

**Spec:** `docs/specs/2026-11-02-como-chegamos-design.md`. Todas as restrições do site (`docs/specs/2026-11-01-site-design.md` e `docs/plans/2026-11-01-site.md`, "Restrições globais") continuam valendo, com a exceção registrada abaixo.

## Restrições globais

- Repositório `dnascimentooficial/nordeste-em-numeros`, clone em `/home/user/nordeste-em-numeros`, branch `claude/como-chegamos`; todo comando com `PYTHONPATH=src` (o pacote instalado no Python global aponta para outro clone). Suíte `PYTHONPATH=src python -m pytest -W error` verde ao fim de cada tarefa; tarefas com navegador também rodam `PYTHONPATH=src PLAYWRIGHT_CHROMIUM=/opt/pw-browsers/chromium python -m pytest -m navegador -W error`.
- Exceção à regra "nenhum número digitado em YAML": nesta página os números históricos ficam em `historia.yaml`, cada um com `tipo` (`oficial`, `historiador` ou `interpretacao`) e `fonte`; a parcela da população nunca é digitada, é calculada de `censos.csv`.
- Tipos de número exibidos: "dado oficial", "estimativa de historiador", "interpretação". `interpretacao` só aparece no campo "O que ficou disso".
- Texto de cada época: alvo de 200 a 250 palavras; a validação recusa fora de 150 a 300.
- Imagens da página: WebP de até 150 000 bytes cada, em `src/nordeste/site/estaticos/historia/`; licença `dominio-publico` ou `ilustracao-do-autor`.
- Cores do site; laranja `#ea2e00` só onde o contraste passa, senão `#c42600`. Fonte serifada só nos títulos desta página e pedida só nela.
- Nenhum partido ou presidente leva crédito ou culpa por resultado; responsabilidade de fora e de dentro da região (spec, seção 6).
- Texto: primeira pessoa, sem travessão (—), sem intensificadores.
- Commits só com `git add` de caminhos explícitos e as linhas de atribuição da sessão; sem push (o controlador empurra).
- Arquivos baixados da internet vão para pastas novas no scratchpad da sessão e são lidos com `python -I`.

## Foco de revisão

1. Endereço com época inexistente (`#9999` ou `#abc`) → a página abre normal, sem modal e sem erro de console. (Teste na Tarefa 5.)
2. Arrasto que termina em cima de um cartão → não abre o modal; só clique sem deslocamento (menos de 6 px) abre. (Teste na Tarefa 5.)
3. Abrir uma época pelo cartão e andar três épocas com "próxima" → um único "voltar" do navegador fecha o modal (anterior/próxima trocam o endereço com `replaceState`; abrir pelo cartão usa `pushState`). (Teste na Tarefa 5.)
4. Primeira e última época → o modal não mostra o botão sem destino ("← época anterior" na primeira, "próxima época →" na última). (Teste na Tarefa 3.)
5. Imagem de época que falha ao carregar → aparece o texto alternativo e o cartão mantém altura e largura. (Teste na Tarefa 5.)

---

### Tarefa 1: Dossiê de pesquisa e lista de imagens (pausa para o usuário)

**Arquivos:** criar `docs/historia/dossie.md` e `docs/historia/imagens-candidatas.md`.

**Interfaces:**
- Produz: o conteúdo de que as Tarefas 6 e 7 dependem. Nenhum código.

- [ ] **Passo 1:** para cada uma das 8 épocas da spec (seção 4), levantar em `dossie.md`: fatos e datas (com os marcos candidatos confirmados ou trocados), de 1 a 3 números com tipo e fonte exata (obra, edição e página, ou tabela do IBGE/Ipea com o código), o que veio de fora e o que foi produzido na região, e as divergências entre autores (inclusive a "crise do açúcar" e o percentual do PIB em 1939; o "30% em 1939" só entra se houver fonte primária).
- [ ] **Passo 2:** abertura: população do Nordeste (estados de hoje, Maranhão a Bahia) e do Brasil em cada censo de 1872 a 2022, com a tabela de origem; conferir os valores de trabalho de 46,7% e 26,9%.
- [ ] **Passo 3:** em `imagens-candidatas.md`, de 1 a 3 candidatas por época: título, autor, data, local, licença (com a prova de domínio público), link da página e do arquivo original no Commons ou no arquivo público, e uma linha sobre o que a imagem mostra. Onde não houver imagem livre, escrever "ilustração do autor".
- [ ] **Passo 4:** fontes usadas listadas no fim de `dossie.md`. Pesquisa só por busca e páginas públicas; nada de contornar bloqueio de rede (se o Commons estiver bloqueado, listar os links para o usuário baixar).
- [ ] **Passo 5:** commit `docs: dossiê histórico e imagens candidatas da página Como chegamos`. **Pausa:** o controlador leva o dossiê ao usuário; as Tarefas 6 e 7 só começam com a aprovação dele.

### Tarefa 2: Conteúdo histórico: leitura e validação

**Arquivos:** criar `src/nordeste/site/historia.py`, `metadados/site/historia.yaml` (provisório), `metadados/site/historia/censos.csv` (provisório); teste `testes/site/test_historia.py`.

**Interfaces:**
- Consome: `Ponto` de `nordeste.site.dados`; `ErroConteudo` de `nordeste.site.conteudo`.
- Produz:
  - `@dataclass(frozen=True) class Marco: ano: int; titulo: str; texto: str`
  - `@dataclass(frozen=True) class NumeroHistorico: valor: str; legenda: str; tipo: str; fonte: str` (`valor` é o texto exibido, ex. "46,7%")
  - `@dataclass(frozen=True) class ImagemHistorica: arquivo: str; titulo: str; autor: str; data: str; licenca: str; alt: str; url: str | None`
  - `@dataclass(frozen=True) class Epoca: id: str; inicio: int; fim: int; nome: str; resumo: str; texto: str; marcos: tuple[Marco, ...]; numeros: tuple[NumeroHistorico, ...]; o_que_ficou: str; fontes: tuple[dict, ...]; imagem: ImagemHistorica | None`
  - `@dataclass(frozen=True) class Historia: provisoria: bool; abertura: dict; epocas: tuple[Epoca, ...]; fecho: dict; censos: tuple[tuple[int, int, int, str], ...]`
  - `carregar_historia(pasta: Path) -> Historia | None` (pasta = `metadados/site`; `None` se `historia.yaml` não existir)
  - `parcela_do_nordeste(historia: Historia) -> list[Ponto]` (valor em %, uma casa; série `"censo"`)
  - `TIPOS = {"oficial": "dado oficial", "historiador": "estimativa de historiador", "interpretacao": "interpretação"}`

Formato de `historia.yaml`: chaves `provisoria` (bool), `abertura` (`titulo`, `subtitulo`, `legenda`, `nota_estados`, `texto`), `epocas` (lista com os campos de `Epoca`; `marcos`, `numeros` e `fontes` como listas; cada fonte com `texto` e `url` opcional; `imagem` com os campos de `ImagemHistorica`) e `fecho` (`titulo`, `texto`, `links`). `censos.csv`: colunas `ano,populacao_nordeste,populacao_brasil,fonte`.

- [ ] **Passo 1: testes que falham** em `testes/site/test_historia.py`, cada um com um `historia.yaml` mínimo em `tmp_path`:
  - `test_carrega_epocas_na_ordem_e_marcos_ordenados` (8 épocas; `Epoca.inicio` crescente; marcos de cada época em ordem de ano);
  - `test_parcela_do_nordeste_calculada_dos_censos` (fixture, não dado real: `censos` 1872 com 4_638_560 e 9_930_478 → `Ponto(1872, 46.7, "censo")`);
  - `test_recusa_numero_sem_tipo_ou_sem_fonte`, `test_recusa_tipo_desconhecido`, `test_recusa_interpretacao_fora_de_o_que_ficou`, `test_recusa_marco_sem_ano`, `test_recusa_epoca_sem_fontes`, `test_recusa_id_repetido`, `test_recusa_texto_fora_de_150_a_300_palavras` (149 e 301 palavras recusam; 150 e 300 passam), `test_recusa_imagem_sem_autor_data_licenca_ou_alt`, `test_recusa_licenca_desconhecida`, `test_recusa_marco_fora_do_periodo_da_epoca`, `test_recusa_censo_com_nordeste_maior_que_brasil`; cada recusa levanta `ErroConteudo` com o caminho do campo na mensagem (ex. `epocas[2].numeros[0].fonte`);
  - `test_imagem_opcional_so_quando_provisoria` (`imagem` ausente passa com `provisoria: true` e é recusada com `false`);
  - `test_sem_historia_yaml_devolve_none`.
- [ ] **Passo 2:** rodar `PYTHONPATH=src python -m pytest testes/site/test_historia.py -W error` → falham (módulo não existe).
- [ ] **Passo 3:** implementar `historia.py` com as interfaces acima, seguindo o padrão de validação de `conteudo.py` (mensagem com o caminho do campo). Contagem de palavras: `len(texto.split())`.
- [ ] **Passo 4:** criar `historia.yaml` provisório (`provisoria: true`): as 8 épocas da spec com nome, período, marcos candidatos e textos marcados "[provisório]" com 150+ palavras; `censos.csv` provisório só com 1872 e 2022 (valores de trabalho do Passo 1 e 203_080_756 / 54_644_582 para 2022, fonte "IBGE, Censo 2022").
- [ ] **Passo 5:** testes verdes; suíte verde; commit `feat(site): conteúdo histórico validado (historia.yaml e censos)`.

### Tarefa 3: Página gerada, abertura e modal no HTML

**Arquivos:** modificar `src/nordeste/site/gerar.py`, `metadados/site/textos.yaml` (`paginas.como-chegamos` e menu); criar `src/nordeste/site/modelos/como_chegamos.html` e `src/nordeste/site/modelos/_epoca.html`; modificar `src/nordeste/site/modelos/sobre.html` (lista de créditos das imagens); teste `testes/site/test_como_chegamos.py`.

**Interfaces:**
- Consome: `carregar_historia`, `parcela_do_nordeste`, `TIPOS` (Tarefa 2); `grafico_linhas(linhas, cfg, governos, largura, altura) -> str`, `Linha`, `ConfigGrafico`, `descricao_acessivel` de `graficos.py`; `Pagina`, `PAGINAS`, `LARGO`, `ESTREITO` de `gerar.py`.
- Produz (para as Tarefas 4 e 5):
  - `Pagina("como-chegamos", "como_chegamos.html", "como-chegamos/index.html", "/como-chegamos/", "Como chegamos aqui")`, inserida no menu entre Início e Estados.
  - Marcação: `<main class="nn-historia">`; abertura em `<section class="nn-hist-abertura">` com `.nn-hist-numero` e o gráfico (`grafico_linhas` com `governos` vazio, `ConfigGrafico(titulo=..., casas=1, sufixo="%", min0=True)`, larguras `LARGO` e `ESTREITO`); linha do tempo em `<ol class="nn-linha-tempo">` com um `<li class="nn-epoca" id="<id>">` por época contendo `<button class="nn-epoca-abrir" data-epoca="<id>">` (imagem `loading="lazy"`, período, nome) e `<article class="nn-epoca-conteudo">` com todo o conteúdo do modal (spec, seção 5, itens 1 a 8); marcos como `<a class="nn-marco" href="#m<ano>" data-epoca="<id>" data-marco="<ano>">`, cada marco no artigo com `id="m<ano>"`; um `<dialog class="nn-modal nn-modal-historia">` vazio no fim; números com `<span class="nn-tipo nn-tipo-<tipo>" title="<fonte>">` e o rótulo de `TIPOS`.
  - `RelatorioSite.paginas` inclui `como-chegamos/index.html` só se `historia` existir e `provisoria` for falsa; com `provisoria: true`, a página não é gerada nem entra no menu, e o relatório ganha `historia_provisoria: bool`.

- [ ] **Passo 1: testes que falham** em `testes/site/test_como_chegamos.py` (gerando com a base mínima `testes/site/base_mini` e um `historia.yaml` de teste com `provisoria: false`):
  - `test_pagina_gerada_no_menu_entre_inicio_e_estados`;
  - `test_abertura_mostra_parcelas_calculadas` (o texto de `.nn-hist-numero` traz "46,7%" e "26,9%" vindos do `censos.csv` de teste);
  - `test_cada_epoca_tem_artigo_completo` (imagem com crédito, resumo, texto, marcos, números com etiqueta de tipo, "O que ficou disso", fontes);
  - `test_primeira_e_ultima_epoca_sem_botao_sem_destino` (Foco 4);
  - `test_marcos_apontam_para_a_epoca_certa`;
  - `test_provisoria_nao_gera_pagina_nem_menu`;
  - `test_creditos_das_imagens_em_sobre`;
  - `test_pagina_tem_og_e_canonical_proprios`.
- [ ] **Passo 2:** rodar → falham.
- [ ] **Passo 3:** implementar no `gerar.py` (contexto da página a partir de `Historia`; `PAGINAS` passa a ser montado com a página nova quando `historia` não é provisória) e os modelos. Imagem OpenGraph `og/como-chegamos.png` pelo mesmo caminho das outras páginas, com o título da página.
- [ ] **Passo 4:** testes verdes; suíte verde (os testes existentes de páginas, recursos externos e OpenGraph passam a cobrir a página nova); commit `feat(site): página Como chegamos até aqui gerada a partir do conteúdo histórico`.

### Tarefa 4: Estética de arquivo histórico

**Arquivos:** modificar `src/nordeste/site/estaticos/estilo.css`; criar `src/nordeste/site/estaticos/fontes/eb-garamond/EBGaramond.woff2` e `OFL.txt`; modificar `src/nordeste/site/modelos/como_chegamos.html` (só o `<link rel="preload">` da fonte); teste em `testes/site/test_estaticos.py` e `testes/navegador/test_site_no_navegador.py`.

**Interfaces:**
- Consome: a marcação da Tarefa 3.
- Produz: classes estilizadas sob `.nn-historia`; variável `--nn-papel-antigo` (o bege da página) e `--nn-sepia` no `:root`.

- [ ] **Passo 1: testes que falham:**
  - `test_fonte_serifada_so_na_pagina_de_historia` (a regra `@font-face` da EB Garamond existe, e o `font-family` dela só aparece em seletores sob `.nn-historia`);
  - `test_ebgaramond_local_com_licenca` (woff2 e OFL.txt presentes; nenhum `url(` externo);
  - navegador: `test_historia_contraste_em_pixels` (390 e 1280 px, temas claro e escuro: títulos, datas dos marcos, etiquetas de tipo e texto ≥ 4,5:1 no pior pixel, como o teste da abertura);
  - navegador: `test_historia_so_pede_a_serifada_nesta_pagina` (as outras rotas não pedem `EBGaramond.woff2`).
- [ ] **Passo 2:** rodar → falham.
- [ ] **Passo 3:** baixar a EB Garamond do Google Fonts (só o subconjunto latino, uma variação de peso), salvar com `OFL.txt`; escrever o CSS: papel envelhecido por gradiente e ruído leve em CSS (sem imagem), títulos serifados, imagens dos cartões com `filter: sepia(...)` que sai no modal, linha e marcos em laranja, datas em estilo de carimbo; no tema escuro, papel escuro quente. Sem `style=`.
- [ ] **Passo 4:** testes verdes; suítes verdes; commit `feat(site): estética de arquivo histórico na página Como chegamos`.

### Tarefa 5: Linha do tempo arrastável e modal por época

**Arquivos:** modificar `src/nordeste/site/estaticos/site.js` e `src/nordeste/site/estaticos/estilo.css`; testes em `testes/navegador/test_site_no_navegador.py`.

**Interfaces:**
- Consome: a marcação da Tarefa 3 e o código do modal "Ampliar" do `site.js` (reaproveitar abrir/fechar, foco e Esc).
- Produz: comportamento; nenhuma função pública nova.

Regras: com JavaScript, o `site.js` marca `<html class="nn-js">` e os `<article class="nn-epoca-conteudo">` ficam escondidos na lista (o conteúdo vai para o modal); sem JavaScript, ficam visíveis abaixo de cada cartão. Computador (> 900 px) com `.nn-linha-tempo` em faixa horizontal com `overflow-x: auto` e `scroll-snap`; arrasto por `pointerdown/move/up` que rola a faixa; clique só abre se o deslocamento for menor que 6 px; botões ‹ › rolam um cartão; setas do teclado movem o foco entre cartões. Até 900 px, lista vertical sem arrasto. Abrir pelo cartão: copia o `<article>` da época para o `<dialog>`, `showModal()`, `history.pushState` com `#<id>`; marco: abre a época e rola até `#m<ano>`; anterior/próxima: troca o conteúdo e usa `history.replaceState`; `popstate` e fechar (X, Esc, clique fora) fecham e devolvem o foco ao cartão; carregar a página com `#<id>` válido abre o modal; id inválido não faz nada. Fade e sépia → cor só com `prefers-reduced-motion: no-preference`.

- [ ] **Passo 1: testes de navegador que falham:**
  - `test_historia_arrasto_rola_e_nao_abre` (arrastar 200 px sobre um cartão rola a faixa e não abre o modal; Foco 2);
  - `test_historia_clique_abre_modal_e_esc_devolve_foco`;
  - `test_historia_teclado_setas_e_enter`;
  - `test_historia_endereco_abre_epoca` (abrir `/como-chegamos/#1763` mostra o modal da época certa) e `test_historia_endereco_invalido_nao_quebra` (`#9999`, `#abc`; Foco 1);
  - `test_historia_proxima_tres_vezes_e_um_voltar_fecha` (Foco 3);
  - `test_historia_marco_abre_epoca_no_marco`;
  - `test_historia_sem_js_mostra_todas_as_epocas`;
  - `test_historia_390_vertical_sem_estouro`;
  - `test_historia_imagem_quebrada_mostra_alt` (Foco 5: troca o `src` de uma imagem por um inexistente antes de carregar; o alt aparece, o cartão mantém tamanho; o 404 provocado não conta como erro da página);
  - `test_historia_peso_abaixo_de_1mb` (soma dos bytes baixados ao abrir a página, sem abrir modais);
  - `test_axe_historia` (claro e escuro, `reduced_motion="reduce"`, página parada e com modal aberto).
- [ ] **Passo 2:** rodar → falham.
- [ ] **Passo 3:** implementar o comportamento no `site.js` (sem bibliotecas, sem estilo inline) e o CSS da faixa horizontal e do modal da história.
- [ ] **Passo 4:** testes verdes; suítes verdes; commit `feat(site): linha do tempo arrastável e modal por época`.

### Tarefa 6: Imagens das épocas e créditos (depois da aprovação do dossiê)

**Arquivos:** criar `src/nordeste/site/estaticos/historia/<id>.webp` (uma por época); modificar `metadados/site/historia.yaml` (bloco `imagem` de cada época), `LICENSE.md` (exceções) e `src/nordeste/site/gerar.py` (copiar `estaticos/historia/` só com a página gerada); teste em `testes/site/test_historia.py`.

**Interfaces:**
- Consome: `imagens-candidatas.md` aprovado (Tarefa 1); `ImagemHistorica` (Tarefa 2).
- Produz: os arquivos e créditos finais.

- [ ] **Passo 1: testes que falham:** `test_imagens_existem_e_pesam_ate_150kb` (para cada época com `imagem`, o arquivo existe em `estaticos/historia/` e tem até 150 000 bytes); `test_licenca_lista_cada_imagem` (cada `imagem.arquivo` aparece em `LICENSE.md`).
- [ ] **Passo 2:** rodar → falham.
- [ ] **Passo 3:** obter os originais (download direto se `upload.wikimedia.org` estiver liberado; senão, os arquivos que o usuário enviar), em pasta nova no scratchpad, lidos com `python -I`; converter para WebP (largura do modal, até 150 000 bytes), preencher crédito, licença e `alt` no `historia.yaml`; acrescentar as exceções ao `LICENSE.md`.
- [ ] **Passo 4:** testes verdes; suítes verdes; commit `feat(site): imagens históricas das épocas com créditos`.

### Tarefa 7: Texto final e conferência cruzada (pausa para o usuário)

**Arquivos:** modificar `metadados/site/historia.yaml` e `metadados/site/historia/censos.csv`.

**Interfaces:**
- Consome: `dossie.md` aprovado; validação da Tarefa 2.
- Produz: o conteúdo final, com `provisoria: false`.

- [ ] **Passo 1:** escrever, a partir do dossiê aprovado, a abertura, as 8 épocas e o fecho na voz do autor (spec, seção 6; checklist do revisor do autor: sem travessão, sem intensificador, sem cena inventada); preencher `censos.csv` com todos os censos do dossiê.
- [ ] **Passo 2:** conferência cruzada por um segundo revisor que recebe só o `historia.yaml` e o dossiê: cada número contra a fonte citada; números que não batem saem ou são corrigidos.
- [ ] **Passo 3:** **pausa:** o controlador leva o texto ao usuário; ajustes até a aprovação.
- [ ] **Passo 4:** `provisoria: false`; suítes verdes; commit `feat(site): texto da página Como chegamos até aqui`.

### Tarefa 8: Publicação

- [ ] **Passo 1 (controlador):** revisão final da branch; levar `claude/como-chegamos` para a `main` (merge sem reescrever história, a `main` recebe commits do robô); CI verde.
- [ ] **Passo 2 (usuário):** disparar `atualizar.yml` (ou esperar a segunda-feira); conferir `https://nordeste.dnascimento.com.br/como-chegamos/` no computador e no celular.
- [ ] **Passo 3:** README: seção "Como chegamos até aqui" (onde editar o conteúdo, como trocar imagens, o que a validação exige).
