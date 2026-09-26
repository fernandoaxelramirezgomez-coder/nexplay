import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NivelRiesgo } from '../api/contrato';
import { GraficaApilada } from '../compartido/graficas/grafica-apilada';
import { GraficaBarras } from '../compartido/graficas/grafica-barras';
import { GraficaColumnas } from '../compartido/graficas/grafica-columnas';
import { Segmento } from '../compartido/graficas/segmento';
import {
  conclusionAnios,
  conclusionGeneros,
  conclusionGratuitos,
  conclusionMotivoPorJuego,
  conclusionMotivos,
  conclusionPrecio,
  conclusionReparto,
  conclusionSinCritica,
} from '../dominio/conclusiones-panorama';
import { ORDEN_BANDAS } from '../dominio/estantes';
import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';
import { numero, porcentaje, porcentajeFino, rangoDeFechas, textoPrecio } from '../dominio/formato';
import {
  gratuitosPorBanda,
  lanzamientosPorAnio,
  motivoPrincipalPorBanda,
  precioPorBanda,
  repartoDeBandas,
  riesgoPorGenero,
  sinCriticaPorBanda,
} from '../dominio/panorama';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { GraficasResenas } from './graficas-resenas';
import { TarjetaGrafica } from './tarjeta-grafica';

/** Cuántos juegos tiene que tener un género para que su porcentaje signifique algo. */
const MINIMO_POR_GENERO = 5;

/** Panorama: el catálogo y su muestra de reseñas, de conjunto. Nunca muestra el score
 * del modelo, solo bandas, conteos y cifras que se pueden contar en la base. */
@Component({
  selector: 'app-panorama',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, GraficaBarras, GraficaColumnas, GraficaApilada, GraficasResenas, TarjetaGrafica],
  templateUrl: './panorama.html',
  styleUrl: './panorama.css',
})
export class Panorama {
  protected readonly catalogo = inject(CatalogoStore);
  protected readonly panorama = inject(PanoramaStore);

  protected readonly rotulo = ROTULO_RIESGO;
  protected readonly bandas = ORDEN_BANDAS;
  protected readonly minimoGenero = MINIMO_POR_GENERO;

  protected readonly genero = signal('');
  protected readonly banda = signal<NivelRiesgo | ''>('');

  /** El corte que se está mirando: todas las gráficas salen de aquí. */
  protected readonly corte = computed(() => {
    const genero = this.genero();
    const banda = this.banda();
    return this.catalogo
      .juegos()
      .filter((juego) => (!genero || juego.generos.includes(genero)) && (!banda || juego.banda_riesgo === banda));
  });

  protected readonly reparto = computed<Segmento[]>(() =>
    repartoDeBandas(this.corte()).map((tajada) => ({
      etiqueta: `Riesgo ${tajada.banda}`,
      valor: tajada.cuantos,
      cifra: `${tajada.cuantos} · ${porcentaje(tajada.fraccion)}`,
      banda: tajada.banda,
      detalle: `${tajada.cuantos} juegos de ${this.corte().length}`,
    })),
  );

  protected readonly generos = computed<Segmento[]>(() =>
    riesgoPorGenero(this.corte(), MINIMO_POR_GENERO).map((fila) => ({
      etiqueta: fila.genero,
      valor: fila.fraccion,
      cifra: `${porcentaje(fila.fraccion)} de ${fila.total}`,
      banda: 'alto',
      detalle: `${fila.altos} de ${fila.total} juegos de ${fila.genero} están en riesgo alto`,
    })),
  );

  protected readonly precios = computed<Segmento[]>(() =>
    precioPorBanda(this.corte()).map((fila) => ({
      etiqueta: `Riesgo ${fila.banda}`,
      valor: fila.mediana ?? 0,
      cifra:
        fila.mediana === null
          ? 'sin datos'
          : textoPrecio({ es_gratis: false, precio_final: fila.mediana, moneda: 'MXN' }),
      banda: fila.banda,
      detalle: `mediana de ${fila.cuantos} juegos de pago con precio conocido`,
    })),
  );

  protected readonly sinCritica = computed<Segmento[]>(() =>
    sinCriticaPorBanda(this.corte()).map((fila) => ({
      etiqueta: `Riesgo ${fila.banda}`,
      valor: fila.fraccion,
      cifra: `${fila.cuantos} de ${fila.total}`,
      banda: fila.banda,
      detalle: `${fila.cuantos} de ${fila.total} juegos con ese riesgo no tienen nota de Metacritic`,
    })),
  );

  protected readonly gratuitos = computed<Segmento[]>(() =>
    gratuitosPorBanda(this.corte()).map((fila) => ({
      etiqueta: `Riesgo ${fila.banda}`,
      valor: fila.fraccion,
      cifra: `${fila.cuantos} de ${fila.total}`,
      banda: fila.banda,
      detalle: `${fila.cuantos} de ${fila.total} juegos con ese riesgo son gratuitos`,
    })),
  );

  protected readonly anios = computed<Segmento[]>(() =>
    lanzamientosPorAnio(this.corte()).map((fila) => ({
      etiqueta: String(fila.anio),
      valor: fila.cuantos,
      cifra: String(fila.cuantos),
      detalle: `${fila.cuantos} juegos salieron en ${fila.anio}`,
    })),
  );

  protected readonly motivos = computed<Segmento[]>(() =>
    (this.panorama.datos()?.motivos ?? []).map((motivo) => ({
      etiqueta: motivo.motivo,
      valor: motivo.frecuencia,
      cifra: porcentaje(motivo.frecuencia),
      detalle: `${motivo.motivo}: ${porcentaje(motivo.frecuencia)} de las reseñas clasificadas`,
    })),
  );

  private readonly porBandaMotivo = computed(() =>
    motivoPrincipalPorBanda(this.corte(), this.panorama.porAppid()),
  );

  /** Los motivos que aparecen en este corte, en orden fijo, para que el color de cada uno
   * sea el mismo en las tres bandas. */
  protected readonly leyendaMotivos = computed(() => {
    const vistos = new Map<string, number>();
    for (const fila of this.porBandaMotivo()) {
      for (const motivo of fila.motivos) {
        vistos.set(motivo.motivo, (vistos.get(motivo.motivo) ?? 0) + motivo.juegos);
      }
    }
    return [...vistos.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'es'))
      .map(([etiqueta], i) => ({ etiqueta, tono: i % 6 }));
  });

  protected readonly motivoPorBanda = computed(() => {
    const tonos = new Map(this.leyendaMotivos().map(({ etiqueta, tono }) => [etiqueta, tono]));
    return this.porBandaMotivo().map((fila) => ({
      etiqueta: `Riesgo ${fila.banda}`,
      banda: fila.banda,
      total: fila.conMotivo,
      tajadas: fila.motivos.map((motivo) => ({
        etiqueta: motivo.motivo,
        valor: motivo.juegos,
        tono: tonos.get(motivo.motivo) ?? 5,
      })),
    }));
  });

  /** Una frase por gráfica, con el corte de ahora (dominio/conclusiones-panorama.ts). */
  protected readonly conclusiones = computed(() => {
    const corte = this.corte();
    const porAppid = this.panorama.porAppid();
    return {
      reparto: conclusionReparto(corte),
      generos: conclusionGeneros(corte, MINIMO_POR_GENERO),
      precio: conclusionPrecio(corte),
      sinCritica: conclusionSinCritica(corte, porAppid),
      gratuitos: conclusionGratuitos(corte),
      anios: conclusionAnios(corte),
      motivos: conclusionMotivos(this.panorama.datos()?.motivos ?? []),
      motivoPorBanda: conclusionMotivoPorJuego(this.porBandaMotivo()),
    };
  });

  /** Con nota y en riesgo alto son pocos juegos: la ⓘ lo dice con el número del corte. */
  protected readonly altosConNota = computed(
    () => this.corte().filter((juego) => juego.banda_riesgo === 'alto' && juego.metacritic !== null).length,
  );

  /** Las cifras clave son de toda la muestra, como dice su rótulo: no cambian con los filtros. */
  protected readonly sinNota = computed(() => this.catalogo.juegos().filter((juego) => juego.metacritic === null).length);

  protected readonly descargaJuegos = computed(() => {
    const ventana = this.panorama.datos()?.descargas.appdetails;
    return ventana ? rangoDeFechas(ventana.desde, ventana.hasta) : '';
  });

  protected readonly descargaResenas = computed(() => {
    const ventana = this.panorama.datos()?.descargas.appreviews;
    return ventana ? rangoDeFechas(ventana.desde, ventana.hasta) : '';
  });

  protected readonly num = numero;
  protected readonly pct = porcentaje;
  protected readonly pctFino = porcentajeFino;
}
