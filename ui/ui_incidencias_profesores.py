if st.button("📨 Enviar incidencia"):
    if not descripcion.strip():
        st.warning("Falta describir la incidencia.")
        return

    if not nombre_solicitante.strip():
        st.warning("Falta poner el nombre de quien envía.")
        return

    if not str(espacio).strip():
        st.warning("Falta indicar el espacio.")
        return

    if centro == "Pearson 9":
        operario = "Luis Lozano"
    else:
        operario = "J.A. Almeda"

    numero_ot = obtener_siguiente_numero_ot(centro, "INC")
    fecha_origen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ruta_foto = ""

    if foto_bytes is not None:
        carpeta = Path("uploads/incidencias")
        carpeta.mkdir(parents=True, exist_ok=True)

        extension = foto.name.split(".")[-1].lower()
        nombre_foto = f"{numero_ot}.{extension}"
        ruta_foto = str(carpeta / nombre_foto)

        with open(ruta_foto, "wb") as f:
            f.write(foto_bytes)

    prioridad_limpia = prioridad.replace("🟢 ", "").replace("🟡 ", "").replace("🔴 ", "")

    datos = (
        numero_ot,
        descripcion.strip(),
        "Abierta",
        centro,
        edificio,
        str(espacio).strip(),
        "Otros",
        prioridad_limpia,
        operario,
        f"Profesores - {tipo_solicitante}",
        nombre_solicitante.strip(),
        fecha_origen,
        ruta_foto,
        tipo_solicitante  # 👈 clave
    )

    crear_orden(datos)

    st.success(f"✅ Incidencia guardada correctamente. Nº OT: {numero_ot}")
