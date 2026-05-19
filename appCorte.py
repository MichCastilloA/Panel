import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import base64
import re

@st.cache_data(ttl=3600) 
def load_data():
    df = pd.read_csv("https://raw.githubusercontent.com/MichCastilloA/Panel/main/consolidado.csv")
    df["FileDate"] = pd.to_datetime(df["FileDate"])
    df["Fecha"] = df["FileDate"].dt.date
    return df
    
if st.button("Actualizar datos"):
    st.cache_data.clear()
    st.rerun()

df = load_data()
col_sucursal = "SUCURSAL"
col_monto = "MONTO"
col_tipo = "TIPO_2"

max_fecha = df["FileDate"].max()
max_id = df.loc[df["FileDate"] == max_fecha, "ID"].max()

META_PROMEDIO_NUEVOS_MONTO = 0
META_PROMEDIO_RECOMPRA_MONTO = 0
META_PROMEDIO_TOTAL_MONTO = 0
META_PROMEDIO_NUEVOS_CASOS = 0
META_PROMEDIO_RECOMPRA_CASOS = 0
META_PROMEDIO_TOTAL_CASOS = 0

if not df.empty:
    df_nuevos = df[df[col_tipo].str.contains("nuevo", case=False, na=False)]
    df_recompra = df[df[col_tipo].str.contains("recompra", case=False, na=False)]
    META_PROMEDIO_NUEVOS_MONTO = df_nuevos["MetaMonto_por_registro"].sum() / 6 if len(df_nuevos) > 0 else 0
    META_PROMEDIO_RECOMPRA_MONTO = df_recompra["MetaMonto_por_registro"].sum() / 6 if len(df_recompra) > 0 else 0
    META_PROMEDIO_TOTAL_MONTO = META_PROMEDIO_NUEVOS_MONTO + META_PROMEDIO_RECOMPRA_MONTO
    META_PROMEDIO_NUEVOS_CASOS = df_nuevos["MetaCasos_por_registro"].sum() / 6 if len(df_nuevos) > 0 else 0
    META_PROMEDIO_RECOMPRA_CASOS = df_recompra["MetaCasos_por_registro"].sum() / 6 if len(df_recompra) > 0 else 0
    META_PROMEDIO_TOTAL_CASOS = META_PROMEDIO_NUEVOS_CASOS + META_PROMEDIO_RECOMPRA_CASOS

def formato_dinero(x): return f"${x:,.0f}"

def filtro_de_base(df_input, territorio_sel, zona_sel, sucursal_sel, fecha_sel, hora_sel):
    mask = pd.Series(True, index=df_input.index)
    if territorio_sel != "Todas":
        mask = mask & (df_input["TERRITORIO"] == territorio_sel)
    if zona_sel != "Todas":
        mask = mask & (df_input["ZONA"] == zona_sel)
    if sucursal_sel != "Todas":
        mask = mask & (df_input["SUCURSAL"] == sucursal_sel)
    if fecha_sel:
        mask = mask & (df_input["Fecha"] == fecha_sel)
    if hora_sel != "Todas":
        mask = mask & (df_input["ID"].astype(str) == hora_sel)
    return df_input.loc[mask].copy()

def calcular_metrica(df_input, tipo_key=None):
    if df_input.empty:
        return 0, 0, 0, 0
    if tipo_key:
        df_filtered = df_input[df_input[col_tipo].str.contains(tipo_key, case=False, na=False)]
    else:
        df_filtered = df_input.copy()
    if df_filtered.empty:
        return 0, 0, 0, 0
    if hora_sel == "Todas":
        df_max_id = df_filtered[df_filtered["ID"] == df_filtered["ID"].max()]
    else:
        df_max_id = df_filtered[df_filtered["ID"] == int(hora_sel)]
    monto = df_max_id[col_monto].sum()
    casos = len(df_max_id)
    meta = df_max_id["MetaMonto_por_registro"].sum()
    logro = (monto / meta * 100) if meta > 0 else 0
    return monto, casos, meta, logro

