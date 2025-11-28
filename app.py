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

st.set_page_config(layout="wide", page_title="Dashboard Campañas", initial_sidebar_state="expanded")

# Rutas por defecto
RUTA_BASE_DEF = r"C:\Users\mcastillo\Documents\pedidos\04 Seguimiento campañas\Insumos\Base.csv"
RUTA_CLIENTES_DEF = r"C:\Users\mcastillo\Documents\pedidos\04 Seguimiento campañas\Insumos\Clientes.csv"

@st.cache_data(ttl=300)
def load_csv(path, encoding='utf-8-sig'):
    try:
        df = pd.read_csv(path, encoding=encoding, on_bad_lines='skip', low_memory=False)
        return df
    except Exception:
        return pd.DataFrame()

def safe_prepare(df):
    if df is None:
        return pd.DataFrame()
    df = df.copy()
    for col in ['Cliente_Consec', 'ACUM', 'Colocacion', 'Monto', 'inicial', 'Sucursal', 'Territorio', 'Zona', 'Campana', 'Fecha', 'Vigencia', 'Semana', 'dictamen', 'Campo']:
        if col not in df.columns:
            if col in ['ACUM', 'Colocacion', 'Monto', 'Vigencia']:
                df[col] = 0
            else:
                df[col] = ''
    df['ACUM'] = pd.to_numeric(df['ACUM'], errors='coerce').fillna(0).astype(int)
    df['Colocacion'] = pd.to_numeric(df['Colocacion'], errors='coerce').fillna(0).astype(int)
    try:
        df['Vigencia'] = pd.to_numeric(df['Vigencia'], errors='coerce').fillna(0).astype(int)
        df['Vigencia'] = df['Vigencia'].apply(lambda x: 1 if x == 1 else 0)
    except:
        df['Vigencia'] = 0
    df['Cliente_Consec'] = df['Cliente_Consec'].astype(str)
    try:
        df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=True, errors='coerce')
    except:
        pass
    return df

def compute_summary(df, group_by):
    g = group_by
    df2 = df.copy()
    potencial = df2.groupby(g)['Cliente_Consec'].nunique().rename('Potencial')
    gestiones = df2.groupby(g)['ACUM'].sum().rename('Gestiones')
    desembolsos = df2.groupby(g)['Colocacion'].sum().rename('Desembolsos')
    resumen = pd.concat([potencial, gestiones, desembolsos], axis=1).reset_index()
    resumen['Conv_Gestiones_%'] = (resumen['Gestiones'] / resumen['Potencial']).replace([np.inf, -np.inf], np.nan).fillna(0)
    resumen['Conv_Desemb_%'] = (resumen['Desembolsos'] / resumen['Potencial']).replace([np.inf, -np.inf], np.nan).fillna(0)
    resumen = resumen.sort_values(by='Potencial', ascending=False)
    return resumen

def format_percent(x):
    return f"{x:.2%}"

