import { SALUDO_CATALOGO, sinMarkdown } from './textos-nia';

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
