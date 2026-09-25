import { protegerTransicionesDeVista } from './transiciones-seguras';

function documentoFalso(visibilidad: DocumentVisibilityState) {
  const llamadasNativas: number[] = [];
  const doc = {
    visibilityState: visibilidad,
    startViewTransition(callback: () => unknown): ViewTransition {
      llamadasNativas.push(1);
      callback();
      const listo = Promise.resolve();
      return {
        ready: listo,
        finished: listo,
        updateCallbackDone: listo,
        skipTransition: () => undefined,
        types: new Set<string>() as unknown as ViewTransitionTypeSet,
      };
    },
  } as unknown as Document;
  return { doc, llamadasNativas };
}

describe('protegerTransicionesDeVista', () => {
  it('con el documento oculto no llama a la API nativa pero sí aplica el cambio', async () => {
    const { doc, llamadasNativas } = documentoFalso('hidden');
    protegerTransicionesDeVista(doc);

    let aplicado = false;
    const transicion = doc.startViewTransition!(() => (aplicado = true));
    await transicion.finished;

    expect(aplicado).toBe(true);
    expect(llamadasNativas).toHaveLength(0);
    expect(() => transicion.skipTransition()).not.toThrow();
  });

  it('con el documento visible delega en la API nativa', async () => {
    const { doc, llamadasNativas } = documentoFalso('visible');
    protegerTransicionesDeVista(doc);

    await doc.startViewTransition!(() => undefined).finished;

    expect(llamadasNativas).toHaveLength(1);
  });

  it('si el callback falla estando oculto, la promesa rechaza en vez de romper la navegación', async () => {
    const { doc } = documentoFalso('hidden');
    protegerTransicionesDeVista(doc);

    const transicion = doc.startViewTransition!(() => {
      throw new Error('falló el cambio de vista');
    });

    await expect(transicion.updateCallbackDone).rejects.toThrow('falló el cambio de vista');
  });

  it('en un navegador sin la API no rompe nada', () => {
    const doc = { visibilityState: 'visible' } as Document;
    expect(() => protegerTransicionesDeVista(doc)).not.toThrow();
    expect((doc as Document & { startViewTransition?: unknown }).startViewTransition).toBeUndefined();
  });
});
