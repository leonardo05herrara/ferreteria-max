# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime

from crear_mysql import CARPETA, PRODUCTOS_INICIALES
import os

RUTA_SQLITE = os.path.join(CARPETA, "ferreteria_local.db")


def sql_local(texto):
    t = texto.replace("%s", "?")
    t = t.replace("UTC_TIMESTAMP()", "datetime('now')")
    t = t.replace(
        "ON DUPLICATE KEY UPDATE cantidad = cantidad + 1",
        "ON CONFLICT(usuario_id, producto_id) DO UPDATE SET cantidad = cantidad + 1",
    )
    return t


def params_local(params):
    if not params:
        return ()
    salida = []
    for valor in params:
        if isinstance(valor, datetime):
            salida.append(valor.strftime("%Y-%m-%d %H:%M:%S"))
        else:
            salida.append(valor)
    return tuple(salida)


class CursorLocal:
    def __init__(self, conexion):
        self.conexion = conexion
        self.cur = conexion.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.conexion.conn.commit()
        self.cur.close()

    def execute(self, sql, params=()):
        self.cur.execute(sql_local(sql), params_local(params))
        return self

    def executemany(self, sql, secuencia):
        self.cur.executemany(sql_local(sql), [params_local(fila) for fila in secuencia])
        return self

    def fetchone(self):
        fila = self.cur.fetchone()
        return dict(fila) if fila else None

    def fetchall(self):
        return [dict(fila) for fila in self.cur.fetchall()]

    @property
    def lastrowid(self):
        return self.cur.lastrowid


class ConexionLocal:
    es_sqlite = True

    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        return CursorLocal(self)

    def close(self):
        self.conn.close()


def crear_local():
    conexion = sqlite3.connect(RUTA_SQLITE)
    conexion.row_factory = sqlite3.Row
    cur = conexion.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nombre TEXT NOT NULL,
          correo TEXT NOT NULL UNIQUE,
          telefono TEXT NOT NULL,
          direccion TEXT NOT NULL,
          clave_hash TEXT NOT NULL,
          correo_verificado INTEGER NOT NULL DEFAULT 0,
          token_verificacion TEXT,
          codigo_verificacion TEXT,
          verificacion_expira TEXT,
          creado_en TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sesiones (
          token TEXT PRIMARY KEY,
          usuario_id INTEGER NOT NULL,
          creado_en TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS productos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nombre TEXT NOT NULL UNIQUE,
          descripcion TEXT NOT NULL,
          precio INTEGER NOT NULL,
          icono TEXT NOT NULL,
          imagen TEXT NOT NULL,
          categoria TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS carrito (
          usuario_id INTEGER NOT NULL,
          producto_id INTEGER NOT NULL,
          cantidad INTEGER NOT NULL DEFAULT 1,
          PRIMARY KEY (usuario_id, producto_id),
          FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
          FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS pedidos (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          usuario_id INTEGER NOT NULL,
          total INTEGER NOT NULL,
          creado_en TEXT DEFAULT (datetime('now')),
          FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS pedido_detalle (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          pedido_id INTEGER NOT NULL,
          producto_id INTEGER NOT NULL,
          cantidad INTEGER NOT NULL,
          precio INTEGER NOT NULL,
          FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
          FOREIGN KEY (producto_id) REFERENCES productos(id)
        );
        """
    )
    cur.execute("SELECT COUNT(*) AS total FROM productos")
    if cur.fetchone()["total"] == 0:
        cur.executemany(
            """
            INSERT INTO productos (nombre, descripcion, precio, icono, imagen, categoria)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            PRODUCTOS_INICIALES,
        )
    conexion.commit()
    conexion.close()


def conectar_local():
    crear_local()
    conn = sqlite3.connect(RUTA_SQLITE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return ConexionLocal(conn)
