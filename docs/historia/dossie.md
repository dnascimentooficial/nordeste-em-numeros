# Dossiê histórico: "Como chegamos até aqui"

Tarefa 1 do subprojeto 4 (spec `docs/specs/2026-11-02-como-chegamos-design.md`, seções 3, 4, 6 e 8). Insumo para o texto (Tarefa 6) e para `historia.yaml` / `censos.csv` (Tarefa 7). Nada aqui é texto final da página.

Data da pesquisa: 2026-11-02.

## Como ler este dossiê

**Limite de acesso desta pesquisa (importante).** A rede desta sessão bloqueou a abertura direta de todas as páginas que tentei: `biblioteca.ibge.gov.br`, `censo2010.ibge.gov.br`, `anuario.ibge.gov.br`, `nphed.cedeplar.ufmg.br`, `www.ceicdata.com` (WebFetch: host fora dos domínios permitidos; curl: 403 do proxy ou sem conexão, também para `repositorio.ipea.gov.br`, `bnb.gov.br`, `sidra.ibge.gov.br`, `commons.wikimedia.org` e `upload.wikimedia.org`). Por isso **nenhum número abaixo foi lido por mim na tabela ou na página original**, com uma exceção: a seção "Abertura: população nos censos", atualizada depois com a API do SIDRA (`apisidra.ibge.gov.br`), que está acessível. O que eu tinha era a busca na web, que devolve trechos das páginas indexadas. Cada número traz o nível de confirmação:

- **[A] trecho da fonte visto na busca:** a busca mostrou o trecho da própria fonte citada (documento oficial, artigo acadêmico ou obra) com o número. Falta abrir a página e anotar tabela e página exatas.
- **[B] fonte secundária:** o número apareceu em fonte secundária (imprensa, compilação, verbete) que cita a origem, ou em duas fontes secundárias que coincidem.
- **[C] não confirmado:** não achei o número em fonte nenhuma ou as fontes divergem sem solução. Não usar sem conferir.

"Página: não confirmada" quer dizer que achei a obra e o número, mas não a página. Antes de o número ir para `historia.yaml`, alguém com acesso às fontes precisa preencher página ou tabela (a conferência cruzada da spec, seção 6, passo 3).

**Tipos (spec, seção 6):** `oficial` (censo, conta nacional, lei, documento de governo), `historiador` (sempre com autor e obra), `interpretacao` (só no "O que ficou disso", e aqui sempre marcada como sugestão).

**Datas de fatos consagrados** (fundação de Salvador, Abolição etc.) que não chequei nesta sessão estão marcadas "data não conferida nesta pesquisa".

---

## Abertura: população nos censos

Recorte: estados que hoje formam o Nordeste (MA, PI, CE, RN, PB, PE, AL, SE, BA). A divisão regional atual não existia em 1872 nem antes de 1970; o IBGE já entrega os anos antigos reagrupados pela divisão atual.

**Atualização (2026-11-02, depois do primeiro commit):** a API do SIDRA (`apisidra.ibge.gov.br`) está acessível nesta rede. Baixei as duas tabelas abaixo com curl, li o JSON com `python -I` e conferi cada valor; batem com a conferência do controlador. Os números desta seção são **[A] lidos na tabela oficial**, ao contrário do resto do dossiê.

- **IBGE, SIDRA, tabela 1286** (população nos censos demográficos, 1872 a 2010, Brasil e Grandes Regiões; variável 606 "População", unidade "Pessoas"): https://apisidra.ibge.gov.br/values/t/1286/n1/all/n2/all/v/606/p/all
- **IBGE, SIDRA, tabela 4709** (Censo Demográfico 2022; variável 93 "População residente", unidade "Pessoas"): https://apisidra.ibge.gov.br/values/t/4709/n1/all/n2/2/v/93/p/2022

| Ano | População NE | População Brasil | % NE | Fonte |
|---|---|---|---|---|
| 1872 | 4.638.560 | 9.930.478 | 46,7 | IBGE, SIDRA, tabela 1286 [A] |
| 1890 | 6.002.047 | 14.333.915 | 41,9 | IBGE, SIDRA, tabela 1286 [A] |
| 1900 | 6.749.507 | 17.438.434 | 38,7 | IBGE, SIDRA, tabela 1286 [A] |
| 1920 | 11.245.921 | 30.635.605 | 36,7 | IBGE, SIDRA, tabela 1286 [A] |
| 1940 | 14.434.080 | 41.236.315 | 35,0 | IBGE, SIDRA, tabela 1286 [A] |
| 1950 | 17.973.413 | 51.944.397 | 34,6 | IBGE, SIDRA, tabela 1286 [A] |
| 1960 | 22.428.873 | 70.992.343 | 31,6 | IBGE, SIDRA, tabela 1286 [A] |
| 1970 | 28.675.110 | 94.508.583 | 30,3 | IBGE, SIDRA, tabela 1286 [A] |
| 1980 | 35.419.156 | 121.150.573 | 29,2 | IBGE, SIDRA, tabela 1286 [A] |
| 1991 | 42.470.225 | 146.917.459 | 28,9 | IBGE, SIDRA, tabela 1286 [A] |
| 2000 | 47.693.253 | 169.590.693 | 28,1 | IBGE, SIDRA, tabela 1286 [A] |
| 2010 | 53.081.950 | 190.755.799 | 27,8 | IBGE, SIDRA, tabela 1286 [A] |
| 2022 | 54.658.515 | 203.080.756 | 26,9 | IBGE, SIDRA, tabela 4709 [A] |

Percentuais calculados por mim a partir dos valores da tabela, com uma casa decimal (valores com duas casas: 46,71; 41,87; 38,70; 36,71; 35,00; 34,60; 31,59; 30,34; 29,24; 28,91; 28,12; 27,83; 26,92). Na página, o gerador calcula a parcela a partir do `censos.csv` (spec, seção 3).

**Notas da série:**

- **Série única.** A tabela 1286 é a série única do IBGE para todos os censos de 1872 a 2010, por Grande Região. Usá-la inteira resolve a mistura de valores de definições diferentes (presente, recenseada, residente) que apareceu na primeira versão deste dossiê, quando eu só tinha valores soltos de fontes variadas.
- **O que a tabela declara.** A resposta da API de valores traz só os cabeçalhos (nível territorial, unidade "Pessoas", variável 606 "População", ano) e **nenhuma nota de rodapé**. A variável se chama apenas "População", sem dizer se é presente, recenseada ou residente em cada ano. As notas da tabela ficam na página descritiva do SIDRA, que cai num desafio Cloudflare, e a API de metadados (`servicodados.ibge.gov.br`) não respondeu nesta rede; não tentei contornar. Segundo a página de séries estatísticas do IBGE vista na busca, os censos usam população presente de 1872 a 1950, recenseada de 1960 a 1980 e residente de 1991 em diante; **não confirmei que a 1286 segue exatamente essa regra**. Sinal disso: para 1991 a 1286 traz Brasil 146.917.459 e Nordeste 42.470.225, enquanto outra tabela do IBGE dá 146.825.475 para o Brasil (residente) e um documento do BNB dá 42.497.540 para o Nordeste; para 2000 a 1286 traz Nordeste 47.693.253, e outras fontes dão 47.741.711. As diferenças mudam o percentual em menos de 0,1 ponto.
- **2022 vem de outra tabela.** A 1286 vai até 2010; o ponto de 2022 vem da 4709, que declara "População residente". É o par revisado pelo IBGE em 31/08/2023, e não o da primeira divulgação (Brasil 203.062.512, Nordeste 54.644.582). A nota do `censos.csv` deve dizer que o último ponto vem de tabela diferente.
- **1910 e 1930 não tiveram censo.** A série pula de 1900 para 1920 e de 1920 para 1940. O gráfico deve ligar os pontos sem sugerir dados nesses anos.
- **1900:** o IBGE registra problemas de cobertura no censo de 1900 (texto "Em 150 anos, conheça a história que o censo conta", Agência de Notícias do IBGE, via busca).

