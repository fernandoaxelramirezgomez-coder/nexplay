// Contrato de la API FastAPI (api/schemas.py), escrito a partir de sus respuestas
// reales. Si schemas.py cambia, este archivo se desfasa sin avisar: revisar ambos.

export type Plataforma = 'pc' | 'playstation' | 'xbox' | 'nintendo';
export type NivelRiesgo = 'bajo' | 'medio' | 'alto';
export type NivelFriccion = 'baja' | 'media' | 'alta';
export type NivelRelativo = 'alto' | 'bajo';
export type DireccionFactor = 'aumenta' | 'reduce';

/** GET /catalogo?q=&genero=&riesgo= */
export interface JuegoCatalogo {
  appid: number;
  nombre: string;
  plataformas: Plataforma[];
  /** Géneros de Steam en español, con mayúsculas: 'Acción', 'Rol', 'Free to Play'. */
  generos: string[];
  metacritic: number | null;
  es_gratis: boolean;
  /** Ya en pesos. null = precio desconocido (o juego gratuito). */
  precio_final: number | null;
  moneda: string | null;
  /** Texto de Steam, p. ej. '16 FEB 2023'; no es una fecha ISO. */
  fecha_lanzamiento: string | null;
  /** short_description de Steam; null cuando la tienda solo la tiene en inglés. */
  descripcion: string | null;
  portada_url: string;
  /** Primer tráiler de Steam en HLS (.m3u8); null si el juego no tiene videos. */
  video_url: string | null;
  tienda_url: string;
  /** "Riesgo general": el riesgo del título, igual para cualquier perfil. */
  banda_riesgo: NivelRiesgo;
  /** Solo para ordenar dentro de una banda. Nunca se muestra. */
  riesgo: number;
}

export interface FiltrosCatalogo {
  q?: string;
  genero?: string;
  riesgo?: NivelRiesgo;
}

/** POST /perfil (cuerpo) */
export interface FormularioAlta {
  compras_al_anio: number;
  horas_por_semana: number;
  tolerancia_friccion: 1 | 2 | 3 | 4 | 5;
  /** Géneros preferidos del catálogo; la API los devuelve en minúsculas. El modelo no los usa. */
  tags_preferidos: string[];
  tags_rechazados: string[];
  plataforma: Plataforma;
}

/** POST /perfil (respuesta) */
export interface PerfilJugador {
  compras_al_anio: number;
  horas_por_semana: number;
  tolerancia_friccion: NivelFriccion;
  tags_preferidos: string[];
  tags_rechazados: string[];
  plataforma: Plataforma;
  segmento: 'novato' | 'veterano';
  disponibilidad: 'baja' | 'media' | 'alta';
}

/** POST /prediccion (cuerpo) */
export interface SolicitudPrediccion {
  perfil: PerfilJugador;
  appid: number;
}

export type Evidencia = 'solida' | 'debil';

export interface FactorPrediccion {
  etiqueta: string;
  /** Nota y precio: contra la referencia del catálogo. Sí/no: alto si se cumple. */
  valor_relativo: NivelRelativo;
  /** Log-odds. No se muestra. */
  contribucion: number;
  direccion: DireccionFactor;
  /** Del bootstrap del notebook 00 (§3.4): la crítica es sólida; precio, descuento y gratuidad, débiles. */
  evidencia: Evidencia;
  /** Aporte chico: casi no mueve la estimación y se muestra sin flecha. */
  cerca_de_lo_tipico: boolean;
  /** La nota o el precio en MXN; null en las de sí o no y en el precio que falta. */
  valor: number | null;
  /** Promedio de la nota o precio mediano del catálogo, contra el que se lee `valor`. */
  referencia: number | null;
  /** Falta el dato y el modelo usó un sustituto (el precio, tomado como 0). */
  imputado: boolean;
}

export interface AvisoEstimacion {
  codigo: 'gratis_extrapola' | 'precio_imputado';
  texto: string;
}

/** POST /prediccion (respuesta) */
export interface PrediccionRiesgo {
  appid: number;
  /** No se muestra: el score no es una probabilidad calibrada. */
  riesgo: number;
  nivel: NivelRiesgo;
  modelo_version: string;
  nota_plataforma: string | null;
  /** Hasta 3, ordenados por magnitud. */
  factores: FactorPrediccion[];
  /** Lo que hace menos firme la estimación: juego gratis, precio que falta. */
  avisos: AvisoEstimacion[];
}

export interface MotivoInsatisfaccion {
  motivo: string;
  /** 0–1, sobre las reseñas clasificadas (no sobre n_casos). */
  frecuencia: number;
}

/** GET /explicacion/{appid} */
export interface ExplicacionJuego {
  appid: number;
  nombre: string;
  /** Reseñas de arrepentimiento temprano (Y=1) analizadas. */
  n_casos: number;
  /** 0–1: proporción que menciona al menos un motivo. */
  pct_clasificados: number;
  /** Vacío si hay menos de 5 casos. */
  motivos: MotivoInsatisfaccion[];
}

