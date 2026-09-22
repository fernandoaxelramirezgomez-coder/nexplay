import { JuegoCatalogo, MotivoInsatisfaccion, PerfilJugador } from '../api/contrato';
import { generosEnComun } from './afinidad';
import { porcentaje } from './formato';
import { Segmento } from './segunda-opinion';

/** Motivos que son fricción: lo que choca con quien declaró aguantar poca. */
const MOTIVOS_DE_FRICCION: Record<string, string> = {
  bugs: 'bugs',
  rendimiento: 'problemas de rendimiento',
  dificultad: 'una dificultad dura',
  controles: 'controles incómodos',
};

/** Las dos horas con las que se define el arrepentimiento temprano (120 minutos). */
const HORAS_DE_LA_VENTANA = 2;

/** Steam devuelve el dinero si se cumplen las dos condiciones: menos de 2 horas jugadas
 * y menos de 14 días desde la compra. El plazo corre aunque no se juegue. */
const DIAS_DE_REEMBOLSO = 14;

/** Por qué este juego le tocaría a quien declaró este perfil: géneros, fricción, tiempo
 * y cuánto pesa una compra. Es contexto, no una recomendación, y no mueve el riesgo:
 * el modelo es de título y no usa ningún dato del perfil.
 *
 * Devuelve null si no hay perfil declarado; entonces no hay historia que contar. */
export function historiaPerfil(
  perfil: PerfilJugador | null,
  juego: JuegoCatalogo,
  motivos: readonly MotivoInsatisfaccion[],
): Segmento[] | null {
  if (!perfil) {
    return null;
  }

  return [
    ...parrafoGeneros(perfil, juego),
    ...parrafoFriccion(perfil, motivos),
    ...parrafoTiempo(perfil),
    ...parrafoCompra(perfil, juego),
  ];
}

function parrafoGeneros(perfil: PerfilJugador, juego: JuegoCatalogo): Segmento[] {
  if (!perfil.tags_preferidos.length) {
    return [
      { texto: 'No declaraste géneros, así que de la afinidad no se puede decir nada. Este juego está en Steam como ' },
      { texto: juego.generos.join(' y ') || 'sin géneros registrados' },
      { texto: '. ' },
    ];
  }

  const comunes = generosEnComun(juego.generos, perfil.tags_preferidos);
  if (comunes.length) {
    return [
      { texto: 'Este juego cae ' },
      { texto: 'dentro', clave: true },
      { texto: ` de lo que sueles jugar: está clasificado en ${comunes.join(' y ')}. ` },
    ];
  }
  return [
    { texto: 'Este juego queda ' },
    { texto: 'fuera', clave: true },
    {
      texto:
        ` de los géneros que declaraste: Steam lo clasifica en ${juego.generos.join(' y ') || 'ningún género'}.` +
        ' Estrenar un género es justo cuando cuesta más saber si algo te va a enganchar. ',
    },
  ];
}

function parrafoFriccion(perfil: PerfilJugador, motivos: readonly MotivoInsatisfaccion[]): Segmento[] {
  const principal = motivos[0];
  const friccion = principal ? MOTIVOS_DE_FRICCION[principal.motivo] : undefined;

  if (!principal) {
    return [{ texto: 'No hay suficientes reseñas de arrepentimiento temprano para saber qué molesta aquí. ' }];
  }
  if (!friccion) {
    return [
      {
        texto:
          'Entre las reseñas de arrepentimiento temprano, lo que más se menciona es' +
          ` ${principal.motivo} (${porcentaje(principal.frecuencia)} de las clasificadas),` +
          ' que no es fricción de juego. ',
      },
    ];
  }

  if (perfil.tolerancia_friccion === 'baja') {
    return [
      {
        texto:
          'Dijiste que aguantas poca fricción, y entre las reseñas de arrepentimiento temprano lo que más' +
          ` se menciona es ${friccion}`,
      },
      { texto: ` (${porcentaje(principal.frecuencia)} de las clasificadas): es ` },
      { texto: 'justo lo que menos toleras', clave: true },
      { texto: '. ' },
    ];
  }
  if (perfil.tolerancia_friccion === 'alta') {
    return [
      {
        texto:
          'Entre las reseñas de arrepentimiento temprano, lo que más se menciona es' +
          ` ${friccion} (${porcentaje(principal.frecuencia)} de las clasificadas), y dijiste que eso no te frena. `,
      },
    ];
  }
  return [
    {
      texto:
        'Entre las reseñas de arrepentimiento temprano, lo que más se menciona es' +
        ` ${friccion} (${porcentaje(principal.frecuencia)} de las clasificadas),` +
        ' con una tolerancia a la fricción como la que declaraste. ',
    },
  ];
}

function parrafoTiempo(perfil: PerfilJugador): Segmento[] {
  const horas = perfil.horas_por_semana;
  if (horas <= 0) {
    return [];
  }

  const dias = (HORAS_DE_LA_VENTANA / horas) * 7;
  if (dias > DIAS_DE_REEMBOLSO) {
    return [
      {
        texto:
          `Con ${horas} h por semana tardarías más de ${DIAS_DE_REEMBOLSO} días en llegar a las dos horas con` +
          ' las que se mide el arrepentimiento temprano, y el reembolso de Steam caduca a los' +
          ` ${DIAS_DE_REEMBOLSO} días de la compra aunque no hayas jugado. `,
      },
    ];
  }
  return [
    {
      texto:
        `Con ${horas} h por semana llegas a esas dos horas en la primera sesión o dos, dentro de los` +
        ` ${DIAS_DE_REEMBOLSO} días en que Steam todavía admite el reembolso. `,
    },
  ];
}

function parrafoCompra(perfil: PerfilJugador, juego: JuegoCatalogo): Segmento[] {
  if (juego.es_gratis) {
    return [{ texto: 'Y es gratuito, así que probarlo no te cuesta más que el rato.' }];
  }
  if (juego.precio_final === null) {
    return [{ texto: 'De cuánto pesaría la compra no se puede decir nada: Steam no devolvió precio para este juego.' }];
  }

  const compras = perfil.compras_al_anio;
  if (compras > 0 && compras <= 12) {
    return [
      { texto: `Compras alrededor de ${compras} ${compras === 1 ? 'juego' : 'juegos'} al año, así que este sería ` },
      { texto: 'una de tus pocas compras', clave: true },
      { texto: ` del año.` },
    ];
  }
  return [{ texto: `Con unas ${compras} compras al año, este es uno más de los que pruebas.` }];
}

/** Trozo de texto; `dato` marca una cifra (porcentaje, horas, días, juegos o compras)
 * que la vista pinta en la fuente mono, como el resto de los datos de la app. */
export interface Trozo {
  texto: string;
  dato?: boolean;
}

const PATRON_DATO = '\\d+(?:[.,]\\d+)?\\s?(?:%|h\\b|días?\\b|juegos?\\b|compras?\\b)';
const PARTIR = new RegExp(`(${PATRON_DATO})`);
const ES_DATO = new RegExp(`^${PATRON_DATO}$`);

/** Separa las cifras del texto corrido sin cambiar una sola letra: al unir los trozos
 * sale el texto original. */
export function partirDatos(texto: string): Trozo[] {
  return texto
    .split(PARTIR)
    .filter((parte) => parte !== '')
    .map((parte) => (ES_DATO.test(parte) ? { texto: parte, dato: true } : { texto: parte }));
}

/** La línea que acompaña siempre a la historia, para que nadie la lea como parte del
 * cálculo. Va aparte porque no es narración: es una advertencia. */
export const AVISO_HISTORIA =
  'Esto es contexto sobre ti y el juego, no una recomendación. Tu perfil no cambia el riesgo estimado: el' +
  ' modelo solo usa datos del juego.';