**Conferência dos valores de trabalho da spec:**

- **46,7% (1872):** confere. 4.638.560 / 9.930.478 = 46,71% (SIDRA 1286).
- **26,9% (2022):** confere. 54.658.515 / 203.080.756 = 26,92% (SIDRA 4709). O número de trabalho da spec para o Nordeste (54.644.582) é da primeira divulgação e deve ser trocado por 54.658.515, que forma par com o total revisado 203.080.756.

**Decisões e cuidados para `censos.csv`:**

1. **Fronteiras.** As mudanças de limite entre províncias do Nordeste não alteram a soma regional em 1872: a Comarca do São Francisco passou de Pernambuco para Minas Gerais em 1824 e para a Bahia em 1827 (data não conferida nesta pesquisa), portanto já era baiana em 1872; trocas entre Ceará e Piauí (Crateús e Amarração, 1880, data não conferida nesta pesquisa) ficam dentro da região. A tabela 1286 já entrega os anos antigos reagrupados nas Grandes Regiões atuais.
2. **Uma tabela por trecho:** 1286 para 1872 a 2010 e 4709 para 2022, com o código da tabela em cada linha do CSV (coluna "tabela do IBGE de origem", spec seção 3). Não misturar valores de outras fontes.
3. **Outra série para 1872.** Marcílio (1973), citada em artigo da *Revista Econômica do Nordeste* (BNB), dá 4.708.160 para o Nordeste e 10.112.061 para o Brasil em 1872 (46,6%), com correções do censo. A página usa a série oficial e pode citar a corrigida como divergência.

---

## Época 1. Colônia do açúcar (1530–1654)

**Resumo do período.** A Coroa portuguesa ocupou o litoral com capitanias e fez do açúcar o negócio da colônia. Os engenhos de Pernambuco e da Bahia, movidos a trabalho escravizado africano, multiplicaram-se na segunda metade do século XVI. Salvador foi sede do governo-geral desde 1549. Em 1630 a Companhia das Índias Ocidentais (holandesa) tomou Olinda e Recife e ficou até 1654; a guerra destruiu engenhos e derrubou a exportação das capitanias ocupadas.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 1549 | Salvador, sede do governo-geral | Jornal *Estado de Minas*, texto sobre 1763 ("Salvador, a primeira capital do governo-geral desde 1549") [B] |
| 1570 | Gandavo conta 60 engenhos, dois terços em Pernambuco (23) e na Bahia (18) | Schwartz, tabela 1 (ver Números) [A] |
| 1630 | Ocupação holandesa de Pernambuco; exportação de açúcar cai | Simonsen (ver Números) [A] |
| 26/01/1654 | Capitulação holandesa na Campina do Taborda (Recife); evacuação a partir de abril | Portal Estratégia Militares; artigo do IGHMB (portaldeperiodicos.marinha.mil.br) [B] |
| 06/08/1661 | Paz de Haia: Portugal paga aos Países Baixos 4 milhões de cruzados (equivalentes a 8 milhões de florins, segundo as fontes) | Verbetes "Treaty of The Hague (1661)" e "Insurrection of Pernambuco"; artigo do periódico naval (IGHMB) [B] |

Marco candidato da spec "1654" confirmado. Sugiro que o marco de 1654 apareça como fim da época 1 e, na época 2, ligado à frase de Furtado sobre as Antilhas.

**Números.**

1. **60 engenhos (1570), 120 (1583–1585), 192 (1612).** Mede o número de engenhos em operação no Brasil. Tipo: `historiador`. Fonte: Stuart B. Schwartz, tabela 1, com dados de Gandavo (1570) e Fernão Cardim (1583–1585); 1612 segundo resumo do mesmo autor. Texto acessível em PDF da UFPR (`docs.ufpr.br/~lgeraldo/textosbrasila/schwartzobrasilcolonial.pdf`, pelo nome do arquivo provavelmente o capítulo "O Brasil colonial, c.1580-1750: as grandes lavouras e as periferias", em Leslie Bethell (org.), *História da América Latina*, v. II; título e página não confirmados). Obra de referência do autor: *Segredos internos: engenhos e escravos na sociedade colonial, 1550-1835* (Companhia das Letras, 1988). Confiabilidade: boa para a ordem de grandeza; são contagens de cronistas da época compiladas por historiador. Para 1629 há só o dado de Pernambuco (150 engenhos, de Cadena de Vilhasanti, na mesma tabela); um total nacional de 346 que circula **não foi confirmado [C]**. **[A]**
2. **Exportação de açúcar das capitanias ocupadas caiu de 60.000 para 30.000 caixas depois de 1630.** Mede a exportação anual de açúcar das capitanias sob ocupação holandesa. Tipo: `historiador`. Fonte: Roberto Simonsen, *História Econômica do Brasil (1500/1820)*, 6ª edição (cópia na plataforma e-Disciplinas da USP; outra cópia em PDF no portal da Secretaria de Fazenda do RJ). Trecho visto na busca: "nas capitanias por eles ocupadas a exportação do açúcar, devido à paralisação e à destruição de vários engenhos, tinha baixado de 60.000 para 30.000 caixas, após 1630". Página: não confirmada. Confiabilidade: média; Simonsen não informa aqui a série completa, e o texto digitalizado tem erros de OCR. **[A]**
3. **218.220 caixas exportadas pelo Brasil holandês entre 1636 e 1643.** Tipo: `historiador`, de segunda mão (Simonsen cita Lippmann, que cita Handelmann). Mesma fonte e mesma ressalva do item 2. Confiabilidade: baixa a média, pela cadeia de citações. **[A]**

**De fora × de dentro.**

- *De fora:* a Coroa decidiu o modelo de ocupação (capitanias, governo-geral em Salvador); a distribuição do açúcar na Europa dependia dos holandeses, que controlavam boa parte do comércio marítimo europeu no início do século XVII (Furtado, segundo resenha de *Formação Econômica do Brasil* da UFRRJ); a guerra de 1630–1654 entre a Companhia das Índias Ocidentais e os luso-brasileiros destruiu engenhos; a paz de 1661 foi negociada entre Lisboa e Haia.
- *De dentro:* a riqueza foi construída sobre o latifúndio canavieiro e a escravidão africana, com poder concentrado nos senhores de engenho; a expulsão de 1654 foi obra de forças locais (Insurreição Pernambucana, 1645–1654). A tese de que parte dos senhores de engenho se rebelou por estar endividada com a Companhia é associada a Evaldo Cabral de Mello (*O negócio do Brasil*), **não confirmada nesta pesquisa [C]**.

**Divergências.**

