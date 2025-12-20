#cd C:\Users\mcastillo\pythonProject
# C:\Users\mcastillo\python\.venv\Scripts\activate
# streamlit run appCorte.py
# appCorte.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import glob
import re

CONSOLIDADO_PATH = r"\\fc-fs01\Planeacion\Nuevo corte\consolidado.parquet"
LOGO_PATH = r"\\fc-fs01\Planeacion\Michel\logo_fincomun.png"
COL_SUCURSAL = "SUCURSAL"
COL_MONTO = "MONTO"
COL_TIPO = "TIPO_2"

@st.cache_data
def load_data():
    df = pd.read_parquet(CONSOLIDADO_PATH)
    df["Fecha"] = df["FileDate"].dt.date
    return df


df = load_data()

max_date = df["FileDate"].max()
MAX_ID = df.loc[df["FileDate"] == max_date, "ID"].max()
METAS_DIR = r"\\fc-fs01\Planeacion\Nuevo corte\Metas por semana"
WEEK_OF_DATA = int(max_date.isocalendar()[1])

meta_files = sorted(glob.glob(os.path.join(METAS_DIR, "*.xls*")))
meta_choice = None
meta_pattern = re.compile(r"meta[_\-]?Sem[_\-]?(\d{1,2})", re.IGNORECASE)
for mf in meta_files:
    m = meta_pattern.search(os.path.basename(mf))
    if m and int(m.group(1)) == WEEK_OF_DATA:
        meta_choice = mf
        break
if meta_choice is None and meta_files:
    meta_choice = max(meta_files, key=os.path.getmtime)

META_PROMEDIO_NUEVOS_MONTO = 0
META_PROMEDIO_RECOMPRA_MONTO = 0
META_PROMEDIO_TOTAL_MONTO = 0
META_PROMEDIO_NUEVOS_CASOS = 0
META_PROMEDIO_RECOMPRA_CASOS = 0
META_PROMEDIO_TOTAL_CASOS = 0

if meta_choice:
    try:
        df_meta_orig = pd.read_excel(meta_choice)
        if "Nuevo ($)" in df_meta_orig.columns and "Recompra ($)" in df_meta_orig.columns:
            total_nuevos_monto = df_meta_orig["Nuevo ($)"].sum()
            total_recompra_monto = df_meta_orig["Recompra ($)"].sum()
            META_PROMEDIO_NUEVOS_MONTO = total_nuevos_monto / 6
            META_PROMEDIO_RECOMPRA_MONTO = total_recompra_monto / 6
            META_PROMEDIO_TOTAL_MONTO = META_PROMEDIO_NUEVOS_MONTO + META_PROMEDIO_RECOMPRA_MONTO

        if "Nuevo (#)" in df_meta_orig.columns and "Recompra (#)" in df_meta_orig.columns:
            total_nuevos_casos = df_meta_orig["Nuevo (#)"].sum()
            total_recompra_casos = df_meta_orig["Recompra (#)"].sum()
            META_PROMEDIO_NUEVOS_CASOS = total_nuevos_casos / 6
            META_PROMEDIO_RECOMPRA_CASOS = total_recompra_casos / 6
            META_PROMEDIO_TOTAL_CASOS = META_PROMEDIO_NUEVOS_CASOS + META_PROMEDIO_RECOMPRA_CASOS

    except Exception as e:
        st.warning(f"Error al cargar metas originales: {e}")

def format_money(x): return f"${x:,.0f}"

def get_filtered_df(df_input, territorio_sel, zona_sel, sucursal_sel, fecha_sel, hora_sel):
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


def calculate_metrics(df_input, tipo_key=None):
    if df_input.empty:
        return 0, 0, 0, 0
    if tipo_key:
        df_filtered = df_input[df_input[COL_TIPO].str.contains(tipo_key, case=False, na=False)]
    else:
        df_filtered = df_input.copy()

    if df_filtered.empty:
        return 0, 0, 0, 0

    df_max_id = df_filtered[df_filtered["ID"] == MAX_ID]

    monto = df_max_id[COL_MONTO].sum()
    casos = len(df_max_id)
    meta = df_max_id["MetaMonto_por_registro"].sum()
    logro = (monto / meta * 100) if meta > 0 else 0
    return monto, casos, meta, logro

