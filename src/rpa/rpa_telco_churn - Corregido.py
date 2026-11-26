#!/usr/bin/env python3
"""
RPA: Extracción y actualización automática de los datos (Customer Churn)
Proyecto Final de Ciencia de Datos - Opción A

Este script es el robot. Cada vez que se ejecuta hace 5 pasos:
  1. Descarga el dataset desde Kaggle (con reintentos).
  2. Valida que el archivo esté bien.
  3. Prepara los datos (arreglo mínimo para Power BI: TotalCharges en blanco = cargo mensual).
  4. Guarda una copia histórica y el archivo que lee Power BI.
  5. Anota lo que pasó en la bitácora.

Cómo ejecutarlo:
    python rpa_telco_churn.py

Código de salida (importante para GitHub Actions y el Programador de tareas):
    0 = la ejecución fue exitosa
    1 = hubo un error (el archivo de Power BI NO se modificó)
"""

import argparse
import filecmp
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import kagglehub
except ImportError:
    sys.exit("Falta la librería kagglehub. Instálala con: pip install -r requirements.txt")

# ----------------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------------

# Las rutas se calculan a partir de la carpeta donde está este script, así el
# robot funciona igual sin importar desde dónde se ejecute (GitHub, Windows...).
BASE = Path(__file__).resolve().parent

# De dónde se descargan los datos (Kaggle)
DATASET_KAGGLE = "blastchar/telco-customer-churn"
ARCHIVO_EN_KAGGLE = "WA_Fn-UseC_-Telco-Customer-Churn.csv"

# Dónde se guardan
CARPETA_CRUDOS = BASE / "datos" / "crudos"
CARPETA_PROCESADOS = BASE / "datos" / "procesados"
ARCHIVO_POWER_BI = CARPETA_PROCESADOS / "telco_churn_actualizado.csv"
ARCHIVO_BITACORA = BASE / "datos" / "bitacora_ejecuciones.csv"

# Cómo debe ser un archivo correcto
COLUMNAS_ESPERADAS = ["customerID", "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
                      "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
                      "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
                      "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges", "Churn"]
MINIMO_DE_FILAS = 1000

# Cuántas veces intenta descargar si falla, y cuántos segundos espera entre intentos
INTENTOS = 3
SEGUNDOS_DE_ESPERA = 5


# ----------------------------------------------------------------------------
# Paso 1: Descargar los datos
# ----------------------------------------------------------------------------
def descargar_datos(dataset, segundos_de_espera=SEGUNDOS_DE_ESPERA):
    for intento in range(1, INTENTOS + 1):
        try:
            print("Intento", intento, "de", INTENTOS, "-> descargando desde Kaggle...")

            # Kaggle descarga el dataset y nos dice en qué carpeta lo dejó
            carpeta_descarga = kagglehub.dataset_download(dataset, force_download=True)
            ruta_archivo = os.path.join(carpeta_descarga, ARCHIVO_EN_KAGGLE)

            # Confirmamos que el archivo que esperamos está en la descarga
            if os.path.exists(ruta_archivo):
                print("Descarga exitosa.")
                return ruta_archivo

            print("La descarga no trajo el archivo", ARCHIVO_EN_KAGGLE)

        except Exception as error:
            print("No se pudo descargar:", error)

        # Si no es el último intento, esperamos antes de volver a intentar
        if intento < INTENTOS:
            time.sleep(segundos_de_espera)

    # Si llegamos aquí es porque fallaron todos los intentos
    raise Exception("No se pudo descargar el dataset de Kaggle después de " + str(INTENTOS) + " intentos")


# ----------------------------------------------------------------------------
# Paso 2: Validar los datos
# ----------------------------------------------------------------------------
def validar_datos(df):
    # 1. Revisamos las columnas
    columnas_faltantes = []
    for columna in COLUMNAS_ESPERADAS:
        if columna not in df.columns:
            columnas_faltantes.append(columna)

    if len(columnas_faltantes) > 0:
        raise Exception("Faltan columnas en el archivo: " + str(columnas_faltantes))

    # 2. Revisamos la cantidad de filas
    if len(df) < MINIMO_DE_FILAS:
        raise Exception("El archivo tiene muy pocas filas: " + str(len(df)))

    # 3. Revisamos que no haya clientes repetidos
    repetidos = df["customerID"].duplicated().sum()
    if repetidos > 0:
        raise Exception("Hay " + str(repetidos) + " códigos de cliente repetidos")

    # 4. Revisamos los valores de Churn
    for valor in df["Churn"].unique():
        if valor not in ["Yes", "No"]:
            raise Exception("La columna Churn tiene un valor que no esperábamos: " + str(valor))

    print("Validación correcta: el archivo tiene", len(df), "filas y", len(df.columns), "columnas.")


# ----------------------------------------------------------------------------
# Paso 3: Preparar los datos
# ----------------------------------------------------------------------------
def preparar_datos(df, fecha_hora):
    df = df.copy()

    # Convertimos TotalCharges a número; los espacios en blanco (clientes nuevos que
    # todavía no tienen cargos) toman el mismo valor de su cargo mensual
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df["TotalCharges"] = df["TotalCharges"].fillna(df["MonthlyCharges"])

    # Agregamos la fecha de actualización
    df["FechaActualizacion"] = fecha_hora.strftime("%Y-%m-%d %H:%M:%S")

    print("Datos preparados.")
    return df