- **"Crise do açúcar".** A leitura clássica (Simonsen, Furtado) liga a decadência do Nordeste à guerra holandesa e à concorrência das Antilhas. A historiografia posterior discute alcance e datas: Antônio Barros de Castro admite uma crise no século XVII, mas vê melhora que se estende até meados da década de 1710; Maximiliano Menz (*Varia Historia*) analisa as crises de 1688 e de 1770 e vê a do Nordeste como crise de oferta, não de demanda; Stuart Schwartz (*Tempo*, 2008) põe a "crise do século XVII" numa escala global, ligada à prata e ao tráfico; Alírio Cardoso descreve a crise de meados do XVII como perda sistemática do valor do açúcar. Vera Ferlini (*Terra, trabalho e poder*) é referência sobre o açúcar de Pernambuco e da Bahia, mas não consegui reproduzir a tese dela com segurança **[C]**. Fontes: artigos em Redalyc e na revista *Clio* (UFPE) listados no fim. Sugestão para o texto: tratar a "crise" como perda de posição relativa, com a ressalva de que historiadores divergem sobre quando e quanto.
- **Os números de Furtado vêm de Simonsen.** Flávio Rabelo Versiani ("Furtado como historiador econômico", IEPE/CdG, 2020) mostra que estimativas atribuídas a Furtado (por exemplo, 300 mil habitantes em 1700) vêm de Simonsen, e que as estimativas de renda do açúcar se apoiam em hipóteses sobre valor da produção e população. Consequência: Furtado e Simonsen não são duas fontes independentes para o mesmo número.
- **Renda da economia açucareira em libras** (estimativa de Furtado no capítulo sobre a colônia açucareira): **não confirmada [C]**; não usar.

**Sugestão de "O que ficou disso"** (sugestão, tipo `interpretacao`): o Nordeste foi o centro da colônia, mas a riqueza ficou concentrada em poucos senhores de terra e de gente, e esse desenho de terra concentrada atravessou os séculos seguintes.

---

## Época 2. Concorrência, ouro e a capital que muda (1654–1808)

**Resumo do período.** Depois da expulsão, os holandeses levaram técnica e capital para as Antilhas, e o açúcar do Nordeste passou a disputar mercado com produção mais nova. No fim do século XVII começou a mineração de ouro em Minas Gerais, que puxou gente, escravizados e atenção da Coroa para o Centro-Sul. Em 1763 a capital saiu de Salvador para o Rio de Janeiro, porto do ouro. A época fecha com a chegada da Corte ao Rio em 1808.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| até c. 1664 | "Menos de um decênio depois da expulsão dos holandeses, já operava nas Antilhas uma economia açucareira de consideráveis proporções" | Celso Furtado, *Formação Econômica do Brasil*, p. 35 da edição usada na resenha de Letícia Inácio (UFRRJ); edição não identificada [A] |
| década de 1690 | Início da mineração de ouro em Minas Gerais | data não conferida nesta pesquisa |
| 1759 | Companhia Geral de Pernambuco e Paraíba (monopólio pombalino) | data não conferida nesta pesquisa |
| 27/01/1763 ou 31/08/1763 | Transferência da capital de Salvador para o Rio de Janeiro e elevação a vice-reinado | Carta régia de 27/01/1763 (texto do TJBA sobre a transferência); Rio "oficialmente elevado a capital em 31 de agosto de 1763" (*Estado de Minas*). Divergência de marco: ver abaixo [B] |
| 1808 | Chegada da Corte ao Rio e abertura dos portos | data não conferida nesta pesquisa |

Marco candidato da spec "1763" confirmado (ano). Sugiro o id `#1763` para a época.

**Números.**

1. **876.629 kg de ouro produzidos no Brasil no século XVIII (cerca de 877 toneladas).** Mede a produção estimada de ouro do século. Tipo: `historiador`. Fonte: Virgílio Noya Pinto, *O ouro brasileiro e o comércio anglo-português*, 2ª ed., São Paulo, Companhia Editora Nacional, 1979 (versão mimeografada de 1972 na USP); quadro final de produção. O número aparece como a estimativa mais citada em artigo acadêmico (Dialnet, `dialnet.unirioja.es/descarga/articulo/7186230.pdf`). Página e quadro: não confirmados. Confiabilidade: média; é a estimativa padrão, mas resenha da época (RAE/FGV) criticou a apresentação da série. **[A]**
2. **Não achei número confiável** da queda do preço do açúcar ou da participação do Nordeste nas exportações no século XVIII. O "preço do açúcar caiu à metade" atribuído a Furtado **não foi confirmado [C]**.

**De fora × de dentro.**

- *De fora:* concorrência antilhana montada com técnica e capital holandeses; a Coroa redirecionou administração e fiscalização para as minas e mudou a capital (a mudança é descrita como meio de fiscalizar as minas e conter o contrabando; Maria Fernanda Bicalho, "O Rio de Janeiro no século XVIII: a transferência da capital e a construção do território centro-sul da América portuguesa", revista *Urbana*, Unicamp); companhias de comércio monopolistas na era pombalina.
- *De dentro:* a economia açucareira seguiu presa ao latifúndio e à escravidão. O deslocamento de escravizados e capitais do Nordeste para as minas é afirmação comum, **não confirmada com número nesta pesquisa [C]**.

**Divergências.**

- **Data do marco de 1763:** carta régia de 27 de janeiro ou elevação oficial em 31 de agosto. Para a página, "1763" basta; o texto não deve trazer dia.
- **Alcance da decadência:** Barros de Castro vê recuperação do açúcar até meados da década de 1710; Menz trata a crise de 1770 como ligada ao ouro e a de 1688 como do açúcar (ver época 1). A página deve dizer que o eixo migrou para o Centro-Sul sem afirmar colapso do açúcar nordestino.

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): o centro de decisão foi para o Sudeste em 1763 e não voltou mais; daí em diante, muito do que se decidiu sobre o Nordeste foi decidido longe dele.

---

## Época 3. Império e revoltas (1808–1889)

**Resumo do período.** Com a Corte no Rio, as províncias do Norte passaram a pagar impostos que sustentavam a nova capital e as guerras do Sul, num momento de seca e de preços ruins para o açúcar e o algodão. Pernambuco se levantou em 1817 e em 1824 e foi reprimido. O café do Vale do Paraíba e depois de São Paulo tomou o lugar do açúcar na pauta. Depois do fim do tráfico atlântico (1850), o Nordeste vendeu escravizados para o Sudeste cafeeiro. A Grande Seca de 1877–1879 matou dezenas a centenas de milhares de pessoas.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 1817 | Revolução Pernambucana: impostos para a Corte e para a campanha da Cisplatina, seca de 1816, queda da produção de açúcar e algodão | Sínteses didáticas coincidentes (historiadomundo, preparaenem) e artigo acadêmico em *Almanack* (periodicos.usp.br/alb) sobre a base social do movimento [B] |
| 1824 | Confederação do Equador | data não conferida nesta pesquisa (marco candidato da spec, consagrado) |
| 1850 | Fim do tráfico atlântico de escravizados; começa o tráfico interprovincial | Slenes (ver Números) [A] |
| 1877–1879 | Grande Seca | ver Números [B] |
| 1888 | Abolição | data não conferida nesta pesquisa |

Marcos candidatos "1817 e 1824" e "1877–1879": confirmados para 1817 e 1877–1879; 1824 não conferido aqui (fato consagrado; conferir fonte).

**Números.**

