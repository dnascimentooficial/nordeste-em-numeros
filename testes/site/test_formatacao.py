from nordeste.site.formatacao import escala_auto, numero


def test_numero_formato_brasileiro():
    assert numero(1234.5, 1) == "1.234,5"
    assert numero(0.5032, 3) == "0,503"
    assert numero(1234567.891, 0) == "1.234.568"


def test_numero_nao_mostra_zero_negativo():
    assert numero(-0.04, 1) == "0,0"
    assert numero(-1.5, 1) == "-1,5"


def test_escala_auto():
    assert escala_auto(2186521) == "2,19 mi"
    assert escala_auto(403431) == "403 mil"


def test_por_extenso_de_zero_a_dez_e_algarismo_acima():
    from nordeste.site.formatacao import por_extenso
    assert por_extenso(5, "pt") == "cinco" and por_extenso(3, "pt") == "três" and por_extenso(10, "pt") == "dez"
    assert por_extenso(5, "en") == "five" and por_extenso(0, "en") == "zero"
    assert por_extenso(11, "pt") == "11" and por_extenso(1200, "en") == "1,200" and por_extenso(2.5, "pt") == "2"
