import { JuegoCatalogo } from '../api/contrato';
import { juegoDePrueba } from './juego-prueba';
import {
  CriteriosSugerencia,
  DatosDeJuego,
  NOTA_DESEMPATE,
  hayEmpates,
  porQueCoincide,
  sugerenciasPara,
} from './sugerencias';

function perfil(generos: string[], cambios: Partial<CriteriosSugerencia> = {}): CriteriosSugerencia {
  return { generos, gasto: null, juegaPoco: false, friccionBaja: false, ...cambios };
}

function juego(nombre: string, generos: string[], cambios: Partial<JuegoCatalogo> = {}): JuegoCatalogo {
  return juegoDePrueba({ appid: nombre.length * 1000 + generos.length, nombre, generos, ...cambios });
}

/** Catálogo chico con la misma forma que el real: "Acción" abundante y "Carreras" raro. */
const CATALOGO: JuegoCatalogo[] = [
  juego('Cities: Skylines', ['Simuladores', 'Estrategia'], { metacritic: 85, precio_final: 449 }),
  juego('Frostpunk', ['Simuladores', 'Estrategia'], { metacritic: 84, precio_final: 334 }),
  juego('Kitchen Sink', ['Acción', 'Aventura', 'Indie', 'Rol', 'Simuladores', 'Estrategia'], { metacritic: 90 }),
  juego('Doom', ['Acción'], { metacritic: 85, precio_final: 499 }),
  juego('Dark Souls', ['Acción'], { metacritic: 89, precio_final: 819 }),
  juego('Portal', ['Acción'], { metacritic: 90, precio_final: 123 }),
  juego('Disco Elysium', ['Rol'], { metacritic: 91, precio_final: 419 }),
  juego('Dirt Rally', ['Carreras', 'Simuladores'], { metacritic: 84, precio_final: 163 }),
  juego('Unpacking', ['Casual', 'Indie', 'Simuladores'], { metacritic: 83, precio_final: 159 }),
];

