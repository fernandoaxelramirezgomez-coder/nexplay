import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { GraficaApilada } from '../compartido/graficas/grafica-apilada';
import { GraficaBarras } from '../compartido/graficas/grafica-barras';
import { GraficaColumnas } from '../compartido/graficas/grafica-columnas';
import { Segmento } from '../compartido/graficas/segmento';
import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';
import { numero, porcentaje, porcentajeFino } from '../dominio/formato';
import { CONSENSO_STEAM, consensoPorBanda, positivosEnBandaAlta, senalPorBanda } from '../dominio/panorama';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

/** Las tres lecturas que explican de qué está hecha la señal: cuánto había jugado quien
 * escribió cada reseña, cuántas de esas reseñas tiene cada banda, y qué dice Steam de los
 * mismos juegos. Las usa el inicio y las reusa Panorama, para que los números salgan de
 * un solo sitio. */
@Component({
  selector: 'app-graficas-muestra',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GraficaBarras, GraficaColumnas, GraficaApilada],
  template: `
    @if (datos(); as p) {
      <div class="graficas" [class.compacto]="compacto()">
        <section class="grafica" aria-labelledby="titulo-playtime" data-testid="grafica-playtime">
          <h3 class="rotulo-seccion" id="titulo-playtime">Cuánto habían jugado al escribir la reseña</h3>
          <p class="meta explica">
            La etiqueta del modelo sale del primer tramo: menos de dos horas es la ventana en la que Steam
            devuelve el dinero. Son {{ num(tramoCorto().cuantas) }} reseñas de {{ num(p.resenas_descargadas) }}.
          </p>
          <app-grafica-columnas [segmentos]="playtime()" idPrueba="columnas-playtime" />
        </section>

        <section class="grafica" aria-labelledby="titulo-senal" data-testid="grafica-senal">
          <h3 class="rotulo-seccion" id="titulo-senal">Cuántas reseñas con esa señal tiene cada banda</h3>
          <p class="meta explica">
            La banda la pone el modelo con datos del juego (precio, gratuidad, descuento y cobertura de
            crítica) y sin mirar estas reseñas. Aun así, la banda alta tiene {{ vecesMas() }} veces más
            reseñas con señal que la baja.
          </p>
          <app-grafica-barras [segmentos]="senal()" [maximo]="topeSenal()" idPrueba="barras-senal" />
        </section>

        <section class="grafica" aria-labelledby="titulo-consenso" data-testid="grafica-consenso">
          <h3 class="rotulo-seccion" id="titulo-consenso">Qué dice Steam de esos mismos juegos</h3>
          <p class="meta explica">
            El resumen de Steam no entra al modelo, así que coincidir con él no es hacer trampa. Coincide a
            grandes rasgos, pero {{ positivos().length }} de los {{ juegosAltos() }} juegos de riesgo alto
            tienen reseñas muy positivas o extremadamente positivas en Steam: la nota general mide toda la
            partida, no las primeras dos horas.
          </p>
          <app-grafica-apilada [filas]="consenso()" [leyenda]="leyenda()" idPrueba="apilada-consenso" />
        </section>
      </div>
    }
  `,
  styles: `
    .graficas {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-40);
    }
    .grafica {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .explica {
      margin: 0;
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    .compacto {
      gap: var(--espacio-24);
    }
  `,
})
export class GraficasMuestra {
  /** En Panorama van más juntas: ahí la página entera es de gráficas. */
  readonly compacto = input(false);
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

  private readonly porBanda = computed(() =>
    senalPorBanda(this.corte(), this.panorama.porAppid()),
  );

  protected readonly senal = computed<Segmento[]>(() =>
    this.porBanda().map((fila) => ({
      etiqueta: `${ROTULO_RIESGO} ${fila.banda}`,
      valor: fila.prevalencia,
      cifra: porcentajeFino(fila.prevalencia),
      banda: fila.banda,
      detalle: `${numero(fila.casos)} reseñas con señal de ${numero(fila.resenas)}, en ${fila.juegos} juegos`,
    })),
  );

  protected readonly topeSenal = computed(() => Math.max(...this.porBanda().map((f) => f.prevalencia), 0.0001));

  /** Cuántas veces más frecuente es la señal en la banda alta que en la baja. */
  protected readonly vecesMas = computed(() => {
    const filas = this.porBanda();
    const baja = filas.find((f) => f.banda === 'bajo')?.prevalencia ?? 0;
    const alta = filas.find((f) => f.banda === 'alto')?.prevalencia ?? 0;
    return baja ? (alta / baja).toFixed(1) : '—';
  });

  protected readonly consenso = computed(() =>
    consensoPorBanda(this.corte(), this.panorama.porAppid()).map((fila) => ({
      etiqueta: `${ROTULO_RIESGO} ${fila.banda}`,
      banda: fila.banda,
      total: fila.total,
      tajadas: fila.tajadas,
    })),
  );

  protected readonly positivos = computed(() =>
    positivosEnBandaAlta(this.corte(), this.panorama.porAppid()),
  );

  protected readonly juegosAltos = computed(
    () => this.corte().filter((juego) => juego.banda_riesgo === 'alto').length,
  );

  protected readonly num = numero;
}
