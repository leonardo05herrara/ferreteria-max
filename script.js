// ==========================================
// FERRETERÍA MAX
// SISTEMA DE CUENTAS CON localStorage
// ==========================================

function mostrarError(id, texto) {
    const caja = document.getElementById(id);
    if (!caja) {
        return;
    }
    caja.textContent = texto;
    caja.style.display = 'block';
}

function limpiarError(id) {
    const caja = document.getElementById(id);
    if (!caja) {
        return;
    }
    caja.textContent = '';
    caja.style.display = 'none';
}

function tokenSesion() {
    return localStorage.getItem('tokenFerreteria') || '';
}

function haySesion() {
    return localStorage.getItem('sesionActiva') === 'true' && !!tokenSesion();
}

async function api(ruta, opciones) {
    const headers = {
        'Content-Type': 'application/json'
    };
    if (tokenSesion()) {
        headers.Authorization = 'Bearer ' + tokenSesion();
    }
    const url = 'http://127.0.0.1:8766' + ruta;
    let respuesta;
    try {
        respuesta = await fetch(url, Object.assign({ headers: headers }, opciones || {}));
    } catch (error) {
        throw new Error('No hay conexión con el servidor. Cierra otras ventanas de Python, abre abrir-tienda.bat y entra a http://127.0.0.1:8766/cuenta.html');
    }
    const texto = await respuesta.text();
    let data = {};
    try {
        data = texto ? JSON.parse(texto) : {};
    } catch (error) {
        throw new Error('Todavía hay un servidor viejo en el puerto 8766. Cierra las ventanas negras de Python, abre abrir-tienda.bat y recarga http://127.0.0.1:8766/cuenta.html');
    }
    if (!respuesta.ok) {
        const err = new Error(data.error || 'No se pudo completar la operación en MySQL.');
        err.data = data;
        throw err;
    }
    return data;
}

const registroForm = document.getElementById('registroForm');

function mostrarCajaVerificar(correo, codigo, enviado) {
    const registroForm = document.getElementById('registroForm');
    const verificarForm = document.getElementById('verificarForm');
    const correoInput = document.getElementById('correoVerificar');
    const aviso = document.getElementById('avisoCodigo');
    const texto = document.getElementById('textoVerificar');
    if (!verificarForm || !correoInput) {
        return;
    }
    correoInput.value = correo;
    if (registroForm) {
        registroForm.hidden = true;
    }
    verificarForm.hidden = false;
    if (texto) {
        texto.textContent = enviado
            ? 'Ingresa el código de 6 dígitos que enviamos a ' + correo + '.'
            : 'No se pudo enviar el correo a ' + correo + '. Usa el código de abajo.';
    }
    if (aviso) {
        if (codigo) {
            aviso.hidden = false;
            aviso.textContent = 'Tu código es: ' + codigo;
        } else {
            aviso.hidden = true;
            aviso.textContent = '';
        }
    }
    const codigoInput = document.getElementById('codigoVerificar');
    if (codigoInput) {
        codigoInput.value = '';
        codigoInput.focus();
    }
}

function correoVerificadoOk(data) {
    const verificarForm = document.getElementById('verificarForm');
    const registroForm = document.getElementById('registroForm');
    if (verificarForm) {
        verificarForm.hidden = true;
    }
    if (registroForm) {
        registroForm.hidden = false;
        registroForm.reset();
    }
    const loginUsuario = document.getElementById('loginUsuario');
    if (loginUsuario && data.correo) {
        loginUsuario.value = data.correo;
    }
    const loginPassword = document.getElementById('loginPassword');
    if (loginPassword) {
        loginPassword.focus();
    }
    alert('Correo verificado. Ya puedes iniciar sesión, ' + (data.nombre || '') + '.');
}

