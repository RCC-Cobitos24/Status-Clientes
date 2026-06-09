# TOP 10 MEJORES MENSAJEROS - ÚLTIMA SEMANA
## Entregas y Recogidas Finalizadas

**Documento de Referencia para Consulta DAX**

---

## 📋 INSTRUCCIONES PARA EJECUTAR EN POWER BI DESKTOP

### Paso 1: Abrir el Editor DAX
1. Abre el archivo: `PRY Estadisticas Mensajeros v2.pbip`
2. Ve a: **Inicio** → **Consultar datos (New Query)** o **Ver** → **Explorador de consultas**
3. Selecciona: **Nueva consulta DAX** o **DAX Query Editor**

### Paso 2: Copiar la Consulta
Copia toda la consulta DAX siguiente (sección "CONSULTA DAX"):

### Paso 3: Ejecutar
- Haz clic en **Ejecutar** (Run)
- Los resultados se mostrarán en una tabla

---

## 🔍 CONSULTA DAX

```dax
EVALUATE
ROW(
    "Período", "Última Semana Completa",
    "Estadísticas", "Entregas Finalizadas + Recogidas Finalizadas",
    "Total Registros", COUNTA(dimUsuario Mensajero[Mensajero])
)

EVALUATE
TOPN(
    10,
    ADDCOLUMNS(
        SUMMARIZE(
            FILTER(
                FacDatos1,
                Fecha[AñoSemanaNum] = MAXX(ALL(Fecha[Año], Fecha[SemanaNum]), Fecha[AñoSemanaNum])
            ),
            dimUsuario Mensajero[Mensajero]
        ),
        "Entregas_Finalizadas",
        SUMX(
            FILTER(
                FacDatos1,
                Fecha[AñoSemanaNum] = MAXX(ALL(Fecha[Año], Fecha[SemanaNum]), Fecha[AñoSemanaNum])
                && FacDatos1[Estadística] = " Entregas finalizadas"
                && dimUsuario Mensajero[Mensajero] = EARLIER(dimUsuario Mensajero[Mensajero])
            ),
            FacDatos1[Valor]
        ),
        "Recogidas_Finalizadas",
        SUMX(
            FILTER(
                FacDatos1,
                Fecha[AñoSemanaNum] = MAXX(ALL(Fecha[Año], Fecha[SemanaNum]), Fecha[AñoSemanaNum])
                && FacDatos1[Estadística] = " Recogidas finalizadas"
                && dimUsuario Mensajero[Mensajero] = EARLIER(dimUsuario Mensajero[Mensajero])
            ),
            FacDatos1[Valor]
        ),
        "Total",
        [Entregas_Finalizadas] + [Recogidas_Finalizadas]
    ),
    [Total],
    DESC
)
```

---

## 📊 ESTRUCTURA DE RESULTADOS

| Columna | Tipo | Descripción |
|---------|------|-------------|
| Mensajero | Texto | Nombre/ID del mensajero |
| Entregas_Finalizadas | Número | Total de entregas finalizadas en la semana |
| Recogidas_Finalizadas | Número | Total de recogidas finalizadas en la semana |
| Total | Número | Entregas + Recogidas |

---

## 🔗 RELACIONES DE DATOS

```
FacDatos1 (Hechos)
├── Usuario ──→ dimUsuario Mensajero[Usuario]
├── Fecha ──→ Fecha[Fecha]
└── Estadística ──→ dimEstadísticas[Estadística]
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Espacios en Estadística**: Los valores de estadística incluyen un espacio al inicio
   - ✓ Correcto: `" Entregas finalizadas"`
   - ✗ Incorrecto: `"Entregas finalizadas"`

2. **Período**: Se calcula automáticamente la última semana completa disponible en los datos
   - Basado en: `Fecha[AñoSemanaNum]` = máximo valor

3. **Valores a Incluir**:
   - ` Entregas finalizadas`
   - ` Recogidas finalizadas`
   - También disponibles: ` Bultos entregados`, ` Bultos recogidos`

---

## 📁 UBICACIONES DE ARCHIVOS

- **Modelo Semántico**: `PRY Estadisticas Mensajeros v2.SemanticModel`
- **Consulta DAX**: `DAXQueries/Top10_Mensajeros_UltimaSemana.dax`
- **Tabla de Datos**: `FacDatos1` (origen: carpeta de datos)

---

## 🚀 ALTERNATIVA: CREAR TABLA CALCULADA EN EL MODELO

Si prefieres persistir estos datos en el modelo:

1. En el Semantic Model, crear una nueva tabla con:
   ```
   Nombre: Top_10_Mensajeros_Semana
   ```

2. Usar la consulta DAX anterior como expresión DAX

3. Guardar el modelo

---

**Última actualización**: 2026-06-09
**Modelo**: PRY Estadísticas Mensajeros v2
**Conexión MCP**: Activa
