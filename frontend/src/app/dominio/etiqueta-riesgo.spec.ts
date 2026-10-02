import { NivelRiesgo } from '../api/contrato';
import { CORTES_DE_NIVEL, definicionDeNiveles } from './etiqueta-riesgo';

const catalogo = (bajo: number, medio: number, alto: number) =>
  (
    [
      ['bajo', bajo],
      ['medio', medio],
      ['alto', alto],
    ] as [NivelRiesgo, number][]
  ).flatMap(([banda_riesgo, cuantos]) => Array.from({ length: cuantos }, () => ({ banda_riesgo })));

/** Una sola definición de los niveles: los cortes salen del entrenamiento, así que el catálogo
 * no queda en tercios. */
describe('definicionDeNiveles', () => {
  it('da los cortes y cuántos juegos del catálogo quedan en cada nivel', () => {
    expect(definicionDeNiveles(catalogo(43, 37, 43))).toBe(
      'Los cortes entre bajo, medio y alto están en los percentiles 33.3 y 66.7 de las estimaciones fuera de ' +
        'pliegue del entrenamiento; en el catálogo quedan 43, 37 y 43.',
    );
  });

  it('sin catálogo, solo los cortes', () => {
    expect(definicionDeNiveles([])).toBe(`${CORTES_DE_NIVEL}.`);
  });

  it('no vuelve a decir tercios del catálogo, partes iguales ni relativo al catálogo', () => {
    expect(definicionDeNiveles(catalogo(43, 37, 43))).not.toMatch(/tercio|partes iguales|relativo al catálogo/i);
  });
});
