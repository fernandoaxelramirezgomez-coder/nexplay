"""Corta los sprites de la hoja de emociones de Nia y les quita el fondo.

La hoja (docs/diseno/nia-hoja-emociones.png, 1536×1024) trae 12 emociones en una
rejilla de 6×2 con 256 px por columna, cada una con su nombre escrito debajo y un
fondo oscuro con resplandores de color distintos por celda. Este script saca solo
las que usa la ficha y las deja con fondo transparente en frontend/public/nia/.

Cómo se separa la figura del fondo. Se midió la hoja: el fondo es un resplandor
morado que va de claro (suma RGB ~300-360) a casi negro en las esquinas; el pelo es
café oscuro (~150-200, con el rojo por encima del azul) y el suéter, negro azulado.

Lo que funciona es inundar el FONDO en dos pasadas, usando los bordes nítidos del
pixel art como muro (el resplandor cambia de a pocos niveles por píxel; el dibujo,
de decenas). Todo lo que ninguna pasada alcanza es la figura y queda opaco.

1. Desde el borde, sembrando solo en resplandor claro y sin entrar nunca a lo
   oscuro. Así no toca el suéter: el borde de abajo lo corta, y en lo oscuro suéter
   y fondo no se distinguen ni por color ni por borde.
2. Solo desde la fila de arriba, dejando pasar lo oscuro pero solo por colores fríos
   (azul >= rojo). Se lleva la esquina negra que la primera pasada no pisa; el pelo
   café, cálido, le hace de muro y le impide bajar hasta el suéter.

Lo que quede suelto tocando el borde de la celda se descarta; lo que flote sin
tocarlo, como el globo de "…", se conserva. Donde nada de esto alcanza —un rincón
de Happy— se tapa a mano con 'tapar'.

Intentos que fallaron, para no repetirlos:
- Sembrar en todo el borde: el de abajo corta el suéter y se inundaba por dentro.
- Tomar "oscuro" como contorno y rellenar lo que encierra: el fondo también es
  oscuro en las esquinas y se mezclaba con el contorno.
- Rellenar la cáscara de bordes nítidos: el pelo y el suéter son zonas lisas, casi
  sin bordes por dentro, y donde la cáscara no cerraba quedaban TRANSPARENTES.
  Sobre el índigo de la app no se notaba —el fondo asomaba por el hueco y parecía
  pelo negro—, así que el recorte se revisa siempre sobre blanco.
- Sembrar la pasada fría también desde los lados: se comía las mangas de Happy.

Uso:
    python scripts/recortar_nia.py
    python scripts/recortar_nia.py --hoja otra/ruta.png
"""

import argparse
from collections import deque
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
    # La esquina de abajo a la izquierda de Happy es fondo oscuro pegado al mechón de
    # pelo: ninguna pasada automática lo separa sin comerse las mangas, así que se tapa.
    "ficha-bajo": {"emocion": "Happy", "caja": (512, 130, 768, 398), "tapar": (512, 367, 541, 399)},
    "ficha-medio": {"emocion": "Think", "caja": (768, 110, 1024, 398)},
    "ficha-alto": {"emocion": "Typing", "caja": (1024, 130, 1280, 398)},
}

# Salto de luminancia entre vecinos a partir del cual hay un borde de dibujo. El
# resplandor del fondo no pasa de unas pocas unidades; el pixel art, de decenas.
_UMBRAL_BORDE = 28
# Los bordes se engordan este radio antes de usarlos como muro, para tapar los
# tramos de contorno de un solo píxel por donde se colaba la inundación.
_RADIO_MURO = 1
# Solo se siembra donde el borde de la celda es resplandor claro, nunca en el suéter.
_BRILLO_MIN_SEMILLA = 200
# Cuánto puede cambiar el color entre dos vecinos para seguir siendo fondo.
_TOLERANCIA = 30
# La inundación no entra a lo oscuro. Sin esto bajaba por el degradado del resplandor
# hasta las esquinas negras de la hoja y de ahí se metía al suéter: en lo oscuro,
# suéter y fondo no se distinguen ni por color ni por borde.
_BRILLO_MIN_FONDO = 170
# Piezas sueltas más chicas que esto se tiran (chispas, corazoncitos); lo que pase de
# aquí y no toque a la figura se conserva, como el globo de "…" de Think.
_AREA_MINIMA = 1500


def _disco(radio: int) -> np.ndarray:
    y, x = np.ogrid[-radio:radio + 1, -radio:radio + 1]
    return x**2 + y**2 <= radio**2


