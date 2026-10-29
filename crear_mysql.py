# -*- coding: utf-8 -*-
import json
import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_CONFIG = os.path.join(CARPETA, "config.json")

PRODUCTOS_INICIALES = [
    ("Martillo profesional", "Martillo con mango resistente y diseño ergonómico para trabajos del hogar.", 58000, "🔨", "imagenes/martillo.png", "Herramientas"),
    ("Juego de destornilladores", "Juego completo para diferentes tipos de trabajos y reparaciones.", 73000, "🪛", "imagenes/destornilladores.png", "Herramientas"),
    ("Llave inglesa", "Llave ajustable para trabajos de reparación y mantenimiento.", 45000, "🔧", "imagenes/llave.png", "Herramientas"),
    ("Alicate profesional", "Alicate de alta resistencia para trabajos eléctricos y mecánicos.", 32000, "🗜️", "imagenes/alicate.png", "Herramientas"),
    ("Sierra manual", "Sierra resistente para trabajos de corte en madera.", 47000, "🪚", "imagenes/sierra.png", "Herramientas"),
    ("Caja de tornillos", "Tornillos de diferentes tamaños para trabajos de construcción.", 25000, "🔩", "imagenes/tornillos.png", "Tornillería"),
    ("Pintura para interiores", "Pintura de excelente cobertura para renovar tus espacios.", 85000, "🎨", "imagenes/pintura.png", "Pinturas"),
    ("Bombillo LED", "Bombillo LED de bajo consumo para iluminación del hogar.", 18000, "💡", "imagenes/bombillo.png", "Electricidad"),
    ("Cinta métrica", "Cinta métrica resistente para mediciones precisas en tus proyectos.", 28000, "📏", "imagenes/cinta.png", "Medición"),
]


def leer_config():
    with open(RUTA_CONFIG, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    clave = os.environ.get("MYSQL_PASSWORD")
    if clave:
        datos["password"] = clave
    return datos


def guardar_config(datos):
    with open(RUTA_CONFIG, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)
        archivo.write("\n")


def pedir_password_si_falta():
    cfg = json.loads(open(RUTA_CONFIG, encoding="utf-8").read())
    if (cfg.get("password") or "").strip() or os.environ.get("MYSQL_PASSWORD"):
        return
    print("MySQL está encendido, pero root tiene contraseña y config.json está vacío.")
    print("Escribe la contraseña que pusiste al instalar MySQL (usuario root).")
    if not sys.stdin.isatty():
        print("Ábrela en config.json, campo password, y vuelve a ejecutar abrir-tienda.bat")
        return
    try:
        clave = input("Contraseña root: ").strip()
    except EOFError:
        clave = ""
    if not clave:
        return
    cfg["password"] = clave
    guardar_config(cfg)
    print("Contraseña guardada en config.json")


def conectar(usar_base=True):
    import pymysql

    cfg = leer_config()
    kwargs = dict(
        host=cfg.get("host", "127.0.0.1"),
        port=int(cfg.get("port", 3306)),
        user=cfg.get("user", "root"),
        password=cfg.get("password", ""),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    if usar_base:
        kwargs["database"] = cfg.get("database", "ferreteria_max")
    return pymysql.connect(**kwargs)


def crear_base():
    cfg = leer_config()
    nombre = cfg.get("database", "ferreteria_max")
    conexion = conectar(usar_base=False)
    with conexion.cursor() as cursor:
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS `%s` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            % nombre
        )
        cursor.execute("USE `%s`" % nombre)
        sql_path = os.path.join(CARPETA, "ferreteria.sql")
        texto = open(sql_path, encoding="utf-8").read()
        for sentencia in texto.split(";"):
            limpia = sentencia.strip()
            if not limpia or limpia.upper().startswith("CREATE DATABASE") or limpia.upper().startswith("USE "):
                continue
            cursor.execute(limpia)
        cursor.execute("SELECT COUNT(*) AS total FROM productos")
        if cursor.fetchone()["total"] == 0:
            cursor.executemany(
                """
                INSERT INTO productos (nombre, descripcion, precio, icono, imagen, categoria)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                PRODUCTOS_INICIALES,
            )
        for columna in ("fecha_nacimiento", "cedula"):
            try:
                cursor.execute("ALTER TABLE usuarios DROP COLUMN `%s`" % columna)
            except Exception:
                pass
        asegurar_verificacion_correo(cursor)
    conexion.close()
    return nombre


def _tiene_columna(cursor, tabla, columna):
    cursor.execute(
        """
        SELECT COUNT(*) AS n
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (tabla, columna),
    )
    return cursor.fetchone()["n"] > 0


def asegurar_verificacion_correo(cursor):
    nuevas = not _tiene_columna(cursor, "usuarios", "correo_verificado")
    if nuevas:
        cursor.execute(
            "ALTER TABLE usuarios ADD COLUMN correo_verificado TINYINT(1) NOT NULL DEFAULT 1"
        )
        cursor.execute("ALTER TABLE usuarios ALTER correo_verificado SET DEFAULT 0")
    if not _tiene_columna(cursor, "usuarios", "token_verificacion"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN token_verificacion CHAR(64) NULL")
    if not _tiene_columna(cursor, "usuarios", "codigo_verificacion"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN codigo_verificacion CHAR(6) NULL")
    if not _tiene_columna(cursor, "usuarios", "verificacion_expira"):
        cursor.execute("ALTER TABLE usuarios ADD COLUMN verificacion_expira DATETIME NULL")


if __name__ == "__main__":
    pedir_password_si_falta()
    try:
        base = crear_base()
        print("MySQL listo. Base de datos:", base)
    except Exception as error:
        print("No se pudo crear la base de datos MySQL.")
        print(error)
        texto = str(error)
        if "1045" in texto:
            print("La contraseña de root es incorrecta o está vacía.")
            print("Ábrela en config.json (campo password, no el de smtp) y vuelve a intentar.")
        else:
            print("Revisa que el servicio MySQL80 esté iniciado.")
        print("La tienda igual va a funcionar con una base local.")
        print("Abre abrir-tienda.bat y entra a http://127.0.0.1:8766/cuenta.html")
        raise SystemExit(0)
