/* Nordeste em Números: valor ao passar o mouse ou o dedo nos gráficos, modal Ampliar do Início, seletores de Estados,
   Explorar (redesenho no navegador, comparação, zoom de período e de escala), linha do tempo e modal das épocas da
   página Como chegamos, menu e movimento.

   Sem bibliotecas. Nada de estilo inline (a Content-Security-Policy é style-src 'self'): a aparência vem só de classes
   do estilo.css e de atributos SVG. O desenho do gráfico repete o de graficos.py, para a vista redesenhada ficar igual
   à que vem pronta no HTML. Todo movimento depende de prefers-reduced-motion: no-preference, e nenhum conteúdo depende
   dele para aparecer: o número final já está no HTML. */
(function () {
  'use strict';

  /* Constantes de graficos.py (o teste confere que são as mesmas). */
  const ANO_INICIAL = 2000;
  const ANO_FINAL = 2027; /* fim do eixo, exclusivo */
  const LARGURA_CARACTERE = 6.6;
  const AFASTAMENTO_ROTULOS = 14;
  const LARGURA_ESTREITA = 520;
  const TOPO = 26;
  const BASE = 24;
  const LARGO = { largura: 720, altura: 300 };
  const ESTREITO = { largura: 360, altura: 240 };
  const SVG = 'http://www.w3.org/2000/svg';

  /* --- números no padrão do idioma da página, arredondados como no Python ------------------------------------ */

  /* O idioma vem do <html lang>: "en" usa 1,234.5 (formatacao.numero com idioma "en"); o resto, 1.234,5. */
  const IDIOMA = typeof document !== 'undefined' && /^en\b/i.test(document.documentElement.lang) ? 'en' : 'pt';

  /* Dígitos de |valor| com `casas` decimais. Como o round do Python: pelo valor exato do double, e o empate exato
     vai para o par (toFixed sozinho manda o empate para cima). */
  function arredondar(valor, casas) {
    const absoluto = Math.abs(valor);
    let fixo = absoluto.toFixed(casas);
    const exato = absoluto.toFixed(Math.min(100, casas + 60));
    const resto = exato.slice(exato.indexOf('.') + 1 + casas);
    if (/^50*$/.test(resto)) {
      let inteiro = BigInt(fixo.replace('.', ''));
      if (inteiro % 2n === 1n) inteiro -= 1n;
      const digitos = inteiro.toString().padStart(casas + 1, '0');
      fixo = casas ? digitos.slice(0, -casas) + '.' + digitos.slice(-casas) : digitos;
    }
    return fixo;
  }

  /* 1234.5, 1 -> "1.234,5" (em inglês, "1,234.5"); nunca "-0,0" (formatacao.numero). */
  function numero(valor, casas, idioma) {
    const [milhar, decimal] = (idioma || IDIOMA) === 'en' ? [',', '.'] : ['.', ','];
    const fixo = arredondar(valor, casas);
    const [inteiro, decimais] = fixo.split('.');
    const negativo = valor < 0 && /[1-9]/.test(fixo);
    return (negativo ? '-' : '') + inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, milhar) + (decimais ? decimal + decimais : '');
  }

  /* Os rótulos que o redesenho do Explorar escreve, do data-rotulos do cartão (interface.py); sem ele, os do português. */
  let rotulos = {
    desc: 'Gráfico de linhas, {titulo}. {partes}. A tabela com todos os valores está logo abaixo.',
    parte: '{rotulo}: {primeiro} em {ano_primeiro} e {ultimo} em {ano_ultimo}',
    e: 'e',
    colunas: ['Ano', 'Território', 'Valor', 'Série da fonte'],
  };

  function preencherModelo(modelo, valores) {
    return modelo.replace(/\{(\w+)\}/g, (inteiro, nome) => (nome in valores ? String(valores[nome]) : inteiro));
  }

  /* --- medição de audiência (Umami) ------------------------------------------------------------------------- */

  /* O que um atributo data-umami-event não expressa (troca de seletor, época aberta, seção lida, gráfico ampliado
     pelo clique no próprio gráfico) vai por umami.track, com o idioma da página. Sem o Umami (bloqueado, fora do ar,
     "Do Not Track"), nada acontece; um erro dele nunca chega à página. */
  function medir(nome, dados) {
    try {
      if (window.umami && typeof window.umami.track === 'function') window.umami.track(nome, Object.assign({ lang: IDIOMA }, dados));
    } catch (erro) {
      /* a medição nunca atrapalha a página */
    }
  }

  /* a chave da página (<body data-pagina>), a mesma nos dois idiomas: index, inovacao, como-chegamos... */
  function paginaAtual() {
    return document.body.getAttribute('data-pagina') || window.location.pathname;
  }

  /* Coordenada com no máximo uma casa, sem ".0" e sem "-0" (graficos._c). */
  function coord(valor) {
    let texto = arredondar(valor, 1);
    if (valor < 0 && /[1-9]/.test(texto)) texto = '-' + texto;
    return texto.endsWith('.0') ? texto.slice(0, -2) : texto;
  }

  /* --- eixo y: os mesmos ticks "bonitos" do Python ------------------------------------------------------------- */

  function arredondar9(valor) {
    return Math.round(valor * 1e9) / 1e9;
  }

  function unidade(inicio, fim, quantidade) {
    const bruto = (fim - inicio) / quantidade;
    const potencia = Math.floor(Math.log10(bruto));
    const erro = bruto / 10 ** potencia;
    const fator = erro >= Math.sqrt(50) ? 10 : erro >= Math.sqrt(10) ? 5 : erro >= Math.sqrt(2) ? 2 : 1;
    return potencia >= 0 ? [fator * 10 ** potencia, false] : [10 ** -potencia / fator, true];
  }

  function ticks(inicio, fim, quantidade) {
    const [passo, fracionario] = unidade(inicio, fim, quantidade);
    const fator = fracionario ? passo : 1 / passo;
    const lista = [];
    for (let i = Math.ceil(arredondar9(inicio * fator)); i <= Math.floor(arredondar9(fim * fator)); i++) {
      lista.push(fracionario ? i / passo : i * passo);
    }
    return lista;
  }

  function dominioBonito(inicio, fim, quantidade) {
    let anterior = null;
    for (let volta = 0; volta < 10; volta++) {
      const [passo, fracionario] = unidade(inicio, fim, quantidade);
      if (anterior && anterior[0] === passo && anterior[1] === fracionario) break;
      if (fracionario) {
        inicio = Math.floor(arredondar9(inicio * passo)) / passo;
        fim = Math.ceil(arredondar9(fim * passo)) / passo;
      } else {
        inicio = Math.floor(arredondar9(inicio / passo)) * passo;
        fim = Math.ceil(arredondar9(fim / passo)) * passo;
      }
      anterior = [passo, fracionario];
    }
    return [inicio, fim];
  }

  /* --- desenho do gráfico de linhas (graficos.grafico_linhas) ------------------------------------------------- */

  function escala(d0, d1, i0, i1) {
    return (v) => i0 + (v - d0) * (i1 - i0) / (d1 - d0);
  }

  function largura(texto) {
    return [...texto].length * LARGURA_CARACTERE;
  }

  function no(nome, atributos, texto) {
    const elemento = document.createElementNS(SVG, nome);
    Object.entries(atributos || {}).forEach(([chave, valor]) => elemento.setAttribute(chave, valor));
    if (texto !== undefined) elemento.textContent = texto;
    return elemento;
  }

  /* Linhas só com os pontos ([ano, valor, serie]) dentro do eixo; linha sem ponto no eixo sai. */
  function visiveis(linhas, a0, a1) {
    return linhas
      .map((l) => Object.assign({}, l, { pontos: l.pontos.filter((p) => p[0] >= a0 && p[0] < a1) }))
      .filter((l) => l.pontos.length);
  }

  /* Quebra a linha na troca de série e no ano faltante: nunca emenda dois trechos. */
  function trechos(pontos) {
    const lista = [];
    pontos.forEach((p) => {
      const ultimo = lista.length ? lista[lista.length - 1] : null;
      const anterior = ultimo ? ultimo[ultimo.length - 1] : null;
      if (anterior && p[0] === anterior[0] + 1 && p[2] === anterior[2]) ultimo.push(p);
      else lista.push([p]);
    });
    return lista;
  }

  function yDosRotulos(alvos, topo, eixo) {
    const ordem = alvos.map((_, i) => i).sort((a, b) => alvos[a] - alvos[b]);
    const ys = alvos.slice();
    if (ordem.length) ys[ordem[0]] = Math.max(topo + 10, ys[ordem[0]]);
    for (let k = 1; k < ordem.length; k++) ys[ordem[k]] = Math.max(ys[ordem[k]], ys[ordem[k - 1]] + AFASTAMENTO_ROTULOS);
    let teto = eixo - 2;
    for (let k = ordem.length - 1; k >= 0; k--) {
      ys[ordem[k]] = Math.min(ys[ordem[k]], teto);
      teto = ys[ordem[k]] - AFASTAMENTO_ROTULOS;
    }
    return ys;
  }

  function descricao(linhas, cfg) {
    const partes = linhas.map((l) => {
      const primeiro = l.pontos[0];
      const ultimo = l.pontos[l.pontos.length - 1];
      return preencherModelo(rotulos.parte, {
        rotulo: l.rotulo, primeiro: numero(primeiro[1], cfg.casas) + cfg.sufixo, ano_primeiro: primeiro[0],
        ultimo: numero(ultimo[1], cfg.casas) + cfg.sufixo, ano_ultimo: ultimo[0],
      });
    });
    return preencherModelo(rotulos.desc, { titulo: cfg.titulo, partes: partes.join('; ') });
  }

  let contadorDeIds = 0;

  /* O <svg> de `linhas` ({rotulo, rotulo_curto, destaque, comparar, pontos}) no período [a0, a1); null quando nenhuma
     linha tem ponto nele. Sem `ampliar`, a escala vertical é a do período completo, como no HTML. */
  function grafico(linhas, cfg, faixas, tamanho, periodo) {
    const a0 = periodo.a0;
    const a1 = periodo.a1;
    const vis = visiveis(linhas, a0, a1);
    if (!vis.length) return null;
    const W = tamanho.largura;
    const H = tamanho.altura;
    const estreito = W < LARGURA_ESTREITA;

    const daEscala = periodo.ampliar ? vis : visiveis(linhas, ANO_INICIAL, ANO_FINAL);
    const valores = daEscala.flatMap((l) => l.pontos.map((p) => p[1]));
    let baixo = Math.min(...valores);
    let alto = Math.max(...valores);
    if (baixo === alto) { baixo -= 1; alto += 1; }
    const dominio = dominioBonito(baixo, alto, 4);
    const marcas = ticks(dominio[0], dominio[1], 4);
    const amplitude = dominio[1] - dominio[0];
    const casasEixo = amplitude < 1 ? 2 : amplitude < 10 ? 1 : 0;
    const rotulosY = marcas.map((t) => numero(t, casasEixo) + cfg.sufixo);
    const rotulosFim = vis.map((l) => `${l.rotulo_curto} ${numero(l.pontos[l.pontos.length - 1][1], cfg.casas)}${cfg.sufixo}`);

    const esquerda = Math.ceil(rotulosY.length ? Math.max(...rotulosY.map(largura)) : 30) + 10;
    const direita = Math.ceil(Math.max(...rotulosFim.map(largura))) + 12;
    const x = escala(a0, a1, esquerda, W - direita);
    const y = escala(dominio[0], dominio[1], H - BASE, TOPO);
    const xp = (p) => x(p[0] + 0.5);
    const eixo = H - BASE;
    const altoQuadro = H - TOPO - BASE;

    contadorDeIds += 1;
    const id = `nnc${contadorDeIds}`;
    const svg = no('svg', {
      role: 'img', 'aria-labelledby': `${id}-t ${id}-d`, width: '100%', viewBox: `0 0 ${W} ${H}`, 'font-size': '11',
      'data-pontos': JSON.stringify(linhas.map((l) => ({
        rotulo: l.rotulo, rotulo_curto: l.rotulo_curto, destaque: l.destaque, pontos: l.pontos,
      }))),
      'data-casas': String(cfg.casas), 'data-sufixo': cfg.sufixo, 'data-eixo': `${a0} ${a1}`,
    });
    svg.append(no('title', { id: `${id}-t` }, cfg.titulo), no('desc', { id: `${id}-d` }, descricao(vis, cfg)));
    const padrao = no('pattern', {
      id: `${id}-h`, width: '6', height: '6', patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)',
    });
    padrao.append(no('line', { x1: '0', y1: '0', x2: '0', y2: '6', class: 'nn-hachura', 'stroke-width': '2.5' }));
    const defs = no('defs');
    defs.append(padrao);
    svg.append(defs);

    faixas.forEach(([nome, inicio, fim, interino], i) => {
      const a = Math.max(a0, inicio);
      const b = Math.min(a1, fim);
      if (b <= a) return;
      const xa = x(a);
      const xb = x(b);
      const quadro = { x: coord(xa), y: String(TOPO), width: coord(xb - xa), height: coord(altoQuadro) };
      if (interino) {
        svg.append(no('rect', Object.assign(quadro, { fill: `url(#${id}-h)` })));
        return;
      }
      svg.append(no('rect', Object.assign({ class: i % 2 ? 'nn-faixa-b' : 'nn-faixa-a' }, quadro)));
      if (xb - xa >= 14) {
        const texto = estreito || xb - xa < 58 ? [...nome][0] : nome;
        svg.append(no('text', {
          class: 'nn-rotulo', x: coord((xa + xb) / 2), y: String(TOPO - 8), 'text-anchor': 'middle',
        }, texto));
      }
    });

    const ultimoAno = Math.max(...vis.map((l) => l.pontos[l.pontos.length - 1][0]));
    if (ultimoAno + 1 < a1) {
      const xa = x(ultimoAno + 1);
      svg.append(no('rect', {
        x: coord(xa), y: String(TOPO), width: coord(x(a1) - xa), height: coord(altoQuadro), fill: `url(#${id}-h)`,
      }));
    }

    marcas.forEach((t, i) => {
      svg.append(no('line', {
        class: 'nn-grade', x1: String(esquerda), x2: coord(W - direita), y1: coord(y(t)), y2: coord(y(t)),
        'stroke-width': '1',
      }));
      svg.append(no('text', {
        class: 'nn-eixo', x: String(esquerda - 6), y: coord(y(t) + 4), 'text-anchor': 'end',
      }, rotulosY[i]));
    });

    const vao = a1 - a0;
    const passo = vao <= 8 ? (estreito ? 2 : 1) : vao <= 16 ? (estreito ? 4 : 2) : (estreito ? 8 : 4);
    for (let ano = Math.ceil(a0 / passo) * passo; ano < a1; ano += passo) {
      svg.append(no('text', {
        class: 'nn-eixo', x: coord(x(ano + 0.5)), y: String(H - 6), 'text-anchor': 'middle',
      }, String(ano)));
    }

    vis.forEach((l) => {
      const classe = l.comparar ? 'nn-linha-cmp' : l.destaque ? 'nn-linha-ne' : 'nn-linha-ref';
      const espessura = l.destaque || l.comparar ? '2.6' : '2';
      const grupo = no('g', { class: classe });
      trechos(l.pontos).forEach((trecho) => {
        if (trecho.length > 1) {
          const d = trecho.map((p, i) => `${i ? 'L' : 'M'}${coord(xp(p))},${coord(y(p[1]))}`).join('');
          grupo.append(no('path', {
            d, fill: 'none', 'stroke-width': espessura, 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
          }));
        }
        const raio = trecho.length > 1 ? '2.2' : '3.4';
        trecho.forEach((p) => grupo.append(no('circle', { cx: coord(xp(p)), cy: coord(y(p[1])), r: raio, stroke: 'none' })));
      });
      svg.append(grupo);
    });

    const alvos = vis.map((l) => y(l.pontos[l.pontos.length - 1][1]) + 4);
    yDosRotulos(alvos, TOPO, eixo).forEach((yRotulo, i) => {
      const l = vis[i];
      svg.append(no('text', {
        class: l.destaque || l.comparar ? 'nn-rotulo-forte' : 'nn-rotulo',
        x: coord(xp(l.pontos[l.pontos.length - 1]) + 7), y: coord(yRotulo),
      }, rotulosFim[i]));
    });

    /* para o arrasto do zoom: de x (unidades do SVG) para ano, e os limites do quadro */
    svg.nnQuadro = { esquerda, direita: W - direita, topo: TOPO, eixo, ano: escala(esquerda, W - direita, a0, a1) };
    return svg;
  }

  /* --- valor ao passar o mouse ou o dedo ---------------------------------------------------------------------- */

  function pontoNoSvg(svg, evento) {
    const matriz = svg.getScreenCTM();
    if (!matriz) return null;
    return new DOMPoint(evento.clientX, evento.clientY).matrixTransform(matriz.inverse());
  }

  /* Liga a dica a um gráfico, lendo data-pontos e os círculos já desenhados (os do Python ou os do redesenho): o
     círculo dá a posição, data-pontos dá o valor. */
  function ligarDica(svg) {
    let linhas;
    try {
      linhas = JSON.parse(svg.getAttribute('data-pontos') || '[]');
    } catch (erro) {
      return;
    }
    const [a0, a1] = (svg.getAttribute('data-eixo') || `${ANO_INICIAL} ${ANO_FINAL}`).split(' ').map(Number);
    const casas = Number(svg.getAttribute('data-casas') || 0);
    const sufixo = svg.getAttribute('data-sufixo') || '';
    const vis = visiveis(linhas, a0, a1);
    const grupos = svg.querySelectorAll('g.nn-linha-ne, g.nn-linha-ref, g.nn-linha-cmp');
    if (grupos.length !== vis.length) return;
    const porAno = new Map();
    for (let i = 0; i < vis.length; i++) {
      const circulos = grupos[i].querySelectorAll('circle');
      if (circulos.length !== vis[i].pontos.length) return;
      const doAno = new Map();
      vis[i].pontos.forEach((p) => doAno.set(p[0], (doAno.get(p[0]) || 0) + 1));
      vis[i].pontos.forEach((p, k) => {
        const ano = p[0];
        if (!porAno.has(ano)) porAno.set(ano, { x: Number(circulos[k].getAttribute('cx')), itens: [] });
        const serie = doAno.get(ano) > 1 ? ` (${p[2]})` : '';
        porAno.get(ano).itens.push({
          forte: vis[i].destaque, texto: `${vis[i].rotulo}: ${numero(p[1], casas)}${sufixo}${serie}`,
        });
      });
    }
    const anos = [...porAno.keys()].sort((a, b) => porAno.get(a).x - porAno.get(b).x);
    if (!anos.length) return;
    const largo = svg.viewBox.baseVal.width;
    const eixo = svg.viewBox.baseVal.height - BASE;
    const pxPorAno = anos.length > 1
      ? Math.abs(porAno.get(anos[anos.length - 1]).x - porAno.get(anos[0]).x) / Math.abs(anos[anos.length - 1] - anos[0])
      : 24;

    function esconder() {
      svg.querySelectorAll('.nn-dica, .nn-regua').forEach((e) => e.remove());
    }

    function mostrar(evento) {
      if (svg.classList.contains('nn-arrastando')) return;
      const ponto = pontoNoSvg(svg, evento);
      if (!ponto) return;
      let melhor = null;
      anos.forEach((ano) => {
        const distancia = Math.abs(porAno.get(ano).x - ponto.x);
        if (melhor === null || distancia < melhor.distancia) melhor = { ano, distancia };
      });
      esconder();
      if (!melhor || melhor.distancia > Math.max(pxPorAno * 0.75, 12)) return;
      const { x, itens } = porAno.get(melhor.ano);
      const ordenados = itens.filter((i) => i.forte).concat(itens.filter((i) => !i.forte));
      svg.append(no('line', { class: 'nn-regua', x1: coord(x), x2: coord(x), y1: String(TOPO), y2: String(eixo) }));
      const dica = no('g', { class: 'nn-dica', 'aria-hidden': 'true' });
      const fundo = no('rect', { class: 'nn-dica-fundo', rx: '8', x: '0', y: '0' });
      dica.append(fundo);
      const textos = [no('text', { class: 'nn-dica-ano', x: '10', y: '19' }, String(melhor.ano))];
      ordenados.forEach((item, k) => textos.push(no('text', { class: 'nn-dica-valor', x: '10', y: String(36 + k * 16) }, item.texto)));
      dica.append(...textos);
      svg.append(dica);
      const larguraDica = Math.ceil(Math.max(...textos.map((t) => t.getComputedTextLength()))) + 20;
      const alturaDica = 28 + ordenados.length * 16;
      fundo.setAttribute('width', String(larguraDica));
      fundo.setAttribute('height', String(alturaDica));
      let esquerdaDica = x + 10;
      if (esquerdaDica + larguraDica > largo - 2) esquerdaDica = Math.max(2, x - 10 - larguraDica);
      dica.setAttribute('transform', `translate(${coord(esquerdaDica)} ${TOPO})`);
    }

    svg.addEventListener('pointermove', mostrar);
    svg.addEventListener('pointerdown', mostrar);
    svg.addEventListener('pointerleave', esconder);
    svg.addEventListener('pointercancel', esconder);
  }

  /* Arrastar sobre o gráfico do Explorar escolhe um período (de ano inteiro em ano inteiro). */
  function ligarArrasto(svg, escolher) {
    const quadro = svg.nnQuadro;
    let inicio = null;
    let selecao = null;
    const limitar = (v) => Math.min(quadro.direita, Math.max(quadro.esquerda, v));

    function soltar() {
      if (selecao) selecao.remove();
      selecao = null;
      inicio = null;
      svg.classList.remove('nn-arrastando');
    }

    svg.addEventListener('pointerdown', (evento) => {
      if (evento.button !== 0) return;
      const ponto = pontoNoSvg(svg, evento);
      if (ponto) inicio = limitar(ponto.x);
    });
    svg.addEventListener('pointermove', (evento) => {
      if (inicio === null) return;
      const ponto = pontoNoSvg(svg, evento);
      if (!ponto) return;
      const atual = limitar(ponto.x);
      if (!selecao && Math.abs(atual - inicio) < 8) return;
      if (!selecao) {
        svg.classList.add('nn-arrastando');
        if (svg.setPointerCapture) svg.setPointerCapture(evento.pointerId);
        svg.querySelectorAll('.nn-dica, .nn-regua').forEach((e) => e.remove());
        selecao = no('rect', { class: 'nn-selecao', y: String(quadro.topo), height: String(quadro.eixo - quadro.topo) });
        svg.append(selecao);
      }
      selecao.setAttribute('x', coord(Math.min(inicio, atual)));
      selecao.setAttribute('width', coord(Math.abs(atual - inicio)));
    });
    svg.addEventListener('pointerup', () => {
      if (selecao) {
        const xa = Number(selecao.getAttribute('x'));
        const xb = xa + Number(selecao.getAttribute('width'));
        const de = Math.max(ANO_INICIAL, Math.round(quadro.ano(xa)));
        const ate = Math.min(ANO_FINAL - 1, Math.round(quadro.ano(xb)) - 1);
        soltar();
        if (ate - de >= 1) escolher(de, ate);
        return;
      }
      soltar();
    });
    svg.addEventListener('pointercancel', soltar);
  }

  /* --- endereço com a escolha da página (para compartilhar e voltar) ------------------------------------------ */

  function lerEndereco() {
    return new URLSearchParams(window.location.search);
  }

  function gravarEndereco(valores) {
    const params = new URLSearchParams();
    Object.entries(valores).forEach(([chave, valor]) => {
      if (valor !== null && valor !== '' && valor !== false) params.set(chave, valor === true ? '1' : String(valor));
    });
    const busca = params.toString();
    window.history.replaceState(null, '', window.location.pathname + (busca ? `?${busca}` : ''));
  }

  function temOpcao(select, valor) {
    return [...select.options].some((o) => o.value === valor);
  }

  /* --- Estados: o seletor só mostra e esconde as vistas que já estão no HTML ---------------------------------- */

  /* O mapa de calor rola de lado no celular e, enquanto há mais para a direita, a borda direita esmaece (CSS). No fim
     da rolagem a classe nn-no-fim tira o esmaecimento, para não apagar o último ano. */
  function marcarFimDosMapas() {
    document.querySelectorAll('.nn-mapa-caixa').forEach((caixa) => {
      caixa.classList.toggle('nn-no-fim', caixa.scrollLeft + caixa.clientWidth >= caixa.scrollWidth - 1);
    });
  }

  function ligarEstados() {
    const seletor = document.getElementById('sel-estado-ind');
    if (!seletor) return;
    const vistas = document.querySelectorAll('.nn-vista[data-vista]');
    const mostrar = () => {
      vistas.forEach((v) => { v.hidden = v.getAttribute('data-vista') !== seletor.value; });
      marcarFimDosMapas();
    };
    document.querySelectorAll('.nn-mapa-caixa').forEach((caixa) => {
      caixa.addEventListener('scroll', marcarFimDosMapas, { passive: true });
    });
    window.addEventListener('resize', marcarFimDosMapas);
    const pedido = lerEndereco().get('indicador');
    if (pedido && temOpcao(seletor, pedido)) seletor.value = pedido;
    mostrar();
    seletor.addEventListener('change', () => {
      mostrar();
      const padrao = [...seletor.options].find((o) => o.defaultSelected);
      gravarEndereco({ indicador: padrao && padrao.value === seletor.value ? null : seletor.value });
      medir('states-select', { indicator: seletor.value });
    });
  }

  /* --- Explorar ----------------------------------------------------------------------------------------------- */

  /* Referências claras do território (explorar.referencias); com comparação, só o Brasil, se ele não for um dos dois. */
  function territoriosDoGrafico(territorio, comparado) {
    if (comparado) return [...([territorio, comparado].includes('BR') ? [] : ['BR']), comparado, territorio];
    if (territorio === 'NE') return ['BR', territorio];
    if (territorio === 'BR' || territorio === 'BR_FORA_NE') return ['NE', territorio];
    return ['NE', 'BR', territorio];
  }

  function celula(texto, classe) {
    const td = document.createElement('td');
    td.textContent = texto;
    if (classe) td.className = classe;
    return td;
  }

  /* Os controles do zoom só fazem sentido com o redesenho, então nascem aqui; os textos vêm do HTML (data-*). */
  function montarZoom(painel) {
    const texto = (nome) => painel.getAttribute(`data-${nome}`);
    const seletorDeAno = (id, rotulo, vazio) => {
      const label = document.createElement('label');
      label.htmlFor = id;
      label.append(rotulo);
      const select = document.createElement('select');
      select.id = id;
      select.append(new Option(vazio, ''));
      for (let ano = ANO_INICIAL; ano < ANO_FINAL; ano++) select.append(new Option(String(ano), String(ano)));
      label.append(select);
      return [label, select];
    };
    const botao = (classe, rotulo) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = `nn-botao ${classe}`;
      b.textContent = rotulo;
      return b;
    };
    const [rotuloDe, zoomDe] = seletorDeAno('zoom-de', texto('de'), texto('inicio'));
    const [rotuloAte, zoomAte] = seletorDeAno('zoom-ate', texto('ate'), texto('fim'));
    const botaoAmpliar = botao('nn-zoom-y', texto('ampliar'));
    botaoAmpliar.setAttribute('aria-pressed', 'false');
    const botaoTodo = botao('nn-zoom-todo', texto('todo'));
    painel.prepend(rotuloDe, rotuloAte, botaoAmpliar, botaoTodo);
    return { zoomDe, zoomAte, botaoAmpliar, botaoTodo };
  }

  function ligarExplorar() {
    const cartao = document.getElementById('explorar-grafico');
    if (!cartao) return;
    const selIndicador = document.getElementById('sel-expl-ind');
    const selTerritorio = document.getElementById('sel-expl-terr');
    const selComparado = document.getElementById('sel-expl-terr2');
    const painel = document.getElementById('explorar-zoom');
    const { zoomDe, zoomAte, botaoAmpliar, botaoTodo } = montarZoom(painel);
    const vista = document.getElementById('explorar-vista');
    const titulo = document.getElementById('explorar-titulo');
    const faixas = JSON.parse(cartao.getAttribute('data-governos'));
    if (cartao.hasAttribute('data-rotulos')) rotulos = Object.assign(rotulos, JSON.parse(cartao.getAttribute('data-rotulos')));
    const nomes = {};
    const etiquetas = {};
    [...selTerritorio.options].forEach((o) => {
      nomes[o.value] = o.textContent;
      etiquetas[o.value] = o.getAttribute('data-etiqueta');
    });
    const inicial = {
      indicador: [...selIndicador.options].find((o) => o.defaultSelected).value,
      territorio: [...selTerritorio.options].find((o) => o.defaultSelected).value,
    };
    const cache = {};
    let pedido = 0;

    const params = lerEndereco();
    const estado = {
      indicador: temOpcao(selIndicador, params.get('indicador')) ? params.get('indicador') : selIndicador.value,
      territorio: temOpcao(selTerritorio, params.get('territorio')) ? params.get('territorio') : selTerritorio.value,
      comparado: temOpcao(selComparado, params.get('comparar')) ? params.get('comparar') : selComparado.value,
      de: temOpcao(zoomDe, params.get('de')) ? params.get('de') : '',
      ate: temOpcao(zoomAte, params.get('ate')) ? params.get('ate') : '',
      ampliar: params.get('ampliar') === '1',
    };
    if (estado.de && estado.ate && Number(estado.de) >= Number(estado.ate)) estado.ate = '';

    function configuracao() {
      const opcao = selIndicador.selectedOptions[0];
      return {
        nome: opcao.getAttribute('data-nome'), unidade: opcao.getAttribute('data-unidade'),
        casas: Number(opcao.getAttribute('data-casas')), sufixo: opcao.getAttribute('data-sufixo') || '',
      };
    }

    function comparadoValido() {
      return estado.comparado && estado.comparado !== estado.territorio ? estado.comparado : '';
    }

    function sincronizar() {
      selIndicador.value = estado.indicador;
      selTerritorio.value = estado.territorio;
      selComparado.value = estado.comparado;
      zoomDe.value = estado.de;
      zoomAte.value = estado.ate;
      const comZoom = Boolean(estado.de || estado.ate);
      if (!comZoom) estado.ampliar = false;
      botaoAmpliar.disabled = !comZoom;
      botaoAmpliar.setAttribute('aria-pressed', estado.ampliar ? 'true' : 'false');
      gravarEndereco({
        indicador: estado.indicador === inicial.indicador ? null : estado.indicador,
        territorio: estado.territorio === inicial.territorio ? null : estado.territorio,
        comparar: comparadoValido() || null, de: estado.de || null, ate: estado.ate || null, ampliar: estado.ampliar,
      });
    }

    function aviso(texto) {
      const p = document.createElement('p');
      p.className = 'nn-muted nn-sem-dados';
      p.textContent = texto;
      return p;
    }

    function tabela(linhas) {
      const doTerritorio = linhas.filter((l) => l.destaque || l.comparar);
      const linhasDaTabela = [];
      doTerritorio.forEach((l, ordem) => l.pontos.forEach((p) => linhasDaTabela.push({ p, l, ordem })));
      if (doTerritorio.length > 1) {
        /* com comparação: por ano, o território escolhido primeiro (ele é o último da lista), depois a série */
        linhasDaTabela.sort((a, b) => a.p[0] - b.p[0] || (b.l.destaque - a.l.destaque) || (a.p[2] < b.p[2] ? -1 : a.p[2] > b.p[2] ? 1 : 0));
      }
      const cfg = configuracao();
      const detalhes = document.createElement('details');
      const resumo = document.createElement('summary');
      resumo.textContent = cartao.getAttribute('data-tabela');
      const caixa = document.createElement('div');
      caixa.className = 'nn-tabela';
      const tab = document.createElement('table');
      const cabeca = document.createElement('thead');
      const linhaCabeca = document.createElement('tr');
      rotulos.colunas.map((texto, i) => [texto, i === 2 ? 'nn-num' : '']).forEach(([texto, classe]) => {
        const th = document.createElement('th');
        th.scope = 'col';
        th.textContent = texto;
        if (classe) th.className = classe;
        linhaCabeca.append(th);
      });
      cabeca.append(linhaCabeca);
      const corpo = document.createElement('tbody');
      linhasDaTabela.forEach(({ p, l }) => {
        const tr = document.createElement('tr');
        tr.append(celula(String(p[0])), celula(l.rotulo), celula(numero(p[1], cfg.casas) + cfg.sufixo, 'nn-num'), celula(p[2]));
        corpo.append(tr);
      });
      tab.append(cabeca, corpo);
      caixa.append(tab);
      detalhes.append(resumo, caixa);
      return detalhes;
    }

    function escolherPeriodo(de, ate) {
      estado.de = String(de);
      estado.ate = String(ate);
      sincronizar();
      desenhar();
    }

    /* Desenha a vista com as linhas dadas, ou com as do JSON do indicador já carregado. */
    function desenhar(linhasProntas) {
      const cfg = configuracao();
      const comparado = comparadoValido();
      titulo.textContent = `${cfg.nome}: ${nomes[estado.territorio]}${comparado ? ` × ${nomes[comparado]}` : ''} (${cfg.unidade})`;
      const linhas = linhasProntas || territoriosDoGrafico(estado.territorio, comparado).map((t) => ({
        rotulo: nomes[t], rotulo_curto: etiquetas[t], destaque: t === estado.territorio, comparar: t === comparado,
        pontos: cache[estado.indicador][t] || [],
      }));
      const principal = linhas.find((l) => l.destaque);
      const aberta = Boolean(vista.querySelector('details[open]'));
      if (!principal || !principal.pontos.length) {
        vista.replaceChildren(aviso(cartao.getAttribute('data-sem-dados')));
        return;
      }
      const periodo = {
        a0: estado.de ? Number(estado.de) : ANO_INICIAL,
        a1: estado.ate ? Number(estado.ate) + 1 : ANO_FINAL,
        ampliar: estado.ampliar,
      };
      const nomeDoGrafico = `${cfg.nome}, ${nomes[estado.territorio]}${comparado ? ` ${rotulos.e} ${nomes[comparado]}` : ''}`;
      const config = { titulo: nomeDoGrafico, casas: cfg.casas, sufixo: cfg.sufixo };
      const noPeriodo = visiveis([principal], periodo.a0, periodo.a1).length;
      const largo = noPeriodo ? grafico(linhas, config, faixas, LARGO, periodo) : null;
      const detalhes = tabela(linhas);
      detalhes.open = aberta;
      if (!largo) {
        vista.replaceChildren(aviso(cartao.getAttribute('data-sem-periodo')), detalhes);
        return;
      }
      const estreito = grafico(linhas, config, faixas, ESTREITO, periodo);
      const caixa = document.createElement('div');
      caixa.className = 'nn-graf';
      caixa.id = 'g-explorar';
      [['nn-graf-largo', largo], ['nn-graf-estreito', estreito]].forEach(([classe, svg]) => {
        const div = document.createElement('div');
        div.className = classe;
        div.append(svg);
        caixa.append(div);
      });
      vista.replaceChildren(caixa, detalhes);
      [largo, estreito].forEach((svg) => {
        ligarDica(svg);
        ligarArrasto(svg, escolherPeriodo);
      });
    }

    /* a medição da seleção (explore-select): só depois de a vista nova estar desenhada, e uma vez por escolha (quem
       troca indicador e território em seguida conta uma vez só, com os dois) */
    let selecaoPendente = false;
    let esperaDaMedida = 0;
    function selecionou() {
      selecaoPendente = true;
      carregarEDesenhar();
    }
    function desenhado() {
      if (!selecaoPendente) return;
      selecaoPendente = false;
      window.clearTimeout(esperaDaMedida);
      esperaDaMedida = window.setTimeout(() => {
        const comparado = comparadoValido();
        medir('explore-select', Object.assign(
          { indicator: estado.indicador, territory: estado.territorio }, comparado ? { compare: comparado } : {}));
      }, 800);
    }

    function carregarEDesenhar() {
      sincronizar();
      const indicador = estado.indicador;
      if (cache[indicador]) {
        desenhar();
        desenhado();
        return;
      }
      pedido += 1;
      const este = pedido;
      vista.setAttribute('aria-busy', 'true');
      fetch(`${cartao.getAttribute('data-dados')}${indicador}.json`)
        .then((resposta) => {
          if (!resposta.ok) throw new Error(String(resposta.status));
          return resposta.json();
        })
        .then((dados) => {
          cache[indicador] = dados;
          if (este === pedido && estado.indicador === indicador) {
            desenhar();
            desenhado();
          }
        })
        .catch(() => {
          if (este === pedido) vista.replaceChildren(aviso(cartao.getAttribute('data-erro')));
        })
        .finally(() => {
          if (este === pedido) vista.removeAttribute('aria-busy');
        });
    }

    selIndicador.addEventListener('change', () => { estado.indicador = selIndicador.value; selecionou(); });
    selTerritorio.addEventListener('change', () => { estado.territorio = selTerritorio.value; selecionou(); });
    selComparado.addEventListener('change', () => { estado.comparado = selComparado.value; selecionou(); });
    zoomDe.addEventListener('change', () => {
      estado.de = zoomDe.value;
      if (estado.de && estado.ate && Number(estado.de) >= Number(estado.ate)) estado.ate = '';
      carregarEDesenhar();
    });
    zoomAte.addEventListener('change', () => {
      estado.ate = zoomAte.value;
      if (estado.de && estado.ate && Number(estado.ate) <= Number(estado.de)) estado.de = '';
      carregarEDesenhar();
    });
    botaoAmpliar.addEventListener('click', () => { estado.ampliar = !estado.ampliar; carregarEDesenhar(); });
    botaoTodo.addEventListener('click', () => {
      estado.de = '';
      estado.ate = '';
      estado.ampliar = false;
      carregarEDesenhar();
    });

    painel.hidden = false;
    const svgInicial = vista.querySelector('.nn-graf-largo svg');
    const comoNoHtml = estado.indicador === inicial.indicador && estado.territorio === inicial.territorio &&
      !comparadoValido() && !estado.de && !estado.ate;
    if (comoNoHtml && svgInicial) {
      /* a vista inicial já está no HTML: redesenha com os mesmos pontos (data-pontos) só para ligar o zoom */
      sincronizar();
      const linhas = JSON.parse(svgInicial.getAttribute('data-pontos')).map((l) => Object.assign(l, { comparar: false }));
      desenhar(linhas);
    } else {
      carregarEDesenhar();
    }
  }

  /* --- mapa do Início: os 27 estados em quadrados ------------------------------------------------------------ */

  /* Sem JavaScript o mapa mostra a vista "quanto cresceu" e as abas ficam com hidden. Com ele, cada aba (botão com
     aria-pressed) troca a classe da vista no <section>, o que troca o tom e o valor dos quadrados, a legenda e o
     ranking. Passar o mouse, focar ou clicar num estado escreve o rótulo dele (nome e valores) na linha de leitura,
     que é só visual: o leitor de tela já lê o mesmo rótulo no próprio botão. A medição conta a troca de aba
     (map-tab) e o clique no estado (map-tile; Enter e espaço no botão também são clique). */
  function ligarMapa() {
    document.querySelectorAll('.nn-mosaico').forEach((bloco) => {
      const abas = bloco.querySelector('.nn-mosaico-abas');
      const leitura = bloco.querySelector('.nn-mosaico-leitura');
      if (abas) {
        const botoes = Array.from(abas.querySelectorAll('.nn-mosaico-aba'));
        botoes.forEach((botao) => {
          botao.addEventListener('click', () => {
            if (botao.getAttribute('aria-pressed') === 'true') return;
            const vista = botao.getAttribute('data-vista');
            botoes.forEach((outro) => outro.setAttribute('aria-pressed', String(outro === botao)));
            botoes.forEach((outro) => bloco.classList.remove('nn-mosaico-vista-' + outro.getAttribute('data-vista')));
            bloco.classList.add('nn-mosaico-vista-' + vista);
            medir('map-tab', { tab: vista });
          });
        });
        abas.hidden = false;
      }
      if (leitura) {
        leitura.textContent = leitura.getAttribute('data-dica') || '';
        leitura.hidden = false;
      }
      bloco.querySelectorAll('.nn-mosaico-uf').forEach((estado) => {
        const mostrar = () => {
          if (leitura) leitura.textContent = estado.getAttribute('aria-label');
        };
        estado.addEventListener('mouseenter', mostrar);
        estado.addEventListener('focus', mostrar);
        estado.addEventListener('click', () => {
          mostrar();
          medir('map-tile', { uf: estado.getAttribute('data-uf') });
        });
      });
    });
  }

  /* --- modal "Ampliar" ---------------------------------------------------------------------------------------- */

  /* Cada gráfico do Início (e da Inovação) tem um <template class="nn-ampliado"> com o gráfico grande (1100 x 520,
     pronto do Python) e o contexto dele. Os templates não vêm no HTML da página: ficam em /ampliados/<idioma>-<página>.json
     (o data-ampliados do <dialog>, com ?v=), que este código pede uma vez, na primeira abertura ou antes, quando o mouse
     ou o foco chega num botão Ampliar. O botão Ampliar (e, com mouse ou caneta, o próprio gráfico) clona o template no
     único <dialog>, abre com showModal() e liga a dica de valor ao SVG grande, como nos gráficos da página. Fecha pelo
     botão, por Esc e por clique fora; o foco volta ao botão que abriu. Sem JavaScript os botões ficam com hidden. */
  function ligarAmpliar() {
    /* os <dialog> das épocas (Como chegamos) e do autor também são .nn-modal, mas são de ligarHistoria e ligarAutor:
       este esvazia o corpo ao fechar */
    const dialogo = document.querySelector('dialog.nn-modal:not(.nn-modal-historia):not(.nn-modal-autor)');
    if (!dialogo || typeof dialogo.showModal !== 'function') return;
    const corpo = dialogo.querySelector('.nn-modal-corpo');
    const endereco = dialogo.getAttribute('data-ampliados');
    let origem = null;
    let pedido = null;
    let abrindo = false;

    /* o JSON dos templates, pedido uma vez; um pedido que falhou pode ser refeito no próximo clique */
    function modelos() {
      if (!pedido) {
        pedido = fetch(endereco, { credentials: 'same-origin' })
          .then((resposta) => {
            if (!resposta.ok) throw new Error('ampliados: ' + resposta.status + ' ' + endereco);
            return resposta.json();
          })
          .catch((erro) => {
            pedido = null;
            throw erro;
          });
      }
      return pedido;
    }

    function mostrar(botao, html) {
      if (dialogo.open || typeof html !== 'string') return;
      const modelo = document.createElement('template');
      modelo.innerHTML = html;
      origem = botao;
      corpo.replaceChildren(modelo.content.cloneNode(true));
      const titulo = corpo.querySelector('.nn-modal-titulo');
      if (titulo) titulo.id = dialogo.getAttribute('aria-labelledby');
      dialogo.showModal();
      dialogo.scrollTop = 0;
      corpo.querySelectorAll('svg[data-pontos]').forEach(ligarDica);
    }

    /* o clique no botão a medição conta pelo data-umami-event dele; o clique no próprio gráfico (`peloGrafico`), aqui */
    function abrir(botao, peloGrafico) {
      if (dialogo.open || abrindo || !endereco) return;
      if (peloGrafico) {
        medir('chart-enlarge', { chart: botao.getAttribute('data-umami-event-chart'), page: paginaAtual() });
      }
      abrindo = true;
      botao.setAttribute('aria-busy', 'true');
      modelos()
        .then((todos) => mostrar(botao, todos[botao.getAttribute('data-ampliado')]))
        .catch((erro) => console.error(erro))
        .finally(() => {
          abrindo = false;
          botao.removeAttribute('aria-busy');
        });
    }

    function adiantar() {
      if (endereco) modelos().catch(() => {});
    }

    dialogo.querySelector('.nn-modal-fechar').addEventListener('click', () => dialogo.close());
    dialogo.addEventListener('click', (evento) => {
      if (evento.target === dialogo) dialogo.close(); /* o fundo escurecido é o próprio <dialog> */
    });
    dialogo.addEventListener('close', () => {
      corpo.replaceChildren();
      if (origem) origem.focus();
      origem = null;
    });

    document.querySelectorAll('.nn-ampliar').forEach((botao) => {
      botao.hidden = false;
      botao.addEventListener('click', () => abrir(botao));
      botao.addEventListener('pointerenter', adiantar, { once: true });
      botao.addEventListener('focus', adiantar, { once: true });
      const grafico = botao.closest('.nn-grafico');
      const caixa = grafico && grafico.querySelector('.nn-graf');
      if (!caixa) return;
      /* no toque, tocar no gráfico mostra o valor (ligarDica); só o botão abre o modal */
      let toque = false;
      caixa.classList.add('nn-clicavel');
      caixa.addEventListener('pointerenter', adiantar, { once: true });
      caixa.addEventListener('pointerdown', (evento) => { toque = evento.pointerType === 'touch'; });
      caixa.addEventListener('click', () => { if (!toque) abrir(botao, true); });
    });
  }

  /* --- modal "Sobre o autor" ------------------------------------------------------------------------------------ */

  /* O conteúdo já vem no HTML, dentro do <dialog class="nn-modal-autor"> de toda página; aqui só se abre e se fecha. O
     gatilho do rodapé é um link para /sobre/#autor, que é o que vale sem JavaScript: com ele, o clique abre o modal em
     vez de navegar. showModal() prende o foco e fecha com Esc; o X e o clique fora também fecham, e o foco volta ao
     gatilho que abriu. */
  function ligarAutor() {
    const dialogo = document.querySelector('dialog.nn-modal-autor');
    const gatilhos = document.querySelectorAll('.nn-autor-abrir');
    if (!dialogo || typeof dialogo.showModal !== 'function' || !gatilhos.length) return;
    let origem = null;
    gatilhos.forEach((gatilho) => {
      gatilho.addEventListener('click', (evento) => {
        evento.preventDefault();
        if (dialogo.open) return;
        origem = gatilho;
        dialogo.showModal();
        dialogo.scrollTop = 0;
      });
    });
    dialogo.querySelector('.nn-modal-fechar').addEventListener('click', () => dialogo.close());
    dialogo.addEventListener('click', (evento) => {
      if (evento.target === dialogo) dialogo.close(); /* o fundo escurecido é o próprio <dialog> */
    });
    dialogo.addEventListener('close', () => {
      if (origem) origem.focus();
      origem = null;
    });
  }

  /* --- Como chegamos: linha do tempo arrastável e o modal de cada época --------------------------------------- */

  /* Sem JavaScript, a lista vertical das épocas com o artigo completo de cada uma é a página. Com ele (classe nn-js no
     <html>), os artigos saem da lista; acima de 900 px a lista vira uma faixa horizontal com scroll-snap, que o mouse
     arrasta e os botões ‹ › rolam de um cartão em um; as setas, Home e End passam o foco entre os cartões.

     O modal é o único <dialog class="nn-modal-historia">: abrir uma época MOVE o <article> dela para lá e fechar o
     devolve ao seu <li> (nada é clonado, então nenhum id se repete). O endereço acompanha: o cartão e o marco abrem com
     pushState (#<época> ou #m<ano>), anterior e próxima trocam com replaceState, e o voltar do navegador fecha. Fechar
     pelo X, pelo Esc ou por fora volta a entrada criada pelo cartão (ou limpa o endereço de quem chegou com ele). Os ids
     começam com dígito: só getElementById e CSS.escape, nunca um seletor '#1763'. */
  const LIMIAR_DO_CLIQUE = 6; /* px: até aqui é clique; a partir daqui, arrasto */

  function ligarHistoria() {
    const faixa = document.querySelector('ol.nn-linha-tempo');
    const dialogo = document.querySelector('dialog.nn-modal-historia');
    if (!faixa || !dialogo || typeof dialogo.showModal !== 'function') {
      /* sem <dialog> (ou fora desta página), nada abre as épocas: a lista com os artigos tem de ficar à vista */
      document.documentElement.classList.remove('nn-js');
      return;
    }
    const corpo = dialogo.querySelector('.nn-modal-corpo');
    const largo = window.matchMedia('(min-width: 901px)');
    const movimento = window.matchMedia('(prefers-reduced-motion: no-preference)');
    let aberta = null; /* o <li> da época cujo artigo está no modal */
    let empurrado = false; /* a abertura criou uma entrada no histórico, que o fechar desfaz */
    let pelaNavegacao = false; /* o modal fecha porque o endereço mudou: o histórico já está certo */
    let fechando = false; /* o fechar chamou history.back(): o popstate que vem daí não pode reabrir uma época */

    faixa.querySelectorAll('.nn-epoca-abrir').forEach((botao) => botao.setAttribute('aria-haspopup', 'dialog')); /* sem JS o cartão não abre nada */

    const epocas = () => [...faixa.querySelectorAll(':scope > li.nn-epoca')];
    const cartao = (li) => li.querySelector('.nn-epoca-abrir');
    const artigoDe = (li) => (li === aberta ? corpo.querySelector('.nn-epoca-conteudo') : li.querySelector(':scope > .nn-epoca-conteudo'));
    const marcoDe = (li, ano) => {
      const artigo = artigoDe(li);
      return artigo && artigo.querySelector('#' + CSS.escape('m' + ano));
    };

    /* `#1654` (época), `#m1763` ou `#1763` (marco): { li, marco }, ou null para qualquer outro endereço */
    function resolver(hash) {
      let nome = '';
      try {
        nome = decodeURIComponent(hash.replace(/^#/, ''));
      } catch (erro) {
        return null; /* % solto no endereço */
      }
      if (!nome) return null;
      for (const id of [nome, 'm' + nome]) {
        const alvo = document.getElementById(id);
        if (!alvo) continue;
        if (alvo.matches('li.nn-epoca') && alvo.parentElement === faixa) return { li: alvo, marco: null };
        if (alvo.matches('.nn-epoca-marcos li')) {
          const li = corpo.contains(alvo) ? aberta : alvo.closest('li.nn-epoca');
          if (li && li.parentElement === faixa) return { li, marco: alvo };
        }
      }
      return null;
    }

    function devolver() {
      const artigo = corpo.querySelector('.nn-epoca-conteudo');
      if (aberta && artigo) aberta.append(artigo);
      corpo.replaceChildren();
    }

    /* põe a época no modal (abrindo-o, se preciso) e rola até o marco ou até o topo */
    function mostrar(li, marco) {
      const artigo = artigoDe(li);
      if (!artigo) return;
      if (li !== aberta) {
        devolver();
        aberta = li;
        corpo.append(artigo);
        medir('era-open', { era: li.id });
      }
      dialogo.setAttribute('aria-labelledby', artigo.getAttribute('aria-labelledby'));
      artigo.querySelectorAll('.nn-marco-alvo').forEach((m) => m.classList.remove('nn-marco-alvo'));
      if (!dialogo.open) dialogo.showModal();
      if (marco) {
        marco.classList.add('nn-marco-alvo');
        const rolar = () => {
          if (!dialogo.open || !marco.classList.contains('nn-marco-alvo')) return;
          const topo = marco.getBoundingClientRect().top - dialogo.getBoundingClientRect().top;
          const fechar = dialogo.querySelector('.nn-modal-topo');
          dialogo.scrollTop += topo - (fechar ? fechar.offsetHeight : 0) - 16; /* abaixo do Fechar, preso no topo, com folga */
        };
        rolar();
        /* a fonte serifada pode chegar depois e mudar a altura do texto acima do marco: rola de novo quando ela chega */
        if (document.fonts && document.fonts.status !== 'loaded') document.fonts.ready.then(rolar);
      } else {
        dialogo.scrollTop = 0;
      }
    }

    function abrir(li, marco) {
      fechando = false;
      mostrar(li, marco);
      const hash = '#' + (marco ? marco.id : li.id);
      if (location.hash !== hash) {
        history.pushState(history.state, '', hash);
        empurrado = true;
      }
    }

    /* o endereço mudou por fora (voltar, avançar, hash digitado): o modal segue o endereço */
    function seguirEndereco() {
      const alvo = resolver(location.hash);
      if (fechando) { /* é o history.back() do fechar: a entrada em que ele caiu pode ainda citar uma época (#1530 -> #1808 -> Esc) */
        fechando = false;
        if (alvo && !dialogo.open) history.replaceState(history.state, '', location.pathname + location.search);
        return;
      }
      if (alvo) {
        if (!dialogo.open) empurrado = true; /* a entrada anterior é a página sem época */
        if (!dialogo.open || alvo.li !== aberta || alvo.marco) mostrar(alvo.li, alvo.marco);
      } else if (dialogo.open) {
        pelaNavegacao = true;
        dialogo.close();
      }
    }

    dialogo.querySelector('.nn-modal-fechar').addEventListener('click', () => dialogo.close());
    dialogo.addEventListener('click', (evento) => {
      if (evento.target === dialogo) dialogo.close(); /* o fundo escurecido é o próprio <dialog> */
    });
    dialogo.addEventListener('close', () => {
      if (dialogo.open) { /* o evento close vem numa tarefa depois do close(): o endereço já reabriu outra época */
        pelaNavegacao = false;
        return;
      }
      const li = aberta;
      devolver();
      aberta = null;
      if (!pelaNavegacao) {
        if (empurrado) {
          fechando = true;
          history.back();
        } else if (location.hash) history.replaceState(history.state, '', location.pathname + location.search);
      }
      empurrado = false;
      pelaNavegacao = false;
      if (li) cartao(li).focus();
    });
    /* anterior e próxima: a outra época no mesmo modal, sem nova entrada no histórico */
    corpo.addEventListener('click', (evento) => {
      const link = evento.target.closest('.nn-epoca-nav a[data-epoca]');
      const li = link && document.getElementById(link.getAttribute('data-epoca'));
      if (!li || !li.matches('li.nn-epoca') || li.parentElement !== faixa) return;
      evento.preventDefault();
      mostrar(li, null);
      history.replaceState(history.state, '', '#' + li.id);
      const titulo = corpo.querySelector('.nn-epoca-titulo');
      if (titulo) {
        titulo.setAttribute('tabindex', '-1');
        titulo.focus({ preventScroll: true });
      }
    });
    window.addEventListener('popstate', seguirEndereco);
    window.addEventListener('hashchange', seguirEndereco);

    /* cartão e marco; o clique que encerra um arrasto é engolido antes de chegar a eles */
    let arrasto = null;
    let engolir = false;
    faixa.addEventListener('click', (evento) => {
      if (!engolir) return;
      engolir = false;
      evento.preventDefault();
      evento.stopPropagation();
    }, true);
    faixa.addEventListener('click', (evento) => {
      const botao = evento.target.closest('.nn-epoca-abrir');
      const marco = evento.target.closest('a.nn-marco');
      const li = (botao || marco) && (botao || marco).closest('li.nn-epoca');
      if (!li) return;
      if (botao) {
        abrir(li, null);
      } else {
        const alvo = marcoDe(li, marco.getAttribute('data-marco'));
        if (!alvo) return;
        evento.preventDefault();
        abrir(li, alvo);
      }
    });

    /* teclado: setas, Home e End passam o foco de cartão em cartão (na lista vertical, até 900 px, também ↑ e ↓) */
    faixa.addEventListener('keydown', (evento) => {
      const atual = evento.target.closest('.nn-epoca-abrir');
      if (!atual || evento.altKey || evento.ctrlKey || evento.metaKey) return;
      const cartoes = epocas().map(cartao);
      const i = cartoes.indexOf(atual);
      const teclas = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: cartoes.length - 1 };
      if (!largo.matches) Object.assign(teclas, { ArrowDown: i + 1, ArrowUp: i - 1 });
      const destino = teclas[evento.key];
      if (destino === undefined || !cartoes[destino]) return; /* sem cartão para onde ir, a seta rola a página como sempre */
      evento.preventDefault();
      cartoes[destino].focus();
    });

    /* arrasto com mouse ou caneta, só na faixa horizontal; no toque, a rolagem nativa da faixa já basta */
    faixa.addEventListener('dragstart', (evento) => evento.preventDefault()); /* links e imagens não viram arrasto do navegador */
    faixa.addEventListener('pointerdown', (evento) => {
      if (!largo.matches || evento.pointerType === 'touch' || evento.button !== 0) return;
      arrasto = { id: evento.pointerId, x: evento.clientX, inicio: faixa.scrollLeft, andou: false };
    });
    faixa.addEventListener('pointermove', (evento) => {
      if (!arrasto || evento.pointerId !== arrasto.id) return;
      if ((evento.buttons & 1) === 0) { /* o botão foi solto fora da faixa (antes da captura): o arrasto acabou */
        largar();
        return;
      }
      const dx = evento.clientX - arrasto.x;
      if (!arrasto.andou) {
        if (Math.abs(dx) < LIMIAR_DO_CLIQUE) return;
        arrasto.andou = true;
        faixa.classList.add('nn-arrastando'); /* sem snap e sem seleção de texto enquanto arrasta */
        faixa.setPointerCapture(evento.pointerId); /* só agora: antes disso o clique tem de chegar ao cartão */
        const selecao = window.getSelection();
        if (selecao) selecao.removeAllRanges();
      }
      faixa.scrollLeft = arrasto.inicio - dx;
    });
    function largar() {
      faixa.classList.remove('nn-arrastando');
      arrasto = null;
    }
    const soltar = (evento) => {
      if (!arrasto || evento.pointerId !== arrasto.id) return;
      if (arrasto.andou && evento.type === 'pointerup') {
        engolir = true; /* o click vem logo depois do pointerup, na mesma tarefa */
        window.setTimeout(() => { engolir = false; }, 0);
      }
      largar();
    };
    /* na janela, não na faixa: o botão pode ser solto fora dela antes de o arrasto passar de 6 px (sem captura ainda) */
    window.addEventListener('pointerup', soltar);
    window.addEventListener('pointercancel', soltar);

    /* botões ‹ › nas pontas da faixa: uma moldura em volta da lista, só com JavaScript */
    const moldura = document.createElement('div');
    moldura.className = 'nn-faixa';
    const seta = (classe, rotulo, sinal, lado) => {
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.className = 'nn-faixa-seta ' + classe;
      botao.setAttribute('aria-label', rotulo);
      const desenho = document.createElement('span');
      desenho.setAttribute('aria-hidden', 'true');
      desenho.textContent = sinal;
      botao.append(desenho);
      botao.addEventListener('click', () => {
        if (botao.getAttribute('aria-disabled') === 'true') return;
        const primeira = faixa.querySelector(':scope > li.nn-epoca');
        const passo = primeira.getBoundingClientRect().width + (parseFloat(getComputedStyle(faixa).columnGap) || 0);
        faixa.scrollBy({ left: lado * passo, behavior: movimento.matches ? 'smooth' : 'auto' });
      });
      return botao;
    };
    const anterior = seta('nn-faixa-anterior', faixa.getAttribute('data-anteriores') || 'Épocas anteriores', '‹', -1);
    const proxima = seta('nn-faixa-proxima', faixa.getAttribute('data-proximas') || 'Próximas épocas', '›', 1);
    faixa.before(moldura);
    moldura.append(anterior, faixa, proxima);
    const marcarPontas = () => {
      const fim = faixa.scrollWidth - faixa.clientWidth;
      anterior.setAttribute('aria-disabled', String(faixa.scrollLeft <= 1));
      proxima.setAttribute('aria-disabled', String(faixa.scrollLeft >= fim - 1));
    };
    faixa.addEventListener('scroll', marcarPontas, { passive: true });
    window.addEventListener('resize', marcarPontas);
    marcarPontas();

    /* quem chega com o endereço de uma época vê o modal dela; fechar só limpa o endereço */
    const inicial = resolver(location.hash);
    if (inicial) mostrar(inicial.li, inicial.marco);
  }

  /* --- menu do alto ------------------------------------------------------------------------------------------- */

  /* Histórias e Dados (e, no celular, a gaveta) são <details>: abrem e fecham sem JavaScript, e o atributo name deixa
     um grupo aberto por vez onde ele já vale. Aqui: Esc fecha o que estiver aberto e devolve o foco ao summary, o
     clique fora fecha, e um grupo aberto fecha o outro também onde o name ainda não vale. */
  function ligarMenu() {
    const menu = document.querySelector('.nn-menu');
    if (!menu) return;
    const topo = menu.closest('.nn-topo');
    const grupos = [...topo.querySelectorAll('.nn-menu-grupo, .nn-menu-movel')];
    document.addEventListener('keydown', (evento) => {
      if (evento.key !== 'Escape') return;
      const abertos = grupos.filter((d) => d.open);
      if (!abertos.length) return;
      abertos.forEach((d) => { d.open = false; });
      abertos[0].querySelector(':scope > summary').focus();
    });
    document.addEventListener('click', (evento) => {
      grupos.forEach((d) => { if (d.open && !d.contains(evento.target)) d.open = false; });
    });
    topo.querySelectorAll('details[name]').forEach((d) => {
      d.addEventListener('toggle', () => {
        if (!d.open) return;
        topo.querySelectorAll('details[name]').forEach((outro) => {
          if (outro !== d && outro.open && outro.getAttribute('name') === d.getAttribute('name')) outro.open = false;
        });
      });
    });
  }

  /* --- Início: o menu lateral das perguntas ------------------------------------------------------------------- */

  /* Sem JavaScript o menu fica sempre à vista e os links são âncoras. Com ele (nn-indice-ligado), o menu aparece
     depois que o placar sai da tela (nn-indice-visivel) e o item da pergunta em leitura ganha aria-current; na faixa
     de atalhos (até 1100 px) a pílula dela rola para dentro da vista. A posição sai do scroll (passive), um cálculo
     por quadro, sem setInterval. */
  function ligarIndice() {
    const indice = document.querySelector('.nn-indice');
    if (!indice) return;
    const placar = document.querySelector('.nn-placar');
    const links = [...indice.querySelectorAll('a[href^="#q-"]')];
    const capitulos = links.map((a) => document.getElementById(a.getAttribute('href').slice(1)));
    const faixa = window.matchMedia('(max-width: 1100px)');
    const movimento = window.matchMedia('(prefers-reduced-motion: no-preference)');
    let atual = -1;
    let pedido = false;

    function marcar() {
      pedido = false;
      const linha = window.innerHeight * 0.3;
      let lendo = 0;
      capitulos.forEach((capitulo, i) => {
        if (capitulo && capitulo.getBoundingClientRect().top <= linha) lendo = i;
      });
      if (lendo !== atual) {
        links.forEach((a, i) => {
          if (i === lendo) a.setAttribute('aria-current', 'true');
          else a.removeAttribute('aria-current');
        });
        if (faixa.matches && atual !== -1 && indice.scrollWidth > indice.clientWidth) {
          indice.scrollTo({ left: links[lendo].offsetLeft - 16, behavior: movimento.matches ? 'smooth' : 'auto' });
        }
        atual = lendo;
      }
      indice.classList.toggle('nn-indice-visivel', !placar || placar.getBoundingClientRect().bottom < 80);
    }

    function pedir() {
      if (pedido) return;
      pedido = true;
      window.requestAnimationFrame(marcar);
    }

    indice.classList.add('nn-indice-ligado');
    marcar();
    window.addEventListener('scroll', pedir, { passive: true });
    window.addEventListener('resize', pedir);
  }

  /* --- voltar ao topo ----------------------------------------------------------------------------------------- */

  /* Sem JavaScript, o link href="#" sempre à vista. Com ele, o botão aparece depois de 80% de uma tela, o anel mostra
     quanto da página já foi lido (stroke-dashoffset pelo CSSOM: a CSP barra o atributo style no HTML, não isto), some
     enquanto o rodapé está na tela e rola suave até o alto (na hora, com movimento reduzido), levando o foco à marca. */
  function ligarVoltar() {
    const botao = document.querySelector('.nn-voltar');
    if (!botao) return;
    const anel = botao.querySelector('.nn-voltar-progresso');
    const volta = 2 * Math.PI * Number(anel.getAttribute('r'));
    const reduzido = window.matchMedia('(prefers-reduced-motion: reduce)');
    let pedido = false;
    anel.style.strokeDasharray = String(volta);

    function atualizar() {
      pedido = false;
      const raiz = document.documentElement;
      const maximo = raiz.scrollHeight - window.innerHeight;
      const lido = maximo > 0 ? Math.min(1, window.scrollY / maximo) : 0;
      anel.style.strokeDashoffset = String(volta * (1 - lido));
      botao.classList.toggle('nn-voltar-visivel', window.scrollY > window.innerHeight * 0.8);
    }

    function pedir() {
      if (pedido) return;
      pedido = true;
      window.requestAnimationFrame(atualizar);
    }

    const rodape = document.querySelector('.nn-rodape');
    if (rodape && 'IntersectionObserver' in window) {
      new IntersectionObserver((entradas) => {
        entradas.forEach((entrada) => botao.classList.toggle('nn-voltar-no-rodape', entrada.isIntersecting));
      }).observe(rodape);
    }
    botao.addEventListener('click', (evento) => {
      evento.preventDefault();
      window.scrollTo({ top: 0, behavior: reduzido.matches ? 'auto' : 'smooth' });
      const marca = document.querySelector('.nn-marca');
      if (marca) marca.focus({ preventScroll: true });
    });
    botao.classList.add('nn-voltar-ligado');
    atualizar();
    window.addEventListener('scroll', pedir, { passive: true });
    window.addEventListener('resize', pedir);
  }

  /* --- medição: as seções lidas ------------------------------------------------------------------------------- */

  /* O "mapa de calor" por seção, sem gravar sessão: cada capítulo ou bloco conta uma vez por visita (scroll-depth),
     quando metade dele fica à vista (ou, se ele é mais alto que a tela, quando ocupa metade da tela). Liga no load,
     depois do script do Umami (defer, depois do site.js); sem ele, nada é observado. */
  const SECOES_LIDAS = 'main .nn-capitulo[id], main .nn-mosaico, main .nn-placar, main .nn-chamada-historia, main .nn-hist-bloco, ' +
    'main .nn-hist-linha, main #sobre > article[id]';

  function nomeDaSecao(secao) {
    return secao.id || (secao.getAttribute('aria-labelledby') || '').replace(/^titulo-/, '');
  }

  function ligarLeitura() {
    if (!window.umami || !('IntersectionObserver' in window)) return;
    const pagina = paginaAtual();
    const limiares = Array.from({ length: 21 }, (_, i) => i / 20);
    const observador = new IntersectionObserver((entradas) => {
      entradas.forEach((entrada) => {
        if (!entrada.isIntersecting) return;
        const metade = Math.min(entrada.boundingClientRect.height, window.innerHeight) / 2;
        if (metade <= 0 || entrada.intersectionRect.height < metade) return;
        observador.unobserve(entrada.target);
        medir('scroll-depth', { page: pagina, section: nomeDaSecao(entrada.target) });
      });
    }, { threshold: limiares });
    document.querySelectorAll(SECOES_LIDAS).forEach((secao) => {
      if (nomeDaSecao(secao)) observador.observe(secao);
    });
  }

  /* --- movimento ---------------------------------------------------------------------------------------------- */

  function abaixoDaDobra(elemento) {
    const caixa = elemento.getBoundingClientRect();
    return caixa.height > 0 && caixa.top > window.innerHeight;
  }

  /* Seções que entram ao rolar e linhas que se desenham ao aparecer. Só o que está fora da tela ao abrir a página
     ganha o estado inicial, para nada piscar; o estado inicial só existe no CSS de prefers-reduced-motion:
     no-preference. */
  function animarAoRolar() {
    const observador = new IntersectionObserver((entradas) => {
      entradas.forEach((entrada) => {
        if (!entrada.isIntersecting) return;
        entrada.target.classList.add('nn-visivel');
        observador.unobserve(entrada.target);
      });
    }, { rootMargin: '0px 0px -10% 0px' });
    document.querySelectorAll('main .nn-card, main .nn-cartao-link, main .nn-legenda').forEach((elemento) => {
      if (!abaixoDaDobra(elemento)) return;
      elemento.classList.add('nn-entra');
      observador.observe(elemento);
    });
    document.querySelectorAll('#resumo .nn-graf').forEach((caixa) => {
      if (!abaixoDaDobra(caixa)) return;
      caixa.querySelectorAll('.nn-linha-ne path, .nn-linha-ref path').forEach((p) => p.setAttribute('pathLength', '1'));
      caixa.classList.add('nn-desenha');
      observador.observe(caixa);
    });
  }

  /* Números da abertura (texto do hero e faixa de números, com as comparações) contando até o valor que já está
     escrito no HTML. */
  const TEXTOS_COM_NUMEROS = '.nn-hero-intro, .nn-numero-comparacao, .nn-numero-valor';
  /* número com decimais no padrão do idioma: 38,8% e 1.234,5 no português; 38.8% e 1,234.5 no inglês */
  const NUMERO_COM_DECIMAIS = IDIOMA === 'en' ? /(\d{1,3}(?:,\d{3})*\.\d+%?)/ : /(\d{1,3}(?:\.\d{3})*,\d+%?)/;
  const [MILHAR, DECIMAL] = IDIOMA === 'en' ? [',', '.'] : ['.', ','];

  function contarNumeros() {
    const alvos = [];
    document.querySelectorAll(TEXTOS_COM_NUMEROS).forEach((paragrafo) => {
      const caminhante = document.createTreeWalker(paragrafo, NodeFilter.SHOW_TEXT);
      const textos = [];
      while (caminhante.nextNode()) textos.push(caminhante.currentNode);
      textos.forEach((texto) => {
        const partes = texto.data.split(NUMERO_COM_DECIMAIS);
        if (partes.length < 2) return;
        const pedaco = document.createDocumentFragment();
        partes.forEach((parte, i) => {
          if (i % 2) {
            const span = document.createElement('span');
            span.className = 'nn-conta';
            span.textContent = parte;
            pedaco.append(span);
            alvos.push(span);
          } else if (parte) {
            pedaco.append(parte);
          }
        });
        texto.replaceWith(pedaco);
      });
    });
    if (!alvos.length) return;
    const duracao = 1200;
    const contar = (span) => {
      const final = span.textContent;
      const sufixo = final.endsWith('%') ? '%' : '';
      const corpo = final.slice(0, final.length - sufixo.length);
      const casas = corpo.split(DECIMAL)[1].length;
      const valor = Number(corpo.split(MILHAR).join('').replace(DECIMAL, '.'));
      const comeco = performance.now();
      const passo = (agora) => {
        const t = Math.min(1, (agora - comeco) / duracao);
        if (t >= 1) {
          span.textContent = final;
          return;
        }
        span.textContent = numero(valor * (1 - (1 - t) ** 3), casas) + sufixo;
        window.requestAnimationFrame(passo);
      };
      window.requestAnimationFrame(passo);
    };
    const observador = new IntersectionObserver((entradas) => {
      entradas.forEach((entrada) => {
        if (!entrada.isIntersecting) return;
        observador.unobserve(entrada.target);
        entrada.target.querySelectorAll('.nn-conta').forEach(contar);
      });
    });
    document.querySelectorAll(TEXTOS_COM_NUMEROS).forEach((p) => observador.observe(p));
  }

  /* --- início ------------------------------------------------------------------------------------------------- */

  /* no Node (teste da formatação), só exporta; no navegador, liga a página */
  if (typeof module === 'object' && module.exports) module.exports = { numero };
  if (typeof document === 'undefined') return;

  /* A classe nn-js (o CSS esconde os artigos das épocas na lista e liga o que só existe com JS) vem do nn-js.js, um
     script pequeno e sem defer no <head> da página Como chegamos: aqui, depois do primeiro desenho, seria tarde. */

  /* cada ligação é isolada: se uma falha, as outras seguem e a página não perde o que já funcionava */
  function tentar(ligar) {
    try {
      ligar();
    } catch (erro) {
      console.error(erro);
    }
  }

  function iniciar() {
    tentar(ligarMenu);
    tentar(ligarIndice);
    tentar(ligarVoltar);
    tentar(() => document.querySelectorAll('.nn-graf svg[data-pontos]').forEach(ligarDica));
    tentar(ligarAmpliar);
    tentar(ligarMapa);
    tentar(ligarAutor);
    tentar(() => {
      try {
        ligarHistoria();
      } catch (erro) {
        document.documentElement.classList.remove('nn-js'); /* ligada pela metade: o conteúdo tem de ficar à vista */
        throw erro;
      }
    });
    tentar(ligarEstados);
    tentar(ligarExplorar);
    tentar(() => {
      const movimento = window.matchMedia('(prefers-reduced-motion: no-preference)').matches;
      if (movimento && 'IntersectionObserver' in window) {
        animarAoRolar();
        contarNumeros();
      }
    });
    const comecarLeitura = () => tentar(ligarLeitura);
    if (document.readyState === 'complete') comecarLeitura();
    else window.addEventListener('load', comecarLeitura, { once: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
}());
