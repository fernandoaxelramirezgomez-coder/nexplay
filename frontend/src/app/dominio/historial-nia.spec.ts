import { MensajeChat } from '../api/contrato';
import { recortarHistorial, sugerenciasParaNia } from './historial-nia';
import { juegoDePrueba } from './juego-prueba';
import { Sugerencia } from './sugerencias';

function hilo(n: number, largo = 10): MensajeChat[] {
  return Array.from({ length: n }, (_, i) => ({
    rol: i % 2 ? ('nia' as const) : ('usuario' as const),
    contenido: `${i}`.padEnd(largo, '.'),
  }));
}

describe('historial de Nia', () => {
  it('manda el hilo entero cuando cabe', () => {
    expect(recortarHistorial(hilo(12))).toHaveLength(12);
  });

  it('corta por mensajes y deja los más recientes', () => {
    const recortado = recortarHistorial(hilo(45));
    expect(recortado).toHaveLength(40);
    expect(recortado[0].contenido.startsWith('5')).toBe(true);
    expect(recortado.at(-1)?.contenido.startsWith('44')).toBe(true);
  });

  it('corta por caracteres, pero la pregunta nueva siempre va', () => {
    expect(recortarHistorial(hilo(10, 1000), 40, 3500)).toHaveLength(3);
    expect(recortarHistorial(hilo(1, 9000), 40, 3500)).toHaveLength(1);
  });

  it('de las sugerencias viajan el appid y los porqués que cumplen, en palabras y nada del perfil', () => {
    const sugerencia = {
      juego: juegoDePrueba({ appid: 1145360, nombre: 'Hades' }),
      razones: [
        {
          tipo: 'generos',
          cumple: true,
          texto: 'Coincide en Rol, que está en 39 de 123 juegos del catálogo.',
          hablada: 'coincide en Rol',
        },
        { tipo: 'precio', cumple: true, texto: '$283 · dentro de tu tope', hablada: 'cuesta $283, dentro de lo que dijiste pagar' },
        { tipo: 'horas', cumple: false, texto: 'Pide más: ~31 h al recomendarlo', hablada: 'pide más tiempo' },
      ],
    } as unknown as Sugerencia;
    expect(sugerenciasParaNia([sugerencia])).toEqual([
      { appid: 1145360, razones: ['coincide en Rol', 'cuesta $283, dentro de lo que dijiste pagar'] },
    ]);
    // Ni la fracción de rareza (el modelo la volvía «20 % de tus gustos») ni etiquetas con «·».
    const razones = sugerenciasParaNia([sugerencia])[0].razones.join(' ');
    expect(razones).not.toContain('de 123');
    expect(razones).not.toContain('·');
    expect(sugerenciasParaNia(Array(9).fill(sugerencia))).toHaveLength(6);
  });
});
