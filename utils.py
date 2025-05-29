import pandas as pd
from fpdf import FPDF
from datetime import datetime
import locale
import calendar

# Diccionario español-inglés con orden
MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def extraer_mes_orden(mes_str):
    """
    Convierte un string tipo 'Abril 2024' a un número que represente su orden cronológico: 2024.04
    """
    try:
        nombre_mes, año = mes_str.lower().split()
        numero_mes = MESES_ES.get(nombre_mes, 0)
        return int(año) * 100 + numero_mes  # Ej: Abril 2024 => 202404
    except:
        return 0  # En caso de error o formato raro

def preparar_datos(df):
    df = df.copy()

    # Asegurarse de que la columna 'Mes' está en formato datetime
    df["Mes"] = pd.to_datetime(df["Mes"], dayfirst=True)

    # Añade columna de orden
    df["Mes_orden"] = df["Mes"]
    
    # Total de gasto (si no existe)
    categorias = [
        "Hipoteca", "Impuestos", "Luz", "Gas", "Agua", "Internet",
        "Escuela", "Acogida", "Inglés", "Comedor", "Natación",
        "Tarjeta DB", "Otros"
    ]
    df["Total de gasto"] = df[categorias].sum(axis=1)

    # Total de ingreso
    if "Ingresado a cuenta" in df.columns:
        df["Total de ingreso"] = df["Ingresado a cuenta"]
    else:
        df["Total de ingreso"] = 0

    df = df.sort_values("Mes_orden").reset_index(drop=True)
    return df

# Para sistemas Windows que no acepten "es_ES.UTF-8", puedes comentar esta línea si da error
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except:
    pass  # Si falla en Windows, no revienta la app

# Carga el Excel y corrige cabecera + NaNs
def cargar_datos(ruta_excel):
    df = pd.read_excel(ruta_excel)
    df.columns.values[0] = "Mes"  # Renombra la primera columna a "Mes"
    df = df.fillna(0)  # Reemplaza valores vacíos por 0
    return df

# Convierte el texto tipo "Mayo 2025" a fecha real para ordenarlo cronológicamente
def convertir_mes(mes_texto):
    try:
        return datetime.strptime(mes_texto, "%B %Y")
    except:
        return None

# Prepara el DataFrame para mostrar en la app
def preparar_datos(df):
    df = df.copy()

    # Categorías de gasto que se suman
    categorias = [
        "Hipoteca", "Impuestos", "Luz", "Gas", "Agua", "Internet",
        "Escuela", "Acogida", "Inglés", "Comedor", "Natación",
        "Tarjeta DB", "Otros"
    ]

    # Total de gasto por fila
    df["Total de gasto"] = df[categorias].sum(axis=1)

    # Renombrar columna si existe
    df["Mes"] = df["Mes"].astype(str)
    if "Ingresado a cuenta" in df.columns:
        df["Total de ingreso"] = df["Ingresado a cuenta"]
    else:
        df["Total de ingreso"] = 0

    # Añade columna de fecha real para ordenarlo correctamente
    df["Mes_orden"] = df["Mes"].apply(convertir_mes)
    df = df.sort_values("Mes_orden").reset_index(drop=True)

    return df

# Generador de PDF con el resumen de gastos
def generar_pdf_resumen(ultimo_mes, top_caros, top_baratos, totales_categoria):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    hoy = datetime.now().strftime("%d/%m/%Y")
    pdf.cell(200, 10, txt=f"Resumen de gastos generado el {hoy}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Resumen del último mes", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Ingresado: {ultimo_mes['Total de ingreso']:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Gasto total: {ultimo_mes['Total de gasto']:.2f} EUR", ln=True)
    pdf.cell(200, 10, txt=f"- Balance: {(ultimo_mes['Total de ingreso'] - ultimo_mes['Total de gasto']):.2f} EUR", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Top 3 meses más caros:", ln=True)
    pdf.set_font("Arial", size=12)
    for _, row in top_caros.iterrows():
        pdf.cell(200, 10, txt=f"{row['Mes']}: {row['Total de gasto']:.2f} EUR", ln=True)

    pdf.ln(2)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Top 3 meses más baratos:", ln=True)
    pdf.set_font("Arial", size=12)
    for _, row in top_baratos.iterrows():
        pdf.cell(200, 10, txt=f"{row['Mes']}: {row['Total de gasto']:.2f} EUR", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt="Gasto acumulado por categoría:", ln=True)
    pdf.set_font("Arial", size=12)
    for cat, valor in totales_categoria.items():
        pdf.cell(200, 10, txt=f"{cat}: {valor:.2f} EUR", ln=True)

    return pdf.output(dest='S').encode('latin-1')