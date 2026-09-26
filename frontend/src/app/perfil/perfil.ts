import { ChangeDetectionStrategy, Component, Injector, afterNextRender, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NexplayApi } from '../api/nexplay-api';
import { Plataforma } from '../api/contrato';
import {
  COMPRAS,
  FRICCION,
  HORAS,
  PLATAFORMAS,
  ValoresPerfil,
  VALORES_VACIOS,
  estaCompleto,
  formularioDesde,
} from '../dominio/opciones-perfil';
import { CatalogoStore } from '../estado/catalogo-store';
import { PerfilStore } from '../estado/perfil-store';
import { SelectorGeneros } from './selector-generos';
import { SugerenciasPerfil } from './sugerencias-perfil';
import { TarjetasOpcion } from './tarjetas-opcion';

@Component({
  selector: 'app-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TarjetasOpcion, SelectorGeneros, SugerenciasPerfil],
  templateUrl: './perfil.html',
  styleUrl: './perfil.css',
})
export class Perfil {
  private readonly api = inject(NexplayApi);
  private readonly inyector = inject(Injector);
  protected readonly perfil = inject(PerfilStore);
  protected readonly catalogo = inject(CatalogoStore);

  protected readonly compras = COMPRAS;
  protected readonly horas = HORAS;
  protected readonly friccion = FRICCION;
  protected readonly plataformas = PLATAFORMAS;

  protected readonly valores = signal<ValoresPerfil>(this.perfil.valores() ?? VALORES_VACIOS);
  /** Sin las cuatro respuestas no hay perfil que crear: el botón espera. */
  protected readonly completo = computed(() => estaCompleto(this.valores()));
  protected readonly guardando = signal(false);
  protected readonly guardado = signal(false);
  protected readonly error = signal('');

  protected readonly resumen = computed(() => {
    const perfil = this.perfil.perfil();
    if (!perfil) {
      return null;
    }
    const generos = perfil.tags_preferidos.length ? perfil.tags_preferidos.join(', ') : 'sin géneros elegidos';
    return `Disponibilidad ${perfil.disponibilidad}, tolerancia a la fricción ${perfil.tolerancia_friccion}, plataforma ${perfil.plataforma}. Géneros: ${generos}.`;
  });

  protected cambiar<K extends keyof ValoresPerfil>(clave: K, valor: ValoresPerfil[K]): void {
    this.valores.update((actuales) => ({ ...actuales, [clave]: valor }));
    this.guardado.set(false);
  }

  protected cambiarPlataforma(valor: Plataforma): void {
    this.cambiar('plataforma', valor);
  }

  protected alternarGenero(genero: string): void {
    this.valores.update((actuales) => ({
      ...actuales,
      generos: actuales.generos.includes(genero)
        ? actuales.generos.filter((g) => g !== genero)
        : [...actuales.generos, genero],
    }));
  }

  protected crear(): void {
    this.guardando.set(true);
    this.error.set('');
    const valores = this.valores();
    this.api.crearPerfil(formularioDesde(valores)).subscribe({
      next: (perfil) => {
        this.perfil.guardar(valores, perfil);
        this.guardando.set(false);
        this.guardado.set(true);
        // Los juegos parecidos aparecen justo debajo al guardar: irse al catálogo dejaba
        // sin ver lo único que el perfil cambia.
        afterNextRender(
          () => document.querySelector('[data-testid="sugerencias"]')?.scrollIntoView({ block: 'start' }),
          { injector: this.inyector },
        );
      },
      error: () => {
        this.guardando.set(false);
        this.error.set('No se pudo crear el perfil. Revisa que la API esté corriendo e inténtalo de nuevo.');
      },
    });
  }

  protected borrar(): void {
    this.perfil.borrar();
    this.valores.set(VALORES_VACIOS);
  }
}
