import { PASOS } from '../como-funciona/como-funciona';
import { EXPLICACION_RIESGO, ROTULO_RIESGO } from './etiqueta-riesgo';
import { AVISO_HISTORIA } from './historia-perfil';

/** El modelo es de título: ningún texto puede prometer que el perfil ajusta el riesgo. */
const PROMESA_DE_AJUSTE = [
  'para tu perfil',
  'ajusta la estimación',
  'ajustar esta estimación',
  'se ajusta a cómo juegas',
  'afinar el riesgo',
];

describe('textos sobre el perfil', () => {
  it('el riesgo tiene un solo rótulo, el que eligió el dueño tras la revisión', () => {
    expect(ROTULO_RIESGO).toBe('Riesgo de arrepentimiento');
  });

  /** El nombre podría hacer creer que el riesgo es de quien mira: la explicación lo niega. */
  it('la explicación del riesgo dice que es del juego y no de la persona', () => {
    expect(EXPLICACION_RIESGO).toContain('Es del juego, no de ti.');
  });

  it('el aviso de la historia dice que el perfil no cambia el riesgo', () => {
    expect(AVISO_HISTORIA).toContain('Tu perfil no cambia el riesgo estimado');
  });

  it('ningún texto promete ajustar el riesgo con el perfil', () => {
    const textos = [ROTULO_RIESGO, EXPLICACION_RIESGO, AVISO_HISTORIA, ...PASOS.flatMap((paso) => [paso.titulo, paso.texto])];
    for (const texto of textos) {
      for (const frase of PROMESA_DE_AJUSTE) {
        expect(texto.toLowerCase(), `"${texto}" dice "${frase}"`).not.toContain(frase);
      }
    }
  });
});
