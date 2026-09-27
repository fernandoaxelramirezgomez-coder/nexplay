import { JuegoPanorama } from '../api/contrato';
import { PESTANAS_ANTES_DE_PAGAR, barrasAntesDePagar, histogramaDePrecios } from './antes-de-pagar';
import { juegoDePrueba } from './juego-prueba';

const JUEGOS = [
  juegoDePrueba({ appid: 1, banda_riesgo: 'bajo', precio_final: 150 }),
  juegoDePrueba({ appid: 2, banda_riesgo: 'bajo', es_gratis: true, precio_final: 0 }),
  juegoDePrueba({ appid: 3, banda_riesgo: 'medio', precio_final: 300 }),
  juegoDePrueba({ appid: 4, banda_riesgo: 'alto', precio_final: 450 }),
  juegoDePrueba({ appid: 5, banda_riesgo: 'alto', precio_final: 1200 }),
  juegoDePrueba({ appid: 6, banda_riesgo: 'alto', precio_final: null }),
];

function fila(appid: number, resenas: number, casos: number, consenso: string | null): JuegoPanorama {
  return {
    appid,
    resenas,
    casos_senal: casos,
    prevalencia: casos / resenas,
    resenas_en_steam: null,
    positivas_en_steam: null,
    consenso,
    motivo_principal: null,
    horas_al_recomendar: null,
  };
}

const POR_APPID = new Map<number, JuegoPanorama>([
  [1, fila(1, 100, 1, 'Very Positive')],
  [2, fila(2, 100, 1, 'Overwhelmingly Positive')],
  [3, fila(3, 100, 2, 'Very Positive')],
  [4, fila(4, 100, 4, 'Mixed')],
  [5, fila(5, 100, 4, 'Very Positive')],
  [6, fila(6, 100, 4, null)],
]);

describe('«Antes de pagar, esto importa»', () => {
  it('la señal: cuántas veces más en riesgo alto, con una barra por nivel', () => {
    const barras = barrasAntesDePagar('senal', JUEGOS, POR_APPID)!;
    expect(barras.cifra).toBe('4.0×');
    expect(barras.segmentos.map((s) => [s.etiqueta, s.cifra])).toEqual([
      ['Riesgo bajo', '1.00%'],
      ['Riesgo medio', '2.00%'],
      ['Riesgo alto', '4.00%'],
    ]);
  });

  it('el precio: medianas de los juegos de pago y cuántas veces más cuesta riesgo alto', () => {
    const barras = barrasAntesDePagar('precio', JUEGOS, POR_APPID)!;
    expect(barras.segmentos.map((s) => s.cifra)).toEqual(['$150', '$300', '$825']);
    expect(barras.cifra).toBe('5×');
  });

  it('las reseñas positivas: la parte de cada nivel, «23 de 43» en riesgo alto', () => {
    const barras = barrasAntesDePagar('positivas', JUEGOS, POR_APPID)!;
    expect(barras.cifra).toBe('33%');
    expect(barras.segmentos.map((s) => s.cifra)).toEqual(['100%', '100%', '33%']);
    expect(barras.segmentos[2].detalle).toContain('1 de 3 juegos');
  });

  it('el histograma cuenta cada juego con precio una sola vez, en su rango y su nivel', () => {
    const rangos = histogramaDePrecios(JUEGOS);
    expect(rangos.map((r) => r.etiqueta)).toEqual(['Gratis', '<200', '200–400', '400–600', '600–900', '900+']);
    const total = rangos.reduce((suma, r) => suma + r.porNivel.bajo + r.porNivel.medio + r.porNivel.alto, 0);
    expect(total).toBe(5);
    expect(rangos[0].porNivel.bajo).toBe(1);
    expect(rangos[5].porNivel.alto).toBe(1);
  });

  it('habla con el vocabulario del proyecto', () => {
    const textos = [
      ...PESTANAS_ANTES_DE_PAGAR.map((p) => p.nombre),
      ...PESTANAS_ANTES_DE_PAGAR.flatMap((p) => {
        const barras = barrasAntesDePagar(p.id, JUEGOS, POR_APPID)!;
        return [barras.linea, ...barras.segmentos.map((s) => `${s.etiqueta} ${s.detalle}`)];
      }),
      ...histogramaDePrecios(JUEGOS).map((r) => r.detalle),
    ];
    for (const texto of textos) {
      expect(texto.toLowerCase(), texto).not.toMatch(/abandono|banda/);
    }
  });
});