/** 404: detail es texto. 422: detail es la lista de errores de Pydantic. */
export interface ErrorApi {
  detail: string | { loc: (string | number)[]; msg: string; type: string }[];
}

/** El voto propio sobre la segunda opinión. Los comentarios son un hilo aparte. */
/** PUT /valoraciones/{appid} */
export interface SolicitudValoracion {
  /** Id anónimo del navegador: identifica, no autentica. */
  usuario: string;
  /** Estrellas, entero de 1 a 5. */
  calificacion: number;
}

/** GET/PUT/DELETE /valoraciones/{appid} */
export interface ResumenValoraciones {
  appid: number;
  /** Promedio de estrellas; null si nadie ha calificado todavía. */
  promedio: number | null;
  total: number;
  /** Las estrellas de quien pregunta, si ya calificó. */
  mia: number | null;
}

/** Hilo público de /comentarios/{appid}, del más viejo al más nuevo y sin identidad:
 * de quién es cada uno solo llega resumido en `es_mio`. */
export interface Comentario {
  id: number;
  texto: string;
  /** Cuándo apareció en el hilo; no cambia al editar. */
  creado: string;
  /** Cuándo se editó por última vez, o null. Es la fecha que se muestra si existe. */
  actualizado: string | null;
  editado: boolean;
  reacciones: number;
  reaccione_mia: boolean;
  /** Solo entonces se puede editar o eliminar desde la app. */
  es_mio: boolean;
}

/** POST /comentarios/{appid} y PUT /comentarios/{appid}/{id} */
export interface SolicitudComentario {
  /** Se guarda para el límite de frecuencia; la API nunca lo devuelve. */
  usuario: string;
  /** Hasta 500 caracteres. */
  texto: string;
}

/** PUT /comentarios/{appid}/{id}/reaccion: un pulgar arriba por persona, en toggle. */
export interface ReaccionComentario {
  comentario_id: number;
  reacciones: number;
  reaccione_mia: boolean;
}

/** POST /nia: el chat de la ficha. */
/** Lo que Nia ofrece al cerrar; las reglas lo cumplen cuando la persona dice «sí». */
export type IntencionOferta =
  | 'riesgo'
  | 'resenas'
  | 'ficha'
  | 'resenas_de_varios'
  | 'ordenar'
  | 'buscar'
  | 'generos'
  | 'como_se_calcula'
  | 'de_donde_salen'
  | 'crear_perfil'
  | 'elegir_juego'
  | 'resumen'
  | 'aclarar';

/** La pregunta con que cerró Nia, como dato: vuelve en el historial tal cual llegó. */
export interface OfertaNia {
  intencion: IntencionOferta;
  juegos: number[];
  criterio?: 'precio' | 'riesgo' | 'nota' | null;
  pregunta?: string | null;
}

export interface MensajeChat {
  rol: 'usuario' | 'nia';
  /** Hasta 500 caracteres. */
  contenido: string;
  /** Solo en mensajes de Nia: lo que ofreció al cerrar. */
  oferta?: OfertaNia | null;
  /** Solo en mensajes de Nia: los juegos de sus tarjetas («esos dos», «ese juego»). Hasta 8. */
  juegos?: number[];
}

/** Un juego sugerido con el perfil, con su porqué ya escrito: es lo único del perfil que
 * viaja a Nia. */
export interface SugerenciaNia {
  appid: number;
  razones: string[];
}

export interface SolicitudNia {
  /** Id anónimo del navegador; solo se usa para el límite de frecuencia. */
  usuario: string;
  /** El juego del que se habla; sin él, Nia habla del catálogo entero. */
  appid?: number;
  /** El hilo, hasta 40 mensajes, incluida la pregunta nueva. */
  mensajes: MensajeChat[];
  /** Las sugerencias que el navegador calculó con el perfil. */
  sugerencias?: SugerenciaNia[];
  /** Los géneros declarados, para decir cuáles coinciden con un juego. Es lo único del
   * formulario que viaja; con IA, llega a OpenAI junto con la pregunta. */
  generos?: string[];
}

export interface RespuestaNia {
  respuesta: string;
  /** 'demostracion' = armada con reglas sobre los datos, sin modelo de lenguaje. */
  /** 'reglas': hay modelo, pero esta respuesta no lo usó (pedir el juego, resumir…). */
  modo: 'openai' | 'demostracion' | 'reglas';
  modelo: string | null;
  aviso: string | null;
  /** Identifica esta respuesta para poder votarla. */
  id: string;
  /** Qué consultó antes de responder, en orden; vacío si no consultó nada. */
  pasos: string[];
  /** Appids que la respuesta menciona y que una herramienta le devolvió en ese turno. */
  juegos: number[];
  /** Appids para las tarjetas «Sugerencia según tu perfil». */
  sugerencias?: number[];
  /** Lo que ofrece la pregunta con que cierra; vuelve en el historial dentro del mensaje. */
  oferta?: OfertaNia | null;
  /** La pregunta es de un juego y no hay ninguno fijado: el chat abre el buscador. */
  pide_juego?: boolean;
  /** Pidieron sugerencias sin perfil: el chat invita a crearlo. */
  pide_perfil?: boolean;
  /** La pregunta no encaja con el catálogo: solo entonces el chat dice sus avisos. */
  fuera_de_tema?: boolean;
  /** Qué prompt la produjo; 'reglas' en modo demostración. No se muestra. */
  version_prompt: string;
}