def crear_grafica_sem(df_input, tipo_filter=None, title="MONTO POR DÍA Y SEMANA"):
    if df_input.empty:
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_white")
        return fig
    max_fecha = df_input["FileDate"].max()
    inicio_sem = max_fecha - pd.Timedelta(days=max_fecha.weekday())
    dias_sem = [inicio_sem + pd.Timedelta(days=i) for i in range(6)]
    dias_prev = [d - pd.Timedelta(days=7) for d in dias_sem]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    labels = [f"{i + 1}.-{dias_es[i]}" for i in range(6)]
    def sum_monto_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[col_tipo].str.contains(tipo_key, case=False, na=False)
            df_day = df_source[day_mask]
            if df_day.empty:
                res.append(0)
            else:
                if hora_sel == "Todas":
                    max_id = df_day["ID"].max()
                else:
                    max_id = int(hora_sel)
                df_max_id = df_day[df_day["ID"] == max_id]
                total = df_max_id[col_monto].sum()
                res.append(total)
        return res
    monto_curr = sum_monto_max_id(dias_sem, df_input, tipo_filter)
    monto_prev = sum_monto_max_id(dias_prev, df_input, tipo_filter)
    def sum_meta_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[col_tipo].str.contains(tipo_key, case=False, na=False)
            df_day = df_source[day_mask]
            if df_day.empty:
                res.append(0)
            else:
                if hora_sel == "Todas":
                    max_id = df_day["ID"].max()
                else:
                    max_id = int(hora_sel)
                df_max_id = df_day[df_day["ID"] == max_id]
                total = df_max_id["MetaMonto_por_registro"].sum()
                res.append(total)
        return res
    meta_curr = sum_meta_max_id(dias_sem, df_input, tipo_filter)
    if tipo_filter == "nuevo":
        promedio = META_PROMEDIO_NUEVOS_MONTO
    elif tipo_filter == "recompra":
        promedio = META_PROMEDIO_RECOMPRA_MONTO
    else:
        promedio = META_PROMEDIO_TOTAL_MONTO
    meta_curr = [promedio if m == 0 else m for m in meta_curr]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=monto_prev, name=f"Semana {dias_sem[0].isocalendar()[1] - 1}", marker_color="#AED6F1"))
    fig.add_trace(go.Bar(x=labels, y=monto_curr, name=f"Semana {dias_sem[0].isocalendar()[1]}", marker_color="#2980B9"))
    fig.add_trace(go.Scatter(x=labels, y=meta_curr, name="META", mode="lines+markers", line=dict(color="#27AE60", width=3, shape="spline"), marker=dict(color="#27AE60", size=6)))
    fig.update_layout(title=title, barmode="group", yaxis=dict(title="Monto", tickformat="$,.0f"), template="plotly_white", height=400, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01), margin=dict(l=20, r=20, t=50, b=20))
    return fig

def crear_grafica_sem_cases(df_input, tipo_filter=None, title="CASOS POR DÍA Y SEMANA"):
    if df_input.empty:
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_white")
        return fig
    max_fecha = df_input["FileDate"].max()
    inicio_sem = max_fecha - pd.Timedelta(days=max_fecha.weekday())
    dias_sem = [inicio_sem + pd.Timedelta(days=i) for i in range(6)]
    dias_prev = [d - pd.Timedelta(days=7) for d in dias_sem]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    labels = [f"{i + 1}.-{dias_es[i]}" for i in range(6)]
    def sum_casos_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[col_tipo].str.contains(tipo_key, case=False, na=False)
            df_day = df_source[day_mask]
            if df_day.empty:
                res.append(0)
            else:
                if hora_sel == "Todas":
                    max_id = df_day["ID"].max()
                else:
                    max_id = int(hora_sel)
                df_max_id = df_day[df_day["ID"] == max_id]
                total = len(df_max_id)
                res.append(total)
        return res
    casos_curr = sum_casos_max_id(dias_sem, df_input, tipo_filter)
    casos_prev = sum_casos_max_id(dias_prev, df_input, tipo_filter)
    def sum_meta_casos_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[col_tipo].str.contains(tipo_key, case=False, na=False)
            df_day = df_source[day_mask]
            if df_day.empty:
                res.append(0)
            else:
                if hora_sel == "Todas":
                    max_id = df_day["ID"].max()
                else:
                    max_id = int(hora_sel)
                df_max_id = df_day[df_day["ID"] == max_id]
                total = df_max_id["MetaCasos_por_registro"].sum()
                res.append(total)
        return res
    meta_curr = sum_meta_casos_max_id(dias_sem, df_input, tipo_filter)
    if tipo_filter == "nuevo":
        promedio = META_PROMEDIO_NUEVOS_CASOS
    elif tipo_filter == "recompra":
        promedio = META_PROMEDIO_RECOMPRA_CASOS
    else:
        promedio = META_PROMEDIO_TOTAL_CASOS
    meta_curr = [promedio if m == 0 else m for m in meta_curr]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=casos_prev, name=f"Semana {dias_sem[0].isocalendar()[1] - 1}", marker_color="#AED6F1"))
    fig.add_trace(go.Bar(x=labels, y=casos_curr, name=f"Semana {dias_sem[0].isocalendar()[1]}", marker_color="#2980B9"))
    fig.add_trace(go.Scatter(x=labels, y=meta_curr, name="META", mode="lines+markers", line=dict(color="#27AE60", width=3, shape="spline"), marker=dict(color="#27AE60", size=6)))
    fig.update_layout(title=title, barmode="group", yaxis=dict(title="Casos", tickformat=","), template="plotly_white", height=400, legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01), margin=dict(l=20, r=20, t=50, b=20))
    return fig

