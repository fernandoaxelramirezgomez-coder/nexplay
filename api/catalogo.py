"""Búsqueda de juegos. Hoy usa una lista fija; cuando exista datos/juegos.parquet
esta capa se reemplaza por una consulta sobre las 71 reseñas ingestadas, sin que
main.py tenga que cambiar."""

from .schemas import JuegoCatalogo, Plataforma

_CATALOGO_SIMULADO = [
    JuegoCatalogo(appid=570, nombre="Dota 2", plataformas=[Plataforma.PC]),
    JuegoCatalogo(appid=730, nombre="Counter-Strike 2", plataformas=[Plataforma.PC]),
    JuegoCatalogo(
        appid=1091500,
        nombre="Cyberpunk 2077",
        plataformas=[Plataforma.PC, Plataforma.PLAYSTATION, Plataforma.XBOX],
    ),
    JuegoCatalogo(
        appid=1245620,
        nombre="Elden Ring",
        plataformas=[Plataforma.PC, Plataforma.PLAYSTATION, Plataforma.XBOX],
    ),
    JuegoCatalogo(appid=1174180, nombre="Red Dead Redemption 2", plataformas=[Plataforma.PC, Plataforma.PLAYSTATION, Plataforma.XBOX]),
]


def buscar(q: str) -> list[JuegoCatalogo]:
    if not q.strip():
        return _CATALOGO_SIMULADO
    q_normalizado = q.strip().lower()
    return [j for j in _CATALOGO_SIMULADO if q_normalizado in j.nombre.lower()]


def obtener(appid: int) -> JuegoCatalogo | None:
    return next((j for j in _CATALOGO_SIMULADO if j.appid == appid), None)