1. **Café passou de 18,4% para 61,5% das exportações; açúcar caiu de 30,1% para 9,9% (decênios 1821–1830 e 1881–1890).** Mede a participação de cada produto no valor exportado pelo Brasil. Tipo: `oficial` (estatística histórica de comércio exterior), visto em compilação. Fontes: 1821–1830 em tabela por decênios no artigo de Garels (*Revista Raízes*, UFCG) e em verbete da Wikipédia (coincidem) **[B]**; 1881–1890 só em verbete da Wikipédia ("Economy of the Empire of Brazil") **[C]**. Fonte primária provável: série de exportação por produtos do *Anuário Estatístico do Brasil* / *Estatísticas Históricas do Brasil* (IBGE), não aberta. Confiabilidade: boa para 1821–1830; a conferir para 1881–1890.
2. **Pelo menos 200 mil escravizados levados ao Sudeste pelo tráfico interno (décadas de 1850 a 1880), cerca de 90 mil entre 1873 e 1881.** Tipo: `historiador`. Fonte: Robert Slenes, tese de doutorado (Stanford, 1976), citado em artigos da revista *Resgate* (Unicamp) e de *Horizontes* (UFS). Página: não confirmada (número de segunda mão). Confiabilidade: boa; é a estimativa de referência. Contando também o comércio dentro das próprias regiões, o total pode passar de 400 mil (Slenes citado por Maria de Fátima Novaes Pires, revista *Áfricas*, Uneb). **[A]** para a citação, página pendente.
3. **Mortes na Grande Seca de 1877–1879.** Estimativas muito diferentes: "pelo menos 500 mil no Nordeste" (artigo de divulgação, sem método, *Jornal do Sudoeste*) e "mais de 100 mil no Ceará" (artigo acadêmico). Tipo: `historiador`. Confiabilidade: baixa para o número regional. **[C] para 500 mil; [B] para a ordem de grandeza no Ceará.** Sugestão: na página, usar só "dezenas de milhares de mortos no Ceará" com a fonte acadêmica, ou não usar número. Fonte de época: Rodolpho Theophilo, *História da Seca do Ceará* (1883), não consultada.

**De fora × de dentro.**

- *De fora:* tributação para manter a Corte e as campanhas do Sul (1817); repressão do governo imperial às revoltas; o café do Sudeste atraiu crédito e mão de obra.
- *De dentro:* proprietários do Nordeste venderam escravizados ao Sul quando o preço subiu; Slenes (2004) mostra que havia também um mercado interno no Norte-Nordeste, com o açúcar ainda demandando escravizados (*Redalyc*, `77070146007`). A base de 1817 foi uma aliança de produtores de açúcar e algodão e comerciantes do Recife.

**Divergências.**

- **Causa de 1817:** a explicação didática (impostos e seca) é a mais repetida; Evaldo Cabral de Mello trabalha com o "contraponto do açúcar e do algodão", e o artigo em *Almanack* questiona se esse esquema dual explica sozinho o conflito.
- **Mortos na seca:** ver número 3.

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): no Império o Nordeste perdeu a disputa da pauta para o café e perdeu também gente, vendida para o Sul; a seca de 1877 fixou a imagem da região como lugar de flagelo.

---

## Época 4. Primeira República: café com leite, seca e Canudos (1889–1930)

**Resumo do período.** Na República, o poder federal ficou com São Paulo e Minas, e a política econômica girou em torno do café. A indústria nasceu concentrada em São Paulo. No sertão baiano, o arraial de Canudos foi destruído pelo Exército em 1897. A resposta federal às secas ganhou um órgão próprio em 1909, que construiu açudes e estradas, muitas vezes em terras de grandes proprietários.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 24/11/1896 a 10/1897 | Guerra de Canudos (primeira batalha em 24/11/1896; quarta expedição encerra a guerra em outubro de 1897) | Matérias de 2021 (*Brasil de Fato*, IHU/Unisinos) [B] |
| 21/10/1909 | Decreto 7.619 cria a Inspetoria de Obras Contra as Secas (IOCS) | Pronunciamento no Senado; artigo em *Risco* (USP) [B] |
| 09/07/1919 | Decreto 13.687 renomeia para Inspetoria Federal de Obras Contra as Secas (IFOCS) | Carta de Serviços do DNOCS (gov.br/dnocs) [A] |

Marcos candidatos "1897" e "1909" confirmados.

**Números.**

1. **Participação de São Paulo no valor da produção industrial brasileira: 15,9% (1907), 31,5% (1919), 37,5% (1929).** Tipo: `historiador`. Fonte: Wilson Cano, *Raízes da concentração industrial em São Paulo* (via resultados que citam o autor; edição e página não confirmadas). Confiabilidade: média; para 1919 outra fonte (Pochmann) dá 32,2%. **[B]** Não achei a participação do Nordeste nesses anos **[C]**.
2. **Canudos: cerca de 25 mil mortos; 10 mil a 12 mil soldados.** Tipo: `historiador`, mas só achei em fontes de divulgação (Poder360, Infopedia), sem origem do cálculo. **[C]** Não recomendo usar sem obra acadêmica (Robert Levine, *O sertão prometido*, ou Walnice Nogueira Galvão; não consultados).

**De fora × de dentro.**

- *De fora:* política federal voltada ao café; o Exército federal destruiu Canudos; o órgão contra as secas foi criado e dirigido a partir do Rio.
- *De dentro:* o mandonismo local (coronelismo) organizou a política sertaneja; os açudes da política hidráulica ficaram muitas vezes dentro de grandes propriedades, crítica que Furtado faria no relatório do GTDN (texto da Fundação Perseu Abramo, "Asas da graúna") **[B]**. A referência clássica sobre coronelismo (Victor Nunes Leal, *Coronelismo, enxada e voto*, 1949) não foi consultada.

**Divergências.**

- **Número de mortos e de moradores de Canudos:** 25 mil mortos é cifra repetida sem fonte; um verbete fala em 30 mil moradores; o número de soldados varia entre 10 mil e 12 mil.
- **Indústria paulista em 1919:** 31,5% (Cano) ou 32,2% (Pochmann).

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): a seca virou política federal em 1909, mas a obra pública chegou primeiro onde já havia poder, e a indústria do país nasceu longe do Nordeste.

---

## Época 5. Vargas e a grande migração (1930–1950)

**Resumo do período.** Depois de 1930 o governo federal centralizou decisões e a industrialização acelerou no Centro-Sul. Nas secas de 1932, governos montaram "campos de concentração" para reter retirantes longe das capitais. A Constituição de 1934 reservou parte da receita federal para obras contra as secas. Milhões deixaram o Nordeste rumo a São Paulo e ao Rio. Em 1945 nasceram a Chesf, para aproveitar a cachoeira de Paulo Afonso, e o DNOCS.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 1932 | Seca; campos de concentração para retirantes (anunciados no *Correio da Manhã* em 1932) | Anais ANPUH 2019 (anpuh.org.br) [A] |
| 1934 | Constituição destina não menos de 4% da receita tributária federal à defesa contra as secas (art. 177) | Texto acadêmico sobre repartição de receitas (fragmentado na busca) [B]; texto constitucional não aberto |
| 03/10/1945 | Decreto-Lei 8.031 cria a Chesf (constituída em assembleia de 15/03/1948) | Planalto (Del8031) e relatórios da Chesf [A] |
| 28/12/1945 | IFOCS vira DNOCS | Carta de Serviços do DNOCS cita "Decreto-Lei nº 8.486, de 28 de dezembro de 1945"; outras fontes citam 8.846. Divergência [B] |

