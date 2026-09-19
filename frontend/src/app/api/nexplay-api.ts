import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  ExplicacionJuego,
  FiltrosCatalogo,
  FormularioAlta,
  JuegoCatalogo,
  PerfilJugador,
  PrediccionRiesgo,
  SolicitudPrediccion,
} from './contrato';

/** Único punto de contacto con la API. */
@Injectable({ providedIn: 'root' })
export class NexplayApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl;

  catalogo(filtros: FiltrosCatalogo = {}): Observable<JuegoCatalogo[]> {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor) {
        params = params.set(clave, valor);
      }
    }
    return this.http.get<JuegoCatalogo[]>(`${this.base}/catalogo`, { params });
  }

  crearPerfil(formulario: FormularioAlta): Observable<PerfilJugador> {
    return this.http.post<PerfilJugador>(`${this.base}/perfil`, formulario);
  }

  predecir(solicitud: SolicitudPrediccion): Observable<PrediccionRiesgo> {
    return this.http.post<PrediccionRiesgo>(`${this.base}/prediccion`, solicitud);
  }

  explicacion(appid: number): Observable<ExplicacionJuego> {
    return this.http.get<ExplicacionJuego>(`${this.base}/explicacion/${appid}`);
  }
}
