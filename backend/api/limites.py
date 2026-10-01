"""Límite de frecuencia en memoria, con ventana deslizante.

Frena el spam sin moderación ni base de datos: guarda las marcas de tiempo de cada
clave (id de usuario, IP) y rechaza cuando se pasan del máximo en la ventana.

Es un tope de costo y de ruido, no seguridad: al reiniciar la API los contadores
vuelven a cero, y con varios procesos cada uno lleva el suyo.
"""

import time
from collections import defaultdict, deque


class LimitePorVentana:
    def __init__(self, maximo: int, ventana_segundos: float = 60.0) -> None:
        self._maximo = maximo
        self._ventana = ventana_segundos
        self._marcas: dict[str, deque[float]] = defaultdict(deque)

    def revisar(self, *claves: str) -> float:
        """Devuelve 0.0 si se permite (y lo registra), o los segundos que faltan para
        volver a intentar. Se registra solo si todas las claves tienen cupo."""
        ahora = time.monotonic()
        espera = 0.0
        for clave in claves:
            marcas = self._marcas[clave]
            while marcas and ahora - marcas[0] >= self._ventana:
                marcas.popleft()
            if len(marcas) >= self._maximo:
                espera = max(espera, self._ventana - (ahora - marcas[0]))

        if espera > 0:
            return espera

        for clave in claves:
            self._marcas[clave].append(ahora)
        return 0.0
