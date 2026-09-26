"""Panorama de la muestra de reseñas: cuántas se descargaron, de cuándo son, qué tan
buenas son y cuántas traen la señal de arrepentimiento temprano.

Es descriptivo, no predictivo: todo sale de contar `datos/nexplay.db`, y `casos_senal`
aplica la definición de la etiqueta (`playtime_at_review < 120` y voto negativo), no el
modelo. Por eso ninguna cifra de aquí es un score y ninguna depende del perfil.

Se calcula **una sola vez al importar el módulo**, como el catálogo: los agregados son
SQL de milisegundos y recorrer los textos de los ~4,100 casos Y=1 para contar motivos
toma medio segundo. Pedirlo en cada request sería repetir ese trabajo para siempre."""

import logging
import sqlite3
import statistics
from pathlib import Path

from . import scoring
from .schemas import (
    CalidadMuestra,
    JuegoPanorama,
    MotivoInsatisfaccion,
    PanoramaCatalogo,
    TramoPlaytime,
    VentanaMuestra,
)

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent / "datos" / "nexplay.db"

# El primer tramo es la ventana de reembolso de Steam: ahí se define la etiqueta.
_TRAMOS = (
    ("Menos de 2 h", 0, 120),
    ("2 a 10 h", 120, 600),
    ("10 a 50 h", 600, 3000),
    ("Más de 50 h", 3000, None),
)

# Con menos reseñas positivas que esto, la mediana de horas dice poco y se deja en None.
_MIN_POSITIVAS_PARA_HORAS = 10

_VACIO = PanoramaCatalogo(
    juegos=0,
    resenas_descargadas=0,
    resenas_en_steam=0,
    cobertura=0.0,
    ventana=VentanaMuestra(desde="", hasta=""),
    casos_senal=0,
    prevalencia=0.0,
    playtime_al_resenar=[],
    muestra=CalidadMuestra(
        compradas_en_steam=0.0,
        recibidas_gratis=0.0,
        acceso_anticipado=0.0,
        con_voto_util=0.0,
        perfiles_privados=0.0,
        en_ingles=0.0,
        resenas_en_ingles=0,
    ),
    motivos=[],
    resenas_clasificadas=0,
    por_juego=[],
)


def _proporcion(parte: int | None, total: int) -> float:
    return round((parte or 0) / total, 4) if total else 0.0