**Números.**

1. **4% da receita tributária federal para as secas (Constituição de 1934, art. 177).** Tipo: `oficial`. Confirmação parcial: o percentual aparece em texto acadêmico sobre repartição de receitas; o artigo da Constituição não foi aberto. **[B]** Conferir no texto da Constituição de 1934 (Planalto).
2. **Participação do Nordeste no PIB em 1939: não confirmada [C].** O Ipea tem a tabela "Brasil: Participação do Norte, Nordeste e Centro-Sul no Produto Interno Líquido, a Custo de Fatores, por Setores de Atividade, 1939 e 1947" em *Desenvolvimento regional no Brasil*, 2ª edição (repositorio.ipea.gov.br, handle 11058/12296), e o BNB tem o "Gráfico 18: Evolução da participação do Nordeste no PIB do Brasil, 1939/2008", p. 29 do documento 2011_ISE_ISAC. Nenhum dos dois pôde ser aberto. **O "30% em 1939" não tem lastro**: o mesmo tipo de cifra (31,2% "da renda nacional" em 1939) aparece num texto da UFC/CAEN sem metodologia, que no mesmo texto cita uma série da CMBEU (1954) incompatível com ele. Pela spec, não entra.
3. **Migração:** não achei número confiável de saldo migratório do Nordeste em 1940–1950 **[C]**. Achei só a informação qualitativa de que Nordeste e Sudeste tiveram saldos negativos nos anos 1940 e que o êxodo rural envolveu cerca de dois milhões de migrantes no país (Camarano e Beltrão, 2000, citados em capítulo do Nepo/Unicamp) **[B]**. Referências que devem ter os números: Douglas Graham, "Padrões de convergência e divergência do crescimento econômico regional e das migrações no Brasil, 1940/1960" (*Revista Brasileira de Economia*); Merrick e Graham, *Population and Economic Development in Brazil* (1979); Moura, *O balanço migratório do Nordeste no período de 1950/70* (1980).

**De fora × de dentro.**

- *De fora:* centralização federal e industrialização no Centro-Sul; os campos de concentração de 1932 foram política de governo; a Chesf foi decisão federal.
- *De dentro:* estrutura fundiária concentrada e trabalho rural precário empurraram a saída; elites locais controlavam frentes de trabalho e água (tema que reaparece no GTDN, época 6).

**Divergências.**

- **PIB em 1939:** ver número 2.
- **Número do decreto-lei do DNOCS:** 8.486 (Carta de Serviços do DNOCS, compatível com a numeração de dezembro de 1945) ou 8.846 (relatório anual do DNOCS de 2009 e pronunciamento no Senado). Conferir no Planalto.

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): foi nessa época que a saída virou destino para milhões de nordestinos, e o Sudeste cresceu também com esse trabalho.

---

## Época 6. BNB, GTDN e Sudene (1950–1964)

**Resumo do período.** A seca de 1951–1952 e a de 1958 expuseram o limite da política de açudes. Em 1952 foi criado o Banco do Nordeste. Em 1959 o Grupo de Trabalho para o Desenvolvimento do Nordeste (GTDN), coordenado por Celso Furtado, diagnosticou que o problema era econômico e estrutural, não só climático, e propôs industrializar a região. No mesmo ano nasceu a Sudene, que ganhou incentivos fiscais (o "34/18") para atrair indústria.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 19/07/1952 | Lei 1.649 cria o Banco do Nordeste do Brasil, com sede em Fortaleza; instalação em 1954 (assembleia de 18/01/1954, estatutos pelo Decreto 35.433, de 30/04/1954) | Planalto, Câmara, Senado; RI do BNB [A] |
| 15/01/1955 | Inauguração da usina Paulo Afonso I (Chesf); a Chesf registra operação comercial em dezembro de 1954 | Verbete e relatórios da Chesf [B] |
| 1959 | Relatório do GTDN, "Uma política de desenvolvimento econômico para o Nordeste" | Catálogo da biblioteca do BNDES (web.bndes.gov.br, handle 1408/17760) [A] |
| 15/12/1959 | Lei 3.692 institui a Sudene | Câmara (ementa oficial) [A] |
| 14/12/1961 e 27/06/1963 | Lei 3.995 (art. 34) cria a dedução do imposto de renda para projetos no Nordeste; Lei 4.239 (art. 18) a amplia (sistema "34/18") | Repositório Ipea (incentivos fiscais) e decretos que citam a Lei 4.239 [B]; um texto cita "4.329/63", provável erro |

Marcos candidatos "1952" e "1959" confirmados.

**Números.**

1. **Renda per capita do Nordeste "inferior a um terço" da do Centro-Sul.** Tipo: `oficial` (relatório de governo). Fonte: GTDN, *Uma política de desenvolvimento econômico para o Nordeste* (1959), em trecho reproduzido na *Revista Brasileira de Geografia* (IBGE, rbg.ibge.gov.br, artigo 2493), com tabela de indicadores em dólares de 1956. Página: não confirmada. Confiabilidade: boa como diagnóstico oficial da época; é estimativa dos anos 1950. **[A]**
2. **Renda per capita do Nordeste igual a 57,3% da média brasileira em 1960.** Tipo: `historiador` (estudo com dados FGV/IBGE). Fonte: Gomes (1994), tabela citada em artigo da *Revista Econômica do Nordeste* (BNB, artigo 2040). Confiabilidade: média; a mesma tabela mostra que para 1970 as estimativas vão de 38,8% (contas nacionais) a 55,6% (censos), sinal de que o nível depende muito da fonte. **[A]** para a citação.
3. **Participação do Nordeste no PIB em 1960: 13,8% ou 13,2% ou 11,7%.** Três valores em fontes diferentes: 13,8% (dados da Sudene citados em artigo da *Revista de Administração Pública*, FGV), 13,2% (Sudene, 1996, citado em texto da UFC/CAEN), 11,7% (outro texto, "nos anos 1960"). Tipo: `oficial`. **[C] até escolher uma série**. A série encadeada do Ipea/IBGE (spec, seção 11) é que deve decidir; não usar valor isolado.

**De fora × de dentro.**

- *De fora:* o governo federal criou o BNB, a Sudene e os incentivos; a energia de Paulo Afonso veio de empresa federal.
- *De dentro:* o próprio GTDN apontou que a política hidráulica beneficiava grandes propriedades; a expressão "indústria da seca", para a rede de latifundiários e políticos que se beneficiava das obras contra a seca, vem das reportagens de Antônio Callado no *Correio da Manhã* (1959), reunidas em *Os industriais da sêca e os "Galileus" de Pernambuco* (Civilização Brasileira, 1960) (artigo na *Revista Brasileira de Estudos Urbanos e Regionais*, ANPUR; ficha FAO AGRIS) **[A]**.

**Divergências.**

- **PIB do Nordeste em 1960:** ver número 3.
- **Data de origem do termo "indústria da seca":** reportagens de 1959 ou livro de 1960; fontes de divulgação dizem "anos 1960".
- **Transferência de recursos do Nordeste para o Centro-Sul pela política cambial,** argumento associado ao GTDN: **não confirmado nesta pesquisa [C]**.

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): pela primeira vez o atraso do Nordeste foi tratado como problema econômico com causa conhecida, e não como castigo do clima; BNB e Sudene existem até hoje por causa dessa virada.

