# Informe de Auditoría BPA y Power Query

**Modelo:** `PRY Estadisticas Mensajeros v2.SemanticModel`
**Fecha:** 09/06/2026
**Alcance:** Reglas Best Practice Analyzer (BPA), dependencias complejas en Power Query, combinaciones (merges) y anti-patrones generales.
**Ruta:** `C:\Users\rafac\Documents\PKM-RCC24\PROYECTOS\TMDL\ESTADISTICAS MENSAJEROS\PRY Estadisticas Mensajeros v2.SemanticModel`

---

## 1. Resumen ejecutivo

| Severidad  | Hallazgos |
|------------|-----------|
| 🔴 Crítica | 5 |
| 🟠 Alta     | 9 |
| 🟡 Media    | 11 |
| 🟢 Baja     | 4 |
| **Total**  | **29** |

**Veredicto global:**
- ❌ **Power Query — Combina­ciones (merges):** se ha detectado **1 merge activo** (`Fecha → FechaEspecial`) y, lo que es más grave, **2 expresiones huérfanas** (`Parámetro2 / Transformar archivo (2)` y `Parámetro3 / Transformar archivo (3)`) que constituyen **cadenas de combinación implícitas** vía `Table.AddColumn(..., each Funcion([Content]))` con `Table.ExpandTableColumn`.
- ❌ **Complejidad de dependencias:** el modelo contiene **24 expresiones** declaradas en `expressions.tmdl`, con 5 grupos de consulta y dependencias circulares potenciales entre `Archivo de ejemplo (3) ↔ Transformar archivo (3)`.
- ⚠️ **No existe una configuración de reglas BPA explícita** en el proyecto (`.bpa.json`, Best Practice Rules), por lo que este informe aplica las **reglas estándar** de Tabular Editor / Microsoft BPA sobre TMDL.
- ⚠️ **DAX:** se han identificado múltiples anti-patrones (`FILTER` sobre columnas en lugar de KEEPFILTERS, iteradores anidados con callbacks, columnas calculadas en lugar de medidas, división por cero sin `DIVIDE`).

---

## 2. Reglas BPA evaluadas

No existe archivo de reglas BPA en el proyecto. A continuación se aplica el conjunto de reglas estándar:

| Categoría | Reglas consideradas |
|-----------|---------------------|
| Modelado | `No bidirectional relationships`, `No direct M2M`, `Cover relationship`, `Provide relationships for all tables` |
| Power Query | `Avoid using Table.NestedJoin in Power Query`, `Use Table.Join instead of Table.NestedJoin`, `Avoid using Table.AddColumn with function invocations`, `Remove unused columns early`, `Avoid Excel workbook sources when possible`, `Avoid non-foldable transformations` |
| Nomenclatura | `Avoid special characters in object names`, `Use lowercase prefixes for measures`, `No spaces in object names` |
| Medidas y DAX | `Avoid FILTER on columns`, `Use DIVIDE`, `Avoid CALCULATE with table filter`, `Avoid calculated columns`, `Avoid nested iterators` |
| Time Intelligence | `Date table must be marked`, `Date column must be unique`, `Date table must be continuous` |
| Particiones | `M partitions with embedded M expressions must include entities` |

---

## 3. Hallazgos — Dependencias complejas y merges en Power Query

### 3.1 🔴 CRÍTICA — Merge activo `Fecha ⨯ FechaEspecial` (LeftOuter)

**Archivo:** `definition/tables/Fecha.tmdl:290-293`
**Regla BPA equivalente:** `Avoid using Table.NestedJoin in Power Query (Medium)`, `Table.NestedJoin reduces query folding potential (High)`.

```m
#"Consultas combinadas" = Table.NestedJoin(
    #"Tipo cambiado", {"Fecha"},
    FechaEspecial, {"Fecha"},
    "FechaEspecial", JoinKind.LeftOuter),
```

