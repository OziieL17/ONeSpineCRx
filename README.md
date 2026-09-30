# ONeSpineCRx

Módulo inicial para análisis **radiográfico cervical 2D** en 3D Slicer. Versión **0.1.0**, con motor independiente de Slicer y adquisición manual guiada de landmarks.

## Estado real

- Implementado: motor geométrico, mediciones estáticas y dinámicas, QC por dependencias, exportación JSON/SVG, adaptador de interfaz Slicer y restauración de landmarks.
- Validado localmente: pruebas unitarias de geometría sintética y compilación Python.
- **Pendiente:** prueba de integración en Slicer 5.2.2/macOS y validación con estudios reales, incluyendo reproducibilidad entre observadores. La interfaz no se ha ejecutado en Slicer en este entorno.
- No implementado aún: detección anatómica automática, clasificación automática de series, métricas AP, módulo craneocervical, informe clínico automático, extracción automática de escala DICOM o persistencia de sesión en un parameter node MRML.

## Instalación sin compilar

1. Descargar este repositorio y descomprimirlo.
2. En Slicer: **Edit → Application Settings → Modules → Additional module paths**, agregar la carpeta que contiene `ONeSpineCRx.py`.
3. Reiniciar Slicer. Abrir **ONe → ONeSpineCRx**.
4. Mantener `ONeSpineCRxLib` junto a `ONeSpineCRx.py`.

El motor usa únicamente la biblioteca estándar de Python y es compatible con Python 3.9. El adaptador usa PythonQt, CTK, VTK y las APIs de Slicer; requiere comprobación en la versión de destino.

## Cinco pasos visibles

1. **Cargar:** “Agregar DICOM” abre el módulo DICOM de Slicer; importar y cargar las radiografías con el flujo nativo.
2. **Clasificar:** asignar manualmente volúmenes a LAT/FLEX/EXT. Cada volumen debe contener una sola imagen en el eje K. No asignar una TC/RM 3D.
3. **Orientar y calibrar:** seleccionar la proyección activa. Marcar `ORIGIN` dentro de la imagen; `ANTERIOR_REF` hacia anterior y `CRANIAL_REF` hacia craneal. La dirección ORIGIN→ANTERIOR_REF debe coincidir con la horizontal de adquisición para slopes y cSVA; confirmar la casilla solo después de verificarlo. Sin referencia horizontal fiable, conservar esos valores pendientes. Para mm, usar dos puntos de un marcador de longitud conocida o confirmar explícitamente una escala anatómica verificada del volumen.
4. **Marcar anatomía:** avanzar con “Colocar siguiente punto”. Registrar cuatro esquinas de C2–C7; T1 superior es opcional. El módulo muestra la imagen y los puntos de la proyección activa. Editar/eliminar desde Markups. El origen y las referencias definen un plano común en RAS; puntos fuera del plano se rechazan.
5. **Revisar:** resultados parciales se actualizan al editar puntos. FLEX/EXT se comparan automáticamente si ambas proyecciones tienen orientación válida. Exportar JSON y figuras SVG de geometría, sin radiografía de fondo.

**Restauración:** cargar y asignar primero las mismas imágenes; después restaurar el JSON. Cambiar un volumen invalida sus landmarks y calibración para evitar aplicar puntos de otra imagen. Verificar visualmente correspondencia y posición: el JSON no incluye identificadores ni imágenes DICOM.

## Mediciones

| Variable | Definición de esta versión | Requisitos |
|---|---|---|
| CL C2–C7 | Diferencia firmada entre platillos inferiores C2 y C7; lordosis positiva | C2/C7 IA-IP |
| cSVA C2–C7 | Distancia horizontal del centro C2 aproximado por cuatro esquinas a C7_SP; anterior positivo | C2 completo, C7 superior, horizontal y calibración |
| T1 slope | Inclinación del platillo superior T1; anterior descendente positiva | T1 SA-SP y horizontal |
| C2 slope | Platillo inferior C2 con la misma convención de slope | C2 IA-IP y horizontal |
| C7 slope | Platillo superior C7; se identifica explícitamente este método | C7 SA-SP y horizontal |
| T1S−CL | T1 slope menos CL C2–C7 | Ambas mediciones disponibles |
| IVA C2–C3 a C7–T1 | Platillo inferior craneal menos superior caudal; ángulo discal, distinto del Cobb entre platillos inferiores de cuerpos vecinos | Ambos platillos |
| DH posterior/25/50/75/anterior | Distancias normales al platillo caudal en la zona de superposición | Ambos platillos y calibración para mm |
| DH media | Media de las cinco muestras | Mismas dependencias |
| Traslación | Esquina posterior inferior craneal menos posterior superior caudal, proyectada sobre el eje caudal | Ambos platillos; calibración para mm |
| Traslación % | Traslación dividida entre longitud AP del platillo superior caudal ×100 | No requiere escala absoluta |
| Razón DH/AP % | Media de altura normal / AP caudal ×100; índice exploratorio explícito | No requiere escala absoluta |

La razón DH/AP **no se denomina DHI/IHI cervical validado**: existen distintas definiciones publicadas que deben seleccionarse y validarse antes de incorporarlas. Los puntos anterior/posterior de DH corresponden a los extremos del **soporte común**, no a esquinas emparejadas en cuerpos desplazados.

La dinámica conserva `delta_ext_minus_flex` y `excursion=abs(delta)` por parámetro. Reporta los niveles con mayor excursión angular observada; no emite diagnósticos de inestabilidad ni umbrales de indicación quirúrgica. Posiciones, magnificación y calidad de esfuerzo deben verificarse al interpretar la dinámica.

## Arquitectura

`Radiografía → ProjectionInput → GeometryModel → Measurements → QC → DynamicAnalysis → StudyResult → GUI / JSON / SVG`

- `ONeSpineCRx.py`: interfaz y adaptación MRML/markups.
- `ONeSpineCRxLib/engine.py`: coordenadas anatómicas, geometría compartida, mediciones y dinámica.
- `ONeSpineCRxLib/report.py`: representación SVG del objeto de resultados.
- `tests/test_engine.py`: escenarios geométricos independientes de Slicer.
- `docs/architecture.md`: contratos, limitaciones y evolución.
- `docs/slicer-validation.md`: prueba manual de integración pendiente.

## Pruebas

Desde la raíz del repositorio:

```bash
python -m unittest discover -s tests -v
python -m compileall -q ONeSpineCRx.py ONeSpineCRxLib tests
```

## Fuentes y métodos

Definiciones de parámetros cervicales consultadas en estudios originales:

- [Internal Chain of Correlation of Sagittal Cervical Alignment in Asymptomatic Subjects](https://pmc.ncbi.nlm.nih.gov/articles/PMC10538324/): CL C2–C7, T1 slope y cSVA con centro C2/C7_SP.
- [T1 Slope and Cervical Sagittal Alignment on Cervical CT Radiographs of Asymptomatic Persons](https://pubmed.ncbi.nlm.nih.gov/24003370/): parámetros cervicales y entrada torácica.
- [Magnetic resonance imaging: A possible alternative to a standing lateral radiograph…](https://pubmed.ncbi.nlm.nih.gov/28953681/): definiciones radiográficas y comparación por modalidad/postura.

Las fórmulas de altura sobre soporte común y traslación aquí implementadas son **convenciones geométricas explícitas del software** y requieren validación específica. La consulta bibliográfica inicial no sustituye validación metrológica.