# ----------------------------------------------------------------------------
# Paso 4: Guardar los datos
# ----------------------------------------------------------------------------
def comparar_con_version_anterior(df_nuevo):
    # Si no existe un archivo anterior, es la primera vez que se ejecuta
    if not ARCHIVO_POWER_BI.exists():
        return "Primera carga"

    df_anterior = pd.read_csv(ARCHIVO_POWER_BI)

    clientes_antes = set(df_anterior["customerID"])
    clientes_ahora = set(df_nuevo["customerID"])

    nuevos = len(clientes_ahora - clientes_antes)
    eliminados = len(clientes_antes - clientes_ahora)

    if nuevos == 0 and eliminados == 0:
        return "Sin cambios en los clientes"
    return str(nuevos) + " clientes nuevos y " + str(eliminados) + " clientes que ya no aparecen"


def guardar_datos(ruta_descargada, df_preparado, fecha_hora):
    # 1. Copia histórica, tal como se descargó de Kaggle.
    #    Si el archivo es idéntico a la última copia guardada, no se repite: así el
    #    repositorio de GitHub no se llena de copias iguales cada semana.
    copias = sorted(CARPETA_CRUDOS.glob("telco_churn_*.csv"))
    if copias and filecmp.cmp(ruta_descargada, copias[-1], shallow=False):
        print("Copia histórica: el archivo es idéntico a la última copia (" + copias[-1].name + "), no se repite.")
    else:
        nombre_crudo = CARPETA_CRUDOS / ("telco_churn_" + fecha_hora.strftime("%Y-%m-%d_%H%M%S") + ".csv")
        shutil.copy(ruta_descargada, nombre_crudo)
        print("Copia histórica guardada en:", nombre_crudo.relative_to(BASE))

    # 2. Archivo para Power BI (reemplaza al anterior)
    df_preparado.to_csv(ARCHIVO_POWER_BI, index=False)
    print("Archivo para Power BI actualizado:", ARCHIVO_POWER_BI.relative_to(BASE))


# ----------------------------------------------------------------------------
# Paso 5: Anotar en la bitácora
# ----------------------------------------------------------------------------
def anotar_en_bitacora(fecha_hora, resultado, filas, clientes_abandono, detalle):
    linea = pd.DataFrame([{
        "FechaHora": fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
        "Resultado": resultado,
        "Filas": filas,
        "ClientesQueAbandonaron": clientes_abandono,
        "Detalle": detalle
    }])

    # Si la bitácora ya existe, agregamos la línea al final. Si no existe, la creamos.
    if ARCHIVO_BITACORA.exists():
        linea.to_csv(ARCHIVO_BITACORA, mode="a", header=False, index=False)
    else:
        linea.to_csv(ARCHIVO_BITACORA, index=False)


# ----------------------------------------------------------------------------
# El robot completo
# ----------------------------------------------------------------------------
def ejecutar_rpa(dataset=DATASET_KAGGLE, segundos_de_espera=SEGUNDOS_DE_ESPERA):
    """Ejecuta los 5 pasos. Devuelve True si salió bien y False si hubo un error."""
    fecha_hora = datetime.now()
    print("===== INICIO DEL ROBOT:", fecha_hora.strftime("%Y-%m-%d %H:%M:%S"), "=====")

    try:
        # Paso 1: descargar
        ruta_descargada = descargar_datos(dataset, segundos_de_espera)
        df = pd.read_csv(ruta_descargada)

        # Paso 2: validar
        validar_datos(df)

        # Paso 3: preparar
        df_preparado = preparar_datos(df, fecha_hora)

        # Paso 4: comparar con la versión anterior y guardar
        detalle = comparar_con_version_anterior(df_preparado)
        guardar_datos(ruta_descargada, df_preparado, fecha_hora)

        # Paso 5: anotar en la bitácora
        clientes_abandono = int((df_preparado["Churn"] == "Yes").sum())
        anotar_en_bitacora(fecha_hora, "EXITOSO", len(df_preparado), clientes_abandono, detalle)
        fecha_fin = datetime.now()
        print("===== FIN DEL ROBOT:", fecha_fin.strftime("%Y-%m-%d %H:%M:%S"), "- EJECUCIÓN EXITOSA (" + detalle + ") =====")
        return True

    except Exception as error:
        # Si algo falla, no se toca el archivo de Power BI y se anota el error
        anotar_en_bitacora(fecha_hora, "ERROR", 0, 0, str(error))
        fecha_fin = datetime.now()
        print("===== FIN DEL ROBOT:", fecha_fin.strftime("%Y-%m-%d %H:%M:%S"), "- HUBO UN ERROR ->", error, "=====")
        print("El archivo de Power BI NO se modificó. Se mantiene la última versión buena.")
        return False


def main():
    parser = argparse.ArgumentParser(description="RPA de datos - Telco Customer Churn")
    parser.add_argument("--dataset", default=DATASET_KAGGLE,
                        help="Dataset de Kaggle a descargar (por defecto: " + DATASET_KAGGLE + ")")
    parser.add_argument("--espera", type=int, default=SEGUNDOS_DE_ESPERA,
                        help="Segundos de espera entre reintentos (por defecto: " + str(SEGUNDOS_DE_ESPERA) + ")")
    args = parser.parse_args()

    # En GitHub Actions, un secreto que no se configuró llega como texto vacío.
    # Lo quitamos para que kagglehub se comporte como si no hubiera credenciales
    # (el dataset es público y se puede descargar sin ellas).
    for variable in ("KAGGLE_USERNAME", "KAGGLE_KEY", "KAGGLE_API_TOKEN"):
        if variable in os.environ and not os.environ[variable].strip():
            del os.environ[variable]

    CARPETA_CRUDOS.mkdir(parents=True, exist_ok=True)
    CARPETA_PROCESADOS.mkdir(parents=True, exist_ok=True)

    exito = ejecutar_rpa(args.dataset, args.espera)

    # El código de salida le dice a GitHub (o al Programador de tareas) si falló.
    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    main()
