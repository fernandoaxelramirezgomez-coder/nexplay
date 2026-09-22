import { PASOS } from '../como-funciona/como-funciona';
import { ROTULO_RIESGO } from './etiqueta-riesgo';
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
  it('la banda tiene un solo rótulo', () => {
    expect(ROTULO_RIESGO).toBe('Riesgo general');
  });

  it('el aviso de la historia dice que el perfil no cambia el riesgo', () => {
    expect(AVISO_HISTORIA).toContain('Tu perfil no cambia el riesgo estimado');
  });

  it('ningún texto promete ajustar el riesgo con el perfil', () => {
    const textos = [ROTULO_RIESGO, AVISO_HISTORIA, ...PASOS.flatMap((paso) => [paso.titulo, paso.texto])];
    for (const texto of textos) {
      for (const frase of PROMESA_DE_AJUSTE) {
        expect(texto.toLowerCase(), `"${texto}" dice "${frase}"`).not.toContain(frase);
      }
    }
  });
});
