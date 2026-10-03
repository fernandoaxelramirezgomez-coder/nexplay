import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { NEVER, Observable, map, of, throwError, timer } from 'rxjs';

import { BuzonSugerencias, EstadoSistema } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { CLAVES_DE_DATOS } from '../dominio/datos-de-sesion';
import { CLAVE_ACTIVIDAD } from '../estado/actividad-store';
import { CLAVE_HISTORIAL } from '../estado/historial-store';
import { CLAVE_PERFIL } from '../estado/perfil-store';
import { Admin, ESPERA_DESPERTANDO_MS, LIMITE_PARA_DESPERTAR_MS, PAUSA_ENTRE_INTENTOS_MS, RECARGAR_PAGINA } from './admin';

const ESTADO: EstadoSistema = {
  nia_con_openai: false,
  modelo_nia: null,
  datos_release: 'data-v3',
  juegos_catalogo: 123,
  modelo_version: 'logreg-juego-2026-10-01',
  modelo_datos: 'data-v1',
  modelo_juegos_entrenamiento: 83,
};
const BUZON: BuzonSugerencias = {
  votos_a_favor: 4,
  votos_en_contra: 2,
  por_motivo: [
    { motivo: 'muy larga', cuantos: 1 },
    { motivo: 'otro motivo', cuantos: 1 },
    { motivo: 'sin motivo', cuantos: 0 },
  ],
  sugerencias: [{ texto: 'Que cuente más del modo historia', cuando: '2026-10-03T10:00:00+00:00' }],
};
const caida = () => throwError(() => new HttpErrorResponse({ status: 0 }));

function montar(estado: () => Observable<EstadoSistema>, buzon: () => Observable<BuzonSugerencias> = () => of(BUZON)) {
  const recargar = vi.fn();
  // Lo demás de la API no responde: aquí solo importan /estado y el buzón.
  const api = new Proxy({} as Partial<NexplayApi>, {
    get: (_, metodo) => (metodo === 'estado' ? estado : metodo === 'buzonDeSugerencias' ? buzon : () => NEVER),
  });
  TestBed.configureTestingModule({
    providers: [
      { provide: NexplayApi, useValue: api },
      { provide: RECARGAR_PAGINA, useValue: recargar },
    ],
  });
  const fixture = TestBed.createComponent(Admin);
  fixture.detectChanges();
  return { fixture, recargar, html: fixture.nativeElement as HTMLElement };
}

