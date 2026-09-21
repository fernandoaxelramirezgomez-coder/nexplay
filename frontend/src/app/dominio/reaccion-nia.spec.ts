import { NivelRiesgo } from '../api/contrato';
import { reaccionPara } from './reaccion-nia';
import { SALUDO_CATALOGO } from './textos-nia';

const BANDAS: NivelRiesgo[] = ['bajo', 'medio', 'alto'];

/** Lo que Nia nunca puede decir, sea cual sea la banda. Las primeras confundirían riesgo
 * con fiabilidad; el resto son recomendaciones de compra o afirmaciones absolutas. */
const PROHIBIDO = [
  'confiable',
  'fiable',
  'confianza',
  'seguro',
  'buena compra',
  'mala compra',
  'no lo compres',
  'te vas a arrepentir',
  'vale la pena',
  'abandono',
  'es malo',
];

/** Fórmulas de consejo: Nia describe la estimación, nunca le dice a nadie qué hacer.
 * Solo se buscan en lo que Nia dice, no en la descripción de la imagen. */
const CONSEJO = ['conviene', 'deberías', 'te recomiendo', 'recomendamos', 'antes de decidir', 'busca ', 'revisa '];

/** Todo lo que Nia dice fuera del chat, para aplicarle el mismo criterio. */
const TEXTOS_DE_NIA = [...BANDAS.map((b) => reaccionPara(b).texto), SALUDO_CATALOGO];

describe('reaccionPara', () => {
  it('cada banda tiene su propia emoción, imagen y texto', () => {
    const reacciones = BANDAS.map(reaccionPara);
    expect(new Set(reacciones.map((r) => r.emocion)).size).toBe(3);
    expect(new Set(reacciones.map((r) => r.imagen)).size).toBe(3);
    expect(new Set(reacciones.map((r) => r.texto)).size).toBe(3);
  });

  it('la emoción sigue a la banda', () => {
    expect(reaccionPara('bajo').emocion).toBe('tranquila');
    expect(reaccionPara('medio').emocion).toBe('pensativa');
    expect(reaccionPara('alto').emocion).toBe('cautelosa');
  });

  it('la imagen de cada banda es la suya y vive con los assets de la ficha', () => {
    for (const banda of BANDAS) {
      expect(reaccionPara(banda).imagen).toBe(`nia/ficha-${banda}.png`);
    }
  });

  it('el texto describe la banda que le toca', () => {
    expect(reaccionPara('bajo').texto).toContain('señal baja');
    expect(reaccionPara('medio').texto).toContain('señal mixta');
    expect(reaccionPara('alto').texto).toContain('señal alta');
    for (const banda of BANDAS) {
      expect(reaccionPara(banda).texto).toContain('arrepentimiento temprano');
    }
  });

  it('la descripción accesible nombra la banda', () => {
    for (const banda of BANDAS) {
      expect(reaccionPara(banda).descripcion).toContain(`riesgo relativo ${banda}`);
    }
  });

  it('ningún texto usa fórmulas prohibidas', () => {
    for (const banda of BANDAS) {
      const { texto, descripcion } = reaccionPara(banda);
      const todo = `${texto} ${descripcion}`.toLowerCase();
      for (const frase of PROHIBIDO) {
        expect(todo, `banda ${banda} dice "${frase}"`).not.toContain(frase);
      }
    }
  });
});

describe('textos cortos de Nia', () => {
  it('describen, nunca aconsejan', () => {
    for (const texto of TEXTOS_DE_NIA) {
      const bajo = texto.toLowerCase();
      for (const frase of [...CONSEJO, ...PROHIBIDO]) {
        expect(bajo, `"${texto}" contiene "${frase.trim()}"`).not.toContain(frase);
      }
    }
  });

  it('el saludo del catálogo usa el vocabulario del proyecto', () => {
    expect(SALUDO_CATALOGO).toContain('arrepentimiento temprano');
    expect(SALUDO_CATALOGO).not.toMatch(/arriba|abajo/);
  });
});
