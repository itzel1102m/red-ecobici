"""Mapa interactivo de la red de estaciones de Ecobici sobre las alcaldías de la CDMX."""
import base64
import io
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from matplotlib.collections import LineCollection
from scipy.sparse.csgraph import shortest_path

from red_ecobici import cargar_estaciones, construir_red

st.set_page_config(page_title="Red Ecobici", layout="wide")


@st.cache_data
def cargar_alcaldias():
    with open("geo/alcaldias_cdmx.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource
def red(v, t, rodeo):
    return construir_red(cargar_estaciones("estaciones.txt"), v_kmh=v, t_min=t, rodeo=rodeo)


@st.cache_data
def resumen(v, t, rodeo):
    G = red(v, t, rodeo)
    componentes = sorted(nx.connected_components(G), key=len, reverse=True)
    gigante = G.subgraph(componentes[0])
    # diámetro en saltos: BFS desde todos los nodos con scipy (networkx es lento en grafos densos)
    saltos = shortest_path(nx.to_scipy_sparse_array(gigante), unweighted=True, directed=False)
    return {
        "aristas": G.number_of_edges(),
        "densidad": nx.density(G),
        "componentes": len(componentes),
        "diametro": int(saltos.max()),
    }


@st.cache_data
def imagen_aristas(v, t, rodeo):
    """Aristas como PNG transparente y las esquinas (lon, lat) donde va sobre el mapa."""
    G = red(v, t, rodeo)
    pos = {n: (d["lon"], d["lat"]) for n, d in G.nodes(data=True)}
    lon, lat = np.array(list(pos.values())).T
    m = 0.005
    oeste, este, sur, norte = lon.min() - m, lon.max() + m, lat.min() - m, lat.max() + m
    ancho = 1600
    alto = int(ancho * (norte - sur) / ((este - oeste) * np.cos(np.radians(19.4))))
    fig = plt.figure(figsize=(ancho / 100, alto / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    # menos aristas -> cada una puede ser más visible
    alpha = float(np.clip(5000 / max(G.number_of_edges(), 1), 0.03, 0.5))
    ax.add_collection(LineCollection([(pos[a], pos[b]) for a, b in G.edges()],
                                     linewidths=0.4, colors="#1f3b73", alpha=alpha))
    ax.set_xlim(oeste, este)
    ax.set_ylim(sur, norte)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    plt.close(fig)
    img = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    return img, [[oeste, norte], [este, norte], [este, sur], [oeste, sur]]


def mapa(G, img, esquinas, alcaldias):
    nodos = list(G)
    grado = [G.degree(n) for n in nodos]
    fig = go.Figure()
    fig.add_trace(go.Choroplethmap(
        geojson=alcaldias, featureidkey="properties.CVEGEO",
        locations=[f["properties"]["CVEGEO"] for f in alcaldias["features"]],
        z=np.zeros(len(alcaldias["features"])),
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
        marker_line_color="#444", marker_line_width=1.5,
        text=[f["properties"]["NOMGEO"] for f in alcaldias["features"]],
        hovertemplate="%{text}<extra></extra>", name="alcaldías"))
    fig.add_trace(go.Scattermap(
        lat=[G.nodes[n]["lat"] for n in nodos], lon=[G.nodes[n]["lon"] for n in nodos],
        mode="markers",
        marker=dict(size=7, color=grado, colorscale="Viridis", showscale=True,
                    colorbar=dict(title="grado")),
        text=[G.nodes[n]["name"] for n in nodos], customdata=grado,
        hovertemplate="<b>%{text}</b><br>grado: %{customdata}<extra></extra>",
        name="estaciones"))
    fig.update_layout(
        map=dict(style="carto-positron", center=dict(lat=19.41, lon=-99.165), zoom=11.6,
                 layers=[dict(sourcetype="image", source=img, below="traces",
                              coordinates=esquinas)]),
        height=720, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    return fig


st.title("Red de estaciones de Ecobici")

with st.sidebar:
    st.header("Parámetros")
    v = st.number_input("Velocidad (km/h)", 1.0, 30.0, 8.47, 0.01,
                        help="Mediana de los viajes reales de Ecobici, en línea recta.")
    t = st.number_input("Tiempo máximo (min)", 1, 120, 45)
    rodeo = st.number_input("Factor de rodeo", 1.0, 2.0, 1.0, 0.05,
                            help="1.0 = distancia en línea recta, consistente con cómo se calculó la velocidad.")
    st.markdown(f"**Radio:** {v * t / 60:.2f} km")

st.markdown(
    f"Cada punto es una estación. Dos estaciones están conectadas si la distancia en línea recta "
    f"entre ellas es ≤ {v * t / 60:.2f} km, lo que se recorre en {t} min a {v} km/h. "
    "Usa la rueda del ratón para hacer zoom y pasa el cursor sobre una estación para ver su nombre y su grado.")

G = red(v, t, rodeo)
r = resumen(v, t, rodeo)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Estaciones", G.number_of_nodes())
c2.metric("Aristas", f"{r['aristas']:,}")
c3.metric("Densidad", f"{r['densidad']:.3f}")
c4.metric("Componentes conexas", r["componentes"])
c5.metric("Diámetro (saltos)", r["diametro"])

img, esquinas = imagen_aristas(v, t, rodeo)
st.plotly_chart(mapa(G, img, esquinas, cargar_alcaldias()), use_container_width=True,
                config={"scrollZoom": True})

st.subheader("Distribución de grados")
grados = [d for _, d in G.degree()]
hist = go.Figure(go.Histogram(x=grados, nbinsx=40, marker_color="#3b6ea5"))
hist.add_vline(np.mean(grados), line_dash="dash",
               annotation_text=f"media = {np.mean(grados):.0f}")
hist.update_layout(xaxis_title="grado", yaxis_title="número de estaciones",
                   height=350, margin=dict(l=0, r=0, t=20, b=0), bargap=0.05)
st.plotly_chart(hist, use_container_width=True)

st.caption("Datos: feed GBFS station_information de Ecobici · Límites de alcaldías: INEGI, "
           "Marco Geoestadístico 2023 (vía PhantomInsights/mexico-geojson) · Mapa base: © OpenStreetMap, © CARTO")
