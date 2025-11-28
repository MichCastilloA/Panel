# app.py
#cd C:\Users\mcastillo\pythonProject
# C:\Users\mcastillo\python\.venv\Scripts\activate
# streamlit run app.py
#streamlit run .\app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import os

st.set_page_config(layout="wide", page_title="Dashboard Campañas", initial_sidebar_state="expanded")

# --- CONFIG: repo/branch where Base.csv is stored ---
GITHUB_OWNER = "MichCastilloA"
GITHUB_REPO = "Panel"
GITHUB_BRANCH = "panel"  # ajusta si tu branch se llama distinto
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/Base.csv"

# --- Helpers para cargar la base ---
def read_csv_from_url(url, headers=None, encoding='utf-8-sig'):
    if not url:
        return pd.DataFrame()
    try:
        resp = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '')
        if 'text' in content_type or 'csv' in content_type:
            return pd.read_csv(io.StringIO(resp.text), encoding=encoding, on_bad_lines='skip', low_memory=False)
        else:
            return pd.read_csv(io.BytesIO(resp.content), encoding=encoding, on_bad_lines='skip', low_memory=False)
    except Exception as e:
        st.warning(f"Error descargando desde URL: {url[:120]}... Error: {e}")
        return pd.DataFrame()

def load_base_fallback(uploaded_file=None, local_path='Base.csv', github_raw_url=GITHUB_RAW_URL, encoding='utf-8-sig'):
    """
    Orden de prioridad:
      1) archivo subido por el usuario (uploader)
      2) archivo incluido en el repo en la raíz (local_path)
      3) raw URL de GitHub (github_raw_url). Si el repo es privado, setea GITHUB_TOKEN en st.secrets
    """
    # 1) upload
    if uploaded_file is not None:
        try:
            return pd.read_csv(uploaded_file, encoding=encoding, on_bad_lines='skip', low_memory=False)
        except Exception as e:
            st.error(f"Error leyendo archivo subido: {e}")
            return pd.DataFrame()

    # 2) archivo local (en la raíz del repo desplegado)
    if os.path.exists(local_path):
        try:
            return pd.read_csv(local_path, encoding=encoding, on_bad_lines='skip', low_memory=False)
        except Exception as e:
            st.warning(f"Error leyendo {local_path}: {e}")

    # 3) GitHub raw URL
    if github_raw_url:
        headers = None
        # Si el repo es privado y añadiste un token como secret GITHUB_TOKEN, úsalo
        if "GITHUB_TOKEN" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            headers = {"Authorization": f"token {token}"}
        df = read_csv_from_url(github_raw_url, headers=headers, encoding=encoding)
        if not df.empty:
            return df

    return pd.DataFrame()

