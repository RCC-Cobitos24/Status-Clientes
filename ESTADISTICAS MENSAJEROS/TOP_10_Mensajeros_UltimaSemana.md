# Top 10 Mejores Mensajeros - Última Semana

## Estructura de Datos Identificada

### Tabla Principal: FacDatos1
- **Campos disponibles:**
  - Fecha (DateTime)
  - Usuario (Mensajero)
  - Estadística (Tipo de operación)
  - Valor (Cantidad)

### Estadísticas Relevantes (Entregas y Recogidas Finalizadas):
- ` Entregas finalizadas`
- ` Recogidas finalizadas`
- ` Bultos entregados`
- ` Bultos recogidos`
- ` Bultos recogidos y entregados`

### Período: Última Semana Completa
- Se identifica usando `Fecha[AñoSemanaNum]` = máximo valor disponible

## Consulta DAX Recomendada

```dax
DEFINE
    VAR MaxWeek = MAXX(ALL(Fecha[Año], Fecha[SemanaNum]), Fecha[AñoSemanaNum])
    VAR LastWeekData = 
        FILTER(
            FacDatos1,
            Fecha[AñoSemanaNum] = MaxWeek
            && FacDatos1[Estadística] IN 
            {
                " Entregas finalizadas",
                " Recogidas finalizadas",
                " Bultos entregados",
                " Bultos recogidos"
            }
        )

EVALUATE
    TOPN(10,
        SUMMARIZE(
            LastWeekData,
            dimUsuario Mensajero[Mensajero],
            "Entregas_Finalizadas", 
                SUMX(
                    FILTER(LastWeekData, FacDatos1[Estadística] IN {" Entregas finalizadas", " Bultos entregados"}),
                    FacDatos1[Valor]
                ),
            "Recogidas_Finalizadas",
                SUMX(
                    FILTER(LastWeekData, FacDatos1[Estadística] IN {" Recogidas finalizadas", " Bultos recogidos"}),
                    FacDatos1[Valor]
                ),
            "Total_Operaciones",
                SUMX(LastWeekData, FacDatos1[Valor])
        ),
        [Total_Operaciones],
        DESC
    )
ORDER BY [Total_Operaciones] DESC
```

## Para Ejecutar

1. **En Power BI Desktop:**
   - Abrir el archivo `PRY Estadisticas Mensajeros v2.pbip`
   - View → DAX Query Editor
   - Copiar la consulta anterior

2. **Mediante conexión MCP:**
   - Ya estamos conectados al modelo
   - Se puede crear una tabla calculada con esta expresión
   - O crear un reporte que visualice estos datos

## Relaciones del Modelo

- **FacDatos1** ← (Usuario) → **dimUsuario Mensajero**
- **FacDatos1** ← (Fecha) → **Fecha**
- **FacDatos1** ← (Estadística) → **dimEstadísticas**

## Notas Importantes

⚠️ Todos los valores de Estadística incluyen un espacio al inicio: " Entregas finalizadas"
⚠️ La tabla Fecha tiene la jerarquía A-S-D (Año-Semana-Día) disponible
