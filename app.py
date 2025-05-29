import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import numpy as np
from sklearn.linear_model import LinearRegression
from utils import generar_pdf_resumen
from utils import cargar_datos, preparar_datos

st.set_page_config(page_title="Gastos del hogar", layout="wide")

def cargar_css(ruta):
    with open(ruta) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

cargar_css("style.css")

st.title("📊 Gastos / Despeses")

df = cargar_datos("data/expenses_template.xlsx")
df_preparado = preparar_datos(df)

# Asegurarse de que la columna "Mes" sea tipo datetime
df_preparado["Mes"] = pd.to_datetime(df_preparado["Mes"], dayfirst=True)

st.markdown("---")

# Selector visual de rango de meses
st.subheader("📅 Filtrar por rango de meses")

# Asegurarse de que las fechas están ordenadas y sin duplicados
meses_unicos = sorted(df_preparado["Mes"].dt.to_period("M").drop_duplicates().tolist())

# Convertimos de Period a datetime (primer día de mes)
meses_disponibles = [pd.Period(m, freq="M").to_timestamp() for m in meses_unicos]

rango_fechas = st.select_slider(
    "Selecciona el rango de meses:",
    options=meses_disponibles,
    value=(meses_disponibles[0], meses_disponibles[-1]),
    format_func=lambda d: d.strftime("%B %Y")
)

# Filtrar el DataFrame principal
df_filtrado = df_preparado[(df_preparado["Mes"] >= rango_fechas[0]) & (df_preparado["Mes"] <= rango_fechas[1])]

st.info(f"🔎 Mostrando datos desde **{rango_fechas[0].strftime('%B %Y')}** hasta **{rango_fechas[1].strftime('%B %Y')}**")

st.markdown("---")

st.markdown("## 🔍 Resumen del mes más reciente")
if not df_filtrado.empty:
    ultimo_mes = df_filtrado.iloc[-1]
else:
    st.warning("⚠️ No hay datos en el rango seleccionado.")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("💰 Ingresado", f"{ultimo_mes['Total de ingreso']:.2f} €")
col2.metric("📤 Gasto total", f"{ultimo_mes['Total de gasto']:.2f} €")
col3.metric(
    "📊 Balance",
    f"{ultimo_mes['Total de ingreso'] - ultimo_mes['Total de gasto']:.2f} €",
    delta_color="normal" if ultimo_mes['Total de ingreso'] > ultimo_mes['Total de gasto'] else "inverse"
)

with st.expander("📋 Ver tabla de datos"):
    st.dataframe(df, use_container_width=True)

st.markdown("---")

st.subheader("📈 Evolución mensual del gasto total + tendencia")

df_preparado_ordenado = df_filtrado.sort_values("Mes_orden").copy()
df_preparado_ordenado["Mes_idx"] = range(len(df_preparado_ordenado))

X = df_preparado_ordenado["Mes_idx"].values.reshape(-1, 1)
y = df_preparado_ordenado["Total de gasto"].values
modelo = LinearRegression().fit(X, y)
tendencias = modelo.predict(X)

df_preparado_ordenado["Mes_label"] = df_preparado_ordenado["Mes"].dt.strftime("%B %Y")
df_preparado_ordenado["Mes_orden_str"] = df_preparado_ordenado["Mes"].dt.strftime("%Y-%m-%d")

df_tendencia = pd.DataFrame({
    "Mes_orden_str": df_preparado_ordenado["Mes_orden_str"],
    "Tendencia": tendencias,
    "Mes_label": df_preparado_ordenado["Mes"]
})

linea_gasto = alt.Chart(df_preparado_ordenado).mark_line(point=True, color="#81A1C1").encode(
    x=alt.X("Mes_orden_str:N", title="Mes", axis=alt.Axis(labelExpr="datum.label")),
    y=alt.Y("Total de gasto", title="Total de gasto (€)"),
    tooltip=["Mes_label:N", "Total de gasto"]
).transform_calculate(
    label="datum.Mes_label"
)

linea_tendencia = alt.Chart(df_tendencia).mark_line(color="orange", strokeDash=[5, 5]).encode(
    x=alt.X("Mes_orden_str:N", title="Mes", axis=alt.Axis(labelExpr="datum.label")),
    y=alt.Y("Tendencia", title="Tendencia (€)")
).transform_calculate(
    label="datum.Mes_label"
)

gasto_medio = df_preparado_ordenado["Total de gasto"].mean()

linea_media = alt.Chart(pd.DataFrame({
    "y": [gasto_medio]
})).mark_rule(color="green", strokeDash=[3, 3]).encode(
    y="y:Q"
)

media_formateada = f"{gasto_medio:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

