# Página inicial mais intuitiva: plano de implementação

> **Para quem executa:** use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans, tarefa a tarefa. Os passos usam caixas (`- [ ]`) para acompanhar.

**Objetivo:** reorganizar a página inicial para que a resposta das seis perguntas apareça numa tela só, cada pergunta comece pela conclusão e a leitura deixe de ser uma pilha de cartões. As perguntas viram capítulos de uma reportagem, com menu lateral fixo. Nenhum dado sai da página.

**Arquitetura:** só a página inicial muda. Ela continua gerada pelo gerador de sempre: `modelos/inicio.html`, `gerar.py`, `metadados/site/textos.yaml` e `perguntas.yaml`. A ordem dos elementos de cada pergunta muda no modelo. O placar é montado dos mesmos dados das perguntas (rótulo, frase feita e fecho), sem texto novo digitado. O detalhe secundário, ou seja, os outros gráficos, as fontes e as ressalvas, vai para `<details>`, que funciona sem JavaScript.

**Tecnologia:** Python 3.12, Jinja2, CSS próprio (`estaticos/estilo.css`), testes com pytest e Playwright.

**Referência visual:** prévia aprovada pelo autor em https://claude.ai/artifact/SBzoNhfQrWnFfg7TzvNsXp (versão 12, "Prévia: Início editorial com menu lateral"). Ela foi feita sobre o HTML gerado pelo script `scratchpad/previa-inicio/ferr/transformar.py`, que serve de referência de estrutura, não de código.

## Restrições globais

- Nenhum dado sai da página. Tudo o que hoje aparece aberto continua na página: aberto ou atrás de um `<details>`.
- Sem JavaScript, tudo funciona e tudo é legível. Os `<details>` abrem sem JS.
- CSP `default-src 'self'`: nada de `style=` nem de script inline.
- Temas claro e escuro. O axe não pode apontar violação grave. O contraste é medido em pixels nos testes que já existem.
- Em 390 px, nada estoura a largura. O teto de primeira carga da inicial (`test_peso_da_inicial`) continua valendo.
- Texto em português, na voz do autor, seguindo o checklist de revisão do site. Os textos novos (títulos de seção, rótulos de botão) ficam em `textos.yaml`, com validação.
- Se um fecho for suprimido pela condição dele, a regra que já existe vale também para o placar: o veredito daquela pergunta não aparece, e a linha mostra "Ver a resposta" em vez de inventar uma conclusão.
- A ordem das perguntas e os ids `q-<id>` não mudam. Isso preserva os links que já circulam.

## Foco de revisão

1. **Fecho suprimido:** o placar não pode mostrar um veredito vazio nem desatualizado. Teste com uma pergunta sem fecho.
2. **Pergunta que saiu inteira:** ela some do placar também, sem deixar link quebrado para `#q-…`.
3. **"Ampliar" dentro de `<details>` fechado:** o modal do gráfico tem que funcionar depois que o `<details>` abre. O id do `<template>` não pode mudar.
4. **Âncoras do placar com o cabeçalho fixo:** ao pular para `#q-escola`, o título do bloco não pode ficar escondido atrás da legenda fixa. Use `scroll-margin-top`.
5. **Card suprimido:** se a condição de um card ficar falsa, o botão "Baixar o card" daquela pergunta some, em vez de levar a um 404.
6. **Menu lateral sem JavaScript:** sem JS, o menu aparece sempre (não some nem esconde conteúdo) e os links funcionam como âncoras.
7. **Telas de 900 a 1100 px:** a coluna do menu (260 px) mais a folha não podem espremer o gráfico. Abaixo de 1100 px, use a versão de faixa de atalhos.

---

### Tarefa 1: Faixa de números em pares

**Arquivos:** `metadados/site/textos.yaml` (faixa), `src/nordeste/site/gerar.py` (validação da faixa), `modelos/inicio.html`, `estaticos/estilo.css`, `testes/site/test_gerar.py`.

- [ ] A faixa passa a ter **dois números**: a riqueza por pessoa e a pobreza.
  - Cada número ganha um campo `comparacao`, um modelo com destaques, por exemplo `era {pib_pc_razao.primeiro:1%} em {pib_pc_razao.ano_primeiro}` e `era {pob_ne.primeiro:1%} em {pob_ne.ano_primeiro} · no Brasil, hoje, {pob_br.ultimo:1%}`.
  - O número do Brasil sai da lista e vira comparação.
- [ ] O parágrafo `faixa.texto` deixa de ser mostrado, porque os números dele estão agora nas comparações. A `condicao` da faixa continua valendo para mostrar ou não os números.
- [ ] Testes:
  - a faixa tem 2 `li.nn-numero`, cada um com `.nn-numero-comparacao`;
  - todos os números que o parágrafo antigo trazia aparecem em algum lugar da faixa;
  - com a condição falsa, a faixa mostra só a nota.

### Tarefa 2: Placar das seis perguntas

**Arquivos:** `modelos/inicio.html`, `gerar.py` (contexto `placar`), `textos.yaml` (chave nova `placar`: `eyebrow`, `titulo`, `sem_veredito`), `estilo.css`, testes em `test_gerar.py` e no navegador.

- [ ] Depois da faixa entra `section.nn-placar`, com `h2` "O que os números respondem" e uma lista ordenada.
  - Cada item é um link para `#q-<id>` com o tema (`rotulo`), a frase feita (sem o "Será?") e o veredito: o `fecho` com a primeira letra maiúscula.
  - Sem fecho, o item usa `placar.sem_veredito` ("Ver a resposta").
- [ ] O placar é montado da mesma lista `perguntas` que o resto da página usa. Não existe texto paralelo para ficar desatualizado.
- [ ] CSS: duas a três colunas no computador e uma no celular. A linha inteira é clicável e tem foco visível.
- [ ] Testes:
  - um item por pergunta publicada, na ordem;
  - cada `href` aponta para um id que existe;
  - o veredito é igual ao fecho do bloco;
  - uma pergunta sem fecho mostra "Ver a resposta";
  - uma pergunta que saiu inteira some do placar;
  - axe e contraste nos dois temas;
  - 390 px sem estouro.

### Tarefa 3: Pirâmide invertida em cada pergunta

**Arquivos:** `modelos/inicio.html` (macro da pergunta), `textos.yaml` (`perguntas_rotulos`: `mais_graficos`, `fonte_metodo`), `estilo.css`, testes.

- [ ] Nova ordem dentro do `article.nn-card`:
  1. eyebrow;
  2. `h2`;
  3. **fecho** (veredito);
  4. `div.nn-pergunta-corpo`, com o **primeiro gráfico** e, ao lado no computador (abaixo no celular), a explicação e o lide;
  5. `details.nn-mais-graficos` com os outros gráficos, quando houver, e o resumo "Ver mais N gráficos";
  6. `details` "Ver os números", como já existe;
  7. `details.nn-fonte-metodo` com o alerta, quando houver, e as fontes e atualizações.
- [ ] Os `<template id="nn-ampliado-…">` continuam fora dos `<details>`, como hoje, no fim da página.
- [ ] `scroll-margin-top` nos `article` para as âncoras do placar.
- [ ] Testes:
  - a ordem dos filhos do artigo é a nova;
  - o primeiro gráfico fica fora de `<details>` e os outros, dentro;
  - a fonte e o alerta ficam dentro de `details.nn-fonte-metodo`;
  - nenhum texto que existia na página sumiu (compare o conjunto de textos visíveis mais o conteúdo dos `<details>` antes e depois);
  - no navegador, "Ampliar" de um gráfico dentro de um `<details>` aberto abre o modal certo.

### Tarefa 4: Saídas de cada pergunta

**Arquivos:** `metadados/site/perguntas.yaml` (campo `card` por pergunta), `gerar.py` (validação: o card existe), `modelos/inicio.html`, `textos.yaml` (`saidas`: `card`, `estados`, `explorar`), `estilo.css`, testes.

- [ ] Ligação de cada pergunta ao card dela:

  | Pergunta | Card |
  |---|---|
  | `renda-per-capita` | `pibpc` |
  | `economia` | `vol` |
  | `escola` | `ideb` |
  | `trabalho` | `desoc` |
  | `idhm` | `idhm` |
  | `pobreza` | `pobreza` |

  Um id que não existe em `cards.yaml` faz a validação falhar com mensagem clara.
- [ ] No pé de cada pergunta entra `nav.nn-saidas`, com três links: "Baixar o card desta resposta" (`/cards/<id>/`, só se o card foi publicado), "Ver os estados" (`/estados/`) e "Explorar os dados" (`/explorar/`).
- [ ] Testes:
  - os links existem e apontam para páginas geradas;
  - com o card suprimido, o primeiro link some;
  - um card inválido em `perguntas.yaml` faz a validação falhar.

### Tarefa 5: Legenda fixa com as siglas dos governos

**Arquivos:** `modelos/inicio.html`, `textos.yaml` (`legenda.siglas`), `estilo.css`, testes.

- [ ] A `.nn-legenda` fica no topo de `#resumo` com `position: sticky; top: 0` e fundo opaco do tema. Ela ganha a linha "F = FHC · L = Lula · D = Dilma · T = Temer · B = Bolsonaro", que sai de `metadados/governos.csv`, não digitada à mão.
- [ ] Testes:
  - a legenda continua visível depois de rolar até a terceira pergunta;
  - as siglas batem com os governos do CSV;
  - o contraste continua bom.

