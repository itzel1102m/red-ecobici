"""Arma la red de estaciones de Ecobici.

Dos estaciones se conectan si  rodeo * d_haversine <= v * t,
es decir, si se alcanza una desde la otra en bici en t minutos.

Como módulo:
    from red_ecobici import cargar_estaciones, construir_red
    G = construir_red(cargar_estaciones("estaciones.txt"), v_kmh=8.47, t_min=45, rodeo=1.0)

Desde la terminal:
    python3 red_ecobici.py --v 8.47 --rodeo 1.0 --t 45 \
        --entrada estaciones.txt --salida red_ecobici_v8.47.graphml
"""
import argparse
import json

import networkx as nx
import numpy as np

R_TIERRA_KM = 6371.0088


def cargar_estaciones(ruta):
    with open(ruta, encoding="utf-8") as f:
        feed = json.load(f)
    return feed["data"]["stations"]


def distancias_haversine(lat, lon):
    """Matriz de distancias (km) entre todas las parejas de puntos."""
    lat, lon = np.radians(lat), np.radians(lon)
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlon / 2) ** 2
    return 2 * R_TIERRA_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def construir_red(estaciones, v_kmh, t_min, rodeo):
    radio_km = v_kmh * t_min / 60
    lat = np.array([e["lat"] for e in estaciones], dtype=float)
    lon = np.array([e["lon"] for e in estaciones], dtype=float)
    D = distancias_haversine(lat, lon)

    G = nx.Graph(radio_km=radio_km, v_kmh=v_kmh, t_min=t_min, rodeo=rodeo)
    for e in estaciones:
        G.add_node(str(e["station_id"]), name=e["name"], lat=float(e["lat"]),
                   lon=float(e["lon"]), capacity=int(e.get("capacity", 0)))

    ids = [str(e["station_id"]) for e in estaciones]
    i, j = np.where(np.triu(rodeo * D <= radio_km, k=1))
    G.add_edges_from((ids[a], ids[b], {"dist_km": float(D[a, b])}) for a, b in zip(i, j))
    return G


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--v", type=float, default=8.47, help="velocidad en km/h")
    p.add_argument("--t", type=float, default=45, help="tiempo máximo en minutos")
    p.add_argument("--rodeo", type=float, default=1.0, help="factor de rodeo sobre la línea recta")
    p.add_argument("--entrada", default="estaciones.txt", help="feed GBFS station_information (JSON)")
    p.add_argument("--salida", default="red_ecobici.graphml")
    args = p.parse_args()

    estaciones = cargar_estaciones(args.entrada)
    G = construir_red(estaciones, args.v, args.t, args.rodeo)
    nx.write_graphml(G, args.salida)
    print(f"radio = {G.graph['radio_km']:.3f} km | {G.number_of_nodes()} vértices, "
          f"{G.number_of_edges()} aristas -> {args.salida}")


if __name__ == "__main__":
    main()
