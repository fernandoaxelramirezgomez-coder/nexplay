# referencias/

Valores fijos contra los que se compara, versionados a propósito:

- `bandas_referencia.json`: las bandas validadas de los 123 juegos. `modelado/verificar_bandas.py`
  las compara en cada build.
- `particion_gkf_data-v1.csv`: la partición congelada de GroupKFold (appid → fold) que usan los
  notebooks; su firma se comprueba en `00_exploracion`.

Cambiar uno es cambiar la referencia: se hace a propósito y con la evidencia al lado. No va
aquí: datos (`datos/`, no versionado) ni código.
