"""Moderación de emergencia del hilo de comentarios, desde la terminal.

Es el único mecanismo de moderación: la API no expone nada para borrar. Por defecto
solo lista; borrar pide el id explícito.

Uso:
  python moderar_comentarios.py                 # todos los comentarios
  python moderar_comentarios.py 1938010         # los de un juego
  python moderar_comentarios.py --borrar 12     # borra ese comentario
"""

import argparse
import sys
import textwrap

from api import valoraciones

ANCHO_TEXTO = 80


def listar(appid: int | None) -> int:
    filas = valoraciones.comentarios_para_moderar(appid)
    if not filas:
        print("no hay comentarios" + (f" para el appid {appid}" if appid else "") + ".")
        return 0

    for id_comentario, appid_fila, usuario, texto, creado in filas:
        print(f"[{id_comentario}] appid={appid_fila} {creado} usuario={usuario[:8]}…")
        for linea in textwrap.wrap(texto, ANCHO_TEXTO) or [""]:
            print(f"      {linea}")
    print(f"\n{len(filas)} comentarios. Para borrar uno: python moderar_comentarios.py --borrar <id>")
    return 0


def borrar(id_comentario: int) -> int:
    filas = {fila[0]: fila for fila in valoraciones.comentarios_para_moderar()}
    objetivo = filas.get(id_comentario)
    if objetivo is None:
        print(f"no existe el comentario {id_comentario}.")
        return 1

    if not valoraciones.borrar_comentario(id_comentario):
        print(f"no se pudo borrar el comentario {id_comentario}.")
        return 1
    print(f"borrado [{id_comentario}] appid={objetivo[1]} {objetivo[4]}: {objetivo[3][:60]}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lista o borra comentarios del hilo público (uso local).")
    parser.add_argument("appid", nargs="?", type=int, help="filtra por juego")
    parser.add_argument("--borrar", type=int, metavar="ID", help="borra ese comentario y sale")
    args = parser.parse_args()
    sys.exit(borrar(args.borrar) if args.borrar is not None else listar(args.appid))