st.set_page_config(layout="wide", page_title="Corte de Colocación")

st.markdown("""
<style>
.block-container h1,
.block-container h2,
.block-container h3,
.block-container h4,
.block-container h5,
.block-container p,
.block-container label,
.block-container .css-1v3fvcr,
.block-container .stMarkdown {
  color: #ffffff !important;
}
.stMetric, .stMetric > div, .stMetricValue, .stMetricLabel, .stMetricDelta, .st-emotion-cache-1q82h82 e1wr3kle3 {
  color: #ffffff !important;
}
.stMetric span, .stMetric div span {
  color: #ffffff !important;
}
.css-1v3fvcr, .css-1q8dd3e { color: #ffffff !important; }
:root{
  --grad-start: #000046;
  --grad-end:   #1CB5E0;
  --card-bg: rgba(0,0,0,0.28);
  --input-bg: rgba(255,255,255,0.06);
  --muted-line: rgba(255,255,255,0.12);
  --shadow: 0 10px 30px rgba(0,0,0,0.35);
}
html, body, .stApp, .reportview-container, .main {
  background: linear-gradient(180deg, var(--grad-start) 0%, var(--grad-end) 100%) fixed !important;
  color: #fff !important;
}
.stApp, .block-container, .stMarkdown, .element-container, .css-1v3fvcr,
.stText, .stButton, .stMetric, .stDataFrame, .stSelectbox, .stDateInput,
.stNumberInput, .stTextInput, .stFileUploader, .stDownloadButton {
  color: #fff !important;
}
div[data-testid="stSelectbox"], div[data-testid="stDateInput"], div[data-testid="stFileUploader"],
div[data-baseweb="select"], input, .css-1lcbmhc, .css-1v3fvcr {
  background: var(--input-bg) !important;
  color: #fff !important;
  border-radius: 10px !important;
  border: 1px solid rgba(255,255,255,0.06) !important;
}
.header-container {
    background-color: linear-gradient(180deg, var(--grad-start) 0%, var(--grad-end) 100%) fixed !important;
    color: white;
    padding: 5px 10px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 5px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.header-title {
    font-size: 46px;
    font-weight: bold;
    text-align: center;
    flex-grow: 1;
    margin: 0 20px;
}
.header-last-cut {
    font-size: 24px;
    white-space: nowrap;
}
</style>
""", unsafe_allow_html=True)

try:
    logo_data = base64.b64encode(open("logo_fincomun.png", "rb").read()).decode()
except:
    logo_data = ""
