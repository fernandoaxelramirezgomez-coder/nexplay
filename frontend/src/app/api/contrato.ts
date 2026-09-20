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
  tienda_url: string;
  /** "Riesgo general": calculado con el perfil neutro de api/catalogo.py. */
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

export interface FactorPrediccion {
  etiqueta: string;
  valor_relativo: NivelRelativo;
  /** Log-odds. No se muestra. */
  contribucion: number;
  direccion: DireccionFactor;
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
export interface Valoracion {
  util: boolean;
  actualizado: string;
}

/** PUT /valoraciones/{appid} */
export interface SolicitudValoracion {
  /** Id anónimo del navegador: identifica, no autentica. */
  usuario: string;
  util: boolean;
}

/** GET/PUT/DELETE /valoraciones/{appid} */
export interface ResumenValoraciones {
  appid: number;
  utiles: number;
  no_utiles: number;
  total: number;
  mia: Valoracion | null;
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
export interface MensajeChat {
  rol: 'usuario' | 'nia';
  /** Hasta 500 caracteres. */
  contenido: string;
}

export interface SolicitudNia {
  /** Id anónimo del navegador; solo se usa para el límite de frecuencia. */
  usuario: string;
  appid: number;
  /** Hasta 10 mensajes, incluida la pregunta nueva. */
  mensajes: MensajeChat[];
  /** Si va, la banda del contexto es la del perfil declarado. */
  perfil?: PerfilJugador;
}

export interface RespuestaNia {
  respuesta: string;
  /** 'demostracion' = armada con reglas sobre los datos, sin modelo de lenguaje. */
  modo: 'openai' | 'demostracion';
  modelo: string | null;
  aviso: string | null;
}
