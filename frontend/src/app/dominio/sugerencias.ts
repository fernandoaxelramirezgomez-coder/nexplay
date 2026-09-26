import { JuegoCatalogo, PerfilJugador } from '../api/contrato';
import { generosEnComun } from './afinidad';

/** Un juego del catálogo que comparte géneros con lo que la persona declaró, con el
 * porqué al lado. No es una predicción ni una recomendación de compra: no existe ningún
 * dato que diga si a alguien le gustó un juego, así que esto no se puede validar como el
 * riesgo (ver docs/evidencia). El riesgo del juego se calcula aparte, solo con datos del
 * juego, y nada de aquí lo toca. */
export interface Sugerencia {
  juego: JuegoCatalogo;
  /** Géneros declarados que el juego tiene, con el nombre tal como los sirve el catálogo. */
  coincidencias: string[];
  /** 0 a 1: cuánto de lo que declaraste cubre el juego, pesando más los géneros raros.
   * Es el criterio principal del orden. No es una probabilidad ni se muestra como número. */
  cobertura: number;
  /** 0 a 1: parecido entre los dos conjuntos de géneros (Jaccard ponderado). Solo separa
   * a los que cubren lo mismo y ya empataron en crítica y precio. */
  afinidad: number;
  /** El género coincidente que menos juegos tienen: el que hace específica la coincidencia. */
  generoMasEspecifico: string;
  /** Cuántos juegos del catálogo tienen ese género. */
  juegosConEseGenero: number;
  /** Cuántos otros juegos cubren lo mismo: entonces manda el desempate. */
  empatanConEl: number;
}

export interface ResultadoSugerencias {
  sugerencias: Sugerencia[];
  /** Todos los que pasaron el filtro, aunque solo se muestren los primeros. */
  candidatos: number;
  /** Por qué la lista puede venir vacía o corta; la vista lo dice con sus palabras. */
  motivo: 'ok' | 'sin-generos' | 'sin-candidatos';
}

const CUANTAS = 6;

/** Rareza de un género: cuántos juegos lo tienen. Un género que está en 4 juegos pesa más
 * que "Acción", que está en 78 de 123: coincidir en lo raro dice más. */
function rarezas(juegos: readonly JuegoCatalogo[]): Map<string, number> {
  const cuenta = new Map<string, number>();
  for (const juego of juegos) {
    for (const genero of juego.generos) {
      const clave = genero.trim().toLowerCase();
      cuenta.set(clave, (cuenta.get(clave) ?? 0) + 1);
    }
  }
  return cuenta;
}

function peso(cuenta: Map<string, number>, total: number, genero: string): number {
  const cuantos = cuenta.get(genero.trim().toLowerCase()) ?? 0;
  return cuantos > 0 ? Math.log(total / cuantos) : 0;
}

/** Juegos del catálogo con géneros parecidos a los declarados.
 *
 * Filtro duro: entra solo el que comparte al menos un género preferido y no tiene ninguno
 * rechazado. Sin él, la lista se rellena con juegos sin nada en común cuando el género
 * declarado es raro (con "Carreras" hay 4 juegos en todo el catálogo).
 *
 * Orden: primero **cuánto cubre de lo que declaraste**, pesando más los géneros raros. Un
 * juego que tiene tus tres géneros va antes que uno que tiene dos, aunque el segundo no
 * traiga nada de más; antes se usaba Jaccard como criterio principal y eso dejaba a
 * Diablo IV (3 coincidencias, 5 géneros) por debajo de Vampire Survivors (2 de 4), que es
 * justo lo contrario de lo que la lista promete.
 *
 * Entre los que cubren lo mismo desempata la crítica —los que no tienen nota van al final,
 * no al principio—, luego el precio (los gratuitos primero, los de precio desconocido al
 * final) y, ya en último lugar, el parecido de conjuntos: con todo lo demás igual, el que
 * no trae seis géneros de más va antes. El nombre cierra para que el orden sea estable.
 *
 * La afinidad mira SOLO géneros: la crítica y el precio desempatan, nunca puntúan, y así la
 * explicación de por qué un juego va antes que otro es literal. */
