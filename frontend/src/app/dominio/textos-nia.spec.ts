import {
  COMO_FILTRAR,
  FICHAS_BURBUJA,
  FICHAS_JUEGO,
  PIDE_JUEGO,
  SALUDO_BURBUJA,
  SALUDO_CATALOGO,
  SALUDO_CHAT_CATALOGO,
  cuantosEmojis,
  saludoDeJuego,
  sinMarkdown,
  textoGlobito,
} from './textos-nia';

/** Las mismas fórmulas que vigila como-funciona.spec.ts: Nia describe, no aconseja. */
const PROHIBIDO = ['cómprate', 'compra este', 'te recomiendo comprar', 'abandono', 'banda', 'confiable'];

describe('sinMarkdown', () => {
  it('quita las negritas y las cursivas sin comerse el texto', () => {
    expect(sinMarkdown('El riesgo es **alto** y el motivo es *rendimiento*.')).toBe(
      'El riesgo es alto y el motivo es rendimiento.',
    );
  });

  it('deshace las viñetas y los títulos', () => {
    expect(sinMarkdown('## Motivos\n- rendimiento\n- bugs')).toBe('Motivos\nrendimiento\nbugs');
  });

  it('quita el código en línea', () => {
    expect(sinMarkdown('La banda es `alto`.')).toBe('La banda es alto.');
  });

  it('no toca un asterisco suelto ni una multiplicación', () => {
    expect(sinMarkdown('Cuesta 2 * 3 pesos y el resto sigue igual.')).toBe('Cuesta 2 * 3 pesos y el resto sigue igual.');
  });

  it('deja intacta una respuesta que ya viene en texto plano', () => {
    expect(sinMarkdown(SALUDO_CATALOGO)).toBe(SALUDO_CATALOGO);
  });

  it('aguanta varias negritas en la misma frase y en varias líneas', () => {
    expect(sinMarkdown('**Uno** y **dos**.\nY **tres**.')).toBe('Uno y dos.\nY tres.');
  });
});

describe('textos de Nia', () => {
  const todos = [
    SALUDO_CHAT_CATALOGO,
    SALUDO_BURBUJA,
    saludoDeJuego('Hades', 'bajo'),
    COMO_FILTRAR,
    PIDE_JUEGO,
    ...FICHAS_JUEGO,
    ...FICHAS_BURBUJA,
    ...(['explorar', 'perfil', 'comparar'] as const).flatMap((vista) => Object.values(textoGlobito(vista, 2))),
  ];

  it('ninguno usa fórmulas prohibidas', () => {
    for (const texto of todos) {
      for (const frase of PROHIBIDO) {
        expect(texto.toLowerCase(), texto).not.toContain(frase);
      }
    }
  });

  it('los que habla Nia llevan de 1 a 3 emojis', () => {
    const habla = [SALUDO_CHAT_CATALOGO, SALUDO_BURBUJA, saludoDeJuego('Hades', 'bajo'), COMO_FILTRAR, PIDE_JUEGO];
    for (const texto of [...habla, ...(['explorar', 'perfil', 'comparar'] as const).map((v) => textoGlobito(v, 2).texto)]) {
      expect(cuantosEmojis(texto), texto).toBeGreaterThanOrEqual(1);
      expect(cuantosEmojis(texto), texto).toBeLessThanOrEqual(3);
    }
  });

  it('el saludo de la ficha nombra el juego y su riesgo', () => {
    expect(saludoDeJuego('Hades', 'bajo')).toBe('¿Te explico por qué Hades tiene riesgo bajo? 🙂');
    // El emoji va con el nivel: ninguna sonrisa junto a un riesgo alto.
    expect(saludoDeJuego('Cyberpunk 2077', 'medio')).toBe('¿Te explico por qué Cyberpunk 2077 tiene riesgo medio? 🤔');
    expect(saludoDeJuego('Amnesia: The Bunker', 'alto')).toBe('¿Te explico por qué Amnesia: The Bunker tiene riesgo alto? 😬');
  });

  it('el globito de Comparar dice cuántos juegos resume', () => {
    expect(textoGlobito('comparar', 3).texto).toBe('¿Te resumo en qué se diferencian estos 3? 📊');
  });

  it('el filtro de markdown no toca los emojis, ni los de dos caracteres', () => {
    const texto = '¡Hola! 👋 Hay 25 🎮 y dos son gratis 🎁. Va, en corto ✍️';
    expect(sinMarkdown(texto)).toBe(texto);
    expect(cuantosEmojis(texto)).toBe(4);
  });
});
