import { JuegoCatalogo } from '../api/contrato';

export interface FiltroCatalogo {
  texto: string;
  /** Vacío = todos los géneros. Con varios, basta con tener uno. */
  generos: readonly string[];
}

/** Filtro del catálogo visual, en el cliente: el texto se busca como subcadena del nombre
 * sin distinguir mayúsculas; los géneros deben coincidir exacto, y con varios elegidos el
 * juego entra si tiene cualquiera de ellos (Acción + Rol trae los de acción y los de rol). */
export function filtrarJuegos(juegos: readonly JuegoCatalogo[], filtro: FiltroCatalogo): JuegoCatalogo[] {
  const texto = filtro.texto.trim().toLowerCase();
  return juegos.filter(
    (juego) =>
      (!texto || juego.nombre.toLowerCase().includes(texto)) &&
      (!filtro.generos.length || filtro.generos.some((genero) => juego.generos.includes(genero))),
  );
}

/** ?genero=Acción,Rol ↔ ['Acción', 'Rol']. Los nombres de género de Steam no llevan comas. */
export function generosDeUrl(valor: string | null | undefined): string[] {
  return [...new Set((valor ?? '').split(',').map((g) => g.trim()).filter(Boolean))];
}

export function generosParaUrl(generos: readonly string[]): string | null {
  return generos.length ? generos.join(',') : null;
}