if (registroForm) {
    registroForm.addEventListener('submit', function (event) {
        event.preventDefault();
        limpiarError('mensajeError');

        const nombre = document.getElementById('nombre').value.trim();
        const correo = document.getElementById('correo').value.trim().toLowerCase();
        const telefono = document.getElementById('telefono').value.trim();
        const direccion = document.getElementById('direccion').value.trim();
        const password = document.getElementById('password').value;
        const correoRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!nombre || !correo || !telefono || !direccion || !password) {
            mostrarError('mensajeError', 'Por favor completa todos los campos.');
            return;
        }

        if (!correoRegex.test(correo)) {
            mostrarError('mensajeError', 'Ingresa un correo válido. Ejemplo: usuario@gmail.com');
            return;
        }

        if (!/^\d{10}$/.test(telefono)) {
            mostrarError('mensajeError', 'Ingresa un teléfono válido de 10 dígitos.');
            return;
        }

        if (password.length < 6) {
            mostrarError('mensajeError', 'La contraseña debe tener mínimo 6 caracteres.');
            return;
        }

        api('/api/registro', {
            method: 'POST',
            body: JSON.stringify({
                nombre: nombre,
                correo: correo,
                telefono: telefono,
                direccion: direccion,
                password: password
            })
        }).then(function (data) {
            mostrarCajaVerificar(data.correo || correo, data.codigo, data.correoEnviado);
        }).catch(function (error) {
            mostrarError('mensajeError', error.message);
        });
    });
}

const verificarForm = document.getElementById('verificarForm');

if (verificarForm) {
    verificarForm.addEventListener('submit', function (event) {
        event.preventDefault();
        limpiarError('mensajeVerificar');
        const correo = document.getElementById('correoVerificar').value.trim().toLowerCase();
        const codigo = document.getElementById('codigoVerificar').value.trim();
        if (!/^\d{6}$/.test(codigo)) {
            mostrarError('mensajeVerificar', 'El código debe tener 6 dígitos.');
            return;
        }
        api('/api/verificar-correo', {
            method: 'POST',
            body: JSON.stringify({ correo: correo, codigo: codigo })
        }).then(correoVerificadoOk).catch(function (error) {
            mostrarError('mensajeVerificar', error.message);
        });
    });
}

const btnReenviarCodigo = document.getElementById('btnReenviarCodigo');

if (btnReenviarCodigo) {
    btnReenviarCodigo.addEventListener('click', function () {
        limpiarError('mensajeVerificar');
        const correo = document.getElementById('correoVerificar').value.trim().toLowerCase();
        api('/api/reenviar-codigo', {
            method: 'POST',
            body: JSON.stringify({ correo: correo })
        }).then(function (data) {
            mostrarCajaVerificar(correo, data.codigo, data.correoEnviado);
            const ok = document.getElementById('mensajeVerificarOk');
            if (ok) {
                ok.style.display = 'block';
                ok.textContent = data.correoEnviado
                    ? 'Te enviamos un código nuevo al correo.'
                    : 'Generamos un código nuevo.';
            }
        }).catch(function (error) {
            mostrarError('mensajeVerificar', error.message);
        });
    });
}

const loginForm = document.getElementById('loginForm');

if (loginForm) {
    loginForm.addEventListener('submit', function (event) {
        event.preventDefault();
        limpiarError('mensajeLogin');

        const usuario = document.getElementById('loginUsuario').value.trim().toLowerCase();
        const password = document.getElementById('loginPassword').value;

        api('/api/login', {
            method: 'POST',
            body: JSON.stringify({
                correo: usuario,
                password: password
            })
        }).then(function (data) {
            localStorage.setItem('tokenFerreteria', data.token);
            localStorage.setItem('sesionActiva', 'true');
            localStorage.setItem('nombreUsuario', data.nombre);
            alert('¡Bienvenido/a ' + data.nombre + '!');
            loginForm.reset();
            actualizarSesion();
            actualizarCarrito();
        }).catch(function (error) {
            if (error.data && error.data.requiereVerificacion) {
                const correoPendiente = error.data.correo || usuario;
                api('/api/reenviar-codigo', {
                    method: 'POST',
                    body: JSON.stringify({ correo: correoPendiente })
                }).then(function (data) {
                    mostrarCajaVerificar(correoPendiente, data.codigo, data.correoEnviado);
                }).catch(function () {
                    mostrarCajaVerificar(correoPendiente, null, true);
                });
            }
            mostrarError('mensajeLogin', error.message);
        });
    });
}

