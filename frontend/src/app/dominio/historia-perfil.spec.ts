import { MotivoInsatisfaccion, PerfilJugador } from '../api/contrato';
import { historiaPerfil } from './historia-perfil';
import { juegoDePrueba } from './juego-prueba';

function perfilDePrueba(cambios: Partial<PerfilJugador> = {}): PerfilJugador {
  return {
    compras_al_anio: 5,
    horas_por_semana: 6,
    tolerancia_friccion: 'media',
    tags_preferidos: ['acción'],
    tags_rechazados: [],
    plataforma: 'pc',
    segmento: 'novato',
    disponibilidad: 'media',
    ...cambios,
  };
}

const MOTIVOS: MotivoInsatisfaccion[] = [
  { motivo: 'rendimiento', frecuencia: 0.86 },
  { motivo: 'bugs', frecuencia: 0.25 },
];

/** La historia son líneas de segmentos: para revisarla basta el texto plano de todas. */
function plano(lineas: ReturnType<typeof historiaPerfil>): string {
  return (lineas ?? []).map((linea) => linea.segmentos.map((s) => s.texto).join('')).join(' ');
}

function lineas(resultado: ReturnType<typeof historiaPerfil>): string[] {
  return (resultado ?? []).map((linea) => linea.segmentos.map((s) => s.texto).join(''));
}

function palabras(linea: string): number {
  return linea.trim().split(/\s+/).length;
}

describe('historiaPerfil', () => {
  it('sin perfil no hay historia que contar', () => {
    expect(historiaPerfil(null, juegoDePrueba(), MOTIVOS)).toBeNull();
  });

  it('dice si el juego cae dentro o fuera de los géneros declarados', () => {
    const dentro = plano(historiaPerfil(perfilDePrueba(), juegoDePrueba(), MOTIVOS));
    expect(dentro).toContain('Dentro');
    expect(dentro).toContain('Acción');

    const fuera = plano(historiaPerfil(perfilDePrueba({ tags_preferidos: ['estrategia'] }), juegoDePrueba(), MOTIVOS));
    expect(fuera).toContain('Fuera');
  });

  it('sin géneros declarados no inventa afinidad', () => {
    const texto = plano(historiaPerfil(perfilDePrueba({ tags_preferidos: [] }), juegoDePrueba(), MOTIVOS));
    expect(texto).toContain('No declaraste géneros');
    expect(texto).not.toContain('Dentro de tus géneros');
  });

  /** Tres líneas de una ojeada: en prosa, esto se leía como una explicación del riesgo,
   * que es justo lo que no es. Doce palabras es lo que cabe en un renglón. */
  it('son tres líneas cortas: géneros, tiempo hasta las dos horas y peso de la compra', () => {
    const resultado = lineas(historiaPerfil(perfilDePrueba(), juegoDePrueba(), MOTIVOS));
    expect(resultado).toHaveLength(3);
    for (const linea of resultado) {
      expect(palabras(linea)).toBeLessThanOrEqual(12);
    }
    const [generos, tiempo, compra] = resultado;
    expect(generos).toBe('Dentro de tus géneros: Acción.');
    expect(tiempo).toBe('Llegas a 2 h en 1–2 sesiones, dentro del reembolso.');
    expect(compra).toBe('Sería una de tus 3–6 compras del año.');
  });

  it('cada línea dice de qué habla, en el orden géneros, tiempo, compra', () => {
    const resultado = historiaPerfil(perfilDePrueba(), juegoDePrueba(), MOTIVOS) ?? [];
    expect(resultado.map((linea) => linea.tipo)).toEqual(['generos', 'tiempo', 'compra']);
  });

  it('no repite el motivo dominante, que ya sale en su propia sección', () => {
    const texto = plano(
      historiaPerfil(perfilDePrueba({ tolerancia_friccion: 'baja' }), juegoDePrueba(), [
        { motivo: 'bugs', frecuencia: 0.4 },
      ]),
    );
    expect(texto).not.toContain('bugs');
    expect(texto).not.toContain('40%');
  });

  it('el reembolso depende de los 14 días, no de las horas por semana', () => {
    // 2 h por semana llega a las dos horas en una semana: sigue dentro del plazo.
    const normal = plano(historiaPerfil(perfilDePrueba({ horas_por_semana: 2 }), juegoDePrueba(), MOTIVOS));
    expect(normal).toContain('dentro del reembolso');

    // Media hora por semana: tardaría un mes en llegar, y el plazo corre igual.
    const lento = plano(historiaPerfil(perfilDePrueba({ horas_por_semana: 0.5 }), juegoDePrueba(), MOTIVOS));
    expect(lento).toContain('más de 14 días: el reembolso caduca antes');
  });

  it('un juego gratuito no habla de cuánto pesa la compra', () => {
    const texto = plano(
      historiaPerfil(perfilDePrueba(), juegoDePrueba({ es_gratis: true, precio_final: 0 }), MOTIVOS),
    );
    expect(texto).toContain('Gratuito');
    expect(texto).not.toContain('compras');
  });

  it('sin precio no se inventa cuánto pesa la compra', () => {
    const texto = plano(historiaPerfil(perfilDePrueba(), juegoDePrueba({ precio_final: null }), MOTIVOS));
    expect(texto).toContain('Steam no devolvió precio');
  });

  it('nunca recomienda comprar ni usa la palabra prohibida', () => {
    for (const tolerancia of ['baja', 'media', 'alta'] as const) {
      const texto = plano(historiaPerfil(perfilDePrueba({ tolerancia_friccion: tolerancia }), juegoDePrueba(), MOTIVOS));
      expect(texto.toLowerCase()).not.toContain('abandono');
      expect(texto.toLowerCase()).not.toContain('te lo recomiendo');
      expect(texto.toLowerCase()).not.toContain('vale la pena');
    }
  });

  /** A la API viaja el punto medio del rango (1, 4, 11 o 25); lo declarado fue un rango,
   * así que es el rango lo que se cuenta de vuelta, ahora en cifras para que la línea
   * quepa en un renglón. */
  it('nombra el rango de compras que se eligió, no el punto medio', () => {
    const uno = plano(historiaPerfil(perfilDePrueba({ compras_al_anio: 1 }), juegoDePrueba(), MOTIVOS));
    expect(uno).toContain('una de tus 0–2 compras del año');
    const cuatro = plano(historiaPerfil(perfilDePrueba({ compras_al_anio: 4 }), juegoDePrueba(), MOTIVOS));
    expect(cuatro).toContain('una de tus 3–6 compras del año');
    const muchos = plano(historiaPerfil(perfilDePrueba({ compras_al_anio: 25 }), juegoDePrueba(), MOTIVOS));
    expect(muchos).toContain('Compras más de 15 al año: este sería uno más');
  });
});
