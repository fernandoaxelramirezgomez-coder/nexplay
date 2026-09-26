import { JuegoCatalogo, MotivoInsatisfaccion, PerfilJugador } from '../api/contrato';
import { generosEnComun } from './afinidad';
import { Segmento } from './segunda-opinion';
import { rangoDeComprasCorto } from './opciones-perfil';

/** Las dos horas con las que se define el arrepentimiento temprano (120 minutos). */
const HORAS_DE_LA_VENTANA = 2;

/** Steam devuelve el dinero si se cumplen las dos condiciones: menos de 2 horas jugadas
 * y menos de 14 días desde la compra. El plazo corre aunque no se juegue. */
const DIAS_DE_REEMBOLSO = 14;

/** Por qué este juego le tocaría a quien declaró este perfil, en tres líneas: si entra en
 * sus géneros, en cuántas sesiones llegaría a las dos horas de la ventana de reembolso y
 * cuánto pesa la compra. Es contexto, no una recomendación, y no mueve el riesgo: el
 * modelo es de título y no usa ningún dato del perfil.
 *
 * Tres líneas cortas, de una ojeada cada una, y no tres párrafos: en prosa esto se leía
 * como una explicación del riesgo, que es justo lo que no es. Lo que decía la fricción ya
 * lo dice la sección de motivos con su porcentaje, así que aquí sobraba.
 *
 * Devuelve null si no hay perfil declarado; entonces no hay historia que contar. */
export function historiaPerfil(
  perfil: PerfilJugador | null,
  juego: JuegoCatalogo,
  _motivos: readonly MotivoInsatisfaccion[] = [],
): Segmento[][] | null {
  if (!perfil) {
    return null;
  }

  return [lineaGeneros(perfil, juego), lineaTiempo(perfil), lineaCompra(perfil, juego)].filter(
    (linea) => linea.length,
  );
}

function lineaGeneros(perfil: PerfilJugador, juego: JuegoCatalogo): Segmento[] {
  if (!perfil.tags_preferidos.length) {
    return [{ texto: 'No declaraste géneros: no hay afinidad que medir.' }];
  }

  const comunes = generosEnComun(juego.generos, perfil.tags_preferidos);
  if (comunes.length) {
    return [{ texto: 'Dentro', clave: true }, { texto: ` de tus géneros: ${comunes.join(', ')}.` }];
  }
  return [
    { texto: 'Fuera', clave: true },
    { texto: ` de tus géneros: Steam lo pone en ${juego.generos.join(', ') || 'ningún género'}.` },
  ];
}

function lineaTiempo(perfil: PerfilJugador): Segmento[] {
  const horas = perfil.horas_por_semana;
  if (horas <= 0) {
    return [];
  }

  const dias = (HORAS_DE_LA_VENTANA / horas) * 7;
  if (dias > DIAS_DE_REEMBOLSO) {
    return [
      { texto: `${HORAS_DE_LA_VENTANA} h te tomarían más de ${DIAS_DE_REEMBOLSO} días: el reembolso caduca antes.` },
    ];
  }
  return [{ texto: `Llegas a ${HORAS_DE_LA_VENTANA} h en 1–2 sesiones, dentro del reembolso.` }];
}

function lineaCompra(perfil: PerfilJugador, juego: JuegoCatalogo): Segmento[] {
  if (juego.es_gratis) {
    return [{ texto: 'Gratuito: probarlo solo te cuesta el rato.' }];
  }
  if (juego.precio_final === null) {
    return [{ texto: 'Steam no devolvió precio: no se puede decir cuánto pesa.' }];
  }

  const compras = perfil.compras_al_anio;
  const rango = rangoDeComprasCorto(compras);
  if (compras > 0 && compras <= 6) {
    return [{ texto: 'Sería una de tus ' }, { texto: `${rango} compras`, clave: true }, { texto: ' del año.' }];
  }
  return [{ texto: `Compras ${rango} al año: este sería uno más.` }];
}

/** La línea que acompaña siempre a la historia, para que nadie la lea como parte del
 * cálculo. Va aparte porque no es narración: es una advertencia. */
export const AVISO_HISTORIA =
  'Esto es contexto sobre ti y el juego, no una recomendación. Tu perfil no cambia el riesgo estimado: el' +
  ' modelo solo usa datos del juego.';
