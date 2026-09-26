"""¿Nia contesta mejor o peor que antes?

Los votos 👍/👎 de las respuestas, agrupados por modo (IA o reglas) y por versión del
prompt, que es el hash de su texto: cuando el prompt cambia, el hash cambia solo, y los
votos de dos versiones distintas dejan de sumarse como si fueran uno. Para saber qué
cambió entre dos hashes:

    git log -S'<un trozo del prompt>' -- api/nia.py

Solo lee datos/valoraciones.db (o la que diga NEXPLAY_VALORACIONES_DB). Con la base vacía
lo dice y sale bien: todavía no hay nada que medir.

Uso:
  python docs/evidencia/valoraciones_nia.py
"""

import os
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BASE = Path(os.environ.get("NEXPLAY_VALORACIONES_DB", RAIZ / "datos" / "valoraciones.db"))

# El % de 👍 por modo y por versión del prompt, con el n al lado: sin él, un 100% de dos
# votos se lee igual que un 100% de doscientos.
_POR_VERSION = """
SELECT r.modo,
       r.version_prompt,
       COUNT(*)                                        AS votos,
       SUM(CASE WHEN v.voto = 1 THEN 1 ELSE 0 END)     AS pulgares_arriba,
       MIN(r.creado)                                   AS primera,
       MAX(r.creado)                                   AS ultima
FROM valoraciones_nia v
JOIN respuestas_nia r ON r.id = v.id_respuesta
GROUP BY r.modo, r.version_prompt
ORDER BY primera
"""

_MOTIVOS = """
SELECT COALESCE(v.motivo, '(sin motivo)') AS motivo, COUNT(*) AS cuantos
FROM valoraciones_nia v
WHERE v.voto = -1
GROUP BY motivo
ORDER BY cuantos DESC
"""

# Cuántas respuestas recibieron voto: un 👍 del 90% sobre el 3% de las respuestas dice
# menos de lo que parece.
_COBERTURA = """
SELECT r.modo,
       COUNT(*)                                                AS respuestas,
       SUM(CASE WHEN v.id_respuesta IS NOT NULL THEN 1 ELSE 0 END) AS votadas
FROM respuestas_nia r
LEFT JOIN valoraciones_nia v ON v.id_respuesta = r.id
GROUP BY r.modo
"""


def main() -> int:
    if not BASE.exists():
        print(f"no existe {BASE}: todavía nadie ha preguntado nada a Nia.")
        return 0

    con = sqlite3.connect(f"file:{BASE}?mode=ro", uri=True)
    try:
        tablas = {fila[0] for fila in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"respuestas_nia", "valoraciones_nia"} <= tablas:
            print("la base todavía no tiene las tablas de Nia: arranca la API una vez y pregúntale algo.")
            return 0

        cobertura = con.execute(_COBERTURA).fetchall()
        filas = con.execute(_POR_VERSION).fetchall()
        motivos = con.execute(_MOTIVOS).fetchall()
    finally:
        con.close()

    if not cobertura:
        print("todavía no hay respuestas de Nia guardadas.")
        return 0

    print(f"{'modo':14} {'respuestas':>11} {'votadas':>8} {'cobertura':>10}")
    for modo, respuestas, votadas in cobertura:
        print(f"{modo:14} {respuestas:11,} {votadas:8,} {votadas / respuestas:9.0%}")

    if not filas:
        print("\nnadie ha votado todavía: no hay % de 👍 que calcular.")
        return 0

    print(f"\n{'modo':14} {'prompt':10} {'votos':>6} {'👍':>5} {'% 👍':>7}  {'desde':10} {'hasta':10}")
    for modo, version, votos, arriba, primera, ultima in filas:
        print(f"{modo:14} {version:10} {votos:6} {arriba:5} {arriba / votos:6.0%}  {primera[:10]:10} {ultima[:10]:10}")

    if motivos:
        print("\nmotivos del 👎:")
        for motivo, cuantos in motivos:
            print(f"  {cuantos:4}  {motivo}")

    total = sum(f[2] for f in filas)
    if total < 30:
        print(f"\nCon {total} votos esto es una pista, no una medida: no compares porcentajes todavía.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
