# referencias/

Valores fijos contra los que se compara, versionados a propósito:

- `bandas_referencia.json`: las bandas validadas de los 123 juegos. `modelado/verificar_bandas.py` las
  compara en cada build.
- `particion_gkf_data-v1.csv`: la partición congelada de GroupKFold (appid → fold). La usan toda
  evaluación y los umbrales del modelo (`splits_congelados` en `modelado/entrenar_baseline.py`), y entra a
  la imagen de Render. Su firma se comprueba en `00_exploracion`. No se recalcula: 73 de los 83 juegos
  empatan en 1,500 reseñas y cada versión de scikit-learn desempata distinto.

Cambiar uno es cambiar la referencia: se hace a propósito y con la evidencia al lado. No va aquí: datos
(`datos/`, que no se versiona) ni código.