def _inundar_fondo(px: np.ndarray, muro: np.ndarray, solo_arriba: bool = False) -> np.ndarray:
    """solo_arriba: siembra únicamente en la fila de arriba y deja pasar lo oscuro."""
    alto, ancho, _ = px.shape
    brillo = px.sum(axis=2)
    fondo = np.zeros((alto, ancho), dtype=bool)
    # En la pasada de arriba solo se pisa lo frío. La esquina oscura de la hoja es
    # morada (azul > rojo) y el pelo es café (rojo > azul): el pelo le hace de muro y
    # la inundación no puede bajar por él hasta el suéter.
    frio = px[:, :, 2] >= px[:, :, 0]
    if solo_arriba:
        # Solo arriba. Desde los lados se probó y se comía las mangas de Happy, que son
        # oscuras, frías y llegan casi al borde; desde abajo se comería el suéter.
        cola = deque((0, x) for x in range(ancho) if not muro[0, x] and frio[0, x])
        brillo_min = -1
    else:
        borde = [(0, x) for x in range(ancho)] + [(alto - 1, x) for x in range(ancho)]
        borde += [(y, 0) for y in range(alto)] + [(y, ancho - 1) for y in range(alto)]
        cola = deque(p for p in borde if brillo[p] > _BRILLO_MIN_SEMILLA and not muro[p])
        brillo_min = _BRILLO_MIN_FONDO
    while cola:
        y, x = cola.popleft()
        if fondo[y, x]:
            continue
        fondo[y, x] = True
        actual = px[y, x]
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < alto and 0 <= nx < ancho and not fondo[ny, nx] and not muro[ny, nx]:
                if solo_arriba and not frio[ny, nx]:
                    continue
                if brillo[ny, nx] > brillo_min and np.abs(px[ny, nx] - actual).sum() <= _TOLERANCIA:
                    cola.append((ny, nx))
    return fondo


def recortar(hoja: Image.Image, caja: tuple, tapar: tuple | None) -> Image.Image:
    celda = hoja.crop(caja).convert("RGB")
    px = np.asarray(celda).astype(np.float32)

    luz = px @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    salto = np.hypot(ndimage.sobel(luz, axis=0), ndimage.sobel(luz, axis=1)) / 4
    muro = ndimage.binary_dilation(salto > _UMBRAL_BORDE, _disco(_RADIO_MURO))

    # Segunda pasada solo desde arriba: la esquina oscura de la hoja cae como un
    # degradado liso hasta el contorno de la cabeza. La compuerta de brillo que protege
    # el suéter le impedía entrar a la primera pasada; desde arriba no hay suéter que
    # proteger, y el contorno negro de la cabeza es un borde fuerte que la frena.
    figura = ~(_inundar_fondo(px, muro) | _inundar_fondo(px, muro, solo_arriba=True))
    if tapar:
        x0, y0, x1, y1 = (tapar[0] - caja[0], tapar[1] - caja[1], tapar[2] - caja[0], tapar[3] - caja[1])
        figura[max(0, y0):y1, max(0, x0):x1] = False

    # Se queda la figura (la pieza más grande) y lo que flote suelto sin tocar el borde
    # de la celda, como el globo de "…". Las esquinas oscuras de la hoja, que la
    # inundación ya no pisa, sí tocan el borde: esas se van. Las chispas, por chicas.
    etiquetas, cuantas = ndimage.label(figura)
    if cuantas:
        tamanos = ndimage.sum(figura, etiquetas, range(1, cuantas + 1))
        figura_principal = int(np.argmax(tamanos)) + 1
        en_borde = set(np.unique(np.concatenate([
            etiquetas[0, :], etiquetas[-1, :], etiquetas[:, 0], etiquetas[:, -1],
        ]))) - {0}
        quedan = [figura_principal] + [
            i + 1 for i, t in enumerate(tamanos)
            if i + 1 != figura_principal and t >= _AREA_MINIMA and (i + 1) not in en_borde
        ]
        figura = np.isin(etiquetas, quedan)
    # El muro engordó el contorno un píxel hacia afuera: se recupera ese borde fino.
    figura = ndimage.binary_erosion(figura, _disco(_RADIO_MURO)) | (figura & (salto > _UMBRAL_BORDE))

    salida = celda.convert("RGBA")
    alfa = Image.fromarray(np.where(figura, 255, 0).astype(np.uint8), mode="L")
    salida.putalpha(alfa.filter(ImageFilter.GaussianBlur(0.5)))
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