---

## Época 7. Ditadura: obra grande e Sudene esvaziada (1964–1985)

**Resumo do período.** Em abril de 1964 Furtado teve os direitos políticos cassados e deixou a Sudene. A superintendência perdeu autonomia e parte dos recursos de incentivo foi redirecionada: em 1970, 30% dos incentivos fiscais passaram a financiar o Programa de Integração Nacional, cuja primeira etapa era a Transamazônica. Em 1974 os incentivos do Nordeste foram reunidos no Finor. A indústria chegou, em boa parte por empresas de fora da região (afirmação a conferir, ver De fora × de dentro), e a distância de renda per capita para o resto do país continuou grande.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 04/1964 | Furtado tem os direitos políticos suspensos por dez anos com base no Ato Institucional n. 1 (fontes divergem entre 1 e 9 de abril; o AI-1 é de 9/4) | FIPE (*Informações Fipe*); biografia no Senado [B] |
| 16/06/1970 | Decreto-Lei 1.106 cria o Programa de Integração Nacional; 30% dos incentivos fiscais vão para o PIN; primeira etapa: Transamazônica e Cuiabá-Santarém | Planalto e Câmara (texto do decreto-lei) [A] |
| 12/12/1974 | Decreto-Lei 1.376 cria o Finor | Monografia UFC (2000) e decretos posteriores [B] |
| 1967 | Subordinação da Sudene ao Ministério do Interior | **não confirmado [C]** |

**Números.**

1. **30% dos incentivos fiscais destinados ao PIN (1970).** Tipo: `oficial`. Fonte: Decreto-Lei 1.106, de 16/06/1970 (Planalto), art. 5º e § 1º ("A parcela de 30% (trinta por cento) referida neste artigo será calculada proporcionalmente entre as diversas destinações dos incentivos"). Confiabilidade: alta (texto legal). **[A]** Observação: o decreto mostra a regra; quanto deixou efetivamente de ir para o Nordeste **não foi quantificado nesta pesquisa [C]**.
2. **Participação do Nordeste no PIB: 13,8% em 1960 e 12% em 1980.** Tipo: `oficial` (dados da Sudene). Fonte: artigo "A questão regional no Brasil: o Nordeste (alguns tópicos)", *Revista de Administração Pública* (FGV, artigo 10611). Página: não confirmada. Confiabilidade: média; outras séries dão níveis diferentes (ver época 6). **[A]**
3. **Renda per capita do Nordeste em 1970: 38,8% da média brasileira (contas nacionais) ou 55,6% (censos).** Tipo: `historiador`. Fonte: Gomes (1994), via *Revista Econômica do Nordeste* (BNB, artigo 2040). Serve mais como exemplo de divergência do que como número de página. **[A]**

**De fora × de dentro.**

- *De fora:* decisões centralizadas em Brasília; parte dos incentivos foi para a Amazônia; a Sudene perdeu o papel de planejamento que tinha.
- *De dentro:* os incentivos atraíram principalmente empresas de fora da região (tema do artigo "Incentivos fiscais, empresas extra-regionais e a industrialização recente do Nordeste brasileiro", *Estudos Econômicos*, USP; conteúdo não lido **[C]**); Francisco de Oliveira, que trabalhou na Sudene de 1959 a 1964, critica em *Elegia para uma re(li)gião* (1977) o modelo seguido pela Sudene, sobretudo na ditadura (Flávio Mendes, *Caderno CRH*, 2018) **[A]**.

**Divergências.**

- **Nível do PIB e da renda per capita do Nordeste nos anos 1960 e 1970:** depende da série (Sudene, contas nacionais, censos). A página deve usar uma única série e dizer qual.
- **Dia da cassação de Furtado:** 1 ou 9 de abril de 1964 nas fontes; o texto pode dizer "abril de 1964".

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): a região ganhou fábricas e obras grandes, mas perdeu o lugar onde se pensava o próprio desenvolvimento; a distância de renda para o resto do país atravessou a ditadura quase igual.

---

## Época 8. Redemocratização até hoje (1985–2026)

**Resumo do período.** A Constituição de 1988 reservou 3% do imposto de renda e do IPI para fundos de financiamento regional, entre eles o FNE, operado pelo BNB. A Sudene foi extinta em 2001 e recriada em 2007. A participação do Nordeste no PIB oscilou entre 12% e 14,5% conforme o ano e a série. Em 2022 a região tinha 26,9% da população e 13,8% do PIB, e o menor PIB per capita entre as cinco regiões, cerca de metade da média nacional.

**Marcos.**

| Data | Fato | Fonte |
|---|---|---|
| 05/10/1988 | Constituição, art. 159, I, "c": 3% da arrecadação de IR e IPI para programas de financiamento do setor produtivo do Norte, Nordeste e Centro-Oeste | Pareceres técnicos da Sudene (gov.br/sudene) [A] |
| 27/09/1989 | Lei 7.827 regulamenta os fundos constitucionais (FNO, FNE, FCO); metade do FNE para o semiárido | Lei 7.827 (gov.br/mdr) [A] |
| 05/2001 | Sudene extinta e substituída pela Adene (MP 2.145 de 02/05/2001 e reedições 2.146-1, 2.146-2 e seguintes) | Câmara, Senado, Congresso [A] |
| 03/01/2007 | Lei Complementar 125 recria a Sudene | Câmara (publicação original) [A] |

Marco candidato "1988" confirmado. Transposição do São Francisco: datas **não conferidas nesta pesquisa**; se entrar, buscar fonte oficial e não atribuir a nenhum governo.

**Números.**

1. **13,8% do PIB brasileiro em 2022.** Tipo: `oficial`. Fonte: IBGE, Sistema de Contas Regionais 2022 (Agência de Notícias, matéria 41893, "Em 2022, PIB cresce em 24 unidades da federação"); o IBGE avisa que a série ainda está no ano-base 2010 e será revista na série de ano-base 2021. Para 2023 (divulgado em 14/11/2025) a participação é descrita como estável, sem o número na busca **[C]**. Confiabilidade: alta, a conferir na tabela. **[B]**
2. **PIB per capita do Nordeste R$ 25.401 em 2022, contra R$ 49.638 do Brasil (51%).** Tipo: `oficial`. Fonte: IBGE, Contas Regionais 2022 (nota do IBGE para o valor do Brasil, R$ 49.638,29) e boletim do BNB/Etene que cita as Contas Regionais (R$ 25.401,43). A razão de 51% é conta minha. **[A]** para o Brasil, **[B]** para o Nordeste.
3. **26,9% da população em 2022** (abertura). Tipo: `oficial`. Ver tabela da abertura.

**De fora × de dentro.**

- *De fora:* fundos constitucionais e bancos federais; extinção e recriação da Sudene por decisão federal.
- *De dentro:* a aplicação dos fundos e dos incentivos passa por governos estaduais, bancos e empresas da própria região. Afirmações sobre guerra fiscal entre estados nordestinos e sobre concentração dos recursos nos estados maiores **não foram confirmadas nesta pesquisa [C]**.

**Divergências.**

