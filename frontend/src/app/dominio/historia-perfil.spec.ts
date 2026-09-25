import { MotivoInsatisfaccion, PerfilJugador } from '../api/contrato';
import { historiaPerfil, partirDatos } from './historia-perfil';
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

/** La historia se lee como un párrafo: para revisarla basta el texto plano. */
function plano(segmentos: ReturnType<typeof historiaPerfil>): string {
  return (segmentos ?? []).map((s) => s.texto).join('');
}

describe('historiaPerfil', () => {
  it('sin perfil no hay historia que contar', () => {
    expect(historiaPerfil(null, juegoDePrueba(), MOTIVOS)).toBeNull();
  });

  it('dice si el juego cae dentro o fuera de los géneros declarados', () => {
    const dentro = plano(historiaPerfil(perfilDePrueba(), juegoDePrueba(), MOTIVOS));
    expect(dentro).toContain('dentro');
    expect(dentro).toContain('Acción');

    const fuera = plano(historiaPerfil(perfilDePrueba({ tags_preferidos: ['estrategia'] }), juegoDePrueba(), MOTIVOS));
    expect(fuera).toContain('fuera');
  });

  it('sin géneros declarados no inventa afinidad', () => {
    const texto = plano(historiaPerfil(perfilDePrueba({ tags_preferidos: [] }), juegoDePrueba(), MOTIVOS));
    expect(texto).toContain('No declaraste géneros');
    expect(texto).not.toContain('dentro de lo que sueles jugar');
  });

  it('cruza la tolerancia baja con el motivo dominante cuando es fricción', () => {
    const texto = plano(
      historiaPerfil(perfilDePrueba({ tolerancia_friccion: 'baja' }), juegoDePrueba(), [
        { motivo: 'bugs', frecuencia: 0.4 },
      ]),
    );
    expect(texto).toContain('bugs');
    expect(texto).toContain('justo lo que menos toleras');
    expect(texto).toContain('40%');
  });

  it('con tolerancia alta el mismo motivo no se presenta como problema', () => {
    const texto = plano(
      historiaPerfil(perfilDePrueba({ tolerancia_friccion: 'alta' }), juegoDePrueba(), [
        { motivo: 'bugs', frecuencia: 0.4 },
      ]),
    );
    expect(texto).toContain('no te frena');
    expect(texto).not.toContain('justo lo que menos toleras');
  });

  it('un motivo que no es fricción no se cruza con la tolerancia', () => {
    const texto = plano(
      historiaPerfil(perfilDePrueba({ tolerancia_friccion: 'baja' }), juegoDePrueba(), [
        { motivo: 'contenido', frecuencia: 0.3 },
      ]),
    );
    expect(texto).toContain('no es fricción de juego');
  });

  it('sin motivos suficientes lo dice en vez de suponer', () => {
    const texto = plano(historiaPerfil(perfilDePrueba(), juegoDePrueba(), []));
    expect(texto).toContain('No hay suficientes reseñas de arrepentimiento temprano');
  });

  it('el reembolso depende de los 14 días, no de las horas por semana', () => {
    // 2 h por semana llega a las dos horas en una semana: sigue dentro del plazo.
    const normal = plano(historiaPerfil(perfilDePrueba({ horas_por_semana: 2 }), juegoDePrueba(), MOTIVOS));
    expect(normal).toContain('dentro de los 14 días');
    expect(normal).not.toContain('venció');

    // Media hora por semana: tardaría un mes en llegar, y el plazo corre igual.
    const lento = plano(historiaPerfil(perfilDePrueba({ horas_por_semana: 0.5 }), juegoDePrueba(), MOTIVOS));
    expect(lento).toContain('caduca a los 14 días de la compra aunque no hayas jugado');
  });

  it('un juego gratuito no habla de cuánto pesa la compra', () => {
    const texto = plano(
      historiaPerfil(perfilDePrueba(), juegoDePrueba({ es_gratis: true, precio_final: 0 }), MOTIVOS),
    );
    expect(texto).toContain('gratuito');
    expect(texto).not.toContain('compras al año');
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

  it('con una compra al año dice «1 juego», en singular', () => {
    const uno = plano(historiaPerfil(perfilDePrueba({ compras_al_anio: 1 }), juegoDePrueba(), MOTIVOS));
    expect(uno).toContain('1 juego al año');
    expect(uno).not.toContain('1 juegos');
    const cinco = plano(historiaPerfil(perfilDePrueba({ compras_al_anio: 5 }), juegoDePrueba(), MOTIVOS));
    expect(cinco).toContain('5 juegos al año');
  });
});

describe('partirDatos', () => {
  it('marca porcentajes, horas, días, juegos y compras sin cambiar el texto', () => {
    const texto = 'Con 6 h por semana, dentro de los 14 días; rendimiento (86% de las clasificadas), 1 juego y 20 compras.';
    const trozos = partirDatos(texto);
    expect(trozos.map((t) => t.texto).join('')).toBe(texto);
    expect(trozos.filter((t) => t.dato).map((t) => t.texto)).toEqual(['6 h', '14 días', '86%', '1 juego', '20 compras']);
  });

  it('un número suelto o una palabra con h no son datos', () => {
    const trozos = partirDatos('Half-Life 2 tiene horas de sobra');
    expect(trozos.some((t) => t.dato)).toBe(false);
  });
});