def create_weekly_chart(df_input, tipo_filter=None, title="MONTO POR DÍA Y SEMANA"):
    if df_input.empty:
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_white")
        return fig

    max_date = df_input["FileDate"].max()
    start_of_week = max_date - pd.Timedelta(days=max_date.weekday())
    dates_week = [start_of_week + pd.Timedelta(days=i) for i in range(6)]
    dates_prev = [d - pd.Timedelta(days=7) for d in dates_week]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    labels = [f"{i+1}.-{dias_es[i]}" for i in range(6)]

    def sum_monto_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[COL_TIPO].str.contains(tipo_key, case=False, na=False)
            df_day = df_source[day_mask]
            if df_day.empty:
                res.append(0)
            else:
                if hora_sel == "Todas":
                    max_id = df_day["ID"].max()
                else:
                    max_id = int(hora_sel)
                df_max_id = df_day[df_day["ID"] == max_id]
                total = df_max_id[COL_MONTO].sum()
                res.append(total)
        return res

    monto_curr = sum_monto_max_id(dates_week, df_input, tipo_filter)
    monto_prev = sum_monto_max_id(dates_prev, df_input, tipo_filter)

    def sum_meta_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[COL_TIPO].str.contains(tipo_key, case=False, na=False)
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

    meta_curr = sum_meta_max_id(dates_week, df_input, tipo_filter)

    # --- REEMPLAZAR META = 0 POR PROMEDIO DIARIO ---
    if tipo_filter == "nuev":
        promedio = META_PROMEDIO_NUEVOS_MONTO
    elif tipo_filter == "recomp":
        promedio = META_PROMEDIO_RECOMPRA_MONTO
    else:
        promedio = META_PROMEDIO_TOTAL_MONTO

    meta_curr = [promedio if m == 0 else m for m in meta_curr]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=monto_prev, name=f"Semana {dates_week[0].isocalendar()[1]-1}", marker_color="#AED6F1"))
    fig.add_trace(go.Bar(x=labels, y=monto_curr, name=f"Semana {dates_week[0].isocalendar()[1]}", marker_color="#2980B9"))
    fig.add_trace(go.Scatter(x=labels, y=meta_curr, name="META", mode="lines+markers", line=dict(color="#27AE60", width=3, shape="spline"), marker=dict(color="#27AE60", size=6)))
    fig.update_layout(
        title=title,
        barmode="group",
        yaxis=dict(title="Monto", tickformat="$,.0f"),
        template="plotly_white",
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

def create_weekly_chart_cases(df_input, tipo_filter=None, title="CASOS POR DÍA Y SEMANA"):
    if df_input.empty:
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_white")
        return fig

    max_date = df_input["FileDate"].max()
    start_of_week = max_date - pd.Timedelta(days=max_date.weekday())
    dates_week = [start_of_week + pd.Timedelta(days=i) for i in range(6)]
    dates_prev = [d - pd.Timedelta(days=7) for d in dates_week]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    labels = [f"{i+1}.-{dias_es[i]}" for i in range(6)]

    def sum_casos_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[COL_TIPO].str.contains(tipo_key, case=False, na=False)
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

    casos_curr = sum_casos_max_id(dates_week, df_input, tipo_filter)
    casos_prev = sum_casos_max_id(dates_prev, df_input, tipo_filter)

    def sum_meta_casos_max_id(dates, df_source, tipo_key=None):
        res = []
        for d in dates:
            day_mask = df_source["FileDate"].dt.date == d.date()
            if tipo_key:
                day_mask = day_mask & df_source[COL_TIPO].str.contains(tipo_key, case=False, na=False)
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

    meta_curr = sum_meta_casos_max_id(dates_week, df_input, tipo_filter)

    # --- REEMPLAZAR META = 0 POR PROMEDIO DIARIO ---
    if tipo_filter == "nuev":
        promedio = META_PROMEDIO_NUEVOS_CASOS
    elif tipo_filter == "recomp":
        promedio = META_PROMEDIO_RECOMPRA_CASOS
    else:
        promedio = META_PROMEDIO_TOTAL_CASOS

    meta_curr = [promedio if m == 0 else m for m in meta_curr]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=casos_prev, name=f"Semana {dates_week[0].isocalendar()[1]-1}", marker_color="#AED6F1"))
    fig.add_trace(go.Bar(x=labels, y=casos_curr, name=f"Semana {dates_week[0].isocalendar()[1]}", marker_color="#2980B9"))
    fig.add_trace(go.Scatter(x=labels, y=meta_curr, name="META", mode="lines+markers", line=dict(color="#27AE60", width=3, shape="spline"), marker=dict(color="#27AE60", size=6)))
    fig.update_layout(
        title=title,
        barmode="group",
        yaxis=dict(title="Casos", tickformat=","),
        template="plotly_white",
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=20, r=20, t=50, b=20)
    )
    return fig

