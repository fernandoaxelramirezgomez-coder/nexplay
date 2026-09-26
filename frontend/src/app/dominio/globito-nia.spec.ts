import { debeMostrarGlobito, hoyLocal, marcarGlobito, vistaConGlobito } from './globito-nia';

describe('globito de la burbuja', () => {
  it('sale una vez por vista y no vuelve hasta el día siguiente', () => {
    let vistos = {};
    expect(debeMostrarGlobito('explorar', '2026-09-26', vistos)).toBe(true);
    vistos = marcarGlobito('explorar', '2026-09-26', vistos);
    expect(debeMostrarGlobito('explorar', '2026-09-26', vistos)).toBe(false);
    expect(debeMostrarGlobito('perfil', '2026-09-26', vistos)).toBe(true);
    expect(debeMostrarGlobito('explorar', '2026-09-27', vistos)).toBe(true);
  });

  it('el día es el local, no el de UTC', () => {
    expect(hoyLocal(new Date(2026, 8, 26, 23, 50))).toBe('2026-09-26');
    expect(hoyLocal(new Date(2026, 0, 3))).toBe('2026-01-03');
  });

  it('solo Explorar, Tu perfil y Comparar tienen globito', () => {
    expect(vistaConGlobito('/explorar?q=hades')).toBe('explorar');
    expect(vistaConGlobito('/perfil')).toBe('perfil');
    expect(vistaConGlobito('/comparar?appids=1,2')).toBe('comparar');
    expect(vistaConGlobito('/juego/1145360')).toBeNull();
    expect(vistaConGlobito('/')).toBeNull();
  });
});
