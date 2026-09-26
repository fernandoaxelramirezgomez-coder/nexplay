import { JuegoCatalogo, JuegoPanorama } from '../api/contrato';
import { generosEnComun } from './afinidad';
import { Gasto, TOPE_GASTO, ValoresPerfil, cabeEnTope } from './opciones-perfil';

/** Lo que las sugerencias toman del perfil: los géneros, el tope de gasto, si juega poco
 * (menos de 4 h por semana) y si tiene poca paciencia con la fricción (nula o baja). */
export interface CriteriosSugerencia {
  /** Con el nombre tal como los sirve el catálogo: 'Acción', 'Rol'. */
  generos: string[];
  gasto: Gasto | null;
  juegaPoco: boolean;
  friccionBaja: boolean;
}

export function criteriosDesde(valores: ValoresPerfil): CriteriosSugerencia {
  return {
    generos: valores.generos,
    gasto: valores.gasto,
    juegaPoco: valores.horas !== null && valores.horas <= 3,
    friccionBaja: valores.friccion !== null && valores.friccion <= 2,
  };
}

/** Lo que se sabe de cada juego además del catálogo, de /panorama. */
export type DatosDeJuego = Pick<JuegoPanorama, 'horas_al_recomendar' | 'motivo_principal'>;

/** Por debajo de esto, un juego "rinde en pocas horas": la mediana de horas de quienes lo
 * recomiendan. La mediana del catálogo es 33 h; 37 de los 123 juegos quedan por debajo. */
export const HORAS_DE_SESION_CORTA = 20;

/** Las quejas que son fricción: lo que la pregunta de tolerancia describe. */
const MOTIVOS_DE_FRICCION = new Set(['bugs', 'rendimiento', 'dificultad', 'controles']);

/** Una razón de la tarjeta: qué criterio del perfil mira, si lo cumple y en qué palabras.
 * Solo salen los criterios que la persona declaró. */
export interface Razon {
  tipo: 'generos' | 'precio' | 'horas' | 'friccion';
  cumple: boolean;
  texto: string;
}

/** Un juego del catálogo que encaja con lo que la persona declaró, con el porqué al lado.
 * No es una predicción ni una recomendación de compra: no existe ningún dato que diga si
 * a alguien le gustó un juego, así que esto no se puede validar como el riesgo (ver
 * docs/evidencia). El riesgo del juego se calcula aparte, solo con datos del juego, y nada
 * de aquí lo toca ni lo usa para ordenar. */
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
  /** 0 a 2: cuántos de horas y fricción cumple, entre los que se declararon. */
  encaje: number;
  razones: Razon[];
}