export function sugerenciasPara(
  juegos: readonly JuegoCatalogo[],
  perfil: PerfilJugador | null,
  cuantas = CUANTAS,
): ResultadoSugerencias {
  const preferidos = (perfil?.tags_preferidos ?? []).map((g) => g.trim().toLowerCase()).filter(Boolean);
  if (!preferidos.length) {
    return { sugerencias: [], candidatos: 0, motivo: 'sin-generos' };
  }
  const rechazados = new Set((perfil?.tags_rechazados ?? []).map((g) => g.trim().toLowerCase()));
  const cuenta = rarezas(juegos);
  const pesoPerfil = preferidos.reduce((suma, g) => suma + peso(cuenta, juegos.length, g), 0);
  const puntuados = juegos
    .filter((juego) => !juego.generos.some((g) => rechazados.has(g.trim().toLowerCase())))
    .map((juego) => {
      const coincidencias = generosEnComun(juego.generos, preferidos);
      const pesoJuego = juego.generos.reduce((suma, g) => suma + peso(cuenta, juegos.length, g), 0);
      const pesoComun = coincidencias.reduce((suma, g) => suma + peso(cuenta, juegos.length, g), 0);
      const union = pesoJuego + pesoPerfil - pesoComun;
      const afinidad = union > 0 ? pesoComun / union : 0;
      const cobertura = pesoPerfil > 0 ? pesoComun / pesoPerfil : 0;
      const masEspecifico = [...coincidencias].sort(
        (a, b) => (cuenta.get(a.toLowerCase()) ?? 0) - (cuenta.get(b.toLowerCase()) ?? 0),
      )[0];
      return {
        juego,
        coincidencias,
        cobertura,
        afinidad,
        generoMasEspecifico: masEspecifico ?? '',
        juegosConEseGenero: cuenta.get(masEspecifico?.toLowerCase() ?? '') ?? juegos.length,
        empatanConEl: 0,
      };
    })
    .filter((s) => s.coincidencias.length > 0);

  if (!puntuados.length) {
    return { sugerencias: [], candidatos: 0, motivo: 'sin-candidatos' };
  }

  puntuados.sort(
    (a, b) =>
      b.cobertura - a.cobertura ||
      critica(b.juego) - critica(a.juego) ||
      precio(a.juego) - precio(b.juego) ||
      b.afinidad - a.afinidad ||
      a.juego.nombre.localeCompare(b.juego.nombre, 'es'),
  );

  const sugerencias = puntuados.slice(0, cuantas).map((s) => ({
    ...s,
    empatanConEl: puntuados.filter((otro) => otro !== s && casiIgual(otro.cobertura, s.cobertura)).length,
  }));
  return { sugerencias, candidatos: puntuados.length, motivo: 'ok' };
}

function casiIgual(a: number, b: number): boolean {
  return Math.abs(a - b) < 1e-9;
}

/** Sin nota de la crítica el juego va al final del desempate, no al principio: no tener
 * cobertura no es una nota baja, pero tampoco es un punto a favor. */
function critica(juego: JuegoCatalogo): number {
  return juego.metacritic ?? -1;
}

/** Los gratuitos valen cero; los de precio desconocido van al final, que es lo único
 * honesto que se puede hacer con un dato que no está. */
function precio(juego: JuegoCatalogo): number {
  if (juego.es_gratis) {
    return 0;
  }
  return juego.precio_final ?? Number.POSITIVE_INFINITY;
}

/** Por qué este juego está en la lista, en palabras. Describe la coincidencia; no dice qué
 * hacer con ella. */
export function porQueCoincide(sugerencia: Sugerencia, totalJuegos: number): string {
  const { coincidencias, generoMasEspecifico, juegosConEseGenero } = sugerencia;
  const generos =
    coincidencias.length === 1
      ? coincidencias[0]
      : `${coincidencias.slice(0, -1).join(', ')} y ${coincidencias[coincidencias.length - 1]}`;
  // Con varios géneros se nombra el más específico: es el que hace que la coincidencia
  // diga algo, y es exactamente lo que pesa en el orden.
  const rareza =
    coincidencias.length === 1
      ? `, que está en ${juegosConEseGenero} de ${totalJuegos} juegos del catálogo`
      : `; el más específico, ${generoMasEspecifico}, está en ${juegosConEseGenero} de ${totalJuegos} juegos`;
  return `Coincide en ${generos}${rareza}.`;
}

/** La regla de desempate es la misma para toda la lista: se dice una vez al pie, no en
 * cada tarjeta, donde sería la misma frase seis veces. */
export const NOTA_DESEMPATE =
  'Varios juegos cubren los mismos géneros que declaraste: entre ellos van primero los que ' +
  'tienen nota de la crítica, de mayor a menor, y después los más baratos.';

/** Si algún juego de la lista empata con otro, la nota de desempate tiene sentido. */
export function hayEmpates(sugerencias: readonly Sugerencia[]): boolean {
  return sugerencias.some((s) => s.empatanConEl > 0);
}
