import { segundaOpinion } from './segunda-opinion';

const texto = (segmentos: { texto: string }[]) => segmentos.map((s) => s.texto).join('');

describe('segundaOpinion', () => {
  const motivos = [
    { motivo: 'rendimiento', frecuencia: 0.86 },
    { motivo: 'bugs', frecuencia: 0.25 },
  ];

  it('reproduce la frase de Wild Hearts de Gradio (alto, rendimiento 86%, sin nota)', () => {
    expect(texto(segundaOpinion('alto', motivos, null))).toBe(
      'Comparado con el resto del catálogo, este juego tiende a generar más arrepentimiento temprano.' +
        ' Entre quienes se arrepintieron pronto, el motivo más mencionado es rendimiento' +
        ' (86% de las reseñas clasificadas).' +
        ' No tiene cobertura de crítica especializada (sin nota de Metacritic).',
    );
  });

  it('solo la palabra de la banda va en negrita', () => {
    expect(segundaOpinion('alto', motivos, null).filter((s) => s.clave).map((s) => s.texto)).toEqual(['más']);
    expect(segundaOpinion('bajo', motivos, 96).filter((s) => s.clave).map((s) => s.texto)).toEqual(['menos']);
    expect(segundaOpinion('medio', motivos, 80).filter((s) => s.clave).map((s) => s.texto)).toEqual(['no se distingue']);
  });

  it('califica la crítica por tramos de Metacritic', () => {
    expect(texto(segundaOpinion('bajo', motivos, 96))).toContain('lo calificó bien (Metacritic 96)');
    expect(texto(segundaOpinion('bajo', motivos, 74))).toContain('lo calificó de forma mixta (Metacritic 74)');
    expect(texto(segundaOpinion('bajo', motivos, 49))).toContain('lo calificó mal (Metacritic 49)');
  });

  it('sin motivos lo dice en vez de inventar uno (Cyberpunk 2077: 4 casos)', () => {
    expect(texto(segundaOpinion('medio', [], 86))).toContain(
      'No hay suficientes reseñas de arrepentimiento temprano de este juego para identificar un motivo dominante.',
    );
  });

  it('nunca recomienda comprar o no comprar', () => {
    const todas = (['bajo', 'medio', 'alto'] as const).map((n) => texto(segundaOpinion(n, motivos, 80)));
    for (const frase of todas) {
      expect(frase).not.toMatch(/compr|recomend|evit/i);
    }
  });
});