// ==========================================
// ACTUALIZAR SESIÓN
// ==========================================

function actualizarSesion() {

    const sesion =
        localStorage.getItem("sesionActiva");

    const nombre =
        localStorage.getItem("nombreUsuario");

    const botonLogin =
        document.querySelector(".btn-login");


    if (
        sesion === "true" &&
        nombre &&
        tokenSesion()
    ) {

        if (botonLogin) {

            botonLogin.textContent =
                "Cerrar sesión";

            botonLogin.href = "#";

            botonLogin.onclick =
                function(event) {

                    event.preventDefault();

                    cerrarSesion();

                };

        }

        console.log(
            "Sesión iniciada: " + nombre
        );

    }

}


// ==========================================
// CERRAR SESIÓN
// ==========================================

function cerrarSesion() {
    api('/api/logout', { method: 'POST', body: '{}' }).catch(function () {});
    localStorage.removeItem('sesionActiva');
    localStorage.removeItem('nombreUsuario');
    localStorage.removeItem('tokenFerreteria');
    alert('Has cerrado sesión correctamente.');
    actualizarBotonLogin();
    actualizarCarrito();
}


// ==========================================
// RESTAURAR BOTÓN DE LOGIN
// ==========================================

function actualizarBotonLogin() {

    const botonLogin =
        document.querySelector(".btn-login");


    if (botonLogin) {

        botonLogin.textContent =
            "Iniciar sesión";

        botonLogin.href = "cuenta.html";

        botonLogin.onclick = null;

    }

}


// ==========================================
// BOTONES DE COMPRA
// ==========================================

function agregarProducto(nombreProducto) {

    if (!haySesion()) {
        alert('Para comprar un producto primero debes iniciar sesión.');
        window.location.href = 'cuenta.html';
        return;
    }

    api('/api/carrito/agregar', {
        method: 'POST',
        body: JSON.stringify({ nombre: nombreProducto })
    }).then(function () {
        actualizarCarrito();
        alert('✓ ' + nombreProducto + ' fue agregado al carrito.');
    }).catch(function (error) {
        alert(error.message);
    });
}

function pintarCarrito(carrito) {
    const contenedor = document.getElementById("productosCarrito");
    const contador = document.getElementById("contadorCarrito");
    const cantidadTexto = document.getElementById("cantidadCarrito");
    const subtotalTexto = document.getElementById("subtotalCarrito");
    const totalTexto = document.getElementById("totalCarrito");

    let cantidadTotal = 0;
    let subtotal = 0;
    carrito.forEach(function (producto) {
        cantidadTotal += producto.cantidad;
        subtotal += producto.precio * producto.cantidad;
    });

    if (contador) {
        contador.textContent = String(cantidadTotal);
    }

    if (!contenedor) {
        return;
    }

    if (carrito.length === 0) {
        contenedor.innerHTML = `
            <div class="carrito-vacio">
                <div class="carrito-vacio-icono">🛒</div>
                <h3>Tu carrito está vacío</h3>
                <p>Agrega algunos productos para comenzar tu compra.</p>
                <a href="productos.html" class="btn-primary">Ver productos</a>
            </div>
        `;
        if (cantidadTexto) cantidadTexto.textContent = "0";
        if (subtotalTexto) subtotalTexto.textContent = "$0 COP";
        if (totalTexto) totalTexto.textContent = "$0 COP";
        return;
    }

    contenedor.innerHTML = "";
    carrito.forEach(function (producto) {
        const caja = document.createElement("div");
        caja.className = "item-carrito";
        caja.innerHTML = `
            <div class="item-carrito-info">
                <div class="item-carrito-icono">
                    ${producto.imagen ? `<img src="${producto.imagen}" alt="${producto.nombre}">` : (producto.icono || "🛒")}
                </div>
                <div>
                    <h3>${producto.nombre}</h3>
                    <p>$${Number(producto.precio).toLocaleString("es-CO")} COP</p>
                </div>
            </div>
            <div class="item-carrito-controles">
                <button class="btn-cantidad" onclick="cambiarCantidad(${producto.id}, -1)">−</button>
                <span class="cantidad">${producto.cantidad}</span>
                <button class="btn-cantidad" onclick="cambiarCantidad(${producto.id}, 1)">+</button>
                <button class="btn-eliminar" onclick="eliminarProducto(${producto.id}, '${String(producto.nombre).replace(/'/g, "\\'")}')">Eliminar</button>
            </div>
        `;
        contenedor.appendChild(caja);
    });

    if (cantidadTexto) cantidadTexto.textContent = cantidadTotal;
    if (subtotalTexto) subtotalTexto.textContent = "$" + subtotal.toLocaleString("es-CO") + " COP";
    if (totalTexto) totalTexto.textContent = "$" + subtotal.toLocaleString("es-CO") + " COP";
}

