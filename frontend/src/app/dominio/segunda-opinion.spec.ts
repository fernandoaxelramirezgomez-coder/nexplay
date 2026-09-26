import { segundaOpinion, titularBanda } from './segunda-opinion';

const texto = (segmentos: { texto: string }[]) => segmentos.map((s) => s.texto).join('');

describe('segundaOpinion', () => {
  const motivos = [
    { motivo: 'rendimiento', frecuencia: 0.86 },
    { motivo: 'bugs', frecuencia: 0.25 },
  ];

  it('arma la frase de Wild Hearts (alto, rendimiento 86%, sin nota)', () => {
    expect(texto(segundaOpinion('alto', motivos, null))).toBe(
      'Comparado con el resto del catálogo, este juego tiende a generar más arrepentimiento temprano.' +
        ' Entre las reseñas con señal de arrepentimiento temprano, el motivo más mencionado es rendimiento' +
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

describe('la n del motivo y la contradicción del Metacritic', () => {
  const motivos = [{ motivo: 'contenido', frecuencia: 1 }];

  it('dice sobre cuántas reseñas se calcula el porcentaje', () => {
    const texto = segundaOpinion('alto', motivos, null, false, 3)
      .map((s) => s.texto)
      .join('');
    expect(texto).toContain('100% de las 3 reseñas clasificadas');
  });

  it('sin el dato, no inventa un número', () => {
    const texto = segundaOpinion('alto', motivos, null)
      .map((s) => s.texto)
      .join('');
    expect(texto).toContain('100% de las reseñas clasificadas');
  });

  it('no repite la nota de la crítica si abajo ya aparece como factor', () => {
    const conFactor = segundaOpinion('alto', motivos, 82, true).map((s) => s.texto).join('');
    const sinFactor = segundaOpinion('alto', motivos, 82, false).map((s) => s.texto).join('');
    expect(conFactor).not.toContain('Metacritic 82');
    expect(sinFactor).toContain('Metacritic 82');
  });

  it('sin nota lo dice siempre, sea factor o no: ahí la ausencia es el dato', () => {
    const texto = segundaOpinion('alto', motivos, null, true).map((s) => s.texto).join('');
    expect(texto).toContain('sin nota de Metacritic');
  });
});

describe('titularBanda', () => {
  /** Al lado del título de la ficha hay una píldora que ya dice "Riesgo medio": el
   * titular del veredicto tiene que decir lo que la píldora no dice. */
  it('no repite la etiqueta de la banda', () => {
    for (const nivel of ['bajo', 'medio', 'alto'] as const) {
      const frase = texto(titularBanda(nivel));
      expect(frase.toLowerCase()).not.toContain(`riesgo ${nivel}`);
      expect(frase).toContain('arrepentimiento temprano');
    }
  });

  it('el titular de medio dice qué significa, no cómo se llama', () => {
    expect(texto(titularBanda('medio'))).toBe('No se distingue del resto del catálogo en arrepentimiento temprano');
  });

  it('marca una sola palabra clave por titular', () => {
    for (const nivel of ['bajo', 'medio', 'alto'] as const) {
      expect(titularBanda(nivel).filter((segmento) => segmento.clave)).toHaveLength(1);
    }
  });
});
