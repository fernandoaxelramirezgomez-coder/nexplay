# Sugerencias por afinidad: qué son y qué no son

En `/perfil`, con un perfil declarado, aparece la sección **"Juegos con características
parecidas a lo que declaraste"**. Es el único lugar del sitio donde el perfil declarado
tiene un efecto real: el modelo de riesgo (B+) es de título y no usa ningún dato del perfil.

**Los dos sistemas son independientes y no deben mezclarse.**

| | Modelo de riesgo (B+) | Sugerencias por afinidad |
|---|---|---|
| Qué estima | Riesgo de arrepentimiento temprano del **título** | Qué juegos comparten **géneros** con lo declarado |
| De dónde sale | Precio, descuento y cobertura/nota de crítica | Los géneros que la persona eligió en el formulario |
| Etiqueta real | Sí: `playtime_at_review < 120 y voted_up == 0` | **No existe ninguna** |
| Cómo se validó | GroupKFold por `appid`, PR-AUC, prueba externa con 40 títulos | **No se puede validar** |
| Efecto del perfil | Ninguno | Es lo único que lo determina |

## La limitación, dicha claro

El modelo de riesgo se puede medir porque hay una columna que dice si pasó lo que el modelo
predice. **Estas sugerencias no tienen nada equivalente.** En los datos no hay ninguna
columna que diga si a alguien le gustó un juego, si lo compró, ni si lo habría comprado.
Lo único que la sección puede afirmar es que un juego **comparte géneros** con lo que la
persona declaró.

Eso significa que no hay forma de calcular su precisión, ni de decir que acierta X% de las
veces, ni de compararla contra un clasificador trivial: no hay contra qué compararla. Es
una **herramienta exploratoria por similitud declarada** —una forma de filtrar 123 juegos
con lo que alguien dijo de sí mismo—, no un modelo evaluado. Por eso en la interfaz nunca
lleva un número, una métrica ni la palabra "recomendación".

## Cómo se calcula (`frontend/src/app/dominio/sugerencias.ts`)

1. **Filtro duro:** entra solo el juego que comparte al menos un género declarado y que no
   tiene ninguno de los rechazados. Sin ese filtro, con un género raro la lista se rellenaba
   con juegos sin nada en común: con "Carreras" hay 4 juegos en todo el catálogo.
2. **Orden:** Jaccard ponderado por rareza — la suma del peso de los géneros compartidos
   sobre la suma de la unión, donde cada género pesa `log(total / juegos con ese género)`.
   Coincidir en "Carreras" (4 juegos) dice más que coincidir en "Acción" (78 de 123), y un
   juego que trae seis géneros de más no le gana al que coincide justo.
3. **La afinidad mira solo géneros.** El precio y la nota de la crítica **desempatan**, no
   puntúan: así la explicación de por qué un juego va antes que otro es literal.
4. **Desempate:** nota de la crítica, luego precio, luego nombre. Con "Acción" empatan 16
   juegos del catálogo real, así que hacía falta un criterio estable y explicable.

Cada tarjeta dice qué géneros coincidieron y qué tan específico es el más raro de ellos
("Estrategia está en 26 de 123 juegos"), más precio, crítica y **la banda de riesgo al
lado, rotulada como lo que es**. La banda nunca entra al cálculo: de las sugerencias de un
perfil de Rol y Aventura, 6 de 10 resultaron de banda alta, y esa tensión se muestra en vez
de esconderse.

## Límites de los datos que la interfaz reconoce

- **Solo los géneros del perfil se usan.** De los cinco campos declarados, es el único con
  correspondencia limpia en el catálogo. El presupuesto no se pregunta, así que no se
  inventa; la tolerancia a la fricción no tiene equivalente (lo más parecido son los motivos
  frecuentes, que salen de las mismas reseñas Y=1 del modelo de riesgo, y usarlos aquí
  mezclaría los dos sistemas).
- **Los géneros de Steam son gruesos y a veces raros:** *Battlefield 2042* está etiquetado
  como "Casual". Por eso se muestra siempre cuál coincidió, para que se vea de dónde salió.
- **Puede haber pocos candidatos, o ninguno**, y la sección lo dice con su número en vez de
  rellenar la lista o quedarse vacía sin explicación.
