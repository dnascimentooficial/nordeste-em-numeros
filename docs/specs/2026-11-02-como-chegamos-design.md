# Página "Como chegamos até aqui" — Design

**Subprojeto 4** · Data: 2026-11-02 · Status: aprovado pelo usuário em 2026-11-02

## 1. Objetivo e público

Uma página do site Nordeste em Números (`https://nordeste.dnascimento.com.br/como-chegamos/`) que conta, em linha do tempo, como o Nordeste passou de centro econômico da colônia à região que largou atrás, da era do açúcar até hoje. Ela dá o contexto histórico que o resto do site (dados de 2000 para cá) não dá: sem a história, a distância parece culpa do nordestino; com ela, aparece como algo construído ao longo de quatro séculos, por decisões de fora e de dentro da região.

Público: o mesmo do site, geral, muitas vezes no celular e a partir de um link recebido.

Critério de sucesso: quem nunca leu Celso Furtado sai da página entendendo por que o Nordeste largou atrás, e consegue conferir cada número na fonte citada.

## 2. Decisões do usuário

| Tema | Decisão |
|---|---|
| Nome e endereço | "Como chegamos até aqui", em `/como-chegamos/`; no menu, "Como chegamos aqui", entre Início e Estados |
| Formato | Linha do tempo: horizontal e arrastável no computador, vertical no celular; clicar numa época abre um modal |
| Épocas | 8 épocas, com marcos destacados dentro delas (seção 4) |
| Abertura | População: parcela dos brasileiros que vivia no Nordeste em 1872 e em 2022 (censos do IBGE), com gráfico de todos os censos |
| Estética | Arquivo histórico com a mesma marca: papel envelhecido, títulos serifados, imagens em sépia que ganham cor no modal, linha do tempo no laranja do site; só nesta página |
| Texto por modal | Médio, em camadas (seção 5) |
| Voz | A de Júlio: primeira pessoa, simples, sem cena; mesmo checklist de revisão do resto do site |
| Imagens | Reais, de domínio público ou CC BY com crédito (Wikimedia Commons, Arquivo Nacional, Agência Brasil); onde não houver imagem livre, ilustração do autor identificada como ilustração (decisão de 2026-11-02, depois do dossiê) |
| Implementação | Gerada pelo mesmo gerador do site, a partir de um arquivo de conteúdo validado (seção 7) |

## 3. Abertura da página

- Título serifado "Como chegamos até aqui".
- Número grande: parcela da população brasileira que vivia no Nordeste no Censo de 1872 e no Censo de 2022 (valores de trabalho: 46,7% e 26,9%; os dois são conferidos na tabela original do IBGE no dossiê, e a página usa o valor conferido). Legenda com a fonte.
- Gráfico de linha com todos os censos de 1872 a 2022, no traço laranja, com a dica de valor dos outros gráficos do site. Os valores vêm de uma tabela própria (`metadados/site/historia/censos.csv`) com, por linha, ano, população do Nordeste, população do Brasil e a tabela do IBGE de origem. A parcela é calculada pelo gerador, não digitada.
- Duas linhas de texto do autor explicando por que esse número resume a história.

A divisão regional de hoje não existia em 1872. A tabela usa os estados que hoje formam o Nordeste (Maranhão a Bahia), e a página diz isso numa nota.

## 4. Linha do tempo e épocas

Épocas (os limites são marcos aproximados; o dossiê pode ajustar datas):

1. Colônia do açúcar (1530–1654)
2. Concorrência, ouro e a capital que muda (1654–1808)
3. Império e revoltas (1808–1889)
4. Primeira República: café com leite, seca e Canudos (1889–1930)
5. Vargas e a grande migração (1930–1950)
6. BNB, GTDN e Sudene (1950–1964)
7. Ditadura: obra grande e Sudene esvaziada (1964–1985)
8. Redemocratização até hoje (1985–2026)

Marcos candidatos (o dossiê confirma): 1654 (expulsão holandesa e o açúcar que vai para as Antilhas), 1763 (capital vai de Salvador para o Rio), 1817 e 1824 (Revolução Pernambucana e Confederação do Equador), 1877–1879 (Grande Seca), 1897 (Canudos), 1909 (órgão federal contra as secas, hoje DNOCS), 1952 (BNB), 1959 (GTDN e Sudene), 1988 (Constituição e fundos regionais).