def _calcular() -> PanoramaCatalogo:
    if not _DB_PATH.exists():
        logger.warning("no existe %s; el panorama queda vacío", _DB_PATH)
        return _VACIO

    con = sqlite3.connect(f"file:{_DB_PATH}?mode=ro", uri=True)
    try:
        total, juegos, casos, compradas, gratis, anticipado, con_voto, privados, ingles = con.execute(
            """
            SELECT count(*),
                   count(DISTINCT appid),
                   sum(playtime_at_review < 120 AND voted_up = 0),
                   sum(steam_purchase),
                   sum(received_for_free),
                   sum(written_during_early_access),
                   sum(votes_up > 0),
                   sum(num_games_owned = 0),
                   sum(idioma = 'english')
            FROM resenas
            """
        ).fetchone()
        if not total:
            logger.warning("la tabla resenas está vacía; el panorama queda vacío")
            return _VACIO

        desde, hasta = con.execute(
            "SELECT date(min(timestamp_created), 'unixepoch'), date(max(timestamp_created), 'unixepoch') FROM resenas"
        ).fetchone()

        tramos = []
        for etiqueta, minimo, maximo in _TRAMOS:
            condicion = f"playtime_at_review >= {minimo}" + (f" AND playtime_at_review < {maximo}" if maximo else "")
            (cuantas,) = con.execute(f"SELECT count(*) FROM resenas WHERE {condicion}").fetchone()
            tramos.append(TramoPlaytime(tramo=etiqueta, cuantas=cuantas, fraccion=_proporcion(cuantas, total)))

        en_steam = dict(con.execute("SELECT appid, total_resenas FROM resumen_resenas"))
        positivas_steam = dict(con.execute("SELECT appid, total_positivas FROM resumen_resenas"))
        consenso = dict(con.execute("SELECT appid, descripcion_score FROM resumen_resenas"))
        por_appid = con.execute(
            """
            SELECT appid, count(*), sum(playtime_at_review < 120 AND voted_up = 0)
            FROM resenas GROUP BY appid ORDER BY appid
            """
        ).fetchall()
        # Cuántas horas llevaba jugadas quien lo recomendó: separa los juegos que rinden
        # en pocas horas de los que piden cientos. SQLite no tiene mediana; va en Python.
        minutos_positivas: dict[int, list[int]] = {}
        for appid, minutos in con.execute(
            "SELECT appid, playtime_at_review FROM resenas WHERE voted_up = 1 AND playtime_at_review IS NOT NULL"
        ):
            minutos_positivas.setdefault(appid, []).append(minutos)
    finally:
        con.close()

    horas_al_recomendar = {
        appid: round(statistics.median(minutos) / 60, 1)
        for appid, minutos in minutos_positivas.items()
        if len(minutos) >= _MIN_POSITIVAS_PARA_HORAS
    }

    conteos_catalogo: dict[str, int] = {}
    clasificadas = 0
    filas = []
    for appid, resenas, casos_juego in por_appid:
        conteos, n_clasificados, n_casos = scoring.contar_motivos(appid)
        clasificadas += n_clasificados
        for categoria, cuantas in conteos.items():
            conteos_catalogo[categoria] = conteos_catalogo.get(categoria, 0) + cuantas
        # Mismo criterio que /explicacion: con menos de cinco casos no se nombra un motivo
        # principal, aunque sus reseñas sí cuenten para el agregado del catálogo.
        principal = (
            max(conteos.items(), key=lambda par: par[1])[0]
            if n_clasificados and n_casos >= scoring.UMBRAL_MIN_CASOS
            else None
        )
        filas.append(
            JuegoPanorama(
                appid=appid,
                resenas=resenas,
                casos_senal=casos_juego or 0,
                prevalencia=_proporcion(casos_juego, resenas),
                resenas_en_steam=en_steam.get(appid),
                positivas_en_steam=positivas_steam.get(appid),
                consenso=consenso.get(appid),
                motivo_principal=principal,
                horas_al_recomendar=horas_al_recomendar.get(appid),
            )
        )

    motivos = [
        MotivoInsatisfaccion(motivo=categoria, frecuencia=round(cuantas / clasificadas, 4))
        for categoria, cuantas in sorted(conteos_catalogo.items(), key=lambda par: -par[1])
        if cuantas > 0
    ] if clasificadas else []

    total_en_steam = sum(v for v in en_steam.values() if v)
    panorama = PanoramaCatalogo(
        juegos=juegos,
        resenas_descargadas=total,
        resenas_en_steam=total_en_steam,
        cobertura=_proporcion(total, total_en_steam),
        ventana=VentanaMuestra(desde=desde or "", hasta=hasta or ""),
        casos_senal=casos or 0,
        prevalencia=_proporcion(casos, total),
        playtime_al_resenar=tramos,
        muestra=CalidadMuestra(
            compradas_en_steam=_proporcion(compradas, total),
            recibidas_gratis=_proporcion(gratis, total),
            acceso_anticipado=_proporcion(anticipado, total),
            con_voto_util=_proporcion(con_voto, total),
            perfiles_privados=_proporcion(privados, total),
            en_ingles=_proporcion(ingles, total),
            resenas_en_ingles=ingles or 0,
        ),
        motivos=motivos,
        resenas_clasificadas=clasificadas,
        por_juego=filas,
    )
    logger.info(
        "panorama: %s reseñas de %s juegos, %s con señal (%.2f%%), %s clasificadas",
        total, juegos, casos, panorama.prevalencia * 100, clasificadas,
    )
    return panorama


_PANORAMA = _calcular()


def resumen() -> PanoramaCatalogo:
    return _PANORAMA
