from datetime import datetime
from zoneinfo import ZoneInfo

from database.db import conectar, _sql, _es_postgres


_ZONA_LOCAL = ZoneInfo("Europe/Madrid")


def _ahora_local():
    return datetime.now(_ZONA_LOCAL)


def asegurar_tabla_accesos_gerencia():
    conn = conectar()
    cursor = conn.cursor()

    if _es_postgres():
        id_sql = "SERIAL PRIMARY KEY"
    else:
        id_sql = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS accesos_gerencia (
            id {id_sql},
            fecha_hora TEXT NOT NULL,
            usuario TEXT,
            centro TEXT
        )
    """)

    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_accesos_gerencia_fecha
            ON accesos_gerencia (fecha_hora)
        """)
    except Exception:
        pass

    conn.commit()
    conn.close()


def registrar_acceso_gerencia(usuario="", centro=""):
    """Registra una entrada real del perfil Gerencia.

    La protección frente a reruns se hace en session_state desde app.py.
    Esta función solo persiste una visita cuando se la llama.
    """
    asegurar_tabla_accesos_gerencia()

    ahora = _ahora_local()

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute(_sql("""
            INSERT INTO accesos_gerencia
            (fecha_hora, usuario, centro)
            VALUES (?, ?, ?)
        """), (
            ahora.isoformat(timespec="seconds"),
            str(usuario or "").strip(),
            str(centro or "").strip(),
        ))

        conn.commit()
        return True

    except Exception:
        conn.rollback()
        return False

    finally:
        conn.close()


def _limites_curso(ahora):
    if ahora.month >= 8:
        inicio = datetime(
            ahora.year,
            8,
            1,
            tzinfo=_ZONA_LOCAL,
        )
        fin = datetime(
            ahora.year + 1,
            9,
            1,
            tzinfo=_ZONA_LOCAL,
        )
    else:
        inicio = datetime(
            ahora.year - 1,
            8,
            1,
            tzinfo=_ZONA_LOCAL,
        )
        fin = datetime(
            ahora.year,
            9,
            1,
            tzinfo=_ZONA_LOCAL,
        )

    return inicio, fin


def obtener_resumen_accesos_gerencia(limite_ultimos=20):
    asegurar_tabla_accesos_gerencia()

    ahora = _ahora_local()
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    if ahora.month == 12:
        inicio_mes_siguiente = datetime(
            ahora.year + 1,
            1,
            1,
            tzinfo=_ZONA_LOCAL,
        )
    else:
        inicio_mes_siguiente = datetime(
            ahora.year,
            ahora.month + 1,
            1,
            tzinfo=_ZONA_LOCAL,
        )

    inicio_mes = datetime(
        ahora.year,
        ahora.month,
        1,
        tzinfo=_ZONA_LOCAL,
    )

    inicio_curso, fin_curso = _limites_curso(ahora)

    conn = conectar()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, fecha_hora, usuario, centro
            FROM accesos_gerencia
            ORDER BY fecha_hora DESC, id DESC
        """)
        filas = cursor.fetchall()
    except Exception:
        filas = []
    finally:
        conn.close()

    registros = []

    for fila in filas:
        try:
            id_acceso, fecha_txt, usuario, centro = fila
            fecha = datetime.fromisoformat(str(fecha_txt))

            if fecha.tzinfo is None:
                fecha = fecha.replace(tzinfo=_ZONA_LOCAL)
            else:
                fecha = fecha.astimezone(_ZONA_LOCAL)

            registros.append({
                "id": id_acceso,
                "fecha": fecha,
                "usuario": str(usuario or "").strip(),
                "centro": str(centro or "").strip(),
            })
        except Exception:
            continue

    total = len(registros)
    hoy = sum(1 for r in registros if r["fecha"] >= inicio_hoy)
    mes = sum(
        1
        for r in registros
        if inicio_mes <= r["fecha"] < inicio_mes_siguiente
    )
    curso = sum(
        1
        for r in registros
        if inicio_curso <= r["fecha"] < fin_curso
    )

    ultimo = registros[0]["fecha"] if registros else None

    ultimos = []
    for registro in registros[:max(1, int(limite_ultimos or 20))]:
        ultimos.append({
            "Fecha y hora": registro["fecha"].strftime("%d/%m/%Y %H:%M:%S"),
            "Usuario": registro["usuario"] or "Gerencia",
            "Centro": registro["centro"] or "-",
        })

    return {
        "hoy": hoy,
        "mes": mes,
        "curso": curso,
        "total": total,
        "ultimo": ultimo,
        "inicio_curso": inicio_curso,
        "fin_curso": fin_curso,
        "ultimos": ultimos,
    }
