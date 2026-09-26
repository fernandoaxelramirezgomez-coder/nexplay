import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { GraficaApilada } from '../compartido/graficas/grafica-apilada';
import { GraficaBarras } from '../compartido/graficas/grafica-barras';
import { GraficaColumnas } from '../compartido/graficas/grafica-columnas';
import { Segmento } from '../compartido/graficas/segmento';
import { conclusionConsenso, conclusionPlaytime, conclusionSenal } from '../dominio/conclusiones-panorama';
import { mesAnio, numero, porcentaje, porcentajeFino } from '../dominio/formato';
import { CONSENSO_STEAM, consensoPorBanda, positivosEnBandaAlta, senalPorBanda } from '../dominio/panorama';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { TarjetaGrafica } from './tarjeta-grafica';

/** Las tres lecturas que explican de qué está hecha la señal: cuánto había jugado quien
 * escribió cada reseña, cuántas de esas reseñas tiene cada nivel, y qué dice Steam de los
 * mismos juegos. El host no ocupa caja: sus tres tarjetas entran a la rejilla de Panorama. */
@Component({
  selector: 'app-graficas-resenas',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GraficaBarras, GraficaColumnas, GraficaApilada, TarjetaGrafica],
  host: { style: 'display: contents' },
  template: `
    @if (datos(); as p) {
      <app-tarjeta-grafica
        idPrueba="grafica-playtime"
        titulo="Cuánto habían jugado al reseñar"
        [conclusion]="conclusionPlaytime()"
        [fuente]="fuentePlaytime()"
      >
        <div ayuda>
          <p>
            La etiqueta del modelo sale del primer tramo: menos de dos horas es la ventana en la que Steam
            devuelve el dinero. Son {{ num(tramoCorto().cuantas) }} reseñas de {{ num(p.resenas_descargadas) }}.
          </p>
          <p>Es de toda la muestra: no cambia con los filtros.</p>
        </div>
        <app-grafica-columnas [segmentos]="playtime()" idPrueba="columnas-playtime" />
      </app-tarjeta-grafica>

      <app-tarjeta-grafica
        idPrueba="grafica-senal"
        titulo="Reseñas con señal por nivel"
        [conclusion]="conclusionSenal()"
        fuente="reseñas de Steam (appreviews) con menos de 2 h jugadas y voto negativo"
      >
        <p ayuda>
          El riesgo lo pone el modelo con datos del juego (precio, gratuidad, descuento y cobertura de crítica) y sin
          mirar estas reseñas. Aun así, el riesgo alto tiene {{ vecesMas() }} veces más reseñas con señal que el bajo.
        </p>
        <app-grafica-barras [segmentos]="senal()" [maximo]="topeSenal()" idPrueba="barras-senal" />
      </app-tarjeta-grafica>

      <app-tarjeta-grafica
        idPrueba="grafica-consenso"
        titulo="Qué dice Steam de esos mismos juegos"
        [conclusion]="conclusionConsenso()"
        fuente="el resumen de reseñas de Steam (appreviews)"
      >
        <p ayuda>
          El resumen de Steam no entra al modelo, así que coincidir con él no es hacer trampa. Coincide a grandes
          rasgos, pero {{ positivos().length }} de los {{ juegosAltos() }} juegos de riesgo alto tienen reseñas muy
          positivas o extremadamente positivas en Steam: la nota general mide toda la partida, no las primeras dos
          horas.
        </p>
        <app-grafica-apilada [filas]="consenso()" [leyenda]="leyenda()" idPrueba="apilada-consenso" />
      </app-tarjeta-grafica>
    }
  `,
})
export class GraficasResenas {
  /** El corte que se está mirando. Sin él, el catálogo entero. */
  readonly juegos = input<JuegoCatalogo[]>();

  private readonly catalogo = inject(CatalogoStore);
  private readonly panorama = inject(PanoramaStore);
  private readonly corte = computed(() => this.juegos() ?? this.catalogo.juegos());
  protected readonly datos = this.panorama.datos;