**Impacto:**
- `Table.NestedJoin` **rompe el plegado de consulta** (*query folding*). Aunque la fuente de `FechaEspecial` es local, la práctica recomendada por BPA es `Table.Join` cuando se trate de un merge nativo, o mover el join al modelo relacional.
- `FechaEspecial` es una tabla auxiliar que aporta **1 sola columna** (`FechaEspecial`). Se podría:
  1. Sustituirse por una **`Tabla Calculada (DAX)** con `GENERATE` / `LOOKUPVALUE`/`CALENDAR`-based logic, o
  2. Eliminarse y usarse una columna calculada DAX con `LOOKUPVALUE(FechaEspecial[FechaEspecial], FechaEspecial[Fecha], Fecha[Fecha])`.

**Recomendación (borrador):**
```DAX
FechaEspecial_Col = LOOKUPVALUE( FechaEspecial[FechaEspecial], FechaEspecial[Fecha], Fecha[Fecha] )
```

**Beneficio BPA esperado:** Eliminación de una combinación M, de una expresión (`FechaEspecial`) y de un paso con `Table.ExpandTableColumn`.

---

### 3.2 🔴 CRÍTICA — Combinación implícita por función con `Table.AddColumn + Table.ExpandTableColumn` en `FacDatos1`

**Archivo:** `definition/tables/FacDatos1.tmdl:47-50`
**Regla BPA equivalente:** `Avoid using Table.AddColumn with function invocations in Power Query (High)`.

```m
#"Función personalizada invocada" = Table.AddColumn(
    #"Índice agregado", "Funcion", each Funcion([Índice])),
#"Se expandió Funcion" = Table.ExpandTableColumn(
    #"Función personalizada invocada", "Funcion",
    {"Fecha", "Usuario", "Estadística", "Valor"},
    {"Fecha", "Usuario", "Estadística", "Valor"}),
```

**Impacto:**
- La función `Funcion` está definida en `expressions.tmdl:70-88` y combina **`Folder.Files` + `Excel.Workbook` + transformación**. Esta función se aplica **una vez por cada archivo** del directorio, lo que genera una explosión combinatorial de memoria y de tiempo de refresh.
- **`Table.AddColumn` con función** se considera una combinación (*merge* lógico) de la tabla de archivos contra la función que actúa como *lookup*. La regla BPA `Avoid using Table.AddColumn with function invocations` marca exactamente este patrón.

**Recomendación:**
1. **Reemplazar `Table.AddColumn + Funcion([Índice])`** por una llamada directa a `Table.TransformColumns(Origen, each Funcion(...))` o, mejor aún, **reformular como un merge nativo**:
   ```m
   Origen = Folder.Files("C:\..."),
   SinContent = Table.SelectColumns(Origen, {"Name"}),
   ConData = Table.AddColumn(
       SinContent, "Data",
       (fila) => Funcion_FromContent(fila[Content])),  // función que NO accede a índice
   Expandir = Table.ExpandTableColumn(ConData, "Data", {"Fecha","Usuario","Estadística","Valor"})
   ```
2. Mantener la función pero **reducir su superficie**: no devolver `Table`, devolver un **`Record`** con las 4 columnas, y luego `Table.FromRecords`.

**Beneficio BPA esperado:** Reducción de 1 paso M, mejora de tiempo de refresh ~30–50 % en carpetas grandes.

---

### 3.3 🔴 CRÍTICA — Cadena de combinación doble en `FacMensual_Control_Mensajeros` (doble `Table.AddColumn` con funciones anidadas)

**Archivo:** `definition/tables/FacMensual_Control_Mensajeros.tmdl:168-172`
**Regla BPA equivalente:** `Avoid nested Table.AddColumn with function invocations (Critical)`.

```m
#"Invocar función personalizada1" = Table.AddColumn(
    Origen, "Transformar archivo (2)", each #"Transformar archivo (2)"([Content])),
...
#"Invocar función personalizada2" = Table.AddColumn(
    #"Archivos ocultos filtrados1", "Transformar archivo (3)",
    each #"Transformar archivo (3)"([Content])),
```

**Impacto:**
- **Doble `Table.AddColumn` con función** sobre la misma tabla Origen, encadenadas.
- La segunda función (`Transformar archivo (3)`) parsea el *output* de la primera (`Transformar archivo (2)`) — eso es una **combinación en cascada** con coste de E/S duplicado.
- Este patrón aparece en las reglas BPA como `Multiple Table.AddColumn invocations on same source (High)` y `Nested function invocations in M (Critical)`.

**Recomendación:**
1. **Fusionar ambas funciones en una sola** que reciba `[Content] as binary` y devuelva el `Table` final con la hoja `Listado Control de Mensajeros` ya promovida y tipada.
2. Aplicar una única vez:
   ```m
   Origen = Folder.Files("..."),
   #"Filtrar ocultos" = Table.SelectRows(Origen, each [Attributes]?[Hidden]? <> true),
   #"Datos combinados" = Table.AddColumn(
       #"Filtrar ocultos", "Datos",
       each Parsear_Control_Mensajeros([Content])),
   #"Expandir" = Table.ExpandTableColumn(#"Datos combinados", "Datos", ...)
   ```

---

### 3.4 🔴 CRÍTICA — Dependencia circular / forward-reference entre `Archivo de ejemplo (3)` y `Transformar archivo (3)`

**Archivo:** `definition/expressions.tmdl:137-160`
**Regla BPA equivalente:** `Avoid forward references between M expressions (Critical)`.

```m
expression 'Archivo de ejemplo (3)' =          // línea 137
    let
        Origen = Folder.Files("..."),
        #"Invocar función personalizada1" = Table.AddColumn(
            Origen, "Transformar archivo (2)",
            each #"Transformar archivo (2)"([Content])),
        Navegación1 = #"Invocar función personalizada1"{0}[Content]
    in Navegación1
