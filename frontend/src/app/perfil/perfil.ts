import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { NexplayApi } from '../api/nexplay-api';
import { Plataforma } from '../api/contrato';
import {
  BIBLIOTECA,
  FRICCION,
  HORAS,
  PLATAFORMAS,
  ValoresPerfil,
  VALORES_POR_DEFECTO,
  formularioDesde,
} from '../dominio/opciones-perfil';
import { CatalogoStore } from '../estado/catalogo-store';
import { PerfilStore } from '../estado/perfil-store';
import { SelectorGeneros } from './selector-generos';
import { TarjetasOpcion } from './tarjetas-opcion';

@Component({
  selector: 'app-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TarjetasOpcion, SelectorGeneros],
  templateUrl: './perfil.html',
  styleUrl: './perfil.css',
})
export class Perfil {
  private readonly api = inject(NexplayApi);
  private readonly router = inject(Router);
  protected readonly perfil = inject(PerfilStore);
  protected readonly catalogo = inject(CatalogoStore);

  protected readonly biblioteca = BIBLIOTECA;
  protected readonly horas = HORAS;
  protected readonly friccion = FRICCION;
  protected readonly plataformas = PLATAFORMAS;

  protected readonly valores = signal<ValoresPerfil>(this.perfil.valores() ?? VALORES_POR_DEFECTO);
  protected readonly guardando = signal(false);
  protected readonly error = signal('');

  protected readonly resumen = computed(() => {
    const perfil = this.perfil.perfil();
    if (!perfil) {
      return null;
    }
    const generos = perfil.tags_preferidos.length ? perfil.tags_preferidos.join(', ') : 'sin géneros elegidos';
    return `Segmento ${perfil.segmento}, disponibilidad ${perfil.disponibilidad}, tolerancia a la fricción ${perfil.tolerancia_friccion}, plataforma ${perfil.plataforma}. Géneros: ${generos}.`;
  });

  protected cambiar<K extends keyof ValoresPerfil>(clave: K, valor: ValoresPerfil[K]): void {
    this.valores.update((actuales) => ({ ...actuales, [clave]: valor }));
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
        this.router.navigate(['/']);
      },
      error: () => {
        this.guardando.set(false);
        this.error.set('No se pudo crear el perfil. Revisa que la API esté corriendo e inténtalo de nuevo.');
      },
    });
  }

  protected borrar(): void {
    this.perfil.borrar();
    this.valores.set(VALORES_POR_DEFECTO);
  }
}