describe('sugerenciasPara', () => {
  it('sin nada declarado no hay con qué sugerir', () => {
    const resultado = sugerenciasPara(CATALOGO, perfil([]));
    expect(resultado.motivo).toBe('sin-respuestas');
    expect(resultado.sugerencias).toEqual([]);
  });

  it('sin perfil tampoco sugiere nada', () => {
    expect(sugerenciasPara(CATALOGO, null).motivo).toBe('sin-respuestas');
  });

  it('solo sugiere juegos que comparten un género declarado', () => {
    const { sugerencias, candidatos } = sugerenciasPara(CATALOGO, perfil(['Simuladores', 'Estrategia']));
    expect(candidatos).toBe(5);
    for (const sugerencia of sugerencias) {
      expect(sugerencia.coincidencias.length).toBeGreaterThan(0);
    }
    // Los tres cubren los dos géneros declarados; entre ellos manda la nota de la crítica.
    expect(sugerencias.slice(0, 3).map((s) => s.juego.nombre)).toEqual([
      'Kitchen Sink',
      'Cities: Skylines',
      'Frostpunk',
    ]);
  });

  /** Antes el juego que traía seis géneros bajaba por traerlos, y eso dejaba tres
   * coincidencias por debajo de dos. Ahora traer géneros de más solo desempata al final:
   * con la misma cobertura, la misma nota y el mismo precio, gana el que coincide justo. */
  it('el que acapara géneros solo gana si además tiene mejor nota', () => {
    const { sugerencias } = sugerenciasPara(CATALOGO, perfil(['Simuladores', 'Estrategia']));
    expect(sugerencias[0].juego.nombre).toBe('Kitchen Sink');
    expect(sugerencias[0].juego.metacritic).toBe(90);
  });

  it('con todo lo demás igual, el que coincide justo va antes que el acaparador', () => {
    // Sobre el catálogo completo: con dos juegos sueltos ningún género es raro y los pesos
    // salen todos en cero, que es justo cuando la rareza no significa nada.
    const justo = juego('Justo', ['Estrategia', 'Simuladores'], { metacritic: 85, precio_final: 300 });
    const acapara = juego('Acapara', ['Estrategia', 'Simuladores', 'Acción', 'Rol', 'Indie'], {
      metacritic: 85,
      precio_final: 300,
    });
    const { sugerencias } = sugerenciasPara(
      [...CATALOGO, acapara, justo],
      perfil(['Estrategia', 'Simuladores']),
    );
    const nombres = sugerencias.map((s) => s.juego.nombre);
    expect(nombres.indexOf('Justo')).toBeGreaterThanOrEqual(0);
    expect(nombres.indexOf('Justo')).toBeLessThan(nombres.indexOf('Acapara'));
  });

  it('con un género raro devuelve los pocos que hay, sin rellenar', () => {
    const { sugerencias, candidatos, motivo } = sugerenciasPara(CATALOGO, perfil(['Carreras']));
    expect(motivo).toBe('ok');
    expect(candidatos).toBe(1);
    expect(sugerencias.map((s) => s.juego.nombre)).toEqual(['Dirt Rally']);
  });

  it('si ningún juego coincide, lo dice en vez de devolver una lista vacía sin motivo', () => {
    const { motivo, candidatos } = sugerenciasPara(CATALOGO, perfil(['Deportes']));
    expect(motivo).toBe('sin-candidatos');
    expect(candidatos).toBe(0);
  });

  it('los empates se rompen por crítica, luego precio y luego nombre', () => {
    const { sugerencias } = sugerenciasPara(CATALOGO, perfil(['Acción']));
    const empatados = sugerencias.filter((s) => s.juego.generos.length === 1);
    expect(empatados.map((s) => s.juego.nombre)).toEqual(['Portal', 'Dark Souls', 'Doom']);
    // Cuatro juegos cubren "Acción" entero, así que cada uno empata con los otros tres.
    expect(empatados.map((s) => s.empatanConEl)).toEqual([3, 3, 3]);
  });

  it('el precio no cambia la afinidad: solo desempata', () => {
    const caro = juego('Caro', ['Estrategia'], { metacritic: 80, precio_final: 1599 });
    const barato = juego('Barato', ['Estrategia'], { metacritic: 80, precio_final: 99 });
    const { sugerencias } = sugerenciasPara([caro, barato], perfil(['Estrategia']));
    expect(sugerencias[0].afinidad).toBe(sugerencias[1].afinidad);
    expect(sugerencias.map((s) => s.juego.nombre)).toEqual(['Barato', 'Caro']);
  });

  it('la cobertura ordena, pero no se usa como probabilidad', () => {
    const { sugerencias } = sugerenciasPara(CATALOGO, perfil(['Simuladores', 'Estrategia']));
    const valores = sugerencias.map((s) => s.cobertura);
    expect(valores).toEqual([...valores].sort((a, b) => b - a));
    for (const valor of valores) {
      expect(valor).toBeGreaterThan(0);
      expect(valor).toBeLessThanOrEqual(1);
    }
  });

  it('la banda de riesgo no interviene en el orden', () => {
    const catalogo = [
      juego('Riesgoso', ['Estrategia'], { banda_riesgo: 'alto', metacritic: 90, precio_final: 200 }),
      juego('Tranquilo', ['Estrategia'], { banda_riesgo: 'bajo', metacritic: 80, precio_final: 200 }),
    ];
    const { sugerencias } = sugerenciasPara(catalogo, perfil(['Estrategia']));
    expect(sugerencias.map((s) => s.juego.nombre)).toEqual(['Riesgoso', 'Tranquilo']);
  });
});

describe('porQueCoincide', () => {
  it('nombra los géneros y qué tan específicos son', () => {
    const { sugerencias } = sugerenciasPara(CATALOGO, perfil(['Simuladores', 'Estrategia']));
    const texto = porQueCoincide(sugerencias[0], CATALOGO.length);
    expect(texto).toContain('Simuladores y Estrategia');
    // Con dos géneros nombra el más específico, que es el que pesa en el orden.
    expect(texto).toContain('el más específico, Estrategia');
    expect(texto).toContain(`de ${CATALOGO.length} juegos`);

    const uno = porQueCoincide(sugerenciasPara(CATALOGO, perfil(['Carreras'])).sugerencias[0], CATALOGO.length);
    expect(uno).toContain(`Coincide en Carreras, que está en 1 de ${CATALOGO.length} juegos del catálogo`);
  });

  it('la regla de desempate se dice aparte, no en cada tarjeta', () => {
    const conEmpate = sugerenciasPara(CATALOGO, perfil(['Acción'])).sugerencias;
    expect(porQueCoincide(conEmpate[0], CATALOGO.length)).not.toContain('crítica');
    expect(hayEmpates(conEmpate)).toBe(true);
    expect(NOTA_DESEMPATE).toContain('nota de la crítica');

    const sinEmpate = sugerenciasPara(CATALOGO, perfil(['Carreras'])).sugerencias;
    expect(hayEmpates(sinEmpate)).toBe(false);
  });

  it('describe la coincidencia sin aconsejar ni prometer', () => {
    const prohibido = ['te recomiendo', 'deberías', 'conviene', 'vale la pena', 'buena compra', 'para tu perfil'];
    const { sugerencias } = sugerenciasPara(CATALOGO, perfil(['Simuladores', 'Estrategia']));
    for (const sugerencia of sugerencias) {
      const texto = porQueCoincide(sugerencia, CATALOGO.length).toLowerCase();
      for (const frase of prohibido) {
        expect(texto, `"${texto}" dice "${frase}"`).not.toContain(frase);
      }
    }
  });
});

