CREATE DATABASE IF NOT EXISTS ferreteria_max
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ferreteria_max;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL,
  correo VARCHAR(160) NOT NULL UNIQUE,
  telefono VARCHAR(20) NOT NULL,
  direccion VARCHAR(200) NOT NULL,
  clave_hash VARCHAR(220) NOT NULL,
  correo_verificado TINYINT(1) NOT NULL DEFAULT 0,
  token_verificacion CHAR(64) NULL,
  codigo_verificacion CHAR(6) NULL,
  verificacion_expira DATETIME NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sesiones (
  token CHAR(64) PRIMARY KEY,
  usuario_id INT NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS productos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(160) NOT NULL UNIQUE,
  descripcion VARCHAR(255) NOT NULL,
  precio INT NOT NULL,
  icono VARCHAR(16) NOT NULL,
  imagen VARCHAR(200) NOT NULL,
  categoria VARCHAR(80) NOT NULL
);

CREATE TABLE IF NOT EXISTS carrito (
  usuario_id INT NOT NULL,
  producto_id INT NOT NULL,
  cantidad INT NOT NULL DEFAULT 1,
  PRIMARY KEY (usuario_id, producto_id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pedidos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  total INT NOT NULL,
  creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pedido_detalle (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id INT NOT NULL,
  producto_id INT NOT NULL,
  cantidad INT NOT NULL,
  precio INT NOT NULL,
  FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
  FOREIGN KEY (producto_id) REFERENCES productos(id)
);