export interface ResultadoSugerencias {
  sugerencias: Sugerencia[];
  /** Todos los que pasaron el filtro, aunque solo se muestren los primeros. */
  candidatos: number;
  /** Por qué la lista puede venir vacía o corta; la vista lo dice con sus palabras. */
  motivo: 'ok' | 'sin-respuestas' | 'sin-candidatos';
  /** Si con el tope declarado no quedaba ningún juego, cuál se usó en su lugar (null =
   * sin tope). La lista nunca queda en blanco por el gasto: se avisa y se relaja. */
  topeRelajado: { pedido: number; usado: number | null } | null;
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

/** Juegos del catálogo que encajan con lo declarado.
 *
 * **Géneros**: si hay, filtran (entra el que comparte al menos uno) y ordenan por cuánto
 * cubre de lo declarado, pesando más los géneros raros. Un juego que tiene tus tres
 * géneros va antes que uno que tiene dos; antes se usaba Jaccard como criterio principal y
 * eso dejaba a Diablo IV (3 coincidencias, 5 géneros) por debajo de Vampire Survivors (2 de
 * 4), que es justo lo contrario de lo que la lista promete. Sin géneros no filtran.
 *
 * **Gasto**: deja fuera lo que pasa del tope (los gratuitos siempre entran; los de precio
 * desconocido, solo sin tope). Si no queda ninguno, sube de tramo hasta que haya y lo
 * devuelve en `topeRelajado` para que la vista lo diga.
 *
 * **Horas y fricción** ordenan después de los géneros: si juega poco, van antes los que la
 * gente recomienda con menos de 20 h encima; si la fricción le pesa, van después los que
 * tienen como queja principal bugs, rendimiento, dificultad o controles.
 *
 * Después desempata la crítica —los que no tienen nota van al final, no al principio—,
 * luego el precio (los gratuitos primero, los de precio desconocido al final) y, ya en
 * último lugar, el parecido de conjuntos. El nombre cierra para que el orden sea estable. */
export function sugerenciasPara(
  juegos: readonly JuegoCatalogo[],
  criterios: CriteriosSugerencia | null,
  datos: ReadonlyMap<number, DatosDeJuego> = new Map(),
  cuantas = CUANTAS,
): ResultadoSugerencias {
  const vacio = (motivo: ResultadoSugerencias['motivo']): ResultadoSugerencias => ({
    sugerencias: [],
    candidatos: 0,
    motivo,
    topeRelajado: null,
  });
  const preferidos = (criterios?.generos ?? []).map((g) => g.trim().toLowerCase()).filter(Boolean);
  if (!criterios || (!preferidos.length && criterios.gasto === null && !criterios.juegaPoco && !criterios.friccionBaja)) {
    return vacio('sin-respuestas');
  }
  const cuenta = rarezas(juegos);
  const pesoPerfil = preferidos.reduce((suma, g) => suma + peso(cuenta, juegos.length, g), 0);

  const porGenero = juegos
    .map((juego) => ({ juego, coincidencias: generosEnComun(juego.generos, preferidos) }))
    .filter(({ coincidencias }) => !preferidos.length || coincidencias.length > 0);
  if (!porGenero.length) {
    return vacio('sin-candidatos');
  }

  // El tope, y si deja la lista vacía, el siguiente tramo hasta que haya algo.
  const pedido = criterios.gasto;
  let tramo = pedido;
  let dentro = porGenero.filter(({ juego }) => cabeEnTope(juego, tramo ? TOPE_GASTO[tramo] : null));
  while (!dentro.length && tramo !== null && tramo < 4) {
    tramo = (tramo + 1) as Gasto;
    dentro = porGenero.filter(({ juego }) => cabeEnTope(juego, TOPE_GASTO[tramo as Gasto]));
  }
  const topePedido = pedido ? TOPE_GASTO[pedido] : null;
  const topeRelajado =
    pedido !== null && tramo !== pedido && topePedido !== null ? { pedido: topePedido, usado: TOPE_GASTO[tramo as Gasto] } : null;

  const puntuados = dentro.map(({ juego, coincidencias }) => {
    const pesoJuego = juego.generos.reduce((suma, g) => suma + peso(cuenta, juegos.length, g), 0);
    const pesoComun = coincidencias.reduce((suma, g) => suma + peso(cuenta, juegos.length, g), 0);
    const union = pesoJuego + pesoPerfil - pesoComun;
    const masEspecifico = [...coincidencias].sort(
      (a, b) => (cuenta.get(a.toLowerCase()) ?? 0) - (cuenta.get(b.toLowerCase()) ?? 0),
    )[0];
    const dato = datos.get(juego.appid);
    const corto = dato?.horas_al_recomendar != null && dato.horas_al_recomendar < HORAS_DE_SESION_CORTA;
    const sinFriccion = !MOTIVOS_DE_FRICCION.has(dato?.motivo_principal ?? '');
    const sugerencia: Sugerencia = {
      juego,
      coincidencias,
      cobertura: pesoPerfil > 0 ? pesoComun / pesoPerfil : 0,
      afinidad: union > 0 ? pesoComun / union : 0,
      generoMasEspecifico: masEspecifico ?? '',
      juegosConEseGenero: cuenta.get(masEspecifico?.toLowerCase() ?? '') ?? juegos.length,
      empatanConEl: 0,
      encaje: Number(criterios.juegaPoco && corto) + Number(criterios.friccionBaja && sinFriccion),
      razones: [],
    };
    sugerencia.razones = razonesDe(sugerencia, criterios, topePedido, dato, juegos.length);
    return sugerencia;
  });

  puntuados.sort(
    (a, b) =>
      b.cobertura - a.cobertura ||
      b.encaje - a.encaje ||
      critica(b.juego) - critica(a.juego) ||
      precio(a.juego) - precio(b.juego) ||
      b.afinidad - a.afinidad ||
      a.juego.nombre.localeCompare(b.juego.nombre, 'es'),
  );

  const sugerencias = puntuados.slice(0, cuantas).map((s) => ({
    ...s,
    empatanConEl: puntuados.filter(
      (otro) => otro !== s && casiIgual(otro.cobertura, s.cobertura) && otro.encaje === s.encaje,
    ).length,
  }));
  return { sugerencias, candidatos: puntuados.length, motivo: 'ok', topeRelajado };
}

const PESOS = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 });

/** Las razones de una tarjeta, en el orden del formulario, solo de lo que se declaró. */
function razonesDe(
  sugerencia: Sugerencia,
  criterios: CriteriosSugerencia,
  tope: number | null,
  dato: DatosDeJuego | undefined,
  totalJuegos: number,
): Razon[] {
  const razones: Razon[] = [];
  if (sugerencia.coincidencias.length) {
    razones.push({ tipo: 'generos', cumple: true, texto: porQueCoincide(sugerencia, totalJuegos) });
  }
  if (criterios.gasto !== null) {
    const { juego } = sugerencia;
    if (juego.es_gratis) {
      razones.push({ tipo: 'precio', cumple: true, texto: 'Gratuito' });
    } else if (juego.precio_final !== null) {
      const cumple = tope === null || juego.precio_final <= tope;
      const donde = tope === null ? 'sin tope' : cumple ? 'dentro de tu tope' : 'arriba de tu tope';
      razones.push({ tipo: 'precio', cumple, texto: `$${PESOS.format(juego.precio_final)} · ${donde}` });
    }
  }
  const horas = dato?.horas_al_recomendar;
  if (criterios.juegaPoco && horas != null) {
    const aprox = Math.max(1, Math.round(horas));
    razones.push(
      horas < HORAS_DE_SESION_CORTA
        ? { tipo: 'horas', cumple: true, texto: `Quien lo recomienda llevaba ~${aprox} h` }
        : { tipo: 'horas', cumple: false, texto: `Pide más: ~${aprox} h al recomendarlo` },
    );
  }
  if (criterios.friccionBaja) {
    const motivo = dato?.motivo_principal ?? null;
    razones.push(
      motivo && MOTIVOS_DE_FRICCION.has(motivo)
        ? { tipo: 'friccion', cumple: false, texto: `Su queja principal es ${motivo}` }
        : { tipo: 'friccion', cumple: true, texto: 'Sus quejas no son de bugs ni de dificultad' },
    );
  }
  return razones;
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
  'encajan con tus horas y tu tolerancia a la fricción, luego los que tienen nota de la ' +
  'crítica, de mayor a menor, y después los más baratos.';

/** Si algún juego de la lista empata con otro, la nota de desempate tiene sentido. */
export function hayEmpates(sugerencias: readonly Sugerencia[]): boolean {
  return sugerencias.some((s) => s.empatanConEl > 0);
}
