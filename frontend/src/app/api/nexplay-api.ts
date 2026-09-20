import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  Comentario,
  ExplicacionJuego,
  FiltrosCatalogo,
  FormularioAlta,
  JuegoCatalogo,
  PerfilJugador,
  PrediccionRiesgo,
  ReaccionComentario,
  RespuestaNia,
  ResumenValoraciones,
  SolicitudComentario,
  SolicitudNia,
  SolicitudPrediccion,
  SolicitudValoracion,
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

  valoraciones(appid: number, usuario: string): Observable<ResumenValoraciones> {
    const params = new HttpParams().set('usuario', usuario);
    return this.http.get<ResumenValoraciones>(`${this.base}/valoraciones/${appid}`, { params });
  }

  guardarValoracion(appid: number, solicitud: SolicitudValoracion): Observable<ResumenValoraciones> {
    return this.http.put<ResumenValoraciones>(`${this.base}/valoraciones/${appid}`, solicitud);
  }

  borrarValoracion(appid: number, usuario: string): Observable<ResumenValoraciones> {
    const params = new HttpParams().set('usuario', usuario);
    return this.http.delete<ResumenValoraciones>(`${this.base}/valoraciones/${appid}`, { params });
  }

  /** El usuario va en la consulta solo para marcar cuáles son suyos y si ya reaccionó. */
  comentarios(appid: number, usuario: string): Observable<Comentario[]> {
    const params = new HttpParams().set('usuario', usuario);
    return this.http.get<Comentario[]>(`${this.base}/comentarios/${appid}`, { params });
  }

  /** Devuelve el hilo completo ya con el comentario nuevo al final. */
  comentar(appid: number, solicitud: SolicitudComentario): Observable<Comentario[]> {
    return this.http.post<Comentario[]>(`${this.base}/comentarios/${appid}`, solicitud);
  }

  /** Solo el dueño: la API responde 403 si el comentario es de otra persona. */
  editarComentario(appid: number, id: number, solicitud: SolicitudComentario): Observable<Comentario[]> {
    return this.http.put<Comentario[]>(`${this.base}/comentarios/${appid}/${id}`, solicitud);
  }

  borrarComentario(appid: number, id: number, usuario: string): Observable<Comentario[]> {
    const params = new HttpParams().set('usuario', usuario);
    return this.http.delete<Comentario[]>(`${this.base}/comentarios/${appid}/${id}`, { params });
  }

  /** Alterna el pulgar arriba y devuelve el conteo ya actualizado de ese comentario. */
  reaccionar(appid: number, id: number, usuario: string): Observable<ReaccionComentario> {
    return this.http.put<ReaccionComentario>(`${this.base}/comentarios/${appid}/${id}/reaccion`, { usuario });
  }

  preguntarANia(solicitud: SolicitudNia): Observable<RespuestaNia> {
    return this.http.post<RespuestaNia>(`${this.base}/nia`, solicitud);
  }
}