st.set_page_config(layout="wide", page_title="Corte de Colocación")
st.markdown(
    """
    <style>
    .header-container {
        background-color: #003366;  
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
    """,
    unsafe_allow_html=True
)

col_logo, col_title, col_time = st.columns([2, 6, 2])
with col_logo:
    st.image(LOGO_PATH, width=1000)
with col_title:
    st.markdown('<div class="header-title">CORTE DE COLOCACIÓN</div>', unsafe_allow_html=True)
with col_time:
    st.markdown(f'<div class="header-last-cut">Último corte:<br><strong>{int(MAX_ID)} hrs</strong></div>', unsafe_allow_html=True)
st.markdown('<div class="header-container" style="height:0; visibility:hidden;"></div>', unsafe_allow_html=True)
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
    monto_nuevos, casos_nuevos, meta_nuevos, logro_nuevos = calculate_metrics(df_f_metrics, "nuev")
    st.metric("MONTO", format_money(monto_nuevos))
    st.write("Casos:", int(casos_nuevos))
    st.write("Meta:", format_money(meta_nuevos))
    st.write(f"Logro: {logro_nuevos:.2f} %")

with col_recomp:
    st.markdown("#### RECOMPRA")
    monto_recomp, casos_recomp, meta_recomp, logro_recomp = calculate_metrics(df_f_metrics, "recomp")
    st.metric("MONTO", format_money(monto_recomp))
    st.write("Casos:", int(casos_recomp))
    st.write("Meta:", format_money(meta_recomp))
    st.write(f"Logro: {logro_recomp:.2f} %")

with col_total:
    st.markdown("#### TOTALES")
    monto_total, casos_total, meta_total, logro_total = calculate_metrics(df_f_metrics, None)
    st.metric("MONTO", format_money(monto_total))
    st.write("Casos:", int(casos_total))
    st.write("Meta:", format_money(meta_total))
    st.write(f"Logro: {logro_total:.2f} %")

st.markdown("---")
st.markdown("### Monto por día y semana")
col_monto_nuevos, col_monto_recomp, col_monto_total = st.columns(3)

with col_monto_nuevos:
    fig_monto_nuevos = create_weekly_chart(df_f_charts, "nuev", title="MONTO - NUEVOS")  # ← Cambiado a "nuev"
    st.plotly_chart(fig_monto_nuevos, use_container_width=True)

with col_monto_recomp:
    fig_monto_recomp = create_weekly_chart(df_f_charts, "recomp", title="MONTO - RECOMPRA")  # ← Cambiado a "recomp"
    st.plotly_chart(fig_monto_recomp, use_container_width=True)

with col_monto_total:
    fig_monto_total = create_weekly_chart(df_f_charts, None, title="MONTO - TOTAL")
    st.plotly_chart(fig_monto_total, use_container_width=True)