Computador: faixa horizontal com um cartão por época (imagem em sépia, período, nome curto) e os marcos como pontos laranja maiores na linha, com a data. Navegação por arrasto, rolagem lateral, setas ‹ › nas pontas e setas do teclado.

Celular (até 900 px): a mesma sequência na vertical.

Sem JavaScript: lista vertical das épocas com o conteúdo completo de cada uma, legível do início ao fim. O arrasto e o modal são camadas sobre esse conteúdo.

## 5. Modal de cada época

Abre ao clicar no cartão ou num marco (que abre a época já rolada até o marco). O conteúdo está no HTML gerado (como o modal "Ampliar"), não é buscado depois.

Conteúdo, nesta ordem:

1. Imagem da época (em cor) com crédito: autor, título, data, "domínio público" ou "ilustração".
2. Frase-resumo.
3. Texto de 200 a 250 palavras.
4. Marcos com data (2 a 4).
5. Números (1 a 3), cada um com a etiqueta do tipo (seção 6) e a fonte.
6. "O que ficou disso": uma frase do autor ligando a época ao Nordeste de hoje.
7. Fontes do modal, com link quando houver versão on-line.
8. Botões "← época anterior" e "próxima época →".

Comportamento: o padrão do modal "Ampliar" (fecha no X, no Esc e clicando fora; foco preso no modal e devolvido ao cartão de origem; tela cheia no celular). Cada época tem um endereço (`#1530`, `#1763`, ...; o identificador é o ano inicial ou o do marco) que abre a página com o modal certo, e o voltar do navegador fecha o modal. Fade de entrada e a imagem de sépia para cor só com `prefers-reduced-motion: no-preference`.

Fim da página: "E de 2000 para cá?", com links para o Início e para os cards.

## 6. Conteúdo e fontes

Três tipos de informação, cada número marcado com um deles:

- **Dado oficial:** censo, conta nacional, estatística pública (IBGE, Ipea).
- **Estimativa de historiador:** sempre com autor e obra.
- **Interpretação:** leitura do autor, assumida como dele; só no "O que ficou disso".

Na página, cada número leva uma etiqueta pequena com o tipo e a fonte (ao passar o mouse ou tocar).

Linhas editoriais:

- Responsabilidade dos dois lados: o que veio de fora (metrópole, capital no Rio, governo federal) e o que foi produzido na região (latifúndio, coronelismo, "indústria da seca", elites locais).
- Nenhum partido ou presidente leva crédito ou culpa por resultado, a mesma regra do resto do site; governos aparecem como contexto e pelas medidas que tomaram.
- O eixo econômico migrou primeiro para o Sudeste (ouro de Minas, capital no Rio em 1763); o açúcar já perdia espaço para as Antilhas desde 1654. Divergências da historiografia (por exemplo, a tese de "crise do açúcar") aparecem como divergência.
- Número que circula sem lastro não entra (exemplo já encontrado: "30% do PIB em 1939").

Produção, com aprovação do usuário em cada passo:

1. Dossiê: fatos, datas e números por época, cada um com a fonte exata (obra e página, ou tabela), e as divergências entre autores; mais a lista de imagens candidatas (seção 8).
2. Texto na voz do autor a partir do dossiê aprovado.
3. Conferência cruzada: um segundo revisor confere cada número contra a fonte citada, sem ver o texto antes; número que não bate não entra.

Fontes de base esperadas (o dossiê confirma ou troca): Celso Furtado, *Formação Econômica do Brasil* (1959) e o relatório do GTDN; Roberto Simonsen, *História Econômica do Brasil*; Francisco de Oliveira, *Elegia para uma re(li)gião*; censos do IBGE de 1872 a 2022 e as *Estatísticas Históricas do Brasil* (IBGE); Ipea (contas regionais desde 1939); documentos públicos da Sudene e do BNB.

## 7. Arquitetura

- Conteúdo em `metadados/site/historia.yaml`: textos da abertura, as 8 épocas (id, período, nome, frase-resumo, texto, marcos, números com tipo e fonte, "O que ficou disso", fontes, imagem com crédito e texto alternativo) e o fecho. Censos em `metadados/site/historia/censos.csv`.
- Validação no carregamento (mesmo padrão de `textos.yaml` e `cards.yaml`): época sem fonte, número sem tipo ou sem fonte, marco sem data, imagem sem autor, data, licença ou texto alternativo, texto fora da faixa de 150 a 300 palavras (alvo de 200 a 250), ou id repetido impedem a geração, com mensagem que diz o que falta.
- Gerador: nova página `como-chegamos/index.html` a partir do modelo `como_chegamos.html`; o gráfico da abertura usa as funções de gráfico existentes. A página entra no menu, no mapa de páginas, no OpenGraph (imagem própria) e nos testes de página existentes.
- Estáticos: estilos próprios da página no `estilo.css` (escopo pela classe da página), fonte serifada local (`woff2` com licença OFL ao lado) carregada só nesta página, imagens em `estaticos/historia/` (WebP até 150 KB cada). Comportamento da linha do tempo e do modal no `site.js`, reaproveitando o código do modal "Ampliar".
- Imagens grandes carregam só quando o modal abre (`loading="lazy"` e imagem dentro do `<template>` do modal).
- Nada muda na base de dados nem na automação semanal; a página é regenerada a cada publicação como as outras.

## 8. Imagens

- Uma imagem real por época, de domínio público; candidatas no dossiê com link, autor, data, local e licença. Exemplos: Frans Post (engenhos em Pernambuco, anos 1640), Debret e Rugendas (anos 1820–1830), fotos da seca de 1877, Flávio de Barros (Canudos, 1897), arquivos públicos (Agência Brasil, Arquivo Nacional) para o século XX.
- Onde não houver imagem livre: ilustração do autor, com o crédito "ilustração".
- Obtenção: download direto se `commons.wikimedia.org` e `upload.wikimedia.org` forem liberados na rede do ambiente; senão, o usuário baixa a partir da lista. Arquivos baixados são tratados como não confiáveis (pasta própria, leitura com `python -I`).
- Tratamento: WebP até 150 KB, nos tamanhos do cartão e do modal; sépia por CSS (o arquivo guarda a cor); texto alternativo descrevendo a cena.
- Créditos no modal e numa lista em Sobre os dados. A licença de cada imagem é registrada no `historia.yaml` e no `LICENSE.md` (exceções).

## 9. Testes

- Conteúdo: cada época completa (seção 5); percentuais da abertura calculados a partir de `censos.csv`; validação recusa cada falta listada na seção 7.
- Acessibilidade: axe sem violação grave nos temas claro e escuro, com a página parada e com o modal aberto; contraste do laranja sobre o papel envelhecido em texto pequeno (se não passar, `#c42600`).
- Teclado: setas percorrem a linha do tempo, Enter abre a época, Esc fecha e o foco volta ao cartão.
- Endereço: abrir `#<id>` abre o modal certo; voltar fecha.
- Sem JavaScript: todas as épocas visíveis, com conteúdo completo.
- Celular a 390 px: nada estoura a largura; a linha é vertical.
- CSP: nada externo, nada inline; a fonte serifada é local e só é pedida nesta página.
- Peso: a página sem abrir modais fica abaixo de 1 MB.
- Os testes existentes (páginas sem erro de console, recursos externos, OpenGraph, mapa de páginas) passam a incluir a página nova.

## 10. Ordem de trabalho

1. Dossiê e lista de imagens (aprovação do usuário).
2. Texto (aprovação do usuário).
3. Página, linha do tempo e modal, com texto provisório que não vai ao ar (em paralelo com o passo 2).
4. Imagens e créditos.
5. Revisão final e publicação pelo robô semanal (ou disparo manual).

## 11. Fora do escopo

- Mapas animados ou interativos por época.
- Séries históricas além da população (a série do PIB desde 1939 aparece como número no modal da época 5 ou 6, não como gráfico próprio, até o dossiê mostrar que a série encadeada é confiável).
- Tradução para outros idiomas.
