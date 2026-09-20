/** `document.startViewTransition()` aborta con `InvalidStateError: Transition was aborted
 * because of invalid state. Document hidden` cuando la pestaña está oculta, y la navegación
 * queda a medias: la vista no se actualiza y los controles dejan de responder, sin error
 * visible para quien usa la app. `withViewTransitions()` del router la llama sin ese
 * resguardo, así que aquí se envuelve: con el documento oculto se aplica el cambio sin
 * transición, que es justo lo que se vería de todos modos en una pestaña que no se ve. */

type OpcionesTransicion = Parameters<Document['startViewTransition']>[0];

export function protegerTransicionesDeVista(documento: Document = document): void {
  const original = documento.startViewTransition;
  if (typeof original !== 'function') {
    // Navegador sin la API: el router ya actualiza sin transición.
    return;
  }

  documento.startViewTransition = (opciones?: OpcionesTransicion): ViewTransition =>
    documento.visibilityState === 'hidden'
      ? sinTransicion(opciones)
      : original.call(documento, opciones);
}

function sinTransicion(opciones?: OpcionesTransicion): ViewTransition {
  const actualizar = typeof opciones === 'function' ? opciones : opciones?.update;

  const aplicado = new Promise<void>((resolver, rechazar) => {
    try {
      Promise.resolve(actualizar?.()).then(() => resolver(), rechazar);
    } catch (error) {
      rechazar(error);
    }
  });
  // Un fallo del callback no debe quedar como rechazo sin atender.
  aplicado.catch(() => undefined);

  return {
    ready: aplicado,
    finished: aplicado,
    updateCallbackDone: aplicado,
    skipTransition: () => undefined,
    types: new Set<string>() as unknown as ViewTransitionTypeSet,
  };
}
