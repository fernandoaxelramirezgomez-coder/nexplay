import { JuegoCatalogo, JuegoPanorama, NivelRiesgo, PanoramaCatalogo } from '../api/contrato';
import { cifrasDeLaMuestra, hallazgoPrecio, hallazgoSenal, hallazgoSteam, hallazgosDelInicio } from './hallazgos-inicio';
import { juegoDePrueba } from './juego-prueba';

let siguiente = 1;

function juego(banda: NivelRiesgo, cambios: Partial<JuegoCatalogo> = {}): JuegoCatalogo {
  return juegoDePrueba({ appid: siguiente++, banda_riesgo: banda, ...cambios });
}

function fila(appid: number, cambios: Partial<JuegoPanorama> = {}): JuegoPanorama {
  return {
    appid,
    resenas: 1000,
    casos_senal: 10,
    prevalencia: 0.01,
    resenas_en_steam: 1000,
    positivas_en_steam: 900,
    consenso: 'Mixed',
    motivo_principal: null,
    horas_al_recomendar: 20,
    ...cambios,
  };
}

/** Se leen con espacio normal: las cifras llevan espacio duro antes de «%». */
function texto(frase: string): string {
  return frase.replaceAll(' ', ' ');
}

describe('hallazgos del Inicio', () => {
  const bajo = juego('bajo', { precio_final: 179.49 });
  const medio = juego('medio', { precio_final: 359 });
  const alto = juego('alto', { precio_final: 579.99 });
  const altoGratis = juego('alto', { es_gratis: true, precio_final: null });
  const juegos = [bajo, medio, alto, altoGratis];
  const porAppid = new Map([
    [bajo.appid, fila(bajo.appid, { resenas: 10000, casos_senal: 102 })],
    [medio.appid, fila(medio.appid, { resenas: 10000, casos_senal: 131 })],
    [alto.appid, fila(alto.appid, { resenas: 10000, casos_senal: 429, consenso: 'Very Positive' })],
    [altoGratis.appid, fila(altoGratis.appid, { resenas: 0, casos_senal: 0, consenso: 'Mixed' })],
  ]);

  it('la señal: cuántas veces más en riesgo alto, sin decir que el modelo no vio las reseñas', () => {
    const h = hallazgoSenal(juegos, porAppid)!;
    expect(h.cifra).toBe('4.2×');
    expect(texto(h.frase)).toBe(
      'Los juegos de riesgo alto tienen 4 veces más reseñas de arrepentimiento temprano que los de riesgo bajo (4.29 % vs 1.02 %).',
    );
    expect(h.dato).toBe('El modelo asigna el riesgo con datos del juego, sin leer las reseñas.');
    expect(h.fuente).toBe('30,000 reseñas de Steam');
  });

  it('el precio: medianas redondeadas en grande y exactas en el dato, "más del triple" sin redondear', () => {
    const h = hallazgoPrecio(juegos)!;
    expect([h.cifra, h.union, h.otra]).toEqual(['$580', 'vs', '$179']);
    expect(h.frase).toBe('Los de riesgo alto cuestan más del triple que los de riesgo bajo.');
    expect(h.dato).toBe('Mediana de precio de los juegos de pago: $579.99 contra $179.49.');
  });

  it('el precio con una razón sin palabra propia dice "N veces lo que"', () => {
    const h = hallazgoPrecio([juego('bajo', { precio_final: 100 }), juego('alto', { precio_final: 450 })])!;
    expect(h.frase).toBe('Los de riesgo alto cuestan 4.5 veces lo que los de riesgo bajo.');
  });

  it('Steam: cuántos de riesgo alto tienen reseñas muy o extremadamente positivas', () => {
    const h = hallazgoSteam(juegos, porAppid)!;
    expect([h.cifra, h.union, h.otra]).toEqual(['1', 'de', '2']);
    expect(h.dato).toBe('La crítica general no ve lo que pasa en las primeras dos horas.');
  });

  it('el trío va en el orden acordado y sin datos no inventa tarjetas', () => {
    expect(hallazgosDelInicio(juegos, porAppid).map((h) => h.id)).toEqual(['senal', 'precio', 'steam']);
    expect(hallazgosDelInicio([], new Map())).toEqual([]);
  });

  it('las cifras de la muestra, con los no vistos que dice el modelo', () => {
    const panorama = {
      resenas_descargadas: 184367,
      casos_senal: 4126,
      modelo: { version: 'v', datos: 'data-v1', juegos_entrenamiento: 83, resenas_entrenamiento: 123972 },
    } as PanoramaCatalogo;
    const catalogo = Array.from({ length: 123 }, () => juego('bajo'));
    expect(cifrasDeLaMuestra(catalogo, panorama).map((c) => `${c.cifra} ${c.texto}`)).toEqual([
      '123 juegos de Steam',
      '184,367 reseñas',
      '4,126 con señal de arrepentimiento',
      '40 juegos que el modelo no vio, para probarlo',
    ]);
    const sinModelo = { ...panorama, modelo: { ...panorama.modelo, juegos_entrenamiento: null } };
    expect(cifrasDeLaMuestra(catalogo, sinModelo)).toHaveLength(3);
  });
});