st.markdown(f"""
<div class="header-container">
    <img src="data:image/png;base64,{logo_data}" width="180" style="margin-right: 80px;">
    <div class="header-title">CORTE DE COLOCACIÓN</div>
    <div class="header-last-cut">Último corte:<br><strong>{int(max_id)} hrs</strong></div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### Filtros")
left, mid, right = st.columns(3)
with left:
    territorio_sel = st.selectbox("Territorio", options=["Todas"] + sorted(df["TERRITORIO"].dropna().unique().tolist()))
    zona_sel = st.selectbox("Zona", options=["Todas"] + sorted(df["ZONA"].dropna().unique().tolist()))
with mid:
    sucursal_sel = st.selectbox("Sucursal", options=["Todas"] + sorted(df["SUCURSAL"].dropna().unique().tolist()))
with right:
    fecha_sel = st.selectbox("Fecha", options=sorted(df["Fecha"].unique(), reverse=True))
    hora_sel = st.selectbox("Hora", options=["Todas"] + sorted(df["ID"].astype(str).unique().tolist()))

mask_metrics = pd.Series(True, index=df.index)
if territorio_sel != "Todas":
    mask_metrics = mask_metrics & (df["TERRITORIO"] == territorio_sel)
if zona_sel != "Todas":
    mask_metrics = mask_metrics & (df["ZONA"] == zona_sel)
if sucursal_sel != "Todas":
    mask_metrics = mask_metrics & (df["SUCURSAL"] == sucursal_sel)
if fecha_sel:
    mask_metrics = mask_metrics & (df["Fecha"] == fecha_sel)
if hora_sel != "Todas":
    mask_metrics = mask_metrics & (df["ID"].astype(str) == hora_sel)
df_f_metrics = df.loc[mask_metrics].copy()

mask_charts = pd.Series(True, index=df.index)
if territorio_sel != "Todas":
    mask_charts = mask_charts & (df["TERRITORIO"] == territorio_sel)
if zona_sel != "Todas":
    mask_charts = mask_charts & (df["ZONA"] == zona_sel)
if sucursal_sel != "Todas":
    mask_charts = mask_charts & (df["SUCURSAL"] == sucursal_sel)
if hora_sel != "Todas":
    mask_charts = mask_charts & (df["ID"].astype(str) == hora_sel)
df_f_charts = df.loc[mask_charts].copy()

st.markdown("---")
st.markdown("### Resumen del día seleccionado")
col_nuevos, col_recomp, col_total = st.columns(3)

with col_nuevos:
    st.markdown("#### NUEVOS")
    monto_nuevos, casos_nuevos, meta_nuevos, logro_nuevos = calcular_metrica(df_f_metrics, "nuevo")
    st.markdown(f'''
    <div>
      <div style="font-size:12px; letter-spacing:1px; color:rgba(255,255,255,0.85); margin-bottom:6px;">MONTO</div>
      <div style="font-size:36px; font-weight:700; color:#FFFFFF; margin-bottom:6px;">{formato_dinero(monto_nuevos)}</div>
    </div>
    ''', unsafe_allow_html=True)
    st.write("Casos:", int(casos_nuevos))
    st.write("Meta:", formato_dinero(meta_nuevos))
    st.write(f"Logro: {logro_nuevos:.2f} %")

with col_recomp:
    st.markdown("#### RECOMPRA")
    monto_recomp, casos_recomp, meta_recomp, logro_recomp = calcular_metrica(df_f_metrics, "recompra")
    st.markdown(f'''
    <div>
      <div style="font-size:12px; letter-spacing:1px; color:rgba(255,255,255,0.85); margin-bottom:6px;">MONTO</div>
      <div style="font-size:36px; font-weight:700; color:#FFFFFF; margin-bottom:6px;">{formato_dinero(monto_recomp)}</div>
    </div>
    ''', unsafe_allow_html=True)
    st.write("Casos:", int(casos_recomp))
    st.write("Meta:", formato_dinero(meta_recomp))
    st.write(f"Logro: {logro_recomp:.2f} %")

with col_total:
    st.markdown("#### TOTALES")
    monto_total, casos_total, meta_total, logro_total = calcular_metrica(df_f_metrics, None)
    st.markdown(f'''
    <div>
      <div style="font-size:12px; letter-spacing:1px; color:rgba(255,255,255,0.85); margin-bottom:6px;">MONTO</div>
      <div style="font-size:36px; font-weight:700; color:#FFFFFF; margin-bottom:6px;">{formato_dinero(monto_total)}</div>
    </div>
    ''', unsafe_allow_html=True)
    st.write("Casos:", int(casos_total))
    st.write("Meta:", formato_dinero(meta_total))
    st.write(f"Logro: {logro_total:.2f} %")

st.markdown("---")
st.markdown("### Monto por día y semana")
col_monto_nuevos, col_monto_recomp, col_monto_total = st.columns(3)

with col_monto_nuevos:
    fig_monto_nuevos = crear_grafica_sem(df_f_charts, "nuevo", title="MONTO - NUEVOS")
    st.plotly_chart(fig_monto_nuevos, use_container_width=True)

with col_monto_recomp:
    fig_monto_recomp = crear_grafica_sem(df_f_charts, "recompra", title="MONTO - RECOMPRA")
    st.plotly_chart(fig_monto_recomp, use_container_width=True)

with col_monto_total:
    fig_monto_total = crear_grafica_sem(df_f_charts, None, title="MONTO - TOTAL")
    st.plotly_chart(fig_monto_total, use_container_width=True)

st.markdown("---")
st.markdown("### Casos por día y semana")
col_casos_nuevos, col_casos_recomp, col_casos_total = st.columns(3)

with col_casos_nuevos:
    fig_casos_nuevos = crear_grafica_sem_cases(df_f_charts, "nuevo", title="CASOS - NUEVOS")
    st.plotly_chart(fig_casos_nuevos, use_container_width=True)

with col_casos_recomp:
    fig_casos_recomp = crear_grafica_sem_cases(df_f_charts, "recompra", title="CASOS - RECOMPRA")
    st.plotly_chart(fig_casos_recomp, use_container_width=True)

with col_casos_total:
    fig_casos_total = crear_grafica_sem_cases(df_f_charts, None, title="CASOS - TOTAL")
    st.plotly_chart(fig_casos_total, use_container_width=True)

st.markdown("---")
st.markdown("### Tabla Nuevos")
col_zona_nuevos, col_sucursal_nuevos = st.columns(2)

with col_zona_nuevos:
    st.markdown("#### ZONA")
    df_zona_nuevos = df_f_metrics[df_f_metrics[col_tipo].str.contains("nuevo", case=False, na=False)].copy()
    if not df_zona_nuevos.empty:
        df_zona_nuevos = df_zona_nuevos.groupby("ZONA").agg(
            MONTO=(col_monto, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_zona_nuevos["LOGRO_PCT"] = (df_zona_nuevos["MONTO"] / df_zona_nuevos["META"].replace({0: pd.NA})) * 100
        df_zona_nuevos["ICONO"] = df_zona_nuevos["LOGRO_PCT"].apply(
            lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 80 else "🔴" if pd.notna(x) else "")
        df_zona_nuevos["MONTO"] = df_zona_nuevos["MONTO"].map(lambda x: f"${x:,.0f}")
        df_zona_nuevos["META"] = df_zona_nuevos["META"].map(lambda x: f"${x:,.0f}")
        df_zona_nuevos["LOGRO_PCT"] = df_zona_nuevos["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_zona_nuevos[["ZONA", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Nuevos.")

with col_sucursal_nuevos:
    st.markdown("#### SUCURSAL")
    df_sucursal_nuevos = df_f_metrics[df_f_metrics[col_tipo].str.contains("nuevo", case=False, na=False)].copy()
    if not df_sucursal_nuevos.empty:
        df_sucursal_nuevos = df_sucursal_nuevos.groupby("SUCURSAL").agg(
            MONTO=(col_monto, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_sucursal_nuevos["LOGRO_PCT"] = (df_sucursal_nuevos["MONTO"] / df_sucursal_nuevos["META"].replace({0: pd.NA})) * 100
        df_sucursal_nuevos["ICONO"] = df_sucursal_nuevos["LOGRO_PCT"].apply(
            lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 80 else "🔴" if pd.notna(x) else "")
        df_sucursal_nuevos["MONTO"] = df_sucursal_nuevos["MONTO"].map(lambda x: f"${x:,.0f}")
        df_sucursal_nuevos["META"] = df_sucursal_nuevos["META"].map(lambda x: f"${x:,.0f}")
        df_sucursal_nuevos["LOGRO_PCT"] = df_sucursal_nuevos["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_sucursal_nuevos[["SUCURSAL", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Nuevos.")

st.markdown("---")
st.markdown("### Tabla Recompra")
col_zona_recomp, col_sucursal_recomp = st.columns(2)

with col_zona_recomp:
    st.markdown("#### ZONA")
    df_zona_recomp = df_f_metrics[df_f_metrics[col_tipo].str.contains("recompra", case=False, na=False)].copy()
    if not df_zona_recomp.empty:
        df_zona_recomp = df_zona_recomp.groupby("ZONA").agg(
            MONTO=(col_monto, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_zona_recomp["LOGRO_PCT"] = (df_zona_recomp["MONTO"] / df_zona_recomp["META"].replace({0: pd.NA})) * 100
        df_zona_recomp["ICONO"] = df_zona_recomp["LOGRO_PCT"].apply(
            lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 80 else "🔴" if pd.notna(x) else "")
        df_zona_recomp["MONTO"] = df_zona_recomp["MONTO"].map(lambda x: f"${x:,.0f}")
        df_zona_recomp["META"] = df_zona_recomp["META"].map(lambda x: f"${x:,.0f}")
        df_zona_recomp["LOGRO_PCT"] = df_zona_recomp["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_zona_recomp[["ZONA", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Recompra.")

with col_sucursal_recomp:
    st.markdown("#### SUCURSAL")
    df_sucursal_recomp = df_f_metrics[df_f_metrics[col_tipo].str.contains("recompra", case=False, na=False)].copy()
    if not df_sucursal_recomp.empty:
        df_sucursal_recomp = df_sucursal_recomp.groupby("SUCURSAL").agg(
            MONTO=(col_monto, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_sucursal_recomp["LOGRO_PCT"] = (df_sucursal_recomp["MONTO"] / df_sucursal_recomp["META"].replace({0: pd.NA})) * 100
        df_sucursal_recomp["ICONO"] = df_sucursal_recomp["LOGRO_PCT"].apply(
            lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 80 else "🔴" if pd.notna(x) else "")
        df_sucursal_recomp["MONTO"] = df_sucursal_recomp["MONTO"].map(lambda x: f"${x:,.0f}")
        df_sucursal_recomp["META"] = df_sucursal_recomp["META"].map(lambda x: f"${x:,.0f}")
        df_sucursal_recomp["LOGRO_PCT"] = df_sucursal_recomp["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_sucursal_recomp[["SUCURSAL", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Recompra.")

st.markdown("---")
st.markdown("### Tabla Colocación")
col_zona_total, col_sucursal_total = st.columns(2)

with col_zona_total:
    st.markdown("#### ZONA")
    df_zona_total = df_f_metrics.copy()
    if not df_zona_total.empty:
        df_zona_total = df_zona_total.groupby("ZONA").agg(
            MONTO=(col_monto, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_zona_total["LOGRO_PCT"] = (df_zona_total["MONTO"] / df_zona_total["META"].replace({0: pd.NA})) * 100
        df_zona_total["ICONO"] = df_zona_total["LOGRO_PCT"].apply(
            lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 80 else "🔴" if pd.notna(x) else "")
        df_zona_total["MONTO"] = df_zona_total["MONTO"].map(lambda x: f"${x:,.0f}")
        df_zona_total["META"] = df_zona_total["META"].map(lambda x: f"${x:,.0f}")
        df_zona_total["LOGRO_PCT"] = df_zona_total["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_zona_total[["ZONA", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos.")

with col_sucursal_total:
    st.markdown("#### SUCURSAL")
    df_sucursal_total = df_f_metrics.copy()
    if not df_sucursal_total.empty:
        df_sucursal_total = df_sucursal_total.groupby("SUCURSAL").agg(
            MONTO=(col_monto, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_sucursal_total["LOGRO_PCT"] = (df_sucursal_total["MONTO"] / df_sucursal_total["META"].replace({0: pd.NA})) * 100
        df_sucursal_total["ICONO"] = df_sucursal_total["LOGRO_PCT"].apply(
            lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 80 else "🔴" if pd.notna(x) else "")
        df_sucursal_total["MONTO"] = df_sucursal_total["MONTO"].map(lambda x: f"${x:,.0f}")
        df_sucursal_total["META"] = df_sucursal_total["META"].map(lambda x: f"${x:,.0f}")
        df_sucursal_total["LOGRO_PCT"] = df_sucursal_total["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_sucursal_total[["SUCURSAL", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos.")