st.markdown("---")
st.markdown("### Casos por día y semana")
col_casos_nuevos, col_casos_recomp, col_casos_total = st.columns(3)

with col_casos_nuevos:
    fig_casos_nuevos = create_weekly_chart_cases(df_f_charts, "nuev", title="CASOS - NUEVOS")  # ← Cambiado a "nuev"
    st.plotly_chart(fig_casos_nuevos, use_container_width=True)

with col_casos_recomp:
    fig_casos_recomp = create_weekly_chart_cases(df_f_charts, "recomp", title="CASOS - RECOMPRA")  # ← Cambiado a "recomp"
    st.plotly_chart(fig_casos_recomp, use_container_width=True)

with col_casos_total:
    fig_casos_total = create_weekly_chart_cases(df_f_charts, None, title="CASOS - TOTAL")
    st.plotly_chart(fig_casos_total, use_container_width=True)

st.markdown("---")
st.markdown("### Tabla Nuevos")

col_zona_nuevos, col_sucursal_nuevos = st.columns(2)

with col_zona_nuevos:
    st.markdown("#### ZONA")
    df_zona_nuevos = df_f_metrics[df_f_metrics[COL_TIPO].str.contains("nuev", case=False, na=False)].copy()
    if not df_zona_nuevos.empty:
        df_zona_nuevos = df_zona_nuevos.groupby("ZONA").agg(
            MONTO=(COL_MONTO, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_zona_nuevos["LOGRO_PCT"] = (df_zona_nuevos["MONTO"] / df_zona_nuevos["META"].replace({0: pd.NA})) * 100
        df_zona_nuevos["ICONO"] = df_zona_nuevos["LOGRO_PCT"].apply(lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 90 else "🔴" if pd.notna(x) else "")
        # Formato moneda
        df_zona_nuevos["MONTO"] = df_zona_nuevos["MONTO"].map(lambda x: f"${x:,.0f}")
        df_zona_nuevos["META"] = df_zona_nuevos["META"].map(lambda x: f"${x:,.0f}")
        df_zona_nuevos["LOGRO_PCT"] = df_zona_nuevos["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_zona_nuevos[["ZONA", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Nuevos.")

with col_sucursal_nuevos:
    st.markdown("#### SUCURSAL")
    df_sucursal_nuevos = df_f_metrics[df_f_metrics[COL_TIPO].str.contains("nuev", case=False, na=False)].copy()
    if not df_sucursal_nuevos.empty:
        df_sucursal_nuevos = df_sucursal_nuevos.groupby("SUCURSAL").agg(
            MONTO=(COL_MONTO, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_sucursal_nuevos["LOGRO_PCT"] = (df_sucursal_nuevos["MONTO"] / df_sucursal_nuevos["META"].replace({0: pd.NA})) * 100
        df_sucursal_nuevos["ICONO"] = df_sucursal_nuevos["LOGRO_PCT"].apply(lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 90 else "🔴" if pd.notna(x) else "")
        # Formato moneda
        df_sucursal_nuevos["MONTO"] = df_sucursal_nuevos["MONTO"].map(lambda x: f"${x:,.0f}")
        df_sucursal_nuevos["META"] = df_sucursal_nuevos["META"].map(lambda x: f"${x:,.0f}")
        df_sucursal_nuevos["LOGRO_PCT"] = df_sucursal_nuevos["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_sucursal_nuevos[["SUCURSAL", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Nuevos.")

# --- TABLAS: RECOMPRA ---
st.markdown("---")
st.markdown("### Tabla Recompra")

col_zona_recomp, col_sucursal_recomp = st.columns(2)

with col_zona_recomp:
    st.markdown("#### ZONA")
    df_zona_recomp = df_f_metrics[df_f_metrics[COL_TIPO].str.contains("recomp", case=False, na=False)].copy()
    if not df_zona_recomp.empty:
        df_zona_recomp = df_zona_recomp.groupby("ZONA").agg(
            MONTO=(COL_MONTO, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_zona_recomp["LOGRO_PCT"] = (df_zona_recomp["MONTO"] / df_zona_recomp["META"].replace({0: pd.NA})) * 100
        df_zona_recomp["ICONO"] = df_zona_recomp["LOGRO_PCT"].apply(lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 90 else "🔴" if pd.notna(x) else "")
        # Formato moneda
        df_zona_recomp["MONTO"] = df_zona_recomp["MONTO"].map(lambda x: f"${x:,.0f}")
        df_zona_recomp["META"] = df_zona_recomp["META"].map(lambda x: f"${x:,.0f}")
        df_zona_recomp["LOGRO_PCT"] = df_zona_recomp["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_zona_recomp[["ZONA", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Recompra.")

with col_sucursal_recomp:
    st.markdown("#### SUCURSAL")
    df_sucursal_recomp = df_f_metrics[df_f_metrics[COL_TIPO].str.contains("recomp", case=False, na=False)].copy()
    if not df_sucursal_recomp.empty:
        df_sucursal_recomp = df_sucursal_recomp.groupby("SUCURSAL").agg(
            MONTO=(COL_MONTO, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_sucursal_recomp["LOGRO_PCT"] = (df_sucursal_recomp["MONTO"] / df_sucursal_recomp["META"].replace({0: pd.NA})) * 100
        df_sucursal_recomp["ICONO"] = df_sucursal_recomp["LOGRO_PCT"].apply(lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 90 else "🔴" if pd.notna(x) else "")
        # Formato moneda
        df_sucursal_recomp["MONTO"] = df_sucursal_recomp["MONTO"].map(lambda x: f"${x:,.0f}")
        df_sucursal_recomp["META"] = df_sucursal_recomp["META"].map(lambda x: f"${x:,.0f}")
        df_sucursal_recomp["LOGRO_PCT"] = df_sucursal_recomp["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_sucursal_recomp[["SUCURSAL", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos para Recompra.")

# --- TABLAS: TOTAL ---
st.markdown("---")
st.markdown("### Tabla Colocación")

col_zona_total, col_sucursal_total = st.columns(2)

with col_zona_total:
    st.markdown("#### ZONA")
    df_zona_total = df_f_metrics.copy()
    if not df_zona_total.empty:
        df_zona_total = df_zona_total.groupby("ZONA").agg(
            MONTO=(COL_MONTO, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_zona_total["LOGRO_PCT"] = (df_zona_total["MONTO"] / df_zona_total["META"].replace({0: pd.NA})) * 100
        df_zona_total["ICONO"] = df_zona_total["LOGRO_PCT"].apply(lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 90 else "🔴" if pd.notna(x) else "")
        # Formato moneda
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
            MONTO=(COL_MONTO, "sum"),
            CASOS=("FileName", "count"),
            META=("MetaMonto_por_registro", "sum")
        ).reset_index()
        df_sucursal_total["LOGRO_PCT"] = (df_sucursal_total["MONTO"] / df_sucursal_total["META"].replace({0: pd.NA})) * 100
        df_sucursal_total["ICONO"] = df_sucursal_total["LOGRO_PCT"].apply(lambda x: "✅" if pd.notna(x) and x >= 100 else "🟡" if pd.notna(x) and x >= 90 else "🔴" if pd.notna(x) else "")
        # Formato moneda
        df_sucursal_total["MONTO"] = df_sucursal_total["MONTO"].map(lambda x: f"${x:,.0f}")
        df_sucursal_total["META"] = df_sucursal_total["META"].map(lambda x: f"${x:,.0f}")
        df_sucursal_total["LOGRO_PCT"] = df_sucursal_total["LOGRO_PCT"].fillna(0).round(2).astype(str) + " %"
        st.dataframe(df_sucursal_total[["SUCURSAL", "MONTO", "CASOS", "META", "ICONO", "LOGRO_PCT"]], hide_index=True, use_container_width=True)
    else:
        st.write("No hay datos.")