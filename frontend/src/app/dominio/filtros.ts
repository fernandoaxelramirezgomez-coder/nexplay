import { JuegoCatalogo } from '../api/contrato';

export interface FiltroCatalogo {
  texto: string;
  /** Vacío = todos los géneros. */
  genero: string;
}

/** Filtro del catálogo visual, en el cliente: el texto se busca como
 * subcadena del nombre sin distinguir mayúsculas; el género debe coincidir exacto. */
export function filtrarJuegos(juegos: readonly JuegoCatalogo[], filtro: FiltroCatalogo): JuegoCatalogo[] {
  const texto = filtro.texto.trim().toLowerCase();
  return juegos.filter(
    (juego) =>
      (!texto || juego.nombre.toLowerCase().includes(texto)) &&
      (!filtro.genero || juego.generos.includes(filtro.genero)),
  );
}
