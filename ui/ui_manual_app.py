import streamlit as st


def pantalla_manual_app():
    st.subheader("📘 Manual de funcionamiento de la app")

    st.info(
        "Guía rápida para saber cómo usar los módulos principales de mantenimiento."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "💧 Legionella",
            "🛠️ Órdenes de trabajo",
            "📅 Preventivo",
            "📦 Inventario",
            "📄 Informes",
        ]
    )

    with tab1:
        st.markdown("## 💧 Funcionamiento Legionella")

        st.markdown("### 1. Crear puntos de control")
        st.write("""
        Entra en **Legionella → Puntos**.

        Desde ahí puedes crear puntos de:
        - ACS
        - AFCH
        - Retorno
        - Acumuladores
        - Duchas
        - Fuentes
        - Válvulas termostáticas
        - Puntos de poco uso
        - Muestras
        """)

        st.markdown("### 2. Registrar un control")
        st.write("""
        Entra en **Legionella → Registrar control**.

        Pasos:
        1. Selecciona centro.
        2. Selecciona edificio.
        3. Selecciona punto.
        4. Selecciona tarea.
        5. Introduce temperaturas, cloro o checklist.
        6. Añade observaciones si hace falta.
        7. Guarda el control.
        """)

        st.markdown("### 3. Qué pasa si hay riesgo")
        st.write("""
        Si un valor sale fuera de rango, la app:
        - Marca el control como **RIESGO** o **INCIDENCIA**.
        - Registra la incidencia.
        - Genera una orden de trabajo automática.
        """)

        st.markdown("### 4. Planificación")
        st.write("""
        En **Legionella → Planificación** puedes:
        - Crear planificación automática desde puntos.
        - Cambiar frecuencias.
        - Cambiar operario.
        - Activar o desactivar tareas.
        - Generar OT cuando toque.
        """)

    with tab2:
        st.markdown("## 🛠️ Órdenes de trabajo")

        st.write("""
        Las órdenes pueden venir de:
        - App
        - Profesores
        - Preventivo
        - Legionella
        - Empresas externas
        - Plan verano

        Estados habituales:
        - Abierta
        - En curso
        - Pendiente material
        - Pendiente proveedor
        - Finalizada
        """)

    with tab3:
        st.markdown("## 📅 Mantenimiento preventivo")

        st.write("""
        El preventivo sirve para programar trabajos periódicos.

        Ejemplos:
        - Cuadros eléctricos
        - Fontanería
        - Climatización
        - Iluminación
        - ACS
        - Jardinería
        - Revisiones visuales
        """)

        st.markdown("### Flujo")
        st.write("""
        1. Crear tarea preventiva.
        2. Asignar centro, edificio y operario.
        3. Definir frecuencia.
        4. Generar OT cuando toque.
        5. El operario completa checklist.
        6. Se guarda en histórico.
        """)

    with tab4:
        st.markdown("## 📦 Inventario")

        st.write("""
        El inventario permite controlar:
        - Materiales
        - Stock
        - Stock mínimo
        - Entradas
        - Salidas
        - Pedidos de material
        - Fotos
        - Proveedor
        """)

        st.markdown("### Pedidos")
        st.write("""
        Los operarios pueden pedir material.
        Abel puede preparar, entregar o marcar sin stock.
        """)

    with tab5:
        st.markdown("## 📄 Informes")

        st.write("""
        Desde los informes puedes generar:
        - Libro de inspección Legionella
        - Histórico de controles
        - Incidencias
        - Informes externos
        - Evidencias para inspección
        """)

        st.warning(
            "Antes de una inspección conviene revisar que los puntos, planificación, controles e informes externos estén completos."
        )