### Tarefa 6: Chamada "Como chegamos" depois das perguntas

**Arquivos:** `modelos/inicio.html`, testes.

- [ ] Move `section.nn-chamada-historia` para depois de `#resumo`. Nenhuma outra mudança nela.
- [ ] Ajusta o teste que hoje exige a chamada logo depois da faixa.

### Tarefa 7: Layout editorial: capítulos, menu lateral e folha sobreposta

**Arquivos:** `modelos/inicio.html`, `estaticos/estilo.css`, `estaticos/site.js` (função `ligarIndice`), testes em `test_gerar.py` e no navegador.

- [ ] **Capítulos em vez de cartões.**
  - Os `article` das perguntas perdem o visual de cartão: sem borda, sem raio e sem fundo próprio, com `padding` vertical generoso.
  - Os capítulos ficam separados por um fio fino (`border-top: 1px solid var(--nn-linha)`), e o primeiro não tem fio.
  - O eyebrow vira `NN / TEMA`, com o número no laranja.
  - Nos capítulos pares, gráfico e texto trocam de lado no computador.
  - O "No frigir dos ovos" deixa a caixa rosa e vira uma citação com fio laranja à esquerda (4 px).
- [ ] **Folha sobreposta.**
  - `#resumo` vira uma grade de duas colunas: menu de 260 px e folha.
  - A folha (`div.nn-folha`) tem o fundo do tema (branco no claro, quase preto no escuro), raio `var(--nn-raio-g)` e sombra suave.
  - `margin-left: -28px` faz a folha sobrepor levemente a coluna do menu.
  - A legenda fixa (tarefa 5) fica no topo da folha.
- [ ] **Menu lateral fixo** (`aside.nn-indice`):
  - `position: sticky; top: 16px`, com a lista numerada das perguntas: número, tema e a frase feita em letra pequena.
  - Com JS, ele aparece com um esmaecido depois que o placar sai da tela (classe `nn-indice-visivel`), e o item da pergunta em leitura ganha `aria-current="true"` e destaque: fundo do tema, fio laranja e sombra.
  - Sem JS, fica sempre visível.
  - A posição de leitura é calculada no `scroll` com `passive: true`, sem nenhum `setInterval`.
- [ ] **Celular e telas até 1100 px:** o menu vira uma faixa horizontal fixa no topo, com atalhos em pílula. A pílula ativa rola para dentro da vista. A folha não sobrepõe nada (`margin-left: 0`).
- [ ] **Placar** como lista numerada com fios entre as linhas: número, tema (coluna de 200 px) e veredito. Sem cartões.
- [ ] Testes:
  - o artigo sem cartão (borda 0 e fundo transparente, medidos no navegador);
  - os capítulos pares invertidos;
  - o menu com um link por pergunta publicada, na ordem;
  - sem JS, o menu visível;
  - com JS, o menu escondido enquanto o placar está na tela e visível depois, com `aria-current` mudando ao rolar até a terceira pergunta;
  - a 1280 px, a folha sobrepõe o menu (borda esquerda da folha menor que a borda direita da coluna do menu);
  - a 390 e a 1000 px, a faixa de atalhos aparece e nada estoura a largura;
  - axe e contraste nos dois temas, com o menu visível.

### Tarefa 8: Fechamento

- [ ] Rode as duas baterias: `PYTHONPATH=src python3 -m pytest -W error` e `-m navegador -W error`.
- [ ] Tire prints a 1280 e 390 px e compare com a prévia aprovada.
- [ ] Revisão final do branch.
- [ ] Junção com o `main` e publicação do site sem coleta, como nas últimas vezes.

---

## Ordem e estimativa

As tarefas 1, 2, 3 e 7 dão o ganho principal e devem ir juntas. As tarefas 4, 5 e 6 são independentes entre si e pequenas.

| Tarefa | Tamanho | Depende de |
|---|---|---|
| 1. Faixa em pares | pequeno | — |
| 2. Placar | médio | — |
| 3. Pirâmide invertida | médio | — |
| 4. Saídas | pequeno | 3 (pé do bloco) |
| 5. Legenda fixa | pequeno | — |
| 6. Chamada no fim | mínimo | — |
| 7. Layout editorial e menu lateral | médio | 2, 3 e 5 |
| 8. Fechamento | — | todas |

## Fora do escopo

- Mudar textos, fechos ou números das perguntas.
- Juntar os três gráficos do IDEB num só. Isso muda a forma de ler o dado e merece decisão própria.
- Mudanças nas outras páginas.
- Tirar a geração das antigas imagens `og/<pagina>.png`, que nenhuma página usa mais. É uma limpeza separada.
