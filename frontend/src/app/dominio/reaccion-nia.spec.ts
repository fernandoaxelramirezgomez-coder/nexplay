import { NivelRiesgo } from '../api/contrato';
import { reaccionPara } from './reaccion-nia';

const BANDAS: NivelRiesgo[] = ['bajo', 'medio', 'alto'];

/** Lo que Nia nunca puede decir, sea cual sea la banda. Las tres primeras confundirían
 * riesgo con fiabilidad; el resto son recomendaciones de compra o afirmaciones absolutas. */
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

  it('el texto no contradice la banda', () => {
    expect(reaccionPara('bajo').texto).toContain('favorables');
    expect(reaccionPara('medio').texto).toContain('mixtas');
    expect(reaccionPara('alto').texto).toContain('mayor riesgo relativo');
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