/** El caso que reportó la revisión: con Acción, Aventura y Casual declarados, el orden
 * ponía tres coincidencias por debajo de dos y "sin nota" por encima de 81. Los datos son
 * los del catálogo real (géneros, Metacritic y precio de esos seis juegos). */
describe('el orden que reportó la revisión', () => {
  const CATALOGO = [
    juego('Marvel’s Spider-Man Remastered', ['Acción', 'Aventura', 'Casual'], { metacritic: null, precio_final: 999 }),
    juego('Battlefield™ 2042', ['Acción', 'Aventura', 'Casual'], { metacritic: null, precio_final: 1399 }),
    juego('Starbound', ['Acción', 'Aventura', 'Casual', 'Indie', 'Rol'], { metacritic: 81, precio_final: 204.99 }),
    juego('Vampire Survivors', ['Acción', 'Casual', 'Indie', 'Rol'], { metacritic: 86, precio_final: 59 }),
    juego('Diablo® IV', ['Acción', 'Aventura', 'Casual', 'Rol', 'Indie'], { metacritic: null, precio_final: 249.75 }),
    juego('The Sims™ 4', ['Aventura', 'Casual', 'Indie', 'Simuladores'], { metacritic: null, precio_final: null }),
  ];
  const DECLARADO = perfil(['Acción', 'Aventura', 'Casual']);

  it('los que cubren los tres géneros van antes que los que cubren dos', () => {
    const orden = sugerenciasPara(CATALOGO, DECLARADO).sugerencias.map((s) => s.juego.nombre);
    const treses = ['Marvel’s Spider-Man Remastered', 'Battlefield™ 2042', 'Starbound', 'Diablo® IV'];
    const doses = ['Vampire Survivors', 'The Sims™ 4'];
    for (const tres of treses) {
      for (const dos of doses) {
        expect(orden.indexOf(tres)).toBeLessThan(orden.indexOf(dos));
      }
    }
  });

  it('entre los que cubren lo mismo, el que tiene nota va antes que los que no', () => {
    const orden = sugerenciasPara(CATALOGO, DECLARADO).sugerencias.map((s) => s.juego.nombre);
    expect(orden[0]).toBe('Starbound');
    expect(orden.indexOf('Starbound')).toBeLessThan(orden.indexOf('Diablo® IV'));
  });

  it('sin nota, desempata el precio de menor a mayor', () => {
    const orden = sugerenciasPara(CATALOGO, DECLARADO).sugerencias.map((s) => s.juego.nombre);
    expect(orden).toEqual([
      'Starbound',
      'Diablo® IV',
      'Marvel’s Spider-Man Remastered',
      'Battlefield™ 2042',
      'Vampire Survivors',
      'The Sims™ 4',
    ]);
  });

  it('el precio desconocido va al final, y el gratuito al principio', () => {
    const iguales = [
      juego('Sin precio', ['Acción'], { metacritic: 80, precio_final: null, es_gratis: false }),
      juego('Gratis', ['Acción'], { metacritic: 80, precio_final: null, es_gratis: true }),
      juego('Barato', ['Acción'], { metacritic: 80, precio_final: 50 }),
    ];
    expect(sugerenciasPara(iguales, perfil(['Acción'])).sugerencias.map((s) => s.juego.nombre)).toEqual([
      'Gratis',
      'Barato',
      'Sin precio',
    ]);
  });
});