def to_csv_bytes(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# --- CARGA ---
st.sidebar.title("Filtros")

uploaded = st.sidebar.file_uploader("Subir Base.csv (opcional)", type=['csv'])
if uploaded is not None:
    df_base = pd.read_csv(uploaded, encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
else:
    df_base = load_csv(RUTA_BASE_DEF)
    if df_base.empty:
        st.sidebar.warning("No se encontró Base.csv en la ruta por defecto. Subir archivo o ajustar ruta.")

uploaded_clients = st.sidebar.file_uploader("Subir Clientes.csv (opcional)", type=['csv'], key="clients")
if uploaded_clients is not None:
    df_clients = pd.read_csv(uploaded_clients, encoding='utf-8-sig', on_bad_lines='skip', low_memory=False)
else:
    df_clients = load_csv(RUTA_CLIENTES_DEF)

df_base = safe_prepare(df_base)

# --- NUEVO: selector Vigencia explicitamente antes de recalcular listas ---
# Construimos las opciones de Vigencia desde la data (por si hay sólo 0 o 1)
vig_options = sorted(df_base['Vigencia'].dropna().unique().tolist())
if not vig_options:
    vig_options = [1, 0]  # fallback
# Mostrar como multiselect para que puedas ver ambas si lo deseas
sel_vigencia = st.sidebar.multiselect("Vigencia (0 = vencida, 1 = vigente)", options=vig_options, default=vig_options)

# Aplicamos el filtro de Vigencia inmediatamente para recalcular las listas de filtros
if sel_vigencia:
    df_vig = df_base[df_base['Vigencia'].isin(sel_vigencia)].copy()
else:
    df_vig = df_base.copy()

# --- RECOMPUTAR LISTAS A PARTIR DE df_vig (aquí te pediste enfoque) ---
campanas = sorted(df_vig['Campana'].dropna().unique().tolist())
territorios = sorted(df_vig['Territorio'].dropna().unique().tolist())
zonas = sorted(df_vig['Zona'].dropna().unique().tolist())
sucursales = sorted(df_vig['Sucursal'].dropna().unique().tolist())
ejecutivos = sorted(df_vig['inicial'].dropna().unique().tolist())

# Mostrar listas en sidebar (aquí el control que dijiste)
sel_campanas = st.sidebar.multiselect("Campaña", options=campanas, default=campanas[:20] if campanas else [])
sel_territorios = st.sidebar.multiselect("Territorio", options=territorios, default=territorios)
sel_zonas = st.sidebar.multiselect("Zona", options=zonas, default=zonas)
sel_suc = st.sidebar.multiselect("Sucursal", options=sucursales, default=sucursales)
sel_ejecutivos = st.sidebar.multiselect("Ejecutivo (Inicial)", options=ejecutivos, default=ejecutivos)

# --- APLICAR MÁSCARA SEGÚN TUS LÍNEAS SOLICITADAS ---
mask_sidebar = (
    df_vig['Campana'].isin(sel_campanas if sel_campanas else df_vig['Campana'].unique()) &
    df_vig['Territorio'].isin(sel_territorios if sel_territorios else df_vig['Territorio'].unique()) &
    df_vig['Zona'].isin(sel_zonas if sel_zonas else df_vig['Zona'].unique()) &
    df_vig['Sucursal'].isin(sel_suc if sel_suc else df_vig['Sucursal'].unique()) &
    df_vig['inicial'].isin(sel_ejecutivos if sel_ejecutivos else df_vig['inicial'].unique()) &
    df_vig['Vigencia'].isin(sel_vigencia if sel_vigencia else df_vig['Vigencia'].unique())
)
df_filtered_global = df_vig[mask_sidebar].copy()

# Indicador visible de la Vigencia seleccionada
st.markdown("")  # espacio
st.info(f"Vigencia seleccionada: {sel_vigencia} — registros resultantes: {len(df_filtered_global)}")

# ===== Tabs y visualizaciones =====
st.title("Dashboard Seguimiento Campañas")
st.markdown("Resumen y visualizaciones por Campaña / Territorio / Zona. Usa los filtros en la izquierda.")

tab = st.tabs(["General", "Tipo de gestión", "Lugar de gestión", "Por semanas", "Históricas"])

with tab[0]:
    st.header("General")
    col1, col2 = st.columns([3,1])
    with col2:
        agr = st.selectbox("Agrupar por", options=['Campana', 'Territorio', 'Zona'], index=0)
        top_n = st.number_input("Mostrar top N", min_value=3, max_value=100, value=20)
    df_filtrado = df_filtered_global.copy()
    resumen = compute_summary(df_filtrado, agr)
    resumen_display = resumen.copy()
    resumen_display['Conv_Gestiones_%'] = resumen_display['Conv_Gestiones_%'].apply(format_percent)
    resumen_display['Conv_Desemb_%'] = resumen_display['Conv_Desemb_%'].apply(format_percent)
    st.dataframe(resumen_display.head(top_n), width='stretch')

    if not resumen.empty:
        fig_g = px.bar(resumen.reset_index(), x=agr, y='Gestiones', text='Gestiones', title='Gestiones por ' + agr)
        fig_g.update_traces(textposition='outside')
        fig_g.update_layout(yaxis_title='Gestiones', xaxis_title=agr, margin=dict(t=50))
        st.plotly_chart(fig_g, width='stretch')

        fig = go.Figure()
        fig.add_trace(go.Bar(x=resumen[agr], y=resumen['Desembolsos'], name='Desembolsos', marker_color='steelblue', text=resumen['Desembolsos'], textposition='auto'))
        fig.add_trace(go.Scatter(x=resumen[agr], y=resumen['Conv_Desemb_%']*100, name='Conv Desemb %', mode='lines+markers+text',
                                 text=[f"{v:.1f}%" for v in resumen['Conv_Desemb_%']*100],
                                 textposition='top center', marker=dict(color='orange'), yaxis='y2'))
        fig.update_layout(title='Desembolsos y Conversión % por ' + agr,
                          yaxis=dict(title='Desembolsos'),
                          yaxis2=dict(title='Conv Desemb (%)', overlaying='y', side='right', tickformat=".1f"),
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                          margin=dict(t=60))
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No hay datos para mostrar con los filtros seleccionados.")

with tab[1]:
    st.header("Tipo de gestión")
    df_tab = df_filtered_global.copy()
    if 'dictamen' not in df_tab.columns or df_tab['dictamen'].nunique() == 0:
        st.info("No hay datos de 'dictamen' en la base filtrada.")
    else:
        tg = df_tab.copy()
        grp = tg.groupby(['Campana', 'dictamen']).size().unstack(fill_value=0)
        st.dataframe(grp, width='stretch')

with tab[2]:
    st.header("Lugar de gestión")
    df_tab = df_filtered_global.copy()
    lugar_col = 'Campo' if 'Campo' in df_tab.columns else None
    if lugar_col is None:
        st.info("La base no contiene columna 'Campo' para lugar de gestión.")
    else:
        lg = df_tab.groupby([lugar_col, 'Campana']).size().unstack(fill_value=0)
        st.dataframe(lg, width='stretch')

with tab[3]:
    st.header("Por semanas")
    df_tab = df_filtered_global.copy()
    if 'Semana' not in df_tab.columns or df_tab['Semana'].nunique() == 0:
        st.info("No hay datos de 'Semana' en la base filtrada.")
    else:
        series = df_tab.groupby('Semana').agg({'Cliente_Consec': 'nunique', 'ACUM': 'sum', 'Colocacion': 'sum'}).rename(columns={'Cliente_Consec': 'Potencial'}).reset_index()
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

with tab[4]:
    st.header("Históricas")
    df_tab = df_filtered_global.copy()
    fecha_lim = st.date_input("Mostrar registros con Fecha <=", value=None)
    if fecha_lim is not None:
        try:
            hist = df_tab.copy()
            hist['Fecha_dt'] = pd.to_datetime(hist['Fecha'], dayfirst=True, errors='coerce')
            hist_sel = hist[hist['Fecha_dt'].notna() & (hist['Fecha_dt'] <= pd.to_datetime(fecha_lim))]
            st.write(f"Registros hasta {fecha_lim}: {len(hist_sel)}")
            st.dataframe(hist_sel.head(100), width='stretch')
            csv_bytes = to_csv_bytes(hist_sel)
            st.download_button("Descargar históricos filtrados (CSV)", csv_bytes, file_name="historicos_filtrados.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Error procesando históricas: {e}")
    else:
        st.info("Selecciona una fecha para filtrar históricos")

# Exportar desde sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("Exportar / Descargar")
if not df_filtered_global.empty:
    st.sidebar.download_button("Descargar Base filtrada (CSV)", data=to_csv_bytes(df_filtered_global), file_name="Base_filtrada.csv", mime="text/csv")
else:
    st.sidebar.info("No hay datos para descargar con los filtros actuales.")