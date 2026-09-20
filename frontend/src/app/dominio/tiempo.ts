/** "hace 5 minutos" a partir de la fecha ISO que devuelve la API (UTC). Más allá de un
 * mes se muestra la fecha, que a esa distancia dice más que "hace 47 días". */
export function hace(creado: string, ahora: Date = new Date()): string {
  const fecha = new Date(creado);
  if (Number.isNaN(fecha.getTime())) {
    return '';
  }

  const segundos = Math.max(0, (ahora.getTime() - fecha.getTime()) / 1000);
  if (segundos < 60) {
    return 'hace un momento';
  }

  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) {
    return `hace ${minutos} ${minutos === 1 ? 'minuto' : 'minutos'}`;
  }

  const horas = Math.floor(minutos / 60);
  if (horas < 24) {
    return `hace ${horas} ${horas === 1 ? 'hora' : 'horas'}`;
  }

  const dias = Math.floor(horas / 24);
  if (dias < 30) {
    return `hace ${dias} ${dias === 1 ? 'día' : 'días'}`;
  }

  return fecha.toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' });
}
