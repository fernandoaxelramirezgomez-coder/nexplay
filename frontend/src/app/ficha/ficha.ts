import { Location } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';

import { NexplayApi } from '../api/nexplay-api';
import { Nia } from '../chat/nia';
import { NotaInfo } from '../compartido/nota-info';
import { PildoraBanda } from '../compartido/pildora-banda';
import { PortadaAncha } from '../compartido/portada-ancha';
import { Skeleton } from '../compartido/skeleton';
import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';
import { factoresVisibles, fraseFactor } from '../dominio/factores';
import { fraseBanda, segundaOpinion, titularBanda } from '../dominio/segunda-opinion';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { HistorialStore } from '../estado/historial-store';
import { PerfilStore } from '../estado/perfil-store';
import { FactoresModelo } from './factores-modelo';
import { HistoriaPerfil } from './historia-perfil';
import { MetadatosJuego } from './metadatos-juego';
import { MotivosBarras } from './motivos-barras';
import { ValoracionOpinion } from './valoracion-opinion';

@Component({
  selector: 'app-ficha',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    PortadaAncha,
    Skeleton,
    MotivosBarras,
    MetadatosJuego,
    FactoresModelo,
    ValoracionOpinion,
    Nia,
    HistoriaPerfil,
    NotaInfo,
    PildoraBanda,
  ],
  templateUrl: './ficha.html',
  styleUrl: './ficha.css',
})
export class Ficha {
  readonly appid = input.required<string>();

  private readonly api = inject(NexplayApi);
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  protected readonly catalogo = inject(CatalogoStore);
  protected readonly perfil = inject(PerfilStore);
  protected readonly comparar = inject(CompararStore);
  private readonly historial = inject(HistorialStore);

  protected readonly juego = computed(() => this.catalogo.porAppid().get(Number(this.appid())));
  protected readonly noEncontrado = computed(
    () => !this.catalogo.cargando() && !this.catalogo.error() && !this.juego(),
  );

  private readonly prediccionRecurso = rxResource({
    params: () => {
      const perfil = this.perfil.efectivo();
      const juego = this.juego();
      return perfil && juego ? { perfil, appid: juego.appid } : undefined;
    },
    stream: ({ params }) => this.api.predecir(params),
  });

  private readonly explicacionRecurso = rxResource({
    params: () => this.juego()?.appid,
    stream: ({ params }) => this.api.explicacion(params),
  });

  protected readonly prediccion = this.prediccionRecurso.value;
  protected readonly explicacion = this.explicacionRecurso.value;
  protected readonly cargando = computed(
    () => this.catalogo.cargando() || this.prediccionRecurso.isLoading() || this.perfil.cargandoNeutro(),
  );
  protected readonly errorRiesgo = computed(() => this.prediccionRecurso.error());
  protected readonly cargandoMotivos = computed(() => this.explicacionRecurso.isLoading());
  protected readonly esperandoOpinion = computed(() => this.cargando() || this.explicacionRecurso.isLoading());

  protected readonly rotulo = ROTULO_RIESGO;

  protected readonly titular = computed(() => {
    const nivel = this.prediccion()?.nivel;
    return nivel ? titularBanda(nivel) : [];
  });

  protected readonly opinion = computed(() => {
    const prediccion = this.prediccion();
    const juego = this.juego();
    if (!prediccion || !juego) {
      return [];
    }
    // La frase de banda ya se muestra en el veredicto: aquí empieza en el motivo.
    const completa = segundaOpinion(
      prediccion.nivel,
      this.explicacion()?.motivos ?? [],
      juego.metacritic,
      this.factores().some((factor) => factor.etiqueta === 'nota de Metacritic'),
      Math.round((this.explicacion()?.n_casos ?? 0) * (this.explicacion()?.pct_clasificados ?? 0)),
    );
    return completa.slice(fraseBanda(prediccion.nivel).length);
  });

  protected readonly factores = computed(() => {
    const prediccion = this.prediccion();
    const juego = this.juego();
    return prediccion && juego ? factoresVisibles(prediccion.factores, juego) : [];
  });

  protected readonly enComparacion = computed(() => {
    const juego = this.juego();
    return !!juego && this.comparar.appids().includes(juego.appid);
  });

  protected readonly frasePara = fraseFactor;

  /** El aviso de "ya hay cuatro en comparación" solo aparece si se intentó agregar, y
   * junto a la acción; antes salía al abrir la ficha con la bandeja llena. */
  protected readonly rechazado = signal(false);
  /** La descripción de Steam entra recortada a dos líneas: es lo que el juego dice de sí
   * mismo, no lo que se viene a leer aquí. */
  protected readonly descripcionEntera = signal(false);
  private reloj?: ReturnType<typeof setTimeout>;

  protected alternarComparar(appid: number): void {
    const resultado = this.comparar.alternar(appid);
    clearTimeout(this.reloj);
    this.rechazado.set(resultado === 'lleno');
    if (resultado === 'lleno') {
      this.reloj = setTimeout(() => this.rechazado.set(false), 4000);
    }
  }

  constructor() {
    // Abrir una ficha es lo que llena el historial; se anota cuando el catálogo ya
    // llegó, que es cuando se sabe el nombre y la banda.
    effect(() => {
      const juego = this.juego();
      if (juego) {
        this.historial.registrar({
          tipo: 'visto',
          appid: juego.appid,
          titulo: juego.nombre,
          banda: juego.banda_riesgo,
        });
      }
    });
  }

  protected volver(): void {
    if (this.router.lastSuccessfulNavigation()?.previousNavigation) {
      this.location.back();
    } else {
      this.router.navigate(['/explorar']);
    }
  }
}