function actualizarCarrito() {
    if (!haySesion()) {
        pintarCarrito([]);
        return;
    }
    api("/api/carrito").then(function (data) {
        pintarCarrito(data.items || []);
    }).catch(function () {
        pintarCarrito([]);
    });
}

function cambiarCantidad(productoId, cambio) {
    api("/api/carrito/cantidad", {
        method: "POST",
        body: JSON.stringify({ productoId: productoId, cambio: cambio })
    }).then(actualizarCarrito).catch(function (error) {
        alert(error.message);
    });
}

function eliminarProducto(productoId, nombreProducto) {
    if (!confirm("¿Quieres eliminar " + nombreProducto + " del carrito?")) {
        return;
    }
    api("/api/carrito/eliminar", {
        method: "POST",
        body: JSON.stringify({ productoId: productoId })
    }).then(actualizarCarrito).catch(function (error) {
        alert(error.message);
    });
}

function finalizarCompra() {
    const mensaje = document.getElementById("mensajeCompra");
    if (!haySesion()) {
        if (mensaje) mensaje.textContent = "Inicia sesión para finalizar la compra.";
        return;
    }
    api("/api/comprar", { method: "POST", body: "{}" }).then(function (data) {
        if (mensaje) {
            mensaje.innerHTML = "<strong>Compra realizada con éxito.</strong><br>Pedido #" +
                data.pedidoId + "<br>Total: $" + Number(data.total).toLocaleString("es-CO") + " COP";
            mensaje.style.display = "block";
        }
        actualizarCarrito();
    }).catch(function (error) {
        if (mensaje) {
            mensaje.textContent = error.message;
            mensaje.style.display = "block";
        } else {
            alert(error.message);
        }
    });
}

// ==========================================
// FORMULARIO DE CONTACTO
// ==========================================

const formularioContacto =
    document.querySelector(".contact-form");


if (formularioContacto) {

    formularioContacto.addEventListener(
        "submit",
        function(event) {

            event.preventDefault();


            alert(
                "¡Mensaje enviado correctamente!\n\n" +
                "Gracias por comunicarte con " +
                "Ferretería Max."
            );


            formularioContacto.reset();

        }
    );

}


// ==========================================
// COMPROBAR SESIÓN AL ABRIR LA PÁGINA
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        actualizarSesion();
        actualizarCarrito();
        marcarPaginaActiva();

        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            api('/api/verificar-correo', {
                method: 'POST',
                body: JSON.stringify({ token: token })
            }).then(function (data) {
                window.history.replaceState({}, '', 'cuenta.html');
                correoVerificadoOk(data);
            }).catch(function (error) {
                mostrarCajaVerificar('', null, true);
                mostrarError('mensajeVerificar', error.message);
            });
        }
    }
);

function marcarPaginaActiva() {
    const archivo = (window.location.pathname.split("/").pop() || "INDEX.HTML").toLowerCase();
    const pagina = archivo === "" ? "index.html" : archivo;
    const hash = window.location.hash;

    document.querySelectorAll(".menu a").forEach(function (enlace) {
        const href = (enlace.getAttribute("href") || "").toLowerCase();
        if (href === pagina || (pagina === "index.html" && href === "index.html")) {
            enlace.classList.add("activo");
        }
    });

    document.querySelectorAll(".catalogo-filtros a").forEach(function (enlace) {
        if (hash && enlace.getAttribute("href") === hash) {
            enlace.classList.add("activo");
        }
    });
}