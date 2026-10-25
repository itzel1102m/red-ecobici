# Red de estaciones de Ecobici

Mapa interactivo de la red de estaciones de Ecobici (CDMX) sobre las alcaldías.

Cada vértice es una estación y dos estaciones se conectan si la distancia haversine entre ellas
es menor o igual a lo que se recorre en bici en 45 minutos:

- Velocidad: 8.47 km/h, la mediana de los viajes reales de Ecobici, calculada con distancia en línea recta.
- Radio: 8.47 × 0.75 h = 6.35 km.
- Sin factor de rodeo (1.0), consistente con cómo se calculó la velocidad.

La velocidad, el tiempo y el factor de rodeo se pueden cambiar en la barra lateral de la app.

## Archivos

- `streamlit_app.py`: la app.
- `red_ecobici.py`: funciones para cargar las estaciones y construir la red. También se puede correr desde la terminal:
  `python3 red_ecobici.py --v 8.47 --rodeo 1.0 --salida red.graphml`
- `estaciones.txt`: feed GBFS `station_information` de Ecobici (677 estaciones).
- `geo/alcaldias_cdmx.json`: límites de las 16 alcaldías, INEGI Marco Geoestadístico 2023,
  tomados de [PhantomInsights/mexico-geojson](https://github.com/PhantomInsights/mexico-geojson) (licencia MIT).

## Correr localmente

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
