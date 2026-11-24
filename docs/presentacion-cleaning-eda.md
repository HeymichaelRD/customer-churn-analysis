# Guion de presentación: equipo Limpieza y EDA

**Autor:** Bryan Abreu · 22 de noviembre de 2026

**Integrantes:** Bryan Abreu, Jhonfrer Villar y Leonis Matos

**Duración sugerida:** de 5 a 7 minutos. Se muestran el notebook [`notebooks/02_eda_bryan.ipynb`](../notebooks/02_eda_bryan.ipynb) y el script [`src/cleaning/clean_data.py`](../src/cleaning/clean_data.py).

---

## Paso 1. Qué le toca a nuestro equipo (30 segundos)

- Somos el equipo de Limpieza y EDA: rama `cleaning-eda`, carpetas `src/cleaning/` y `notebooks/`.
- Entregamos tres cosas: los datos limpios para Modelos y la API, el análisis con los hallazgos para la web, y los datos para el dashboard de Power BI.
- Usamos el dataset Telco Customer Churn de IBM: 7,043 clientes y 21 columnas. La variable objetivo es `Churn` (si el cliente se fue).

## Paso 2. Cómo sabemos que la data es la correcta (1 minuto)

**Mostrar:** sección 1 del notebook (Verificación).

- Antes de analizar, comprobamos que el archivo, las filas, las columnas y los valores son los que dicen el README y el contrato de la API.
- También revisamos las reglas de coherencia: ningún cliente sin teléfono tiene líneas múltiples, ninguno sin internet tiene servicios de internet, y todos tienen al menos uno de los dos.
- Si algo no cuadra, el código se detiene con un error y no seguimos con datos equivocados.

## Paso 3. Qué limpiamos y por qué (1 minuto)

**Mostrar:** `clean_data.py` y, si se puede, correrlo en vivo con `python src/cleaning/clean_data.py`.

- No hay duplicados ni nulos. El único problema es `TotalCharges`: venía como texto y tenía 11 valores vacíos.
- Los 11 vacíos son clientes con `tenure` 0, es decir, recién llegados que todavía no han pagado nada.
- **Criterio:** los llenamos con 0 y no los borramos, porque son clientes reales y la API va a recibir clientes nuevos con ese mismo caso.
- **Criterio:** la limpieza solo toca `TotalCharges`. El resto de columnas queda igual que el original para no romper el contrato de la API ni el modelo.
- El script tiene 6 pasos: cargar, verificar, limpiar, verificar el resultado, guardar el CSV limpio y guardar los datos para el dashboard.

## Paso 4. Los hallazgos (2 minutos)

**Mostrar:** secciones 4, 6, 7 y 8 del notebook.

1. Se fue el 26.5% de los clientes, y con ellos US$139,131 al mes, el 30.5% del ingreso.
2. El contrato es el factor más fuerte: mes a mes se va el 42.7%, con un año el 11.3% y con dos años solo el 2.8%.
3. El primer año es el más riesgoso: se va el 47.4% de los que tienen 12 meses o menos, contra el 9.5% de los que llevan más de 4 años.
4. La fibra óptica (41.9%) y el pago con cheque electrónico (45.3%) se relacionan con más bajas.
5. Entre los clientes con internet, los que no tienen seguridad en línea o soporte técnico se van casi el triple: alrededor de 42% contra 15%.

**Segmento de mayor riesgo:** mes a mes + fibra óptica + 12 meses o menos. Son 916 clientes y se va el 70.2%.

**Aclaración:** hablamos de "se relaciona con" y no de "causa", porque el EDA muestra relaciones, no causas.

## Paso 5. Cómo comprobamos que los cálculos están bien (30 segundos)

**Mostrar:** sección 10 del notebook (Comprobación de las cifras).

- El equipo API y Web había publicado cifras preliminares. Nuestros cálculos dan exactamente lo mismo: 26.5%, US$139,131, 42.7%, 2.8% y 70.2%.
- Las 33 pruebas automáticas del proyecto siguen pasando.

## Paso 6. Cómo se conecta con el resto del proyecto (1 minuto)

- **Modelos:** usa el CSV limpio para entrenar la segmentación con K-Means y el modelo de churn. Les sugerimos estratificar el split, medir con recall y F1, y probar K-Means con `tenure`, `MonthlyCharges` y `Contract`.
- **API y Web:** usan el CSV limpio y nuestros 5 hallazgos para la página de Hallazgos.
- **Dashboard:** usa `data/output/telco_churn_dashboard.csv`, con `churn_flag` y `tenure_group` para mostrar las mismas cifras que la web. Modelos le agrega la columna `segment`.

## Paso 7. Qué queda pendiente (30 segundos)

Los pendientes y su responsable propuesto están en [`plan-cleaning-eda.md`](plan-cleaning-eda.md#pendientes-del-equipo).

---

## Posibles preguntas

| Pregunta | Respuesta |
|---|---|
| ¿Por qué no borraron los `TotalCharges` vacíos? | Porque son clientes reales nuevos, son solo 11 y la API va a recibir ese mismo caso |
| ¿Por qué no eliminaron columnas como `gender`? | Porque, aunque casi no influyen, decidir qué variables usa el modelo le toca al equipo de Modelos, y la API recibe los 19 campos |
| ¿Por qué importa que las clases estén desbalanceadas? | Porque un modelo que diga "nadie se va" acierta el 73.5% y no sirve; por eso se mide con recall |
| ¿El ingreso anual perdido es exacto? | No, es aproximado: supone que esos clientes habrían pagado lo mismo todo el año |
