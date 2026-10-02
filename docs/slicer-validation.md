# Validación manual de integración — pendiente

Entorno objetivo: Slicer 5.2.2, macOS, Python 3.9. Ejecutar antes de interpretar mediciones reales.

1. Instalar por Additional module paths; comprobar importación de ONeSpineCRxLib y apertura de interfaz sin traceback.
2. Importar una radiografía DICOM; asignar LAT. Verificar plano Red coincidente con el plano IJK y permitir visualizar todos los bordes. La vista no debe cortar el volumen.
3. Marcar ORIGIN/ANTERIOR_REF/CRANIAL_REF con anterior anatómico verificado; comprobar nombres de cada punto y que no se generan puntos duplicados al editar.
4. Marcar marcador conocido; comparar longitud manual externa y resultado. Modificar CAL_A/CAL_B y comprobar actualización de escala; eliminar un punto y confirmar que mm queda pendiente.
5. Confirmar horizontal y mover una referencia de orientación; comprobar que slopes/cSVA quedan pendientes hasta nueva confirmación.
6. Marcar C2–C7 y T1 visible; comprobar signos sobre un caso de lordosis y uno de cifosis. Verificar cSVA contra medición directa con centro C2.
7. Omitir T1: CL, alturas C2–C7 y traslación deben continuar disponibles.
8. Cambiar a FLEX/EXT: confirmar imagen y color de puntos; comprobar resultados independientes y dinámica actualizada tras edición.
9. Invertir SA/SP: comprobar QC y ausencia de valores derivados de ese platillo. Corregirlo y verificar recuperación.
10. Exportar JSON + SVG, abrir ambas salidas y comparar numéricamente contra pantalla. Comprobar que no contienen identificación de paciente.
11. Cargar y asignar imágenes en sesión nueva; restaurar JSON y confirmar coordenadas, nombres y resultados. Cambiar imagen y comprobar invalidación de puntos/escala de esa proyección.
12. Cerrar/reabrir módulo y probar cleanup de observers. No se promete persistencia al guardar MRB en esta versión.

Registrar versión exacta de Slicer, resultados y errores; estas comprobaciones no están ejecutadas en el entorno de desarrollo inicial.

## Regresión v0.1.1 — pendiente en Slicer

- Girar/invertir radiografía sin geometría DICOM; puntos existentes deben permanecer sobre el mismo píxel.
- Importar series con módulo abierto: no deben autoasignarse a múltiples proyecciones.
- Asignar LAT/FLEX/EXT diferentes y activar sus botones: confirmar imagen, nodo y conservación de puntos.
- Marcar dos puntos con avance automático y verificar etiquetas; detener o cambiar proyección cancela continuación pendiente.
- Saltar punto y volver a omitidos.
- Rechazar asignación duplicada sin eliminar landmarks anteriores.
