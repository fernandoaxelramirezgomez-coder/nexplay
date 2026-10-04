import { JuegoPanorama } from '../api/contrato';
import { PESTANAS_ANTES_DE_PAGAR, barrasAntesDePagar, histogramaDePrecios } from './antes-de-pagar';
import { juegoDePrueba, senalDePrueba } from './juego-prueba';

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
  it('la señal: cuántas veces más en riesgo alto que en bajo, en los juegos que el modelo no vio', () => {
    const barras = barrasAntesDePagar('senal', JUEGOS, POR_APPID, senalDePrueba())!;
    expect(barras.cifra).toBe('1.9×');
    expect(barras.linea).toBe(
      'más señal de arrepentimiento temprano en riesgo alto que en bajo, en los 40 juegos que el modelo no vio',
    );
    expect(barras.segmentos.map((s) => [s.etiqueta, s.cifra])).toEqual([
      ['Riesgo bajo', '1.86%'],
      ['Riesgo medio', '1.63%'],
      ['Riesgo alto', '3.58%'],
    ]);
  });

  it('dice el intervalo, que es una tendencia, por qué el medio sale abajo y de dónde sale el 4.2×', () => {
    const barras = barrasAntesDePagar('senal', JUEGOS, POR_APPID, senalDePrueba())!;
    expect(barras.notas).toEqual([
      'Intervalo de 95 %: de 0.87× a 3.50×. Con 40 juegos es una tendencia, no una conclusión firme.',
      'El riesgo medio sale un poco abajo del bajo: en juegos que el modelo no vio, el medio no se separa del bajo, ' +
        'y con 13 o 14 juegos por nivel esa diferencia es ruido. Lo que se sostiene es el riesgo alto.',
      'En los 123 juegos son 4.2×, pero ahí cuentan los 83 con que se entrenó el modelo.',
    ]);
  });

  it('si el medio no sale abajo del bajo, no lo explica; sin el corte de los externos, no hay cifra', () => {
    const barras = barrasAntesDePagar('senal', JUEGOS, POR_APPID, senalDePrueba({ resenas: 20000, casos: 500 }))!;
    expect(barras.notas.some((n) => n.startsWith('El riesgo medio'))).toBe(false);
    expect(barrasAntesDePagar('senal', JUEGOS, POR_APPID, senalDePrueba().slice(0, 1))).toBeNull();
  });

  it('no hay pestaña de precio: el precio entra al modelo y compararlo por nivel es circular', () => {
    expect(PESTANAS_ANTES_DE_PAGAR.map((p) => p.id)).toEqual(['senal', 'positivas']);
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
        const barras = barrasAntesDePagar(p.id, JUEGOS, POR_APPID, senalDePrueba())!;
        return [barras.linea, ...barras.notas, ...barras.segmentos.map((s) => `${s.etiqueta} ${s.detalle}`)];
      }),
      ...histogramaDePrecios(JUEGOS).map((r) => r.detalle),
    ];
    for (const texto of textos) {
      expect(texto.toLowerCase(), texto).not.toMatch(/abandono|banda/);
    }
  });
});