/** GET /nia/opiniones: lo que Nia opina de un juego en una frase, armado con las reglas del
 * chat sobre los datos del catálogo. No pasa por el modelo de lenguaje ni se guarda. */
export interface OpinionNia {
  appid: number;
  nombre: string;
  nivel: NivelRiesgo;
  pregunta: string;
  respuesta: string;
}

/** 1 es 👍 y -1 es 👎. */
export type VotoNiaValor = 1 | -1;

/** PUT /nia/valoracion/{id} */
export interface SolicitudVotoNia {
  usuario: string;
  voto: VotoNiaValor;
  /** Solo acompaña al 👎, y solo uno de MOTIVOS_VOTO_NIA. */
  motivo?: string;
  /** Solo con 👎 y «otro motivo»: qué mejorar, hasta 280 caracteres. Se ve sin nombre en el buzón de /admin. */
  sugerencia?: string;
}

/** DELETE /nia/valoracion/{id}: el usuario va en el cuerpo, no en la URL. */
export interface SolicitudQuitarVotoNia {
  usuario: string;
}

export interface VotoNia {
  id_respuesta: string;
  voto: VotoNiaValor | null;
  motivo: string | null;
  sugerencia?: string | null;
}

/** GET /estado: el sistema de un vistazo, para /admin. De OpenAI solo el booleano y el
 * nombre del modelo: la clave nunca sale de la API. */
export interface EstadoSistema {
  nia_con_openai: boolean;
  modelo_nia: string | null;
  /** Release de datos del catálogo servido (data-v3); null si la base no trae su marca. */
  datos_release: string | null;
  juegos_catalogo: number;
  modelo_version: string;
  modelo_datos: string | null;
  modelo_juegos_entrenamiento: number | null;
}

/** GET /nia/sugerencias: el buzón de /admin. Sin usuario ni pregunta: /admin no tiene contraseña. */
export interface BuzonSugerencias {
  votos_a_favor: number;
  votos_en_contra: number;
  /** Los 👎 por motivo, con «sin motivo» al final. */
  por_motivo: { motivo: string; cuantos: number }[];
  /** Las de «otro motivo» con texto, de la más reciente. */
  sugerencias: { texto: string; cuando: string }[];
}

/** GET /panorama: la muestra de reseñas detrás del catálogo. Es descriptivo —sale de
 * contar la base, no de predecir—, así que ninguna cifra de aquí es un score. */
export interface TramoPlaytime {
  /** "Menos de 2 h" es la ventana de reembolso de Steam: ahí se define la etiqueta. */
  tramo: string;
  cuantas: number;
  fraccion: number;
}

export interface CalidadMuestra {
  compradas_en_steam: number;
  recibidas_gratis: number;
  acceso_anticipado: number;
  con_voto_util: number;
  /** num_games_owned = 0: bandera de privacidad, no biblioteca vacía. */
  perfiles_privados: number;
  en_ingles: number;
  /** El conteo, no la proporción: 184,366 de 184,367 redondea a 1.0 y diría "todas". */
  resenas_en_ingles: number;
}

/** Una fila por juego. No trae la banda: se cruza con /catalogo, que es donde vive. */
export interface JuegoPanorama {
  appid: number;
  resenas: number;
  casos_senal: number;
  prevalencia: number;
  resenas_en_steam: number | null;
  /** De esas, las positivas; con resenas_en_steam da el porcentaje de Steam. */
  positivas_en_steam: number | null;
  /** Resumen de Steam, en inglés: 'Very Positive', 'Mixed'… */
  consenso: string | null;
  /** null si el juego no llega al mínimo de casos para nombrar uno. */
  motivo_principal: string | null;
  /** Mediana de horas jugadas de quienes lo recomiendan; null con menos de 10 positivas. */
  horas_al_recomendar: number | null;
}

export interface PanoramaCatalogo {
  juegos: number;
  resenas_descargadas: number;
  resenas_en_steam: number;
  cobertura: number;
  ventana: { desde: string; hasta: string };
  /** Cuándo se descargó cada fuente (UTC, YYYY-MM-DD). La ventana es cuándo se escribieron. */
  descargas: { appdetails: { desde: string; hasta: string }; appreviews: { desde: string; hasta: string } };
  /** Con qué se entrenó el modelo servido: los juegos del catálogo que no están aquí son
   * los que nunca vio. */
  modelo: {
    version: string;
    datos: string | null;
    juegos_entrenamiento: number | null;
    resenas_entrenamiento: number | null;
  };
  casos_senal: number;
  prevalencia: number;
  playtime_al_resenar: TramoPlaytime[];
  muestra: CalidadMuestra;
  motivos: MotivoInsatisfaccion[];
  resenas_clasificadas: number;
  por_juego: JuegoPanorama[];
}