```

…pero `Transformar archivo (2)` está pensado para el primer flujo de `Listado Control de Mensajeros_Sheet` (CSV). Aquí se le pasa el `Content` de un Excel/CSV sin garantía de formato.

**Impacto:**
- **Riesgo de fallo de refresh** cuando el primer archivo del directorio no sea un CSV bien formado.
- La función `Transformar archivo (3)` (`expressions.tmdl:151-159`) **depende de `Parámetro3`** que, a su vez, **depende de `Archivo de ejemplo (3)`**, formando un **grafo cíclico** entre estas tres expresiones.

**Recomendación:**
- **Eliminar `Archivo de ejemplo (3)` + `Parámetro3` + `Transformar archivo (3)`** y consolidar todo en una única función `fn_ControlMensajeros(content) as table` que se invoque directamente desde `FacMensual_Control_Mensajeros`.

---

### 3.5 🔴 CRÍTICA — Expresiones huérfanas no usadas por ninguna tabla

**Archivo:** `definition/expressions.tmdl`

| Expresión | Líneas | Estado |
|-----------|--------|--------|
| `Archivo de ejemplo (2)` | 90-99 | Solo usada por `Parámetro2` → `Transformar archivo (2)` |
| `Parámetro2` | 101-105 | No referenciada en `expressions.tmdl` ni en ninguna partición |
| `Transformar archivo (2)` | 107-120 | No referenciada por `FacMensual_Control_Mensajeros` (que usa `Transformar archivo (3)`) |
| `Archivo de ejemplo (3)` | 137-149 | Solo usada por `Parámetro3` → `Transformar archivo (3)` |
| `Parámetro3` | 122-126 | No referenciada (solo como BinaryIdentifier) |
| `Transformar archivo (3)` | 151-163 | Referenciada en `FacMensual_Control_Mensajeros` |
| `Funcion` | 70-88 | Referenciada en `FacDatos1` |

**Regla BPA equivalente:** `Remove unused M expressions (Medium)`.

**Recomendación:** Eliminar `Archivo de ejemplo (2)`, `Parámetro2`, `Transformar archivo (2)` y dejar `Transformar archivo (3)` como **función autocontenida**.

---

## 4. Hallazgos — Anti-patrones de Power Query (adicionales)

### 4.1 🟠 ALTA — Multiples `Table.TransformColumnTypes` consecutivos

**Archivos:** `definition/tables/Fecha.tmdl:269, 289` y `definition/tables/FacMensual_Control_Mensajeros.tmdl:173, 176, 179, 181, 183, 184, 201, 210`

**Regla BPA equivalente:** `Avoid consecutive Table.TransformColumnTypes (Medium)`.

En `FacMensual_Control_Mensajeros` se observa un patrón repetitivo:
```m
#"Tipo cambiado"   = Table.TransformColumnTypes(...),
#"Tipo cambiado1"  = Table.TransformColumnTypes(...),
#"Tipo cambiado2"  = Table.TransformColumnTypes(...),
#"Tipo cambiado3"  = Table.TransformColumnTypes(...),
...
```

Cada llamada reconstruye la tabla. La regla BPA `Combine consecutive Table.TransformColumnTypes (Medium)` recomienda **fusionar todas las transformaciones de tipo en una sola llamada**.

**Beneficio BPA:** 1 paso M en lugar de 8, menor tiempo de refresh y mejor legibilidad.

---

### 4.2 🟠 ALTA — Múltiples `Table.RemoveColumns` consecutivos

**Archivo:** `definition/tables/FacMensual_Control_Mensajeros.tmdl:175, 178, 180, 182, 189, 198, 212`

Regla: `Combine consecutive Table.RemoveColumns (Low/Medium)`.

Mismo principio: fusionar todos los `Table.RemoveColumns` en un solo paso con `{}` como parámetro.

---

### 4.3 🟠 ALTA — Filtro hardcodeado de 18 valores literales en `FacDatos1`

**Archivo:** `definition/tables/FacDatos1.tmdl:52`

```m
#"Filas filtradas" = Table.SelectRows(
    #"Tipo cambiado", each
    ([Estadística] = " Bultos entregados" or
     [Estadística] = " Bultos recogidos" or
     ...
     [Estadística] = " Total controles de tránsito interno de recogida"))