- **Participação no PIB ao longo do período:** 14,1% em 1985 e 13,5% em 2002 (artigo da *Revista Econômica do Nordeste*, 2006); 12% em 1995 e 13,1% em 2008 (Ipea, com dados do IBGE); 13,09% em 2002 e 14,48% em 2017 (BNB/Etene). As diferenças vêm de séries com anos-base diferentes. Não comparar números de séries distintas na página.
- **Regra editorial:** nenhum resultado desta época pode ser creditado a governo ou partido (spec, seção 6). Os números acima são da região, não de mandatos.

**Sugestão de "O que ficou disso"** (sugestão, `interpretacao`): a distância que começou a se formar em 1654 ainda está nos números de hoje: mais de um em cada quatro brasileiros vive no Nordeste, e a região produz menos de um sétimo da riqueza do país.

---

## Fontes

Todas acessadas apenas por resultados de busca em 2026-11-02, exceto as tabelas 1286 e 4709 do SIDRA, lidas pela API (ver "Como ler").

**Oficiais (IBGE, leis, órgãos públicos)**

- IBGE, SIDRA, tabela 1286 (população nos censos, 1872–2010, Brasil e Grandes Regiões), lida pela API. https://apisidra.ibge.gov.br/values/t/1286/n1/all/n2/all/v/606/p/all
- IBGE, SIDRA, tabela 4709 (Censo 2022, população residente), lida pela API. https://apisidra.ibge.gov.br/values/t/4709/n1/all/n2/2/v/93/p/2022
- IBGE, Agência de Notícias. "Em 150 anos, conheça a história que o censo conta" (série Brasil 1872 a 1950). https://agenciadenoticias.ibge.gov.br/pt/agencia-noticias/33495-em-150-anos-conheca-a-historia-que-o-censo-conta.html
- IBGE. Sinopse do Censo Demográfico 2010, Tabela 1.4 "População nos Censos Demográficos, segundo as Grandes Regiões e as Unidades da Federação, 1872/2010" (não aberta). https://censo2010.ibge.gov.br/sinopse/index.php?dados=4&uf=00 e PDF https://biblioteca.ibge.gov.br/visualizacao/livros/liv49230.pdf
- IBGE. Séries estatísticas, "População residente: distribuição por Grandes Regiões" (nota sobre presente/recenseada/residente). https://seriesestatisticas.ibge.gov.br/series.aspx?no=1&op=2&vcodigo=POP100&t=populacao-residente-distribuicao-grandes-regioes
- IBGE. Anuário Estatístico do Brasil 2023 e 2024, tabelas 2.1.3.1 (densidade 1940–2022) e s2t1301 (não abertas). https://anuario.ibge.gov.br/images/aeb/2023/s2/2_pdf/s2t1301.pdf
- IBGE, Agência de Notícias. Release do Censo 2010 (190.755.799). https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/14007-asi-primeiros-resultados-definitivos-do-censo-2010-populacao-do-brasil-e-de-190755799-pessoas
- IBGE, Agência de Notícias. "Em 2022, PIB cresce em 24 unidades da federação" (Contas Regionais 2022). https://agenciadenoticias.ibge.gov.br/pt/agencia-noticias/41893-em-2022-pib-cresce-em-24-unidades-da-federacao.html
- IBGE-BA. "Data em Dados: Dia do/a Nordestino/a" (reproduzido por Atualiza Bahia). https://atualizabahia.com.br/ibge-ba-data-em-dados-dia-do-a-nordestino-a/
- IBGE. *IBGE Informa*, n. 24/25, 1973 (população de 1970). https://biblioteca.ibge.gov.br/visualizacao/periodicos/190/ibge_inf_1973_n24_n25.pdf
- IBGE. *Revista Brasileira de Geografia*, artigo com trechos do relatório do GTDN. https://rbg.ibge.gov.br/index.php/rbg/article/view/2493/1872
- Fundaj-Dipes. Nota Técnica 02/2023, "Censo Demográfico 2022: reflexões iniciais sobre a região Nordeste". https://www.gov.br/fundaj/pt-br/composicao/dipes-1/publicacoes/relatorios-de-pesquisas/censo-demografico-2022-reflexoes-iniciais-sobre-a-regiao-nordeste.pdf
- Ipea. *Desenvolvimento regional no Brasil*, 2ª ed. (tabela de 1939 e 1947; não aberta). https://repositorio.ipea.gov.br/bitstream/11058/12296/1/Desenvolvimento_regional_no_Brasil_segunda_edicao.pdf
- BNB/Etene. 2011_ISE_ISAC, Gráfico 18, p. 29 (não aberto). https://bnb.gov.br/s482-dspace/bitstream/123456789/1824/1/2011_ISE_ISAC.pdf
- BNB. Informações socioeconômicas (Juazeiro-BA, 2019), tabela de 1991. https://www.bnb.gov.br/documents/45799/1016332/Juazeiro-BA%2B-%2B2019.pdf/30fd7a18-8bc4-0862-cdee-b53006464cef
- BNB/Etene. Boletim com PIB per capita 2022 (2024_INET_03). https://bnb.gov.br/s482-dspace/bitstream/123456789/2007/1/2024_INET_03.pdf
- BNB, Relações com Investidores, "History". https://ri.bnb.gov.br/en/about-the-bank/history
- Lei 1.649, de 19/07/1952 (BNB). https://planalto.gov.br/ccivil_03/leis/1950-1969/l1649.htm
- Lei 3.692, de 15/12/1959 (Sudene). https://www2.camara.leg.br/legin/fed/lei/1950-1959/lei-3692-15-dezembro-1959-354371-norma-pl.html
- Decreto-Lei 8.031, de 03/10/1945 (Chesf). https://planalto.gov.br/ccivil_03/Decreto-Lei/Del8031.htm
- Decreto-Lei 1.106, de 16/06/1970 (PIN). https://www.planalto.gov.br/ccivil_03/decreto-lei/1965-1988/del1106.htm
- Lei 7.827, de 27/09/1989 (fundos constitucionais). https://www.gov.br/mdr/pt-br/assuntos/fundos-regionais-e-incentivos-fiscais/fundos-constitucionais-de-financiamento-fno-fne-e-fco/L7827.pdf
- Medida Provisória 2.146-1, de 04/05/2001. https://www2.camara.leg.br/legin/fed/medpro/2001/medidaprovisoria-2146-1-4-maio-2001-348819-norma-pe.html ; MP 2.146-2, de 05/06/2001. https://www.planalto.gov.br/ccivil_03/mpv/Antigas_2001/2146-2.htm
- Lei Complementar 125, de 03/01/2007. https://www2.camara.leg.br/legin/fed/leicom/2007/leicomplementar-125-3-janeiro-2007-548989-publicacaooriginal-64228-pl.html
- DNOCS. Carta de Serviços ao Cidadão. https://www.gov.br/dnocs/pt-br/acesso-a-informacao/acoes-e-programas/copy_of_carta-de-servicos-ao-cidadao/cartadeservicos-red.pdf ; Relatório anual 2009. https://www.dnocs.gov.br/php/CGU/dnocs_relatorio_anual_2009.pdf
- Senado Federal. Pronunciamento sobre a criação da IOCS. https://www25.senado.leg.br/web/atividade/pronunciamentos/-/p/pronunciamento/341240
- Sudene. Pareceres técnicos sobre o FNE (art. 159, I, "c"). https://www.gov.br/sudene/pt-br/acesso-a-informacao/institucional/conselho-deliberativo/arquivos/1-sei_sudene-0513046-nota-tecnica-272-2023.pdf
- Ipea. *Considerações sobre o sistema de incentivos fiscais para o desenvolvimento do Nordeste*. https://repositorio.ipea.gov.br/bitstream/11058/14213/1/Consideracoes_sistema_de_incentivos_fiscais_desenvolvimento_nordeste.pdf
- Biblioteca do BNDES. Ficha do relatório do GTDN (1959). https://web.bndes.gov.br/bib/jspui/handle/1408/17760

