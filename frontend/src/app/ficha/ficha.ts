import { Location } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';

import { NexplayApi } from '../api/nexplay-api';
import { Nia } from '../chat/nia';
import { PortadaAncha } from '../compartido/portada-ancha';
import { Skeleton } from '../compartido/skeleton';
import { rotuloRiesgo } from '../dominio/etiqueta-riesgo';
import { factoresVisibles, fraseFactor } from '../dominio/factores';
import { fraseBanda, segundaOpinion } from '../dominio/segunda-opinion';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
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

  protected readonly rotulo = computed(() => rotuloRiesgo(this.perfil.hayPerfil()));
  /** Con perfil declarado la banda puede diferir de la del catálogo (perfil neutro). */
  protected readonly bandaGeneralDistinta = computed(() => {
    const juego = this.juego();
    const nivel = this.prediccion()?.nivel;
    return this.perfil.hayPerfil() && juego && nivel && juego.banda_riesgo !== nivel ? juego.banda_riesgo : null;
  });

  protected readonly frase = computed(() => {
    const nivel = this.prediccion()?.nivel;
    return nivel ? fraseBanda(nivel) : [];
  });

  protected readonly opinion = computed(() => {
    const prediccion = this.prediccion();
    const juego = this.juego();
    if (!prediccion || !juego) {
      return [];
    }
    // La frase de banda ya se muestra en el veredicto: aquí empieza en el motivo.
    const completa = segundaOpinion(prediccion.nivel, this.explicacion()?.motivos ?? [], juego.metacritic);
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

  protected volver(): void {
    if (this.router.lastSuccessfulNavigation()?.previousNavigation) {
      this.location.back();
    } else {
      this.router.navigate(['/']);
    }
  }
}
