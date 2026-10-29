# -*- coding: utf-8 -*-
import hashlib
import json
import os
import secrets
import smtplib
import subprocess
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from crear_mysql import CARPETA, conectar, crear_base, leer_config
from base_local import conectar_local, crear_local


def conectar_o_error(handler):
    try:
        return conectar()
    except Exception:
        crear_local()
        return conectar_local()

PUERTO = 8766


def liberar_puerto(puerto):
    try:
        salida = subprocess.check_output("netstat -ano", shell=True, text=True, errors="ignore")
    except Exception:
        return
    yo = str(os.getpid())
    pids = set()
    for linea in salida.splitlines():
        if "LISTENING" not in linea:
            continue
        partes = linea.split()
        if len(partes) < 2:
            continue
        local = partes[1]
        numero = local.rsplit(":", 1)[-1]
        if numero != str(puerto):
            continue
        pid = partes[-1]
        if pid.isdigit() and pid != yo:
            pids.add(pid)
    for pid in pids:
        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
    if pids:
        time.sleep(0.6)


def hash_clave(clave, sal=None):
    if sal is None:
        sal = os.urandom(16).hex()
    digesto = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal.encode("utf-8"), 120000)
    return sal + "$" + digesto.hex()


def verificar_clave(clave, guardado):
    if not guardado or "$" not in guardado:
        return False
    sal, _resto = guardado.split("$", 1)
    return hash_clave(clave, sal) == guardado