**Historiadores e estudos**

- Simonsen, Roberto. *História Econômica do Brasil (1500/1820)*, 6ª ed. (cópia USP e-Disciplinas). https://edisciplinas.usp.br/mod/resource/view.php?id=1512462 ; outra cópia: https://portal2.fazenda.rj.gov.br/wp-content/uploads/2022/09/historia-economica-do-brasil-1500-1820.pdf
- Schwartz, Stuart B. Capítulo sobre o Brasil colonial c.1580-1750 (PDF UFPR; título provável). https://docs.ufpr.br/~lgeraldo/textosbrasila/schwartzobrasilcolonial.pdf ; *Segredos internos* (Companhia das Letras, 1988).
- Furtado, Celso. *Formação Econômica do Brasil* (1959), via resenha de Letícia Inácio (UFRRJ). https://cursos.ufrrj.br/grad/cienciaseconomicas/files/2021/01/Resenha-Formação-Econômica-do-Brasil-Letícia-Inácio-.pdf
- Versiani, Flávio Rabelo. "F.E.B.: Furtado como historiador econômico" (2020). https://iepecdg.com.br/wp-content/uploads/2020/05/F.R.Versiani_-F.E.B.-FURTADO-COMO-HISTORIADOR-ECONOMICO-maio20.pdf
- Debate sobre a "crise do açúcar": Barros de Castro, Menz, Schwartz, Cardoso, Ferlini (artigos em Redalyc e *Clio*). https://periodicos.ufpe.br/revistas/index.php/revistaclio/article/download/24458/19774/48886 ; https://www.redalyc.org/pdf/3844/384434841003.pdf ; https://www.redalyc.org/journal/3381/338161218006/338161218006.pdf ; https://www.redalyc.org/pdf/1670/167042154001.pdf ; https://www.redalyc.org/pdf/1670/167013399011.pdf
- Noya Pinto, Virgílio. *O ouro brasileiro e o comércio anglo-português*, 2ª ed., 1979; estimativa citada em https://dialnet.unirioja.es/descarga/articulo/7186230.pdf ; resenha em https://periodicos.fgv.br/rae/article/download/40037/38777/81884
- Bicalho, Maria Fernanda. "O Rio de Janeiro no século XVIII: a transferência da capital e a construção do território centro-sul da América portuguesa", *Urbana* (Unicamp). https://periodicos.sbu.unicamp.br/ojs/index.php/urbana/article/download/8635108/2923/4361
- Tribunal de Justiça da Bahia. Texto sobre o Tribunal da Relação e a transferência da capital. https://www.tjba.jus.br/portal/o-tribunal-da-relacao-da-bahia-o-padre-jose-de-anchieta-e-a-transferencia-da-capital/
- Slenes, Robert (tese, 1976), citado em: https://periodicos.sbu.unicamp.br/ojs/index.php/resgate/article/download/8645794/13094/18520 ; https://ufs.emnuvens.com.br/HORIZONTES/article/download/22098/17320/76368 ; https://revistas.uneb.br/index.php/africas/article/view/4390/2767 ; Slenes (2004): https://www.redalyc.org/journal/770/77070146007/77070146007.pdf
- Garels, tabela de exportações por decênios, *Revista Raízes* (UFCG). https://raizes.revistas.ufcg.edu.br/index.php/raizes/article/download/550/524
- Artigo sobre 1817 em *Almanack*. https://periodicos.usp.br/alb/article/download/11605/13374/14480
- Grande Seca: https://www.jornaldosudoeste.com/a-grande-seca-no-nordeste-entre-1877-1878/ (divulgação) e artigos listados na busca (redalyc 307470821003; UECE).
- Cano, Wilson. *Raízes da concentração industrial em São Paulo* (via resultados que o citam).
- Artigo da USP *Risco* sobre as Obras Contra as Secas (1909–1945). https://revistas.usp.br/risco/article/view/203768
- Anais ANPUH 2019 (campos de concentração de 1932). https://anpuh.org.br/uploads/anais-simposios/pdf/2019-01/1548874926_f8b61f43959074f84c38312d02d3702b.pdf
- Nepo/Unicamp, capítulo sobre mobilidade (Camarano e Beltrão). https://www.nepo.unicamp.br/publicacoes/livros/mobilidade/cap7.pdf
- "A questão regional no Brasil: o Nordeste (alguns tópicos)", *Revista de Administração Pública* (FGV). https://periodicos.fgv.br/rap/article/download/10611/9606
- Gomes (1994), via *Revista Econômica do Nordeste*. https://bnb.gov.br/revista/ren/article/download/2040/1244/7409
- UFC/CAEN, texto com o "31,2% em 1939" (citado como exemplo de número sem lastro). https://caen.ufc.br/wp-content/uploads/2021/11/seec-43.pdf
- Marcílio (1973), via *Revista Econômica do Nordeste*. https://bnb.gov.br/revista/ren/article/download/95/74
- Callado, Antônio. *Os industriais da sêca e os "Galileus" de Pernambuco* (1960); artigo ANPUR. https://rbeur.anpur.org.br/rbeur/article/download/7827/5724/31270 ; ficha FAO AGRIS. https://agris.fao.org/search/en/records/65ddf653b766d82b18fb8982
- Mendes, Flávio, sobre *Elegia para uma re(li)gião*, *Caderno CRH* (2018). https://www.redalyc.org/journal/3476/347659220009/347659220009.pdf
- "Asas da graúna: Nordeste, Nordestes" (Fundação Perseu Abramo). https://fpabramo.org.br/asas-da-grauna-nordeste-nordestes/
- FIPE, *Informações Fipe* 512 (cassação de Furtado). https://downloads.fipe.org.br/publicacoes/bif/bif512-82-84.pdf

**Secundárias e de divulgação (usadas só onde marcado [B] ou [C])**

- Cedeplar/UFMG, base Pop-72, README da Base dos Dados (`basedosdados/pipelines`, `models/br_ufmg_censo_demografico_1872/README.md`). https://github.com/basedosdados/pipelines
- Kotobank, verbete "Nordeste" (4.638.560 em 1872).
- CEIC Data, "Population Census: Northeast". https://www.ceicdata.com/en/brazil/population-census-by-region/population-census-northeast
- citypopulation.de, Região Nordeste. https://citypopulation.de/en/brazil/regiaonordeste/
- populacao.org, "População da Região Nordeste". https://populacao.org/regioes/nordeste/
- Wikipédia (en/pt): "1872 Brazilian census", "Demographics of Brazil", "Economy of the Empire of Brazil", "Treaty of The Hague (1661)", "Censo demográfico do Brasil de 2022", "Região Nordeste do Brasil" (ponto de partida; nenhum número final depende só dela sem marcação [B]/[C]).
- Poder360, Brasil de Fato, IHU/Unisinos, Infopedia (Canudos); Movimento Econômico (PIB 2022); *Estado de Minas* (1763); Estratégia Militares (1654).
