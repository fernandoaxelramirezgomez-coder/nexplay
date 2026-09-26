import { Injectable, signal } from '@angular/core';

import { colorDominante } from '../dominio/color-portada';

const CLAVE = 'nexplay.color-portada.v1';

function leerGuardados(): Map<number, string> {
  try {
    const crudo = JSON.parse(localStorage.getItem(CLAVE) ?? '{}') as Record<string, string>;
    return new Map(
      Object.entries(crudo)
        .filter(([, color]) => /^#[0-9a-f]{6}$/.test(color))
        .map(([appid, color]) => [Number(appid), color]),
    );
  } catch {
    return new Map();
  }
}

/** El color dominante de cada portada del catálogo, para el resplandor de su tarjeta.
 *
 * Las portadas de Steam traen `access-control-allow-origin: *`, así que se pueden leer en
 * un canvas si se piden con crossOrigin. Se piden aparte de la imagen que se ve (que no
 * lleva crossOrigin: si algún día la CDN quita la cabecera, la portada se sigue viendo y
 * lo único que se pierde es el color). Se calcula una vez por juego y se guarda. */
@Injectable({ providedIn: 'root' })
export class ColorPortadaStore {
  private readonly colores = signal<ReadonlyMap<number, string | null>>(leerGuardados());
  private readonly enCamino = new Set<number>();

  color(appid: number): string | null | undefined {
    return this.colores().get(appid);
  }

  pedir(appid: number, url: string): void {
    if (this.colores().has(appid) || this.enCamino.has(appid) || typeof Image === 'undefined') {
      return;
    }
    this.enCamino.add(appid);
    const imagen = new Image();
    imagen.crossOrigin = 'anonymous';
    imagen.decoding = 'async';
    imagen.onload = () => this.anotar(appid, this.leer(imagen));
    // Sin red o sin cabecera CORS no hay color: la tarjeta queda con el resplandor neutro.
    imagen.onerror = () => this.anotar(appid, null, false);
    imagen.src = url;
  }

  private leer(imagen: HTMLImageElement): string | null {
    try {
      const lienzo = document.createElement('canvas');
      lienzo.width = 32;
      lienzo.height = 15;
      const contexto = lienzo.getContext('2d', { willReadFrequently: true });
      if (!contexto) {
        return null;
      }
      contexto.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
      return colorDominante(contexto.getImageData(0, 0, lienzo.width, lienzo.height).data);
    } catch {
      return null;
    }
  }

  private anotar(appid: number, color: string | null, guardar = true): void {
    this.enCamino.delete(appid);
    this.colores.update((actual) => new Map(actual).set(appid, color));
    if (!guardar || !color) {
      return;
    }
    try {
      const guardados = Object.fromEntries(
        [...this.colores()].filter(([, valor]) => valor).map(([id, valor]) => [String(id), valor]),
      );
      localStorage.setItem(CLAVE, JSON.stringify(guardados));
    } catch {
      // Sin almacenamiento el color se vuelve a calcular en la próxima visita.
    }
  }
}