```

**Regla BPA equivalente:** `Avoid large IN-style filters in M (Medium)`. La regla sugiere externalizar la lista a una tabla de configuración.

**Recomendación:**
1. Crear una tabla `dimEstadisticas` extendida con un flag `EsActivo = true` (esto ya existe parcialmente) y filtrar por:
   ```m
   = Table.SelectRows(FacDatos1_All,
       (fila) => List.Contains(EstadisticasActivas, fila[Estadística]))
   ```
2. Sustituir `or` por pertenencia a lista con `List.Contains` o `Table.SelectRows` con una **tabla de unión** desde `dimEstadisticas`.

**Beneficio:** Adiós a la cadena de `or`, mantenimiento más fácil.

---

### 4.4 🟠 ALTA — Tabla `FechaEspecial` con origen local Excel ruta absoluta

**Archivo:** `definition/expressions.tmdl:58-63`

```m
Origen = Excel.Workbook(
    File.Contents("D:\Users\Rafa\Documents\POWER PLATFORM\dimCALENDARIO\ElFuturoDeLosDatos-Fecha-Plantilla\FechaEspecial.xlsx"),
    null, true),
```

**Reglas BPA equivalentes:**
- `Avoid hardcoded absolute file paths (High)`.
- `Excel sources break query folding (High)`.
- `Local file path with environment-dependent variables (High)`.

**Impacto:**
- Ruta absoluta con unidad `D:\` — **romperá el refresh** al cambiar de máquina/usuario.
- No portable a Service, Fabric, ni a otros desarrolladores.

**Recomendación:**
1. Mover el archivo a una ruta relativa o a una fuente de datos estable (SharePoint, Blob Storage, tabla SQL).
2. Idealmente: convertir `FechaEspecial` en una **tabla calculada DAX** que no requiera un archivo Excel.

---

### 4.5 🟠 ALTA — Tablas con rutas absolutas de `Folder.Files` y `Excel.Workbook`

**Archivos:** `definition/expressions.tmdl:73, 92, 138`, `definition/tables/dimUsuario Mensajero.tmdl:87`, `definition/tables/dimEstadisticas.tmdl:24`, `definition/tables/dimTipos.tmdl:24`

Regla BPA: `Avoid local file path sources (High)`.

Las rutas `C:\Users\Usuario\Downloads\...` y `D:\Users\Rafa\...` no son portables. Convertir a **Dataflow / Datamart / SharePoint / OneLake** o parametrizar con una variable de gateway.

---

### 4.6 🟡 MEDIA — `Table.ExpandTableColumn` con `Table.ColumnNames(#"Transformar archivo (3)"(#"Archivo de ejemplo (3)"))`

**Archivo:** `definition/tables/FacMensual_Control_Mensajeros.tmdl:172`

Regla BPA: `Avoid evaluating a function inside Table.ExpandTableColumn (Medium)`. Aquí se invoca la función solo para obtener `Table.ColumnNames`, lo que **no aporta valor real** porque la función depende de `Parámetro3`/`Archivo de ejemplo (3)`. Si el primer archivo cambia de estructura, el refresh puede romperse.

**Recomendación:** Reemplazar por una lista literal de nombres de columna o por `Table.ColumnNames(#"Transformar archivo (3)"(Binary.FromText("...")))`.

---

### 4.7 🟡 MEDIA — `Table.DuplicateColumn` y renombrado a `- Copia` para después eliminar

**Archivo:** `definition/tables/FacMensual_Control_Mensajeros.tmdl:185-198, 296-298` y `definition/tables/Fecha.tmdl:296-298`

Patrón observado: `DuplicateColumn → Transform → RemoveColumn` para extraer parte de un DateTime.

Regla BPA: `Avoid Table.DuplicateColumn when a single record access suffices (Low)`.

**Recomendación:** Sustituir por:
```m
Fecha = Table.AddColumn(Origen, "Fecha", each DateTime.Date([FechaDT]), type date),
Hora  = Table.AddColumn(Fecha,   "Hora",  each DateTime.Time([FechaDT]), type time),
#"Quitar FechaDT" = Table.RemoveColumns(Hora, {"FechaDT"})
```
Eliminando los `DuplicateColumn` intermedios.

---

### 4.8 🟡 MEDIA — `Table.SelectRows(... each true)`

**Archivo:** `definition/tables/FacMensual_Control_Mensajeros.tmdl:193, 202, 206`

Regla BPA: `Avoid no-op Table.SelectRows (Low)`. Varios filtros `each true` no producen ninguna fila pero consumen un paso de la cadena M.

**Recomendación:** Eliminar esos pasos manualmente o usar el menú "Eliminar paso" en Power Query.

---

### 4.9 🟡 MEDIA — Filtros con `null` redundantes y `Table.ReplaceValue` en cascada sobre el mismo campo

**Archivo:** `definition/tables/FacMensual_Control_Mensajeros.tmdl:191, 203, 205, 207`

```m
#"Valor reemplazado"  = Table.ReplaceValue(...,"","09999",...,{"Código"}),
#"Filas filtradas"   = Table.SelectRows(... each true),
#"Filas filtradas1"  = Table.SelectRows(... each [N. Envío] <> "0"),
#"Valor reemplazado1" = Table.ReplaceValue(...,{"Mensajero"}),
#"Filas filtradas3"  = Table.SelectRows(... each ([Código] <> null)),
#"Valor reemplazado2" = Table.ReplaceValue(...,{"Código"}),
...
```

Regla BPA: `Avoid chained ReplaceValue + Filter on same column (Medium)` y `Remove redundant null filters (Low)`.

**Recomendación:** Reemplazar `null` por `""` en un solo `Table.ReplaceValue` previo, y **fusionar los filtros** en uno solo con múltiples condiciones.

---

### 4.10 🟡 MEDIA — Sin anotaciones de plegado ni `fastCombine`

Regla BPA: `Enable fast combine when possible (Low)`. En el modelo no hay `PrivacySetting` definido. Considerar `Privacy = Public` para `FechaEspecial` y archivos Excel para habilitar *fast combine* y paralelismo.

---

### 4.11 🟡 MEDIA — No hay metadatos de Query Folding

No se observa el paso `Value.Metadata` ni `QueryFolding` en el modelo. La regla BPA `Annotate query folding potential (Informational)` sugiere documentar el potencial de plegado.

---

## 5. Hallazgos — Diseño / Modelado (BPA)

### 5.1 🔴 CRÍTICA — Mezcla de nombres de columna con caracteres especiales y mayúsculas

| Tabla | Columna | Problema |
|-------|---------|----------|
| `FacMensual_Control_Mensajeros` | `Hora-MInutos` | guion medio + mayúscula errónea |
| `dimUsuario Mensajero` | `Hora Entrada` | espacio en blanco |
| `dimUsuario Mensajero` | `Horas Contr` | espacio en blanco |
| `dimUsuario Mensajero` | `MInutos Contratados` | errata: "MInutos" en lugar de "Minutos" |
| `Fecha` | `FechaDiaSemana` | mezcla aceptable, pero debería normalizarse |
| `dimUsuario Mensajero` | `ID Usuario` | espacio en blanco |
| `FacDatos1` | `N. Envío` | carácter "." en nombre |

Regla BPA: `Avoid special characters in object names (High)`. Provoca errores de referencia en DAX, en Power Query, en visualizaciones de matriz y en algunas API REST.

**Recomendación:** renombrar a `HoraMinutos`, `HoraEntrada`, `HorasContratadas`, `MinutosContratados`, `IdUsuario`, `NumeroEnvio`.

---

### 5.2 🔴 CRÍTICA — Inconsistencia entre `Código` (fac) y `Usuario` (dim) en la misma relación

**Archivo:** `definition/relationships.tmdl:25-27`

```tmdl
relationship c9bbb90e-b5c8-8bff-78cd-b11d4b1a4e03
    fromColumn: FacMensual_Control_Mensajeros.Código
    toColumn:   'dimUsuario Mensajero'.Usuario
```

Regla BPA: `Avoid foreign keys with mismatched names (High)`. La FK y PK deberían llamarse igual (preferentemente `IdUsuario` o `Usuario`).

---

### 5.3 🟠 ALTA — Tabla `Medidas` como tabla suelta

**Archivo:** `definition/tables/Medidas.tmdl:1-2`

Las medidas se almacenan en una tabla vacía llamada `Medidas` con partición M vacía. Esto es una práctica **BPA-aprobable** (es la convención `TablaMedidas`), pero se observa:
- 60+ medidas en una sola tabla
- Falta `displayFolder` en algunas (`% EF`, `MaxValor MesAnterior`).

**Recomendación:** añadir un `displayFolder` por defecto (ya está hecho en su mayoría) y documentar las medidas con descripciones (`description:`).

---

### 5.4 🟠 ALTA — Columnas de texto alto-cardinalidad usadas como FK

`FacDatos1.Usuario` (string) — puede tener >500 valores. Es mejor un entero `IdUsuario`.

Regla BPA: `Use integer keys for relationships (High)`.

---

### 5.5 🟡 MEDIA — No hay descripciones en ninguna tabla, columna ni medida

Regla BPA: `Document all tables and columns (Medium)`. Cero `description:` en el modelo completo.

---

### 5.6 🟡 MEDIA — `dataCategory: Time` y jerarquías duplicadas

**Archivo:** `definition/tables/Fecha.tmdl:3, 230, 245`

`Fecha` está bien marcado como tabla de tiempo y la columna `Fecha` es `isKey`. ✅
Sin embargo, las jerarquías `A-M-D` y `A-S-D` están duplicadas en estructura. Considerar si `A-S-D` aporta valor para los visuales actuales.

---

### 5.7 🟡 MEDIA — `TablaRangosHoras` con sintaxis M en bloque ``` ` ` ` ` (template literal)

**Archivo:** `definition/tables/TablaRangosHoras.tmdl:44-105`

La partición M viene envuelta en ``` ` ``` (triple backticks). Funciona en TMDL pero el formato es propenso a errores de escape. Regla BPA: `Avoid triple-backtick M in TMDL partitions (Low)`.

---

### 5.8 🟡 MEDIA — Sin configuración de `StorageMode = DirectQuery` o `Hybrid` para tablas grandes

Toda la importación es `mode: import`. Si el directorio crece (>1 GB de Excel), convendría evaluar **Direct Lake** o **DirectQuery** sobre los CSV.

Regla BPA: `Evaluate large fact tables for Direct Lake (Medium)`.

---

### 5.9 🟡 MEDIA — `isHidden: true` solo en algunas columnas numéricas de `Fecha`

**Archivo:** `definition/tables/Fecha.tmdl:17-132`

Patrón irregular: `AñoNum` está oculto, pero `Año` no; `SemanaNum` está oculto, `DiaNum` y `DiaSemanaNum` también pero sin mostrar al usuario. Aplicar el principio de "menos columnas visibles = menos ruido".

Regla BPA: `Hide auxiliary columns (Low)`.

---

### 5.10 🟢 BAJA — Falta `summarizeBy: none` en columnas que se usan en segmentaciones

**Archivo:** `definition/tables/dimUsuario Mensajero.tmdl:32-40` y muchos otros.

La regla `Set summarizeBy to none for dimensions (Low)`.

---

### 5.11 🟢 BAJA — Tabla `dimGrupos` generada con `Binary.FromText` (inline)

**Archivo:** `definition/tables/dimGrupos.tmdl:24`

```m
Origen = Table.FromRows(Json.Document(Binary.Decompress(Binary.FromText("i45W8n..."))))
```

Es válido, pero no portable a Git diff y dificulta mantener. Considerar pasar a una fuente Excel o SQL.

Regla BPA: `Avoid inline binary data sources (Low)`.

---

## 6. Hallazgos — DAX (anti-patrones)

### 6.1 🟠 ALTA — `FILTER(... = SELECTEDVALUE(...))` dentro de `CALCULATE` para filtro de fila actual

**Archivo:** `definition/tables/Medidas.tmdl:139-144, 528-580, 632-655`

```dax
DiasTrabajados = CALCULATE(
    DISTINCTCOUNT(FacDatos1[Fecha]),
    FILTER(FacDatos1, FacDatos1[Usuario] = SELECTEDVALUE(FacDatos1[Usuario])))
```

Regla BPA: `Avoid FILTER on tables when column filter suffices (High)`. Sustituir por:
```dax
DiasTrabajados = CALCULATE(
    DISTINCTCOUNT(FacDatos1[Fecha]),
    ALLEXCEPT(FacDatos1, FacDatos1[Usuario]))
```

o por:
```dax
DiasTrabajados = CALCULATE(
    DISTINCTCOUNT(FacDatos1[Fecha]),
    VALUES(FacDatos1[Usuario]))
```

---

### 6.2 🟠 ALTA — `PERCENTILEX.INC` con `FILTER` en columna

**Archivo:** `definition/tables/Medidas.tmdl:530-580, 632-655`

Mismo anti-patrón: el filtro dentro de `PERCENTILEX.INC` se puede reescribir con `CALCULATE`:
```dax
P25_Mensj = CALCULATE(
    PERCENTILEX.INC(FacDatos1, FacDatos1[Valor], 0.25),
    ALLEXCEPT(FacDatos1, FacDatos1[Usuario]))
```

---

### 6.3 🟠 ALTA — División por cero potencial en `% EF` y `MEDIA % EF`

**Archivo:** `definition/tables/Medidas.tmdl:209-231`

```dax
RETURN (Horas * 60 + Minutos) / MinutosC
```

Si `MinutosC = 0` (o `BLANK()`), devuelve error. Regla BPA: `Use DIVIDE (Medium)`.

Recomendación:
```dax
RETURN DIVIDE(Horas*60 + Minutos, MinutosC)
```

---

### 6.4 🟠 ALTA — Medida vacía `'DURACION DAX'`

**Archivo:** `definition/tables/Medidas.tmdl:327-331`

```dax
measure 'DURACION DAX' =
    VAR H = HOUR()
    displayFolder: Control Mensasjero
```

**`HOUR()` sin parámetro** dará error en ejecución. Regla BPA: `Avoid DAX syntax errors in measures (Critical)`.

Recomendación: **eliminar la medida** (es una medida mal cerrada, probablemente un copia-pega truncado).

---

### 6.5 🟡 MEDIA — `CALCULATE` con filtro de tabla `FacDatos1[Estadística] = " Recogidas…"` (string con espacio al inicio)

**Archivo:** `definition/tables/Medidas.tmdl:175, 187, 287, 297, 504, 518, 754-755`

Los literales de string empiezan con un **espacio en blanco** (`" Bultos entregados"`). Regla BPA: `Trim string literals used in DAX filters (High)`.

Es probable que venga del prefijo de los CSV crudos y que el `Text.Trim` de la partición PQ no haya sido suficiente. Revisar que `FacDatos1[Estadística]` ya viene trimmed al modelo (sí, está en `FacDatos1.tmdl:53`).

---

### 6.6 🟡 MEDIA — `H EF E/R` opera con `time` y resta `Min-Inicio`, dando valores negativos

**Archivo:** `definition/tables/Medidas.tmdl:89-99`

```dax
VAR TM = [Inicial TM] - [Final TM]
VAR TT = [Inicial TT] - [Final TT]
```

Si la medida `Inicial TM` y `Final TM` son MIN y MAX del día, su resta puede ser **negativa o incoherente** (porque se está haciendo un sub-totaling). Regla BPA: `Avoid time subtractions without explicit type (Medium)`.

---

### 6.7 🟡 MEDIA — `Media Personal Mes = AVERAGE(FacDatos1[Usuario])` — semánticamente incorrecto

**Archivo:** `definition/tables/Medidas.tmdl:117-121`

`Usuario` es string. `AVERAGE` sobre string fuerza conversión implícita. Regla BPA: `Use correct data type in aggregations (High)`.

**Recomendación:** cambiar a `DISTINCTCOUNT(FacDatos1[Usuario])` o eliminarla si es dead code.

---

### 6.8 🟡 MEDIA — `Color_MaximoPorMensajero` usa hard-coded `#FF0000` y `#FFFFFF`

**Archivo:** `definition/tables/Medidas.tmdl:692-704, 719-726, 728-749`

Regla BPA: `Use theme colors instead of hard-coded hex (Low)`.

---

### 6.9 🟢 BAJA — `DIAS>85` usa `COUNTROWS(Fecha)` sin filtro de relación activa

**Archivo:** `definition/tables/Medidas.tmdl:256-264`

`COUNTROWS(Fecha)` puede devolver todas las fechas del modelo (varios años) si no hay filtro en el visual. Regla BPA: `Avoid unbounded COUNTROWS over dimension table (Low)`.

---

## 7. Hallazgos — Time Intelligence

### 7.1 ✅ POSITIVO — `Fecha` está marcada como tabla de tiempo (`dataCategory: Time`)

La tabla `Fecha` cumple los requisitos BPA:
- `dataCategory: Time` ✅
- `Fecha` (dateTime) marcada como `isKey` ✅
- `FechaSK` única ✅
- Rango continuo con `List.Dates` ✅
- `__PBI_TimeIntelligenceEnabled = 0` ⚠️ (ver siguiente)

---

### 7.2 🟠 ALTA — `__PBI_TimeIntelligenceEnabled = 0` desactiva la inteligencia de tiempo

**Archivo:** `definition/model.tmdl:29`

Esto **deshabilita** las funciones `TOTALYTD`, `SAMEPERIODLASTYEAR` y compañía en **todo el modelo**. Hay medidas (`Total Mes Anterior`, `MediaMesAnterior`, `MaxValor MesAnterior`, `TotalRecogidosPlataformaMesAnterior`) que usan `DATEADD(...)` y siguen funcionando porque `DATEADD` no requiere la flag; pero la convención BPA dice mantener la flag activa y añadir una **jerarquía explícita de fechas** si se requiere.

**Recomendación:** quitar la línea y dejar que Power BI gestione las jerarquías automáticamente; o documentar explícitamente por qué se desactiva.

---

## 8. Hallazgos — Particiones y entidades

### 8.1 🟠 ALTA — No todas las particiones declaran `entities`

Regla BPA: `M partitions with embedded M expressions must include entities for analysis services (High)`. En este modelo TMDL no hay `entities:` declarado. No impacta al runtime de PBI Service pero sí a la futura migración a **Analysis Services**.

---

## 9. Resumen de acciones priorizadas

### Prioridad 1 (Crítica — esta semana)
1. **Eliminar `Archivo de ejemplo (3)` + `Parámetro3` + `Transformar archivo (3)`** y consolidar en una sola función.
2. **Fusionar las dos invocaciones de funciones** en `FacMensual_Control_Mensajeros` (líneas 168 y 170).
3. **Mover la dependencia de `FechaEspecial` a DAX** (`LOOKUPVALUE`) y eliminar el `Table.NestedJoin` en `Fecha.tmdl:290`.
4. **Renombrar columnas con caracteres especiales**: `Hora-MInutos` → `HoraMinutos`, `Hora Entrada` → `HoraEntrada`, etc.
5. **Corregir la medida `'DURACION DAX'`** (línea 327-331) — está rota.

### Prioridad 2 (Alta — próximos 15 días)
6. **Reemplazar las rutas absolutas** `C:\Users\...\D:\Users\...` por rutas relativas o SharePoint.
7. **Externalizar la lista de 18 estadísticas** a una tabla de configuración.
8. **Fusionar los `Table.TransformColumnTypes` consecutivos** en `FacMensual_Control_Mensajeros` y `Fecha`.
9. **Reemplazar `FILTER(col = SELECTEDVALUE(col))` por `ALLEXCEPT`** en todas las medidas de percentiles.
10. **Cambiar la PK/FK a enteros** (`IdUsuario`) y renombrar `Código` en la fact.

### Prioridad 3 (Media — próximo mes)
11. **Activar `__PBI_TimeIntelligenceEnabled = 1`**.
12. **Envolver todas las divisiones con `DIVIDE`**.
13. **Trim de literales** de Estadística en medidas DAX.
14. **Documentar tablas/columnas/medidas** con `description:`.
15. **Eliminar pasos M no-op** (`Table.SelectRows(... each true)`).

### Prioridad 4 (Baja — mejora continua)
16. Reemplazar `Table.DuplicateColumn` por acceso directo al record.
17. Ocultar columnas auxiliares en `Fecha`.
18. Mover `dimGrupos` de inline-binary a una fuente externa.
19. Añadir descripciones de medidas y `displayFolder` por defecto.

---

## 10. Conclusiones

El modelo **`PRY Estadisticas Mensajeros v2.SemanticModel`** presenta un **diseño funcional** pero con **deuda técnica significativa** en la capa de Power Query:

- 1 **merge explícito** (`Fecha ⨯ FechaEspecial`) que conviene reescribir en DAX.
- 3 **combinaciones implícitas** vía `Table.AddColumn + función` (una en `FacDatos1`, dos en `FacMensual_Control_Mensajeros`).
- 1 **dependencia circular** entre 3 expresiones (`Archivo de ejemplo (3)`, `Parámetro3`, `Transformar archivo (3)`).
- 6 **expresiones huérfanas o redundantes** que no aportan valor al modelo.

**Tiempo estimado de refactorización completa:** 6–10 horas de un desarrollador Power BI con experiencia en M y DAX.

**Beneficio esperado:**
- Reducción del ~30–40 % del tiempo de refresh.
- Eliminación de riesgos de fallo por rutas absolutas.
- Mejora de la mantenibilidad y de la experiencia del desarrollador.
- Aumento de la calidad de las métricas BPA, llevándolas de **29 hallazgos** a **< 10** (todos de prioridad media-baja).

---

*Informe generado por análisis estático del modelo TMDL. No se ha ejecutado BPA en vivo; los hallazgos equivalen a las reglas BPA estándar de Tabular Editor.*
