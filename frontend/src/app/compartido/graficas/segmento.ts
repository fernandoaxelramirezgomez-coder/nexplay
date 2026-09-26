import { NivelRiesgo } from '../../api/contrato';

/** Una barra, columna o tajada de cualquiera de las gráficas. El valor manda el tamaño;
 * `cifra` es lo que se lee al lado, siempre en texto, para que la gráfica se entienda sin
 * distinguir colores. `detalle` es el título accesible de ese segmento. */
export interface Segmento {
  etiqueta: string;
  valor: number;
  cifra: string;
  /** Pinta con el color de esa banda de riesgo. Sin banda, usa el acento. */
  banda?: NivelRiesgo;
  detalle?: string;
  /** Marca el segmento como el que explica la etiqueta del modelo. */
  destacado?: boolean;
}
