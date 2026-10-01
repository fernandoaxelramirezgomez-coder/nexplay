# ingesta/

De dónde salen los datos: `ingesta_steam.py` baja juegos y reseñas de la API pública de Steam según
`appids.txt`. No hace falta correrla para usar el proyecto, porque los datos ya están publicados en
releases con tag fijo y `make data` los baja de ahí.

No va aquí: lo que se publica a partir de esos datos (`publicacion/`).