const texto = (html: HTMLElement, id: string) =>
  html.querySelector(`[data-testid="${id}"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';

describe('Administración: el estado del sistema', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    TestBed.resetTestingModule();
  });

  it('conectado: backend, modo de Nia, release, juegos y modelo', () => {
    const { html } = montar(() => of(ESTADO));

    expect(texto(html, 'admin-backend-estado')).toBe('Conectado');
    expect(texto(html, 'admin-openai')).toContain('Modo demostración (reglas)');
    expect(texto(html, 'admin-datos')).toContain('data-v3');
    expect(texto(html, 'admin-datos')).toContain('123 juegos en el catálogo');
    expect(texto(html, 'admin-modelo')).toContain('logreg-juego-2026-10-01');
    expect(texto(html, 'admin-modelo')).toContain('Entrenado con 83 juegos (data-v1)');
    expect(texto(html, 'admin-buzon-votos')).toBe('👍 4 · 👎 2');
    expect(texto(html, 'admin-buzon-sugerencias')).toContain('Que cuente más del modo historia');
  });

  it('con clave, OpenAI dice «Configurado» y el modelo de Nia; la clave no está en el contrato', () => {
    const { html } = montar(() => of({ ...ESTADO, nia_con_openai: true, modelo_nia: 'gpt-prueba' }));

    expect(texto(html, 'admin-openai')).toContain('Configurado');
    expect(texto(html, 'admin-modelo')).toContain('gpt-prueba');
    expect(Object.keys(ESTADO).some((campo) => /key|clave/i.test(campo))).toBe(false);
  });

  it('si tarda más de 3 s dice «Despertando…» en vez de un error, y luego «Conectado»', () => {
    const { fixture, html } = montar(() => timer(ESPERA_DESPERTANDO_MS + 2_000).pipe(map(() => ESTADO)));

    expect(texto(html, 'admin-backend-estado')).toBe('Conectando…');
    vi.advanceTimersByTime(ESPERA_DESPERTANDO_MS);
    fixture.detectChanges();
    expect(texto(html, 'admin-backend-estado')).toBe('Despertando…');
    vi.advanceTimersByTime(2_000);
    fixture.detectChanges();
    expect(texto(html, 'admin-backend-estado')).toBe('Conectado');
  });

  it('si los primeros intentos fallan, reintenta: Render todavía no despierta', () => {
    const estado = vi.fn().mockReturnValueOnce(caida()).mockReturnValueOnce(caida()).mockReturnValue(of(ESTADO));
    const { fixture, html } = montar(estado);

    expect(texto(html, 'admin-backend-estado')).toBe('Despertando…');
    vi.advanceTimersByTime(PAUSA_ENTRE_INTENTOS_MS * 2);
    fixture.detectChanges();
    expect(estado).toHaveBeenCalledTimes(3);
    expect(texto(html, 'admin-backend-estado')).toBe('Conectado');
  });

  it('sin respuesta en 90 s: «Sin conexión», todo en gris y «Reintentar»', () => {
    const estado = vi.fn(caida);
    const { fixture, html } = montar(estado);

    vi.advanceTimersByTime(LIMITE_PARA_DESPERTAR_MS);
    fixture.detectChanges();
    expect(texto(html, 'admin-backend-estado')).toBe('Sin conexión');
    for (const id of ['admin-openai', 'admin-datos', 'admin-modelo']) {
      expect(html.querySelector(`[data-testid="${id}"]`)?.getAttribute('data-estado')).toBe('no-disponible');
      expect(texto(html, id)).toContain('No disponible');
    }
    expect(html.querySelector('[data-testid="admin-buzon-no-disponible"]')).not.toBeNull();

    const llamadas = estado.mock.calls.length;
    html.querySelector<HTMLButtonElement>('[data-testid="admin-reintentar"]')!.click();
    fixture.detectChanges();
    expect(estado.mock.calls.length).toBe(llamadas + 1);
  });
});

describe('Administración: tu sesión en este navegador', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => TestBed.resetTestingModule());

  it('sin datos, cada cifra es «—» y el perfil está pendiente', () => {
    const { html } = montar(() => of(ESTADO));

    for (const id of ['conversaciones', 'mensajes', 'juegos', 'comparaciones', 'valoraciones']) {
      expect(texto(html, `admin-${id}`)).toContain('—');
    }
    expect(texto(html, 'admin-perfil')).toContain('Pendiente');
  });

  it('con datos, cuenta lo del historial, lo de la actividad y el perfil', () => {
    const cuando = '2026-10-03T10:00:00.000Z';
    localStorage.setItem(
      CLAVE_HISTORIAL,
      JSON.stringify([
        { tipo: 'visto', appid: 1, titulo: 'Hades', cuando },
        { tipo: 'visto', appid: 2, titulo: 'Celeste', cuando },
        { tipo: 'comparado', titulo: 'Hades · Celeste', appids: [1, 2], cuando },
        { tipo: 'nia', appid: 1, titulo: 'Hades', cuando },
      ]),
    );
    localStorage.setItem(
      CLAVE_ACTIVIDAD,
      JSON.stringify({ conversacionesNia: 2, mensajesNia: 5, juegosValorados: [1], respuestasVotadas: ['a', 'b'], comentarios: 1 }),
    );
    localStorage.setItem(
      CLAVE_PERFIL,
      JSON.stringify({
        valores: { compras: 4, horas: 6, friccion: 3, gasto: 2, plataformas: ['pc'], generos: ['Rol', 'Estrategia'] },
        perfil: {
          compras_al_anio: 4, horas_por_semana: 6, tolerancia_friccion: 'media', tags_preferidos: [], tags_rechazados: [],
          plataforma: 'pc', segmento: 'novato', disponibilidad: 'media',
        },
      }),
    );
    const { html } = montar(() => of(ESTADO));

    expect(texto(html, 'admin-conversaciones')).toContain('2');
    expect(texto(html, 'admin-mensajes')).toContain('5');
    expect(texto(html, 'admin-juegos')).toContain('2');
    expect(texto(html, 'admin-comparaciones')).toContain('1');
    expect(texto(html, 'admin-perfil')).toContain('Completado');
    expect(texto(html, 'admin-perfil')).toContain('2 géneros elegidos');
    // Cada parte: su cifra (dd) y su etiqueta en singular o plural (dt).
    const parte = (id: string) =>
      ['dd', 'dt'].map((celda) => html.querySelector(`[data-testid="admin-valoraciones-${id}"] ${celda}`)?.textContent?.trim());
    expect(parte('estrellas')).toEqual(['1', 'juego con estrellas']);
    expect(parte('votos')).toEqual(['2', 'votos a Nia']);
    expect(parte('comentarios')).toEqual(['1', 'comentario']);
  });
});

describe('Administración: restablecer los datos de esta sesión', () => {
  const AJENAS = {
    'nexplay.usuario.v1': 'anonimo-1234',
    'nexplay.tema.v1': 'claro',
    'nexplay.barra.v1': 'corta',
    'nexplay.video.v1': '0.4',
    'otra-app.preferencias': 'no es de NexPlay',
  };

  beforeEach(() => {
    localStorage.clear();
    for (const clave of CLAVES_DE_DATOS) {
      localStorage.setItem(clave, '[]');
    }
    for (const [clave, valor] of Object.entries(AJENAS)) {
      localStorage.setItem(clave, valor);
    }
  });
  afterEach(() => TestBed.resetTestingModule());

  it('pide confirmación, dice que los comentarios públicos no se borran, y borra solo los datos de NexPlay', () => {
    const { fixture, html, recargar } = montar(() => of(ESTADO));

    html.querySelector<HTMLButtonElement>('[data-testid="admin-restablecer"]')!.click();
    fixture.detectChanges();
    expect(texto(html, 'admin-confirmar')).toContain('Los comentarios públicos y los votos que ya enviaste no se borran');
    expect(CLAVES_DE_DATOS.every((clave) => localStorage.getItem(clave) !== null)).toBe(true);

    html.querySelector<HTMLButtonElement>('[data-testid="admin-borrar"]')!.click();
    expect(CLAVES_DE_DATOS.some((clave) => localStorage.getItem(clave) !== null)).toBe(false);
    for (const [clave, valor] of Object.entries(AJENAS)) {
      expect(localStorage.getItem(clave)).toBe(valor);
    }
    expect(recargar).toHaveBeenCalledOnce();
  });

  it('«Cancelar» no borra nada', () => {
    const { fixture, html, recargar } = montar(() => of(ESTADO));

    html.querySelector<HTMLButtonElement>('[data-testid="admin-restablecer"]')!.click();
    fixture.detectChanges();
    html.querySelector<HTMLButtonElement>('[data-testid="admin-cancelar"]')!.click();
    fixture.detectChanges();

    expect(html.querySelector('[data-testid="admin-confirmar"]')).toBeNull();
    expect(CLAVES_DE_DATOS.every((clave) => localStorage.getItem(clave) !== null)).toBe(true);
    expect(recargar).not.toHaveBeenCalled();
  });
});