def usuario_por_token(token):
    if not token:
        return None
    try:
        conexion = conectar()
    except Exception:
        crear_local()
        conexion = conectar_local()
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.nombre, u.correo
            FROM sesiones s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token = %s
            """,
            (token,),
        )
        fila = cursor.fetchone()
    conexion.close()
    return fila


def leer_json(handler):
    largo = int(handler.headers.get("Content-Length") or 0)
    if largo <= 0:
        return {}
    return json.loads(handler.rfile.read(largo).decode("utf-8"))


def token_de(handler):
    auth = handler.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return ""


def codigo_verificacion():
    return "".join(secrets.choice("0123456789") for _ in range(6))


def enviar_correo_verificacion(destino, codigo, token):
    enlace = "http://127.0.0.1:%s/cuenta.html?token=%s" % (PUERTO, token)
    texto = (
        "Hola,\n\n"
        "Tu código para verificar el correo en Ferretería Max es: %s\n\n"
        "También puedes abrir este enlace:\n%s\n\n"
        "El código vence en 20 minutos.\n"
    ) % (codigo, enlace)
    print("Código de verificación para %s: %s" % (destino, codigo))

    cfg = leer_config().get("smtp") or {}
    host = (cfg.get("host") or "").strip()
    usuario = (cfg.get("user") or "").strip()
    clave = cfg.get("password") or ""
    remitente = (cfg.get("remitente") or usuario or "").strip()
    puerto = int(cfg.get("port") or 587)
    if not host or not usuario or not clave:
        return False

    mensaje = EmailMessage()
    mensaje["Subject"] = "Verifica tu correo | Ferretería Max"
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje.set_content(texto)
    try:
        with smtplib.SMTP(host, puerto, timeout=20) as servidor_smtp:
            servidor_smtp.starttls()
            servidor_smtp.login(usuario, clave)
            servidor_smtp.send_message(mensaje)
        return True
    except Exception as error:
        print("No se pudo enviar el correo:", error)
        return False


def guardar_verificacion(cursor, usuario_id, correo):
    codigo = codigo_verificacion()
    token = secrets.token_hex(32)
    expira = datetime.utcnow() + timedelta(minutes=20)
    cursor.execute(
        """
        UPDATE usuarios
        SET correo_verificado = 0,
            codigo_verificacion = %s,
            token_verificacion = %s,
            verificacion_expira = %s
        WHERE id = %s
        """,
        (codigo, token, expira, usuario_id),
    )
    enviado = enviar_correo_verificacion(correo, codigo, token)
    return codigo, enviado


class ServidorFerreteria(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CARPETA, **kwargs)

    def log_message(self, formato, *args):
        print(formato % args)

    def enviar_json(self, data, codigo=200):
        cuerpo = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        ruta = unquote(parsed.path)

        if ruta == "/api/salud":
            try:
                conexion = conectar()
                conexion.close()
                self.enviar_json({"ok": True, "mysql": True, "sqlite": False})
            except Exception:
                crear_local()
                conexion = conectar_local()
                conexion.close()
                self.enviar_json({"ok": True, "mysql": False, "sqlite": True})
            return

        if ruta == "/api/sesion":
            usuario = usuario_por_token(token_de(self))
            if not usuario:
                self.enviar_json({"ok": False}, 401)
                return
            self.enviar_json({"ok": True, "usuario": usuario})
            return

        if ruta == "/api/verificar-correo" and (parsed.query or ""):
            params = parse_qs(parsed.query)
            token = (params.get("token") or [""])[0].strip()
            if token:
                self.completar_verificacion("", "", token)
            else:
                self.enviar_json({"error": "Falta el token."}, 400)
            return

        if ruta == "/api/carrito":
            usuario = usuario_por_token(token_de(self))
            if not usuario:
                self.enviar_json({"error": "Inicia sesión para ver el carrito."}, 401)
                return
            conexion = conectar_o_error(self)
            if not conexion:
                return
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.id, p.nombre, p.precio, p.icono, p.imagen, c.cantidad
                    FROM carrito c
                    JOIN productos p ON p.id = c.producto_id
                    WHERE c.usuario_id = %s
                    ORDER BY p.nombre
                    """,
                    (usuario["id"],),
                )
                items = cursor.fetchall()
            conexion.close()
            self.enviar_json({"ok": True, "items": items})
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        ruta = unquote(parsed.path)
        try:
            datos = leer_json(self)
        except Exception:
            self.enviar_json({"error": "JSON inválido."}, 400)
            return

        if ruta == "/api/registro":
            self.registrar(datos)
            return
        if ruta == "/api/verificar-correo":
            self.completar_verificacion(
                (datos.get("correo") or "").strip().lower(),
                (datos.get("codigo") or "").strip(),
                (datos.get("token") or "").strip(),
            )
            return
        if ruta == "/api/reenviar-codigo":
            self.reenviar_codigo((datos.get("correo") or "").strip().lower())
            return
        if ruta == "/api/login":
            self.login(datos)
            return
        if ruta == "/api/logout":
            self.logout()
            return
        if ruta == "/api/carrito/agregar":
            self.carrito_agregar(datos)
            return
        if ruta == "/api/carrito/cantidad":
            self.carrito_cantidad(datos)
            return
        if ruta == "/api/carrito/eliminar":
            self.carrito_eliminar(datos)
            return
        if ruta == "/api/comprar":
            self.comprar()
            return

        self.enviar_json({"error": "Ruta no encontrada."}, 404)

    def registrar(self, datos):
        nombre = (datos.get("nombre") or "").strip()
        correo = (datos.get("correo") or "").strip().lower()
        telefono = (datos.get("telefono") or "").strip()
        direccion = (datos.get("direccion") or "").strip()
        password = datos.get("password") or ""

        if not all([nombre, correo, telefono, direccion, password]):
            self.enviar_json({"error": "Por favor completa todos los campos."}, 400)
            return
        if "@" not in correo or "." not in correo.split("@")[-1]:
            self.enviar_json({"error": "Ingresa un correo válido."}, 400)
            return
        if len(password) < 6:
            self.enviar_json({"error": "La contraseña debe tener mínimo 6 caracteres."}, 400)
            return

        conexion = conectar_o_error(self)
        if not conexion:
            return
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, correo_verificado FROM usuarios WHERE correo = %s",
                    (correo,),
                )
                existente = cursor.fetchone()
                if existente and existente.get("correo_verificado"):
                    self.enviar_json({"error": "Este correo ya tiene una cuenta registrada."}, 409)
                    return
                if existente:
                    cursor.execute(
                        """
                        UPDATE usuarios
                    SET nombre = %s, telefono = %s, direccion = %s, clave_hash = %s
                    WHERE id = %s
                    """,
                        (nombre, telefono, direccion, hash_clave(password), existente["id"]),
                    )
                    usuario_id = existente["id"]
                else:
                    cursor.execute(
                        """
                    INSERT INTO usuarios
                    (nombre, correo, telefono, direccion, clave_hash, correo_verificado)
                    VALUES (%s, %s, %s, %s, %s, 0)
                    """,
                        (nombre, correo, telefono, direccion, hash_clave(password)),
                    )
                    usuario_id = cursor.lastrowid
                codigo, enviado = guardar_verificacion(cursor, usuario_id, correo)
            respuesta = {
                "ok": True,
                "nombre": nombre,
                "correo": correo,
                "correoEnviado": enviado,
                "pendienteVerificacion": True,
            }
            if not enviado:
                respuesta["codigo"] = codigo
            self.enviar_json(respuesta)
        except Exception as error:
            self.enviar_json({"error": "No se pudo guardar la cuenta: " + str(error)}, 500)
        finally:
            conexion.close()

    def completar_verificacion(self, correo, codigo, token):
        if not token and (not correo or not codigo):
            self.enviar_json({"error": "Ingresa el código que te enviamos al correo."}, 400)
            return
        conexion = conectar_o_error(self)
        if not conexion:
            return
        try:
            with conexion.cursor() as cursor:
                if token:
                    cursor.execute(
                        """
                        SELECT id, nombre, correo FROM usuarios
                        WHERE token_verificacion = %s
                          AND verificacion_expira > UTC_TIMESTAMP()
                        """,
                        (token,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, nombre, correo FROM usuarios
                        WHERE correo = %s
                          AND codigo_verificacion = %s
                          AND verificacion_expira > UTC_TIMESTAMP()
                        """,
                        (correo, codigo),
                    )
                usuario = cursor.fetchone()
                if not usuario:
                    self.enviar_json({"error": "El código no es válido o ya venció."}, 400)
                    return
                cursor.execute(
                    """
                    UPDATE usuarios
                    SET correo_verificado = 1,
                        token_verificacion = NULL,
                        codigo_verificacion = NULL,
                        verificacion_expira = NULL
                    WHERE id = %s
                    """,
                    (usuario["id"],),
                )
            self.enviar_json({"ok": True, "nombre": usuario["nombre"], "correo": usuario["correo"]})
        except Exception as error:
            self.enviar_json({"error": "No se pudo verificar el correo: " + str(error)}, 500)
        finally:
            conexion.close()

    def reenviar_codigo(self, correo):
        if not correo:
            self.enviar_json({"error": "Falta el correo."}, 400)
            return
        conexion = conectar_o_error(self)
        if not conexion:
            return
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, correo_verificado FROM usuarios WHERE correo = %s",
                    (correo,),
                )
                usuario = cursor.fetchone()
                if not usuario:
                    self.enviar_json({"error": "No hay una cuenta con ese correo."}, 404)
                    return
                if usuario.get("correo_verificado"):
                    self.enviar_json({"error": "Ese correo ya está verificado. Inicia sesión."}, 400)
                    return
                codigo, enviado = guardar_verificacion(cursor, usuario["id"], correo)
            respuesta = {"ok": True, "correoEnviado": enviado}
            if not enviado:
                respuesta["codigo"] = codigo
            self.enviar_json(respuesta)
        except Exception as error:
            self.enviar_json({"error": "No se pudo reenviar el código: " + str(error)}, 500)
        finally:
            conexion.close()

    def login(self, datos):
        correo = (datos.get("correo") or "").strip().lower()
        password = datos.get("password") or ""
        conexion = conectar_o_error(self)
        if not conexion:
            return
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, nombre, clave_hash, correo_verificado FROM usuarios WHERE correo = %s",
                    (correo,),
                )
                usuario = cursor.fetchone()
                if not usuario or not verificar_clave(password, usuario["clave_hash"]):
                    self.enviar_json({"error": "Correo o contraseña incorrectos."}, 401)
                    return
                if not usuario.get("correo_verificado"):
                    self.enviar_json(
                        {
                            "error": "Debes verificar tu correo antes de iniciar sesión.",
                            "requiereVerificacion": True,
                            "correo": correo,
                        },
                        403,
                    )
                    return
                token = secrets.token_hex(32)
                cursor.execute(
                    "INSERT INTO sesiones (token, usuario_id) VALUES (%s, %s)",
                    (token, usuario["id"]),
                )
            self.enviar_json({"ok": True, "token": token, "nombre": usuario["nombre"]})
        except Exception as error:
            self.enviar_json({"error": "No se pudo iniciar sesión: " + str(error)}, 500)
        finally:
            conexion.close()

    def logout(self):
        token = token_de(self)
        if token:
            conexion = conectar_o_error(self)
            if not conexion:
                return
            with conexion.cursor() as cursor:
                cursor.execute("DELETE FROM sesiones WHERE token = %s", (token,))
            conexion.close()
        self.enviar_json({"ok": True})

    def carrito_agregar(self, datos):
        usuario = usuario_por_token(token_de(self))
        if not usuario:
            self.enviar_json({"error": "Inicia sesión para comprar."}, 401)
            return
        nombre = (datos.get("nombre") or "").strip()
        conexion = conectar_o_error(self)
        if not conexion:
            return
        try:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT id FROM productos WHERE nombre = %s", (nombre,))
                producto = cursor.fetchone()
                if not producto:
                    self.enviar_json({"error": "No se encontró el producto."}, 404)
                    return
                cursor.execute(
                    """
                    INSERT INTO carrito (usuario_id, producto_id, cantidad)
                    VALUES (%s, %s, 1)
                    ON DUPLICATE KEY UPDATE cantidad = cantidad + 1
                    """,
                    (usuario["id"], producto["id"]),
                )
            self.enviar_json({"ok": True, "nombre": nombre})
        finally:
            conexion.close()

    def carrito_cantidad(self, datos):
        usuario = usuario_por_token(token_de(self))
        if not usuario:
            self.enviar_json({"error": "Inicia sesión."}, 401)
            return
        producto_id = int(datos.get("productoId") or 0)
        cambio = int(datos.get("cambio") or 0)
        conexion = conectar_o_error(self)
        if not conexion:
            return
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT cantidad FROM carrito WHERE usuario_id = %s AND producto_id = %s",
                (usuario["id"], producto_id),
            )
            fila = cursor.fetchone()
            if not fila:
                conexion.close()
                self.enviar_json({"error": "Ese producto no está en el carrito."}, 404)
                return
            nueva = fila["cantidad"] + cambio
            if nueva <= 0:
                cursor.execute(
                    "DELETE FROM carrito WHERE usuario_id = %s AND producto_id = %s",
                    (usuario["id"], producto_id),
                )
            else:
                cursor.execute(
                    "UPDATE carrito SET cantidad = %s WHERE usuario_id = %s AND producto_id = %s",
                    (nueva, usuario["id"], producto_id),
                )
        conexion.close()
        self.enviar_json({"ok": True})

    def carrito_eliminar(self, datos):
        usuario = usuario_por_token(token_de(self))
        if not usuario:
            self.enviar_json({"error": "Inicia sesión."}, 401)
            return
        producto_id = int(datos.get("productoId") or 0)
        conexion = conectar_o_error(self)
        if not conexion:
            return
        with conexion.cursor() as cursor:
            cursor.execute(
                "DELETE FROM carrito WHERE usuario_id = %s AND producto_id = %s",
                (usuario["id"], producto_id),
            )
        conexion.close()
        self.enviar_json({"ok": True})

    def comprar(self):
        usuario = usuario_por_token(token_de(self))
        if not usuario:
            self.enviar_json({"error": "Inicia sesión."}, 401)
            return
        conexion = conectar_o_error(self)
        if not conexion:
            return
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.id, p.precio, c.cantidad
                    FROM carrito c
                    JOIN productos p ON p.id = c.producto_id
                    WHERE c.usuario_id = %s
                    """,
                    (usuario["id"],),
                )
                items = cursor.fetchall()
                if not items:
                    self.enviar_json({"error": "Tu carrito está vacío."}, 400)
                    return
                total = sum(item["precio"] * item["cantidad"] for item in items)
                cursor.execute(
                    "INSERT INTO pedidos (usuario_id, total) VALUES (%s, %s)",
                    (usuario["id"], total),
                )
                pedido_id = cursor.lastrowid
                for item in items:
                    cursor.execute(
                        """
                        INSERT INTO pedido_detalle (pedido_id, producto_id, cantidad, precio)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (pedido_id, item["id"], item["cantidad"], item["precio"]),
                    )
                cursor.execute("DELETE FROM carrito WHERE usuario_id = %s", (usuario["id"],))
            self.enviar_json({"ok": True, "total": total, "pedidoId": pedido_id})
        finally:
            conexion.close()


def main():
    os.chdir(CARPETA)
    liberar_puerto(PUERTO)
    crear_local()
    try:
        crear_base()
        print("MySQL conectado.", flush=True)
    except Exception as error:
        print("MySQL no disponible (" + str(error) + "). Usando base local ferreteria_local.db", flush=True)
    try:
        servidor = ThreadingHTTPServer(("127.0.0.1", PUERTO), ServidorFerreteria)
    except OSError:
        print("El puerto %s sigue ocupado. Cierra las ventanas negras de Python y vuelve a abrir abrir-tienda.bat." % PUERTO, flush=True)
        raise
    print("Abre: http://127.0.0.1:%s/cuenta.html" % PUERTO, flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()