etiqueta_media = alt.Chart(pd.DataFrame({
    "x": [df_preparado_ordenado["Mes_orden_str"].iloc[-1]],
    "y": [gasto_medio + 300],
    "texto": [f"Media: {media_formateada}"]
})).mark_text(
    align="right",
    fontSize=13,
    color="white"
).encode(
    x="x:N",
    y="y:Q",
    text="texto"
)

# Etiqueta visual para el mes más caro
mes_mas_caro = df_preparado_ordenado.loc[df_preparado_ordenado["Total de gasto"].idxmax()]

etiqueta_mas_caro = alt.Chart(pd.DataFrame({
    "Mes_orden_str": [mes_mas_caro["Mes"].strftime("%Y-%m-%d")],
    "y": [mes_mas_caro["Total de gasto"] + 300],
    "texto": [f"📌 Mes más caro"]
})).mark_text(
    align="center",
    fontSize=13,
    color="orange"
).encode(
    x=alt.X("Mes_orden_str:N"),
    y=alt.Y("y:Q"),
    text="texto"
)

st.altair_chart((linea_gasto + linea_tendencia + linea_media + etiqueta_media + etiqueta_mas_caro).properties(width=700, height=400), use_container_width=True)

st.markdown("---")

st.subheader("💰 Comparativa: Ingresos vs Gastos")

df_altair = df_filtrado.sort_values("Mes")[["Mes", "Total de ingreso", "Total de gasto"]].copy()
df_altair["Mes_str"] = df_altair["Mes"].dt.strftime("%B %Y")

df_melted = df_altair.melt(
    id_vars="Mes_str", 
    value_vars=["Total de ingreso", "Total de gasto"],
    var_name="Tipo", 
    value_name="Cantidad"
)

grafico_altair = alt.Chart(df_melted).mark_bar().encode(
    x=alt.X("Mes_str:N", title="Mes", sort=df_altair["Mes_str"].tolist()),
    y=alt.Y("Cantidad", title="Cantidad (€)"),
    color="Tipo",
    tooltip=["Mes_str", "Tipo", "Cantidad"]
).properties(width=700, height=400)

st.altair_chart(grafico_altair, use_container_width=True)

st.markdown("---")

st.subheader("🧾 Distribución por categoría acumulada")

categorias = [
    "Hipoteca", "Impuestos", "Luz", "Gas", "Agua", "Internet",
    "Escuela", "Acogida", "Inglés", "Comedor", "Natación",
    "Tarjeta DB", "Otros"
]

suma_por_categoria = df_filtrado[categorias].sum().sort_values(ascending=False)

# Filtramos solo categorías con valor positivo
suma_filtrada = suma_por_categoria[suma_por_categoria > 0]

# Diccionario de iconos
iconos_categoria = {
    "Hipoteca": "🏠", "Impuestos": "💰", "Luz": "💡", "Gas": "🔥",
    "Agua": "🚿", "Internet": "🌐", "Escuela": "🎒", "Acogida": "🧒",
    "Inglés": "🇬🇧", "Comedor": "🍽️", "Natación": "🏊", "Tarjeta DB": "💳", "Otros": "📦"
}

col1, col_sep, col2 = st.columns([1, 0.1, 1.3])

with col1:
    st.markdown("#### 📊 Gasto total por categoría")

    if not suma_filtrada.empty:
        pie_chart = px.pie(
            values=suma_filtrada,
            names=suma_filtrada.index,
            hole=0.3
        )
        st.plotly_chart(pie_chart, use_container_width=True)
    else:
        st.info("No hay datos disponibles para mostrar en el gráfico.")

with col2:
    st.markdown("#### 📦 Gasto acumulado por categoría")

    for i in range(0, len(categorias), 2):
        cols = st.columns(2)
        for j, cat in enumerate(categorias[i:i+2]):
            if cat in suma_por_categoria:
                valor = suma_por_categoria[cat]
                icono = iconos_categoria.get(cat, "")
                label = f"{icono} {cat}"
                cols[j].metric(label, f"{valor:.2f} €")

st.markdown("---")

st.subheader("⚠️ Alertas financieras")
balances = pd.to_numeric(df_filtrado["Balance"], errors="coerce").fillna(0)
negativos = balances < 0
racha = 0
max_racha = 0
for negativo in negativos:
    if negativo:
        racha += 1
        max_racha = max(max_racha, racha)
    else:
        racha = 0

if max_racha >= 2:
    st.warning(f"⚠️ ¡Atención! Llevas {max_racha} meses seguidos con balance negativo.")
else:
    st.success("✅ Tus balances están bajo control. ¡Sigue así!")

st.subheader("📉 Balance mensual: diferencia entre ingresos y gastos")

