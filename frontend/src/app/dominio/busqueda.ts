import { JuegoCatalogo } from '../api/contrato';

export interface DestinoBusqueda {
  ruta: (string | number)[];
  parametros?: Record<string, string>;
}

/** Nombre para comparar: sin mayúsculas, sin marcas (™ ® ©) y con los espacios en uno. */
function comparable(nombre: string): string {
  return nombre.replace(/[™®©]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
}

/** Adónde lleva «Buscar un juego →» del inicio: con el campo vacío, al catálogo; si lo
 * escrito es el nombre de un juego, a su ficha; si no, al catálogo filtrado con eso. */
export function destinoDeBusqueda(juegos: readonly JuegoCatalogo[], texto: string): DestinoBusqueda {
  const buscado = comparable(texto);
  if (!buscado) {
    return { ruta: ['/explorar'] };
  }
  const exacto = juegos.find((juego) => comparable(juego.nombre) === buscado);
  if (exacto) {
    return { ruta: ['/juego', exacto.appid] };
  }
  return { ruta: ['/explorar'], parametros: { q: texto.trim() } };
}