# --- Normalizar y preparar base ---
def safe_prepare(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.copy()
    # Normalizar nombres de columnas comunes en tu flujo
    # Asegurar columnas necesarias
    for col in ['Cliente_Consec', 'Campana', 'Territorio', 'Zona', 'Sucursal', 'inicial', 'Etiqueta', 'ACUM', 'Colocacion', 'Fecha', 'Semana', 'Campo', 'dictamen']:
        if col not in df.columns:
            if col in ['ACUM', 'Colocacion']:
                df[col] = 0
            else:
                df[col] = ''
    # Tipo y limpieza mínima
    df['Cliente_Consec'] = df['Cliente_Consec'].astype(str)
    df['Etiqueta'] = df['Etiqueta'].fillna('Pendiente').astype(str)
    # Asegurar campos numéricos
    df['ACUM'] = pd.to_numeric(df['ACUM'], errors='coerce').fillna(0).astype(int)
    # Colocacion puede tener 1/0 o True/False
    df['Colocacion'] = pd.to_numeric(df['Colocacion'], errors='coerce').fillna(0).astype(int)
    # Fecha como datetime cuando exista
    try:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
    except:
        pass
    return df

# --- Nuevo cálculo: Potencial, Gestiones, Desembolsos según tu definición ---
def compute_summary_correct(df, group_by):
    """
    Potencial = número de registros con el mismo valor del grupo (count rows)
    Gestiones = conteo de registros donde Etiqueta != 'Pendiente'
    Desembolsos = conteo de registros donde Etiqueta == 'Desembolsado'
    Devuelve DataFrame con columnas: [group_by, Potencial, Gestiones, Desembolsos, Conv_Gestiones_%, Conv_Desemb_%]
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[group_by, 'Potencial', 'Gestiones', 'Desembolsos', 'Conv_Gestiones_%', 'Conv_Desemb_%'])
    g = group_by
    # Asegurar que la columna exista
    if g not in df.columns:
        st.warning(f"No existe la columna '{g}' en la base. Usando 'Campana' como fallback.")
        g = 'Campana' if 'Campana' in df.columns else df.columns[0]
    grouped = df.groupby(g).agg(
        Potencial = ('Campana', 'count'),  # count of rows in the group
        Gestiones = ('Etiqueta', lambda s: s.ne('Pendiente').sum()),
        Desembolsos = ('Etiqueta', lambda s: (s == 'Desembolsado').sum())
    ).reset_index()
    # Conversiones relativas al Potencial
    grouped['Conv_Gestiones_%'] = (grouped['Gestiones'] / grouped['Potencial']).replace([np.inf, -np.inf], 0).fillna(0)
    grouped['Conv_Desemb_%'] = (grouped['Desembolsos'] / grouped['Potencial']).replace([np.inf, -np.inf], 0).fillna(0)
    grouped = grouped.sort_values('Potencial', ascending=False).reset_index(drop=True)
    return grouped

# --- UI: Sidebar / carga ---
st.sidebar.title("Filtros / Carga")

uploaded = st.sidebar.file_uploader("Subir Base.csv (opcional)", type=['csv'])
# Intentamos cargar desde GitHub raw (tu repo). Si es privado, añade GITHUB_TOKEN en Secrets.
df_base = load_base_fallback(uploaded_file=uploaded, local_path='./Base.csv', github_raw_url=GITHUB_RAW_URL)

if df_base.empty:
    st.sidebar.warning("No se encontró Base.csv (u opción de carga). Puedes subirlo temporalmente con el uploader o configurar GITHUB_TOKEN en Secrets si el repo es privado.")
else:
    st.sidebar.success(f"Base cargada: {len(df_base):,} filas")

# --- Preparar y limpiar ---
df_base = safe_prepare(df_base)

# --- Construir opciones de filtros (sin Vigencia) ---
campanas = sorted(df_base['Campana'].dropna().unique().tolist())
territorios = sorted(df_base['Territorio'].dropna().unique().tolist())
zonas = sorted(df_base['Zona'].dropna().unique().tolist())
sucursales = sorted(df_base['Sucursal'].dropna().unique().tolist())
ejecutivos = sorted(df_base['inicial'].dropna().unique().tolist())

sel_campanas = st.sidebar.multiselect("Campaña", options=campanas, default=campanas if len(campanas)<=50 else campanas[:50])
sel_territorios = st.sidebar.multiselect("Territorio", options=territorios, default=territorios)
sel_zonas = st.sidebar.multiselect("Zona", options=zonas, default=zonas)
sel_suc = st.sidebar.multiselect("Sucursal", options=sucursales, default=sucursales)
sel_ejecutivos = st.sidebar.multiselect("Ejecutivo (Inicial)", options=ejecutivos, default=ejecutivos)

# Aplicar filtros
if df_base.empty:
    df_filtered = pd.DataFrame(columns=df_base.columns)
else:
    mask = (
        df_base['Campana'].isin(sel_campanas if sel_campanas else df_base['Campana'].unique()) &
        df_base['Territorio'].isin(sel_territorios if sel_territorios else df_base['Territorio'].unique()) &
        df_base['Zona'].isin(sel_zonas if sel_zonas else df_base['Zona'].unique()) &
        df_base['Sucursal'].isin(sel_suc if sel_suc else df_base['Sucursal'].unique()) &
        df_base['inicial'].isin(sel_ejecutivos if sel_ejecutivos else df_base['inicial'].unique())
    )
    df_filtered = df_base[mask].copy()

# --- Main UI ---
st.title("Dashboard Seguimiento Campañas")
st.markdown("Resumen y visualizaciones por Campaña / Territorio / Zona. Usa los filtros en la izquierda.")

tab = st.tabs(["General", "Tipo de gestión", "Lugar de gestión", "Por semanas", "Históricas"])

# General
with tab[0]:
    st.header("General")
    col1, col2 = st.columns([3,1])
    with col2:
        agr = st.selectbox("Agrupar por", options=['Campana', 'Territorio', 'Zona'], index=0)
        top_n = st.number_input("Mostrar top N", min_value=3, max_value=200, value=20)

    resumen = compute_summary_correct(df_filtered, agr)
    # Formateo de porcentajes para visual
    resumen_display = resumen.copy()
    resumen_display['Conv_Gestiones_%'] = resumen_display['Conv_Gestiones_%'].apply(lambda x: f"{x:.2%}")
    resumen_display['Conv_Desemb_%'] = resumen_display['Conv_Desemb_%'].apply(lambda x: f"{x:.2%}")

    if resumen.empty:
        st.info("No hay datos para mostrar con los filtros seleccionados.")
    else:
        st.dataframe(resumen_display.head(top_n), width='stretch')

        # Gráfica: Gestiones por grupo
        fig_g = px.bar(resumen, x=agr, y='Gestiones', text='Gestiones', title=f'Gestiones por {agr}')
        fig_g.update_traces(textposition='outside')
        fig_g.update_layout(yaxis_title='Gestiones', xaxis_title=agr, margin=dict(t=50))
        st.plotly_chart(fig_g, width='stretch')

        # Combinada: Desembolsos y conversión
        fig = go.Figure()
        fig.add_trace(go.Bar(x=resumen[agr], y=resumen['Desembolsos'], name='Desembolsos', marker_color='steelblue', text=resumen['Desembolsos'], textposition='auto'))
        fig.add_trace(go.Scatter(x=resumen[agr], y=resumen['Conv_Desemb_%']*100, name='Conv Desemb %', mode='lines+markers+text',
                                 text=[f"{v:.1f}%" for v in resumen['Conv_Desemb_%']*100],
                                 textposition='top center', marker=dict(color='orange'), yaxis='y2'))
        fig.update_layout(
            title=f'Desembolsos y Conversión % por {agr}',
            yaxis=dict(title='Desembolsos'),
            yaxis2=dict(title='Conv Desemb (%)', overlaying='y', side='right', tickformat=".1f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=60)
        )
        st.plotly_chart(fig, width='stretch')

# Tipo de gestión
with tab[1]:
    st.header("Tipo de gestión")
    df_tab = df_filtered.copy()
    if 'dictamen' not in df_tab.columns or df_tab['dictamen'].nunique() == 0:
        st.info("No hay datos de 'dictamen' en la base filtrada.")
    else:
        tg = df_tab.groupby(['Campana', 'dictamen']).size().unstack(fill_value=0)
        st.dataframe(tg, width='stretch')

# Lugar de gestión
with tab[2]:
    st.header("Lugar de gestión")
    df_tab = df_filtered.copy()
    lugar_col = 'Campo' if 'Campo' in df_tab.columns else None
    if lugar_col is None:
        st.info("La base no contiene columna 'Campo' para lugar de gestión.")
    else:
        lg = df_tab.groupby([lugar_col, 'Campana']).size().unstack(fill_value=0)
        st.dataframe(lg, width='stretch')

# Por semanas
with tab[3]:
    st.header("Por semanas")
    df_tab = df_filtered.copy()
    if 'Semana' not in df_tab.columns or df_tab['Semana'].nunique() == 0:
        st.info("No hay datos de 'Semana' en la base filtrada.")
    else:
        series = df_tab.groupby('Semana').agg({'Cliente_Consec': 'count', 'ACUM': 'sum', 'Colocacion': 'sum'}).rename(columns={'Cliente_Consec': 'Potencial'}).reset_index()
        # orden sencillo por texto/semana
        try:
            series['order_week'] = series['Semana'].apply(lambda x: int(str(x).split('Sem')[-1]) if 'Sem' in str(x) else 0)
            series = series.sort_values('order_week')
        except:
            pass
        fig_s = go.Figure()
        fig_s.add_trace(go.Bar(x=series['Semana'], y=series['ACUM'], name='Gestiones'))
        fig_s.add_trace(go.Bar(x=series['Semana'], y=series['Colocacion'], name='Desembolsos'))
        fig_s.update_layout(barmode='group', title="Series semanales (Gestiones / Desembolsos)", xaxis_title='Semana')
        st.plotly_chart(fig_s, width='stretch')
        st.dataframe(series, width='stretch')

# Históricas
with tab[4]:
    st.header("Históricas")
    df_tab = df_filtered.copy()
    fecha_lim = st.date_input("Mostrar registros con Fecha <=", value=None)
    if fecha_lim is not None:
        try:
            hist = df_tab.copy()
            hist['Fecha_dt'] = pd.to_datetime(hist['Fecha'], dayfirst=True, errors='coerce')
            hist_sel = hist[hist['Fecha_dt'].notna() & (hist['Fecha_dt'] <= pd.to_datetime(fecha_lim))]
            st.write(f"Registros hasta {fecha_lim}: {len(hist_sel)}")
            st.dataframe(hist_sel.head(200), width='stretch')
            csv_bytes = hist_sel.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Descargar históricos filtrados (CSV)", csv_bytes, file_name="historicos_filtrados.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Error procesando históricas: {e}")
    else:
        st.info("Selecciona una fecha para filtrar históricos")

# Exportar desde sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("Exportar / Descargar")
if not df_filtered.empty:
    csv_bytes = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button("Descargar Base filtrada (CSV)", data=csv_bytes, file_name="Base_filtrada.csv", mime="text/csv")
else:
    st.sidebar.info("No hay datos para descargar con los filtros actuales.")