  /** Solo las etiquetas que de verdad aparecen en el corte: una leyenda con nueve
   * entradas de las que cinco no están en ninguna barra no explica nada. */
  protected readonly leyenda = computed(() => {
    const presentes = new Set(this.consenso().flatMap((fila) => fila.tajadas.map((t) => t.etiqueta)));
    const orden = [...CONSENSO_STEAM.map(({ etiqueta, tono }) => ({ etiqueta, tono })), { etiqueta: 'Sin dato', tono: 5 }];
    return orden.filter(
      (entrada, i, todas) =>
        presentes.has(entrada.etiqueta) && todas.findIndex((o) => o.etiqueta === entrada.etiqueta) === i,
    );
  });

  protected readonly tramoCorto = computed(
    () => this.datos()?.playtime_al_resenar[0] ?? { tramo: '', cuantas: 0, fraccion: 0 },
  );

  protected readonly playtime = computed<Segmento[]>(() =>
    (this.datos()?.playtime_al_resenar ?? []).map((tramo, i) => ({
      etiqueta: tramo.tramo,
      valor: tramo.cuantas,
      cifra: porcentaje(tramo.fraccion),
      destacado: i === 0,
      detalle: `${tramo.tramo}: ${numero(tramo.cuantas)} reseñas, ${porcentaje(tramo.fraccion)} del total`,
    })),
  );

  protected readonly conclusionPlaytime = computed(() => conclusionPlaytime(this.datos()?.playtime_al_resenar ?? []));

  protected readonly fuentePlaytime = computed(() => {
    const p = this.datos();
    return p
      ? `${numero(p.resenas_descargadas)} reseñas de Steam (appreviews), escritas entre ${mesAnio(p.ventana.desde)} y ${mesAnio(p.ventana.hasta)}`
      : 'reseñas de Steam (appreviews)';
  });

  private readonly porBanda = computed(() => senalPorBanda(this.corte(), this.panorama.porAppid()));

  protected readonly senal = computed<Segmento[]>(() =>
    this.porBanda().map((fila) => ({
      etiqueta: `Riesgo ${fila.banda}`,
      valor: fila.prevalencia,
      cifra: porcentajeFino(fila.prevalencia),
      banda: fila.banda,
      detalle: `${numero(fila.casos)} reseñas con señal de ${numero(fila.resenas)}, en ${fila.juegos} juegos`,
    })),
  );

  protected readonly conclusionSenal = computed(() => conclusionSenal(this.corte(), this.panorama.porAppid()));

  protected readonly topeSenal = computed(() => Math.max(...this.porBanda().map((f) => f.prevalencia), 0.0001));

  /** Cuántas veces más frecuente es la señal en el riesgo alto que en el bajo. */
  protected readonly vecesMas = computed(() => {
    const filas = this.porBanda();
    const baja = filas.find((f) => f.banda === 'bajo')?.prevalencia ?? 0;
    const alta = filas.find((f) => f.banda === 'alto')?.prevalencia ?? 0;
    return baja ? (alta / baja).toFixed(1) : '—';
  });

  protected readonly consenso = computed(() =>
    consensoPorBanda(this.corte(), this.panorama.porAppid()).map((fila) => ({
      etiqueta: `Riesgo ${fila.banda}`,
      banda: fila.banda,
      total: fila.total,
      tajadas: fila.tajadas,
    })),
  );

  protected readonly conclusionConsenso = computed(() => conclusionConsenso(this.corte(), this.panorama.porAppid()));

  protected readonly positivos = computed(() => positivosEnBandaAlta(this.corte(), this.panorama.porAppid()));

  protected readonly juegosAltos = computed(
    () => this.corte().filter((juego) => juego.banda_riesgo === 'alto').length,
  );

  protected readonly num = numero;
}