describe('el resto del perfil', () => {
  const corto = juego('Corto', ['Acción'], { appid: 91, metacritic: 70, precio_final: 150 });
  const largo = juego('Largo', ['Acción'], { appid: 92, metacritic: 95, precio_final: 150 });
  const conBugs = juego('Con bugs', ['Acción'], { appid: 93, metacritic: 95, precio_final: 150 });
  const caro = juego('Caro', ['Acción'], { appid: 94, metacritic: 99, precio_final: 900 });
  const gratis = juego('Gratis', ['Acción'], { appid: 95, metacritic: 60, precio_final: null, es_gratis: true });
  const catalogo = [corto, largo, conBugs, caro, gratis];
  const datos = new Map<number, DatosDeJuego>([
    [corto.appid, { horas_al_recomendar: 6, motivo_principal: 'contenido' }],
    [largo.appid, { horas_al_recomendar: 120, motivo_principal: 'contenido' }],
    [conBugs.appid, { horas_al_recomendar: 8, motivo_principal: 'bugs' }],
    [caro.appid, { horas_al_recomendar: 10, motivo_principal: null }],
    [gratis.appid, { horas_al_recomendar: 3, motivo_principal: null }],
  ]);
  const nombres = (criterios: CriteriosSugerencia) =>
    sugerenciasPara(catalogo, criterios, datos).sugerencias.map((s) => s.juego.nombre);

  it('el gasto deja fuera lo que pasa del tope; los gratuitos siempre entran', () => {
    const lista = nombres(perfil(['Acción'], { gasto: 1 }));
    expect(lista).not.toContain('Caro');
    expect(lista).toContain('Gratis');
  });

  it('si el tope deja la lista vacía, sube de tramo y lo avisa: nunca en blanco', () => {
    const soloCaros = [caro, juego('Otro caro', ['Acción'], { appid: 96, precio_final: 650 })];
    const resultado = sugerenciasPara(soloCaros, perfil(['Acción'], { gasto: 1 }), datos);
    expect(resultado.sugerencias.length).toBeGreaterThan(0);
    expect(resultado.topeRelajado).toEqual({ pedido: 200, usado: 1000 });
    expect(sugerenciasPara(catalogo, perfil(['Acción'], { gasto: 1 }), datos).topeRelajado).toBeNull();
  });

  it('sin géneros, el gasto basta para sugerir', () => {
    const resultado = sugerenciasPara(catalogo, perfil([], { gasto: 1 }), datos);
    expect(resultado.motivo).toBe('ok');
    expect(resultado.sugerencias.map((s) => s.juego.nombre)).not.toContain('Caro');
  });

  it('si juega poco, van antes los que se recomiendan con pocas horas encima', () => {
    const lista = nombres(perfil(['Acción'], { juegaPoco: true }));
    expect(lista.indexOf('Corto')).toBeLessThan(lista.indexOf('Largo'));
    // Sin ese criterio, la crítica pone a Largo antes.
    const sin = nombres(perfil(['Acción']));
    expect(sin.indexOf('Largo')).toBeLessThan(sin.indexOf('Corto'));
  });

  it('si la fricción le pesa, van después los que se quejan de bugs o dificultad', () => {
    const lista = nombres(perfil(['Acción'], { friccionBaja: true }));
    expect(lista.indexOf('Largo')).toBeLessThan(lista.indexOf('Con bugs'));
  });

  it('cada tarjeta dice sus razones, solo de lo declarado, y lo que no cumple', () => {
    const { sugerencias } = sugerenciasPara(catalogo, perfil(['Acción'], { gasto: 2, juegaPoco: true, friccionBaja: true }), datos);
    const deBugs = sugerencias.find((s) => s.juego.nombre === 'Con bugs')!;
    expect(deBugs.razones.map((r) => r.tipo)).toEqual(['generos', 'precio', 'horas', 'friccion']);
    expect(deBugs.razones.find((r) => r.tipo === 'friccion')).toEqual({
      tipo: 'friccion',
      cumple: false,
      texto: 'Su queja principal es bugs',
    });
    const deLargo = sugerencias.find((s) => s.juego.nombre === 'Largo')!;
    expect(deLargo.razones.find((r) => r.tipo === 'horas')).toEqual({
      tipo: 'horas',
      cumple: false,
      texto: 'Pide más: ~120 h al recomendarlo',
    });
    expect(deLargo.razones.find((r) => r.tipo === 'precio')?.texto).toBe('$150 · dentro de tu tope');

    const soloGeneros = sugerenciasPara(catalogo, perfil(['Acción']), datos).sugerencias[0];
    expect(soloGeneros.razones.map((r) => r.tipo)).toEqual(['generos']);
  });
});

