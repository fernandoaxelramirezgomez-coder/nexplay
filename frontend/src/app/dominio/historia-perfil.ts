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

/** La ventana que define la variable: 120 minutos, el plazo de reembolso de Steam. */
const HORAS_DE_LA_VENTANA = 2;

/** Por qué este juego le tocaría a quien declaró este perfil: géneros, fricción, tiempo
 * y cuánto pesa una compra. Es contexto, no una recomendación, y no mueve el riesgo:
 * el modelo solo usa las compras al año, nunca los gustos ni las horas.
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

  const semanas = HORAS_DE_LA_VENTANA / horas;
  if (semanas >= 1) {
    return [
      {
        texto:
          `Con ${horas} h por semana, las dos primeras horas —la ventana en la que se mide el arrepentimiento` +
          ' temprano— te toman más de una semana: cuando notes si te gustó, el reembolso de Steam ya venció. ',
      },
    ];
  }
  return [
    {
      texto:
        `Con ${horas} h por semana, esas dos primeras horas se te van en la primera sesión o dos,` +
        ' todavía dentro del plazo de reembolso de Steam. ',
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
      { texto: `Compras alrededor de ${compras} juegos al año, así que este sería ` },
      { texto: 'una de tus pocas compras', clave: true },
      { texto: ` del año.` },
    ];
  }
  return [{ texto: `Con unas ${compras} compras al año, este es uno más de los que pruebas.` }];
}

/** La línea que acompaña siempre a la historia, para que nadie la lea como parte del
 * cálculo. Va aparte porque no es narración: es una advertencia. */
export const AVISO_HISTORIA =
  'Esto es contexto sobre ti y el juego, no una recomendación. Tus gustos y tus horas no cambian el riesgo' +
  ' estimado: el modelo no los usa.';
