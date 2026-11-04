import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import heapq

# Configuración inicial de la página
st.set_page_config(
    page_title="Enterprise Routing & Sink Tree Simulator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual moderno y limpio
st.markdown("""
    <style>
        .main { background-color: #0e1117; color: #ffffff; }
        .stMetric { background-color: #1a1c23; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

st.title("🌐 Enterprise Multi-Variable Routing & Sink Tree Simulator")
st.markdown(
    "Simulador de enrutamiento adaptativo de alta fidelidad basado en el **Principio de Optimalidad**, "
    "función de costos multicriterio ($α, β, γ$) y control avanzado de saltos."
)

# ==========================================
# 1. GESTIÓN DEL ESTADO (SESSION STATE)
# ==========================================
if "nodes" not in st.session_state:
    st.session_state.nodes = [
        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"
    ]

if "edges" not in st.session_state:
    base_edges = [
        ("A", "B", 5, 100, 99.9), ("A", "D", 8, 100, 99.8), ("A", "F", 12, 50, 99.5),
        ("B", "C", 6, 100, 99.9), ("C", "J", 7, 100, 99.9), ("C", "I", 10, 50, 99.0),
        ("D", "G", 9, 50, 99.5), ("D", "H", 8, 100, 99.9), ("D", "I", 11, 50, 99.2),
        ("E", "H", 15, 100, 99.0), ("E", "J", 4, 100, 99.9), ("F", "K", 14, 20, 98.5),
        ("G", "L", 10, 50, 99.0), ("H", "O", 20, 50, 98.0), ("I", "J", 5, 100, 99.9),
        ("J", "N", 9, 50, 99.5), ("K", "L", 8, 50, 99.0), ("L", "M", 6, 100, 99.9),
        ("M", "N", 7, 100, 99.9), ("N", "O", 4, 100, 99.9)
    ]
    st.session_state.edges = {}
    for u, v, d, c, a in base_edges:
        st.session_state.edges[(u, v)] = {"delay": d, "capacity": c, "availability": a, "status": "Activo"}

if "pos" not in st.session_state:
    st.session_state.pos = {
        "A": (1, 5), "B": (5, 5), "C": (7, 4), "D": (2.5, 3.8), "E": (4.5, 3.8),
        "F": (1, 3), "G": (2.5, 2.5), "H": (3.5, 2), "I": (5.5, 3), "J": (7, 2.8),
        "K": (1, 1), "L": (2.5, 1.2), "M": (4.5, 0.5), "N": (6.5, 1.5), "O": (7, 0.5)
    }

# ==========================================
# 2. PANEL DE CONTROL (SIDEBAR)
# ==========================================
st.sidebar.header("🎛️ Configuración de Red")

# Ponderaciones Multicriterio
st.sidebar.subheader("Pesos Multicriterio ($α, β, γ$ suma = 1.0)")
alpha = st.sidebar.slider("α (Peso Retardo / Delay)", 0.0, 1.0, 0.50, 0.05)
beta = st.sidebar.slider("β (Peso Capacidad / Ancho de Banda)", 0.0, 1.0, 0.35, 0.05)
gamma = st.sidebar.slider("γ (Peso Disponibilidad / Confiabilidad)", 0.0, 1.0, 0.15, 0.05)

# Valores de referencia
d_ref = st.sidebar.number_input("Retardo de Referencia ($d_{ref}$ ms)", value=10.0, min_value=1.0)
b_ref = st.sidebar.number_input("Capacidad de Referencia ($b_{ref}$ Mbps)", value=100.0, min_value=1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Origen y Destino")
origen = st.sidebar.selectbox("Nodo Origen (Source)", st.session_state.nodes, index=7) # H por defecto
destino = st.sidebar.selectbox("Nodo Destino / Sumidero (Sink)", st.session_state.nodes, index=1) # B por defecto

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Restricción Manual de Saltos")
forzar_saltos = st.sidebar.checkbox("🔒 Forzar número de saltos específico")
target_saltos = st.sidebar.slider("Cantidad exacta de saltos", min_value=1, max_value=8, value=3)

# ==========================================
# 3. GESTIÓN AVANZADA DE TOPOLOGÍA
# ==========================================
with st.sidebar.expander("🛠️ Editor de Topología (Routers y Enlaces)"):
    nuevo_router = st.text_input("Añadir nuevo Router (Ej: P)").upper()
    if st.button("Crear Router"):
        if nuevo_router and nuevo_router not in st.session_state.nodes:
            st.session_state.nodes.append(nuevo_router)
            st.session_state.pos[nuevo_router] = (float(len(st.session_state.nodes)), 2.5)
            st.success(f"Router {nuevo_router} añadido.")
            st.rerun()

    st.markdown("---")
    u_link = st.selectbox("Router U", st.session_state.nodes, key="u_l")
    v_link = st.selectbox("Router V", st.session_state.nodes, key="v_l")
    d_input = st.number_input("Retardo (ms)", value=10.0)
    c_input = st.number_input("Capacidad (Mbps)", value=100.0)
    a_input = st.number_input("Disponibilidad (%)", value=99.9)
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if st.button("Añadir / Actualizar Enlace"):
            if u_link != v_link:
                st.session_state.edges[(u_link, v_link)] = {
                    "delay": d_input, "capacity": c_input, "availability": a_input, "status": "Activo"
                }
                st.success(f"Enlace {u_link}-{v_link} configurado.")
                st.rerun()
            else:
                st.error("Un router no puede enlazarse a sí mismo.")
    with col_e2:
        if st.button("Eliminar Enlace"):
            if (u_link, v_link) in st.session_state.edges:
                del st.session_state.edges[(u_link, v_link)]
                st.warning(f"Enlace {u_link}-{v_link} eliminado.")
                st.rerun()
            elif (v_link, u_link) in st.session_state.edges:
                del st.session_state.edges[(v_link, u_link)]
                st.warning(f"Enlace {v_link}-{u_link} eliminado.")
                st.rerun()

# ==========================================
# 4. CONSTRUCCIÓN DEL GRAFO Y CÁLCULO DE COSTOS
# ==========================================
G = nx.Graph()
G.add_nodes_from(st.session_state.nodes)

for (u, v), attrs in st.session_state.edges.items():
    if attrs["status"] == "Activo":
        d = attrs["delay"]
        b = attrs["capacity"]
        b_safe = max(b, 0.1)
        costo_enlace = alpha + beta * (d / d_ref) + gamma * (b_ref / b_safe)
        G.add_edge(u, v, weight=round(costo_enlace, 4), delay=d, capacity=b, availability=attrs["availability"])

# ==========================================
# 5. ALGORITMO SINK TREE Y FILTRO DE SALTOS
# ==========================================
def calcular_sink_tree(grafo, destino_nodo):
    distances = {node: float('inf') for node in grafo.nodes}
    previous_nodes = {node: None for node in grafo.nodes}
    distances[destino_nodo] = 0
    pq = [(0, destino_nodo)]
    
    while pq:
        current_distance, current_node = heapq.heappop(pq)
        if current_distance > distances[current_node]:
            continue
        for neighbor in grafo.neighbors(current_node):
            weight = grafo[current_node][neighbor]['weight']
            distance = current_distance + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))
    return distances, previous_nodes

distances, previous_nodes = calcular_sink_tree(G, destino)

# Lógica de selección de ruta (Normal por Dijkstra o Forzada por Saltos)
camino_actual = []

if forzar_saltos:
    mejor_ruta_forzada = None
    menor_costo_forzado = float('inf')
    
    # Buscar todos los caminos simples entre origen y destino que cumplan con la cantidad de saltos exacta
    try:
        caminos_posibles = nx.all_simple_paths(G, source=origen, target=destino, cutoff=target_saltos + 2)
        for path in caminos_posibles:
            if len(path) - 1 == target_saltos:
                costo_camino = sum([G[path[i]][path[i+1]]['weight'] for i in range(len(path)-1)])
                if costo_camino < menor_costo_forzado:
                    menor_costo_forzado = costo_camino
                    mejor_ruta_forzada = path
    except Exception:
        pass
        
    if mejor_ruta_forzada:
        camino_actual = mejor_ruta_forzada
        camino_valido = True
    else:
        camino_valido = False
        st.sidebar.warning(f"⚠️ No hay rutas activas con exactamente {target_saltos} saltos entre {origen} y {destino}.")
else:
    current = origen
    while current is not None:
        camino_actual.append(current)
        current = previous_nodes[current]
    camino_valido = len(camino_actual) > 1 or origen == destino

# ==========================================
# 6. VISUALIZACIÓN GRÁFICA PROFESIONAL
# ==========================================
fig, ax = plt.subplots(figsize=(11, 7), facecolor="#0e1117")
ax.set_facecolor("#0e1117")

nx.draw_networkx_edges(G, st.session_state.pos, edge_color="#30363d", width=1.5, style="dashed", ax=ax)

# Resaltar el Sink Tree general si no se fuerza ruta específica
if not forzar_saltos:
    sink_edges = [(node, prev) for node, prev in previous_nodes.items() if prev is not None]
    nx.draw_networkx_edges(G, st.session_state.pos, edgelist=sink_edges, edge_color="#2ecc71", width=2.0, ax=ax, label="Sink Tree Óptimo")

# Resaltar ruta seleccionada
if camino_valido and len(camino_actual) > 1:
    path_edges = [(camino_actual[i], camino_actual[i+1]) for i in range(len(camino_actual)-1)]
    color_trazo = "#e74c3c" if forzar_saltos else "#3498db"
    label_trazo = f"Ruta Forzada ({target_saltos} saltos)" if forzar_saltos else f"Ruta Óptima ({origen} → {destino})"
    nx.draw_networkx_edges(G, st.session_state.pos, edgelist=path_edges, edge_color=color_trazo, width=4.5, ax=ax, label=label_trazo)

node_colors = []
for n in G.nodes():
    if n == origen:
        node_colors.append("#3498db")
    elif n == destino:
        node_colors.append("#e67e22")
    else:
        node_colors.append("#6c5ce7")

nx.draw_networkx_nodes(G, st.session_state.pos, node_size=700, node_color=node_colors, alpha=0.9, ax=ax)
nx.draw_networkx_labels(G, st.session_state.pos, font_color="white", font_weight="bold", font_size=11, ax=ax)

edge_labels = {(u, v): f"w:{d['weight']}" for u, v, d in G.edges(data=True)}
nx.draw_networkx_edge_labels(G, st.session_state.pos, edge_labels=edge_labels, font_color="#8b949e", font_size=8, ax=ax)

ax.legend(loc="upper right", frameon=True, facecolor="#1a1c23", labelcolor="white")
ax.axis("off")

st.pyplot(fig)

# ==========================================
# 7. PANEL DE MÉTRICAS Y ANÁLISIS
# ==========================================
st.markdown("---")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric(label="📍 Ruta Activa", value=" → ".join(camino_actual) if camino_valido and len(camino_actual)>0 else "Sin conexión")
with col_m2:
    costo_total_actual = sum([G[camino_actual[i]][camino_actual[i+1]]['weight'] for i in range(len(camino_actual)-1)]) if camino_valido and len(camino_actual)>1 else 0
    st.metric(label="📊 Costo Multicriterio", value=f"{costo_total_actual:.2f}")
with col_m3:
    retardo_total = sum([G[camino_actual[i]][camino_actual[i+1]]['delay'] for i in range(len(camino_actual)-1)]) if camino_valido and len(camino_actual)>1 else 0
    st.metric(label="⏱️ Retardo Acumulado", value=f"{retardo_total} ms")
with col_m4:
    saltos_total = len(camino_actual) - 1 if camino_valido and len(camino_actual)>1 else 0
    st.metric(label="🔄 Número de Saltos", value=f"{saltos_total}")

# Tabla detallada de la red
with st.expander("📋 Ver Tabla Completa de Enlaces y Métricas de Red"):
    data_tabla = []
    for (u, v), attrs in st.session_state.edges.items():
        w = G[u][v]['weight'] if G.has_edge(u, v) else "N/A (Caído)"
        data_tabla.append({
            "Origen": u, "Destino": v, "Retardo (ms)": attrs["delay"],
            "Capacidad (Mbps)": attrs["capacity"], "Disponibilidad (%)": attrs["availability"],
            "Costo Multicriterio": w, "Estado": attrs["status"]
        })
    st.dataframe(pd.DataFrame(data_tabla), use_container_width=True)