"""Cores do tema white label: extração a partir do logo e derivação das
variações usadas na interface (contraste mínimo de 4,5:1 garantido)."""

import re

from PIL import Image

COR_PRIMARIA_PADRAO = "#1a1a1a"
COR_SECUNDARIA_PADRAO = "#8B7355"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Fundo da barra lateral/botões é a cor primária com texto claro: acima
# desta luminância relativa a cor é escurecida. 0,105 garante 4,5:1 até
# para o texto dos itens inativos da barra lateral (branco a 80%,
# OPACIDADE_TEXTO_INATIVO), no pior matiz.
LUMINANCIA_MAXIMA_PRIMARIA = 0.105
OPACIDADE_TEXTO_INATIVO = 0.8
# A secundária vira texto/link sobre branco, papel quente e areia; 0,14
# garante 4,5:1 sobre a areia (#ede8e0), a mais escura das três.
LUMINANCIA_MAXIMA_SECUNDARIA = 0.14


def hex_valido(valor):
    return bool(valor) and bool(_HEX.match(valor))


def hex_para_rgb(valor):
    valor = valor.lstrip("#")
    return tuple(int(valor[i:i + 2], 16) for i in (0, 2, 4))


def rgb_para_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c))) for c in rgb))


def luminancia(rgb):
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    """Razão de contraste WCAG entre duas cores RGB."""
    clara, escura = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (clara + 0.05) / (escura + 0.05)


def misturar(frente, fundo, opacidade):
    """Cor resultante de `frente` com `opacidade` sobre `fundo`."""
    return tuple(f * opacidade + b * (1 - opacidade) for f, b in zip(frente, fundo))


def escurecer_ate_contraste(rgb, maximo=LUMINANCIA_MAXIMA_PRIMARIA):
    """Escurece a cor (mantendo o matiz) até a luminância `maximo`."""
    fator = 1.0
    while luminancia(tuple(c * fator for c in rgb)) > maximo and fator > 0.01:
        fator -= 0.01
    return tuple(c * fator for c in rgb)


def clarear(rgb, quantidade=0.12):
    return tuple(c + (255 - c) * quantidade for c in rgb)


def _distancia(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def cores_predominantes(arquivo, quantidade=2):
    """As cores mais frequentes do logo (hex), ignorando fundo
    transparente e branco/quase branco. Vazio se não houver cor útil."""
    imagem = Image.open(arquivo)
    imagem.thumbnail((96, 96))
    rgba = imagem.convert("RGBA")
    pixels = [(r, g, b) for r, g, b, a in rgba.getdata() if a >= 128]
    if not pixels:
        return []
    reduzida = Image.new("RGB", (len(pixels), 1))
    reduzida.putdata(pixels)
    paleta = reduzida.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    cores = paleta.convert("RGB").getcolors(maxcolors=len(pixels)) or []
    candidatas = [
        cor for _, cor in sorted(cores, key=lambda item: -item[0])
        if min(cor) < 225
    ]
    escolhidas = []
    for cor in candidatas:
        if all(_distancia(cor, outra) > 60 for outra in escolhidas):
            escolhidas.append(cor)
        if len(escolhidas) == quantidade:
            break
    return [rgb_para_hex(cor) for cor in escolhidas]


def _rgb_css(rgb):
    return " ".join(str(round(c)) for c in rgb)


def tema(cor_primaria, cor_secundaria):
    """Variáveis de tema (RGB "r g b") já com contraste garantido, e as
    cores efetivamente aplicadas em hex (exibidas na identidade visual)."""
    primaria = hex_para_rgb(cor_primaria if hex_valido(cor_primaria) else COR_PRIMARIA_PADRAO)
    secundaria = hex_para_rgb(cor_secundaria if hex_valido(cor_secundaria) else COR_SECUNDARIA_PADRAO)
    primaria = escurecer_ate_contraste(primaria)
    secundaria = escurecer_ate_contraste(secundaria, LUMINANCIA_MAXIMA_SECUNDARIA)
    return {
        "primaria_rgb": _rgb_css(primaria),
        "primaria_hover_rgb": _rgb_css(clarear(primaria)),
        "secundaria_rgb": _rgb_css(secundaria),
        "primaria_hex": rgb_para_hex(primaria),
        "secundaria_hex": rgb_para_hex(secundaria),
    }
