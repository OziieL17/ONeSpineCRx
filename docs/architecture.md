# Arquitectura cervical v0.1

## Contratos

1. **Entrada:** proyecciones independientes `lat`, `flex`, `ext`. Asignación manual; no inferencia anatómica basada solo en el nombre de la serie. Una imagen puede faltar.
2. **Coordenadas:** posiciones MRML en RAS mundo → plano 2D anatómico definido por tres referencias. X anterior positiva, Y craneal positiva. La referencia anterior por sí sola no certifica horizontal física; slopes/cSVA requieren confirmación adicional.
3. **Calibración:** `mm_per_unit=null` hasta confirmación. Una calibración manual aplica un factor una sola vez a distancias. Mover CAL_A/CAL_B recalcula la escala con la longitud conocida almacenada. Cambiar las referencias de orientación retira confirmación de horizontal.
4. **Anatomía primaria:** SA/SP/IA/IP C2–C7 y SA/SP T1. C1 y occipucio requieren geometría específica; no se modelan como cuerpos rectangulares.
5. **Geometría compartida:** platillos, vectores AP, normales craneales, puntos medios, longitudes AP y centro aproximado por cuatro esquinas. C2 real no es rectangular; la aproximación debe compararse contra marcaje directo del centro en validación.
6. **Medidas:** objeto `{value, unit, status, reason, method}`. Datos faltantes producen `unavailable`; nunca cero sustitutivo ni NaN JSON. Razones sin unidad conservan disponibilidad sin calibración.
7. **QC:** orden AP, degeneración de referencia, coplanaridad, cuerpos cruzados, platillos discales cruzados, ausencia de superposición, dependencia horizontal/escala. No se exige FLEX < LAT < EXT en todos los parámetros: no es un invariante matemático ni clínico.
8. **Dinámica:** parejas FLEX/EXT disponibles; cambios firmados y magnitudes. Ties en máxima movilidad se conservan; excursión angular cero no se interpreta como nivel predominante.
9. **Salida:** `StudyResult` único para JSON, pantalla y figuras. Entradas anatómicas 2D y bloque Slicer RAS permiten reconstrucción y trazabilidad. No se incluyen nombres de paciente, UID DICOM, nombres de volumen ni píxeles.

## Estados

- Sin volumen: asignar imagen.
- Sin plano: marcar referencias.
- Sin calibración: ángulos y razones disponibles; mm pendiente.
- Anatomía parcial: calcular únicamente dependencias válidas.
- Resultados calculados: `partial` o `review_required`.
- Revisión clínica: el archivo conserva `review_status=unreviewed`; esta versión no ofrece firma ni aprobación automática.

## Lo que esta versión no resuelve

No mide diámetro foraminal, compresión medular, canal ni balance espinal global a partir de radiografía lateral. No determina adecuación del esfuerzo FLEX/EXT. No compensa magnificación variable por profundidad ni reconstruye morfología 3D. El QC geométrico no verifica si un punto está anatómicamente sobre el borde correcto.

El JSON omite identificación deliberadamente: una restauración depende de selección correcta de la imagen por el operador. La integración Slicer aún no tiene parameter node para recargar estado al abrir MRB; el guardado funcional es el JSON.

## Evolución prevista

1. Prueba Slicer 5.2.2/macOS con radiografías LAT/FLEX/EXT y ajustes de API necesarios.
2. Validación de medidas contra marcaje independiente, error absoluto, Bland–Altman y variabilidad inter/intraobservador.
3. Modelo craneocervical: C0–C2, C1–C2 y ADI con landmarks dedicados y definiciones explícitas; CBVA solo con contorno facial e información postural adecuada.
4. Perfil AP independiente; no reutilizar el motor sagital para cálculos coronales.
5. Persistencia MRML y figuras sobre radiografías con control de identificadores.
6. Clasificación asistida y detección de landmarks con corrección humana tras contar con datos anotados y validados.