df_balance = df_filtrado.sort_values("Mes").copy()
df_balance["Mes_str"] = df_balance["Mes"].dt.strftime("%B %Y")
df_balance["Balance"] = df_balance["Total de ingreso"] - df_balance["Total de gasto"]
df_balance["Color"] = np.where(df_balance["Balance"] >= 0, "Positivo", "Negativo")

grafico_balance = alt.Chart(df_balance).mark_bar().encode(
    x=alt.X("Mes_str:N", title="Mes", sort=df_balance["Mes_str"].tolist()),
    y=alt.Y("Balance", title="Balance mensual (€)"),
    color=alt.Color("Color", 
                    scale=alt.Scale(domain=["Positivo", "Negativo"], range=["#A3BE8C", "#BF616A"]),
                    legend=None),
    tooltip=["Mes_str", "Balance"]
).properties(width=700, height=400)

st.altair_chart(grafico_balance, use_container_width=True)

st.markdown("---")

st.subheader("📊 Top meses por gasto total")

# Elegimos los top 3
top_mas_caros = df_filtrado.sort_values("Total de gasto", ascending=False).head(3)
top_mas_baratos = df_filtrado.sort_values("Total de gasto", ascending=True).head(3)

# Formatear mes y gasto
def formatear_euro(valor):
    return f"{valor:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

top_mas_caros["Mes"] = top_mas_caros["Mes"].dt.strftime("%B %Y").str.capitalize()
top_mas_caros["Total de gasto"] = top_mas_caros["Total de gasto"].apply(formatear_euro)

top_mas_baratos["Mes"] = top_mas_baratos["Mes"].dt.strftime("%B %Y").str.capitalize()
top_mas_baratos["Total de gasto"] = top_mas_baratos["Total de gasto"].apply(formatear_euro)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔴 Más caros")
    st.table(top_mas_caros[["Mes", "Total de gasto"]].set_index("Mes"))

with col2:
    st.markdown("### 🟢 Más baratos")
    st.table(top_mas_baratos[["Mes", "Total de gasto"]].set_index("Mes"))

st.markdown("---")

st.subheader("📆 Detalle de un mes concreto")
df_filtrado["Mes_str"] = df_filtrado["Mes"].dt.strftime("%B %Y")  # ej: "Mayo 2024"

# Crear lista formateada para el selectbox
mes_opciones = df_filtrado["Mes_str"].tolist()
mes_seleccionado_str = st.selectbox("📆 Elige el mes para ver detalles:", mes_opciones)

# Filtrar usando la fecha real correspondiente
mes_real = df_filtrado[df_filtrado["Mes_str"] == mes_seleccionado_str]["Mes"].iloc[0]
df_mes = df_filtrado[df_filtrado["Mes"] == mes_real].T.reset_index()

df_mes.columns = ["Categoría", "Valor"]
df_mes = df_mes[~df_mes["Categoría"].isin(["Ingresado a cuenta", "Balance"])]
st.bar_chart(df_mes.set_index("Categoría"))

# 💳 Tarjetas visuales por categoría
st.subheader("📇 Gasto por categoría del mes seleccionado")

iconos_categoria = {
    "Hipoteca": "🏠",
    "Impuestos": "💰",
    "Luz": "💡",
    "Gas": "🔥",
    "Agua": "🚿",
    "Internet": "🌐",
    "Escuela": "🎒",
    "Acogida": "🧒",
    "Inglés": "🇬🇧",
    "Comedor": "🍽️",
    "Natación": "🏊",
    "Tarjeta DB": "💳",
    "Otros": "📦"
}

gastos_mes = df_mes.set_index("Categoría")["Valor"].to_dict()

for i in range(0, len(categorias), 4):
    cols = st.columns(4)
    for j, cat in enumerate(categorias[i:i+4]):
        if cat in gastos_mes:
            valor = gastos_mes[cat]
            icono = iconos_categoria.get(cat, "")
            label = f"{icono} {cat}"
            cols[j].metric(label, f"{valor:.2f} €")

st.markdown("---")

st.subheader("📂 Descargar datos")
csv = df_filtrado.to_csv(index=False).encode('utf-8')
st.download_button(
    "📥 Descargar tabla en CSV",
    data=csv,
    file_name='gastos_domesticos.csv',
    mime='text/csv'
)

# Crear copias sin formatear para evitar errores en el PDF
top_mas_caros_pdf = df_filtrado.sort_values("Total de gasto", ascending=False).head(3)
top_mas_baratos_pdf = df_filtrado.sort_values("Total de gasto", ascending=True).head(3)

pdf_bytes = generar_pdf_resumen(ultimo_mes, top_mas_caros_pdf, top_mas_baratos_pdf, df_filtrado[categorias].sum())

st.download_button(
    label="📄 Descargar resumen en PDF",
    data=pdf_bytes,
    file_name="resumen_gastos.pdf",
    mime="application/pdf"
)