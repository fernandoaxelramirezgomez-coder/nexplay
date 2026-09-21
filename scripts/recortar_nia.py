"""Corta los sprites de la hoja de emociones de Nia y les quita el fondo.

La hoja (docs/diseno/nia-hoja-emociones.png, 1536×1024) trae 12 emociones en una
rejilla de 6×2 con 256 px por columna, cada una con su nombre escrito debajo y un
fondo oscuro con resplandores de color distintos por celda. Este script saca solo
las que usa la ficha y las deja con fondo transparente en frontend/public/nia/.

Cómo se separa la figura del fondo, y por qué así. Se midió la hoja: el contorno
negro del pixel art es lo más oscuro que hay (suma RGB < 110), mientras el fondo es
un resplandor más claro (~300-360) e incluso más claro que el pelo (~190).

Dos intentos anteriores fallaron y conviene no repetirlos:
- Inundar desde el borde de la celda sembraba también en el borde de abajo, que
  corta la sudadera: se inundaba la figura por dentro y quedaba solo la cara.
- Sembrar solo en fondo claro arregló una emoción, pero en las otras el resplandor
  se oscurece junto al dibujo y la inundación se colaba por los tramos finos del
  contorno hasta comerse el pelo.

- Tomar "oscuro" como contorno y rellenar lo que encierra: el fondo de la hoja
  también es oscuro en las esquinas y entre celdas, y se mezclaba con el contorno.

Lo que funciona: la diferencia entre figura y fondo no es el color sino la NITIDEZ.
El resplandor del fondo cambia de a pocos niveles por píxel; el pixel art tiene
bordes duros por todos lados. Se detectan esos bordes, se cierran en una cáscara y
se rellena su interior. La base de la celda se trata como un borde más, porque el
recorte corta la sudadera justo antes del nombre de la emoción.

Uso:
    python scripts/recortar_nia.py
    python scripts/recortar_nia.py --hoja otra/ruta.png
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

_RAIZ = Path(__file__).resolve().parent.parent
_HOJA = _RAIZ / "docs" / "diseno" / "nia-hoja-emociones.png"
_SALIDA = _RAIZ / "frontend" / "public" / "nia"

# Cajas en coordenadas de la hoja. El borde de abajo se corta justo antes del nombre
# de la emoción, que viene escrito en la hoja y no debe llegar a la interfaz.
# 'tapar' (opcional) vuelve transparente una zona antes de recortar.
#
# Banda alta: se probó "Error" sin su globo de X y se descartó mirando la captura.
# Sin la X ya no dice "no lo compres", pero el corazón que abraza domina el dibujo y se
# lee como cariño: contradice la banda. "Typing" —Nia revisando en su laptop— es la
# pose más neutra y seria de la hoja, y coincide con lo que dice su texto ("conviene
# revisar los motivos"). La cautela la completan el halo y el acento de la banda.
_SPRITES = {
    "ficha-bajo": {"emocion": "Happy", "caja": (512, 130, 768, 398)},
    "ficha-medio": {"emocion": "Think", "caja": (768, 110, 1024, 398)},
    "ficha-alto": {"emocion": "Typing", "caja": (1024, 130, 1280, 398)},
}

# Salto de luminancia entre vecinos a partir del cual hay un borde de dibujo. El
# resplandor del fondo no pasa de unas pocas unidades; el pixel art, de decenas.
_UMBRAL_BORDE = 28
# Radio con el que se juntan los bordes en una cáscara cerrada antes de rellenarla.
_RADIO_SELLADO = 3
# Piezas sueltas más chicas que esto se tiran (chispas, corazoncitos); lo que pase de
# aquí y no toque a la figura se conserva, como el globo de "…" de Think.
_AREA_MINIMA = 1500


def _disco(radio: int) -> np.ndarray:
    y, x = np.ogrid[-radio:radio + 1, -radio:radio + 1]
    return x**2 + y**2 <= radio**2


def recortar(hoja: Image.Image, caja: tuple, tapar: tuple | None) -> Image.Image:
    celda = hoja.crop(caja).convert("RGB")
    px = np.asarray(celda).astype(np.float32)

    luz = px @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    salto = np.hypot(ndimage.sobel(luz, axis=0), ndimage.sobel(luz, axis=1)) / 4
    bordes = salto > _UMBRAL_BORDE
    if tapar:
        x0, y0, x1, y1 = (tapar[0] - caja[0], tapar[1] - caja[1], tapar[2] - caja[0], tapar[3] - caja[1])
        bordes[max(0, y0):y1, max(0, x0):x1] = False

    cascara = ndimage.binary_closing(bordes, _disco(_RADIO_SELLADO))
    # La base del recorte cierra la cáscara por abajo: ahí se cortó la sudadera.
    cascara[-1, :] = True
    figura = ndimage.binary_fill_holes(cascara)
    figura[-1, :] = figura[-2, :]

    etiquetas, cuantas = ndimage.label(figura)
    if cuantas:
        tamanos = ndimage.sum(figura, etiquetas, range(1, cuantas + 1))
        quedan = [i + 1 for i, t in enumerate(tamanos) if t >= _AREA_MINIMA]
        figura = np.isin(etiquetas, quedan)
    if tapar:
        figura[max(0, y0):y1, max(0, x0):x1] = False

    salida = celda.convert("RGBA")
    alfa = Image.fromarray(np.where(figura, 255, 0).astype(np.uint8), mode="L")
    salida.putalpha(alfa.filter(ImageFilter.GaussianBlur(0.6)))
    return salida.crop(salida.getbbox())


def main() -> None:
    parser = argparse.ArgumentParser(description="Corta los sprites de Nia para la ficha")
    parser.add_argument("--hoja", type=Path, default=_HOJA, help="por defecto %(default)s")
    args = parser.parse_args()

    hoja = Image.open(args.hoja)
    _SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, spec in _SPRITES.items():
        sprite = recortar(hoja, spec["caja"], spec.get("tapar"))
        ruta = _SALIDA / f"{nombre}.png"
        sprite.save(ruta, optimize=True)
        print(f"{nombre:12} ({spec['emocion']:6}) {sprite.size[0]}×{sprite.size[1]}  "
              f"{ruta.stat().st_size / 1024:.0f} KB  → {ruta.relative_to(_RAIZ)}")


if __name__ == "__main__":
    main()
