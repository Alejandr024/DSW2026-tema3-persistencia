import os
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    render_template,
    url_for,
    redirect,
    request,
    make_response,
    session,
    flash,
    abort,
)
from app.models import Usuario, db, Producto
from app.forms import ProductoForm, RegistroForm, LoginForm, CambiarPassword
from datetime import timedelta
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from functools import wraps

app = Flask(__name__)
app.debug = True

app.config["SECRET_KEY"] = "una_contraseña_segura_al_azar"

toolbar = DebugToolbarExtension(app)
# Configuracion de la base de datos (En local= SQLite)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tienda.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# Configurar la carpeta destino para las imágenes
app.config["UPLOAD_FOLDER"] = os.path.join("app", "static", "img", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Límite de 2MB por seguridad

# Configuración vida útil de las sesiones permanentes(2 días)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=2)

# Viculamos SQLAlchemy con nuestra aplicación de Flask
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

# Indicamos el nombre de la función de vista a la que redirigir si un anónimo intenta entrar a una ruta protegida
login_manager.login_view = "login"
login_manager.login_message = "Por favor, inicia sesión para acceder a esta sección."
login_manager.login_message_category = "info"


@login_manager.user_loader
def cargar_usuario(user_id):
    """Recupera el objeto Usuario desde tienda.db a partir del ID guardado en la cookie session."""
    return db.session.get(Usuario, int(user_id))


def admin_required(f):
    """Decorador que restringe el acceso exclusivamente a usuarios con rol 'admin'."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Si es un visitante anónimo, lo enviamos al formulario de login
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        # 2. Si está logueado pero NO es administrador, lanzamos error HTTP 403 (Prohibido)
        if not current_user.es_admin:
            abort(403)
        # 3. Si es admin, ejecutamos la función de vista original con normalidad
        return f(*args, **kwargs)

    return decorated_function


with app.app_context():
    db.create_all()  # Crea las tablas en la base de datos (si no existieran)

    if not Producto.query.first():
        nuevo_producto = Producto(nombre="Teclado Mecánico RGB", precio=49.99)
        db.session.add(nuevo_producto)
        db.session.commit()
        print(">>>> Producto de prueba insertado en la BB. <<<<", nuevo_producto)
    # 2. Semilla de usuarios de prueba (Administrador y Cliente)
    if not Usuario.query.first():
        admin = Usuario(username="admin", email="admin@tienda.com", rol="admin")
        admin.set_password("admin123")

        cliente = Usuario(username="cliente", email="cliente@tienda.com", rol="cliente")
        cliente.set_password("cliente123")

        db.session.add_all([admin, cliente])
        db.session.commit()
        print(">>> Usuarios de prueba (admin y cliente) creados correctamente.")


@app.route("/")
def home():
    return redirect(url_for("mostrar_catalogo"))


# 1. READ: Mostrar todos los productos en la plantilla catalogo.html
@app.route("/catalogo")
def mostrar_catalogo():
    productos = Producto.query.all()
    ultimo = request.cookies.get("ultimo_visto")
    return render_template(
        "catalogo.html", lista_productos=productos, ultimo_visto=ultimo
    )


# 2. CREATE: Mostrar formulario y guardar un nuevo producto en la BD
@app.route("/producto/nuevo", methods=["GET", "POST"])
@admin_required
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        # Llega con POST
        nombre_imagen = None

        # Procesar el upload de la imagen
        if form.archivo_imagen.data:  # Chequea si se ha subido una imagen
            archivo = form.archivo_imagen.data
            nombre_imagen = secure_filename(archivo.filename)

            # Asegurar que la ruta existe
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

            # Guardar el fichero
            archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre_imagen))

        nuevo_prod = Producto(
            nombre=form.nombre.data,
            precio=form.precio.data,
            disponible=form.disponible.data,
            imagen=nombre_imagen,
        )

        db.session.add(nuevo_prod)
        db.session.commit()
        # Patrón PRG: Redirigimos tras procesar el POST con éxito
        return redirect(url_for("mostrar_catalogo"))
    # Llega con GET
    return render_template("producto_form.html", form=form, titulo="Nuevo Producto")


# 3. UPDATE: Recuperar un producto existente, rellenar el formulario y guardar cambios
@app.route("/producto/<int:prod_id>/editar", methods=["GET", "POST"])
@admin_required
def editar_producto(prod_id):
    # Busca el producto por su clave primaria o lanza un error 404 si no existe
    producto = db.get_or_404(Producto, prod_id)

    # Al pasar obj=producto, en la petición GET los campos aparecen ya rellenos con los datos actuales
    form = ProductoForm(obj=producto)

    if form.validate_on_submit():
        # Actualizar los datos
        producto.nombre = form.nombre.data
        producto.precio = form.precio.data
        producto.disponible = form.disponible.data

        if form.archivo_imagen.data:  # Chequea si se ha subido una imagen
            archivo = form.archivo_imagen.data
            nombre_imagen = secure_filename(archivo.filename)

            # Asegurar que la ruta existe
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

            # Asegurar que la ruta existe
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            # Guardar el fichero
            archivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nombre_imagen))

            # Eliminar el archivo anterior:

            if producto.imagen and producto.imagen != nombre_imagen:
                ruta_antigua = os.path.join(
                    app.config["UPLOAD_FOLDER"], producto.imagen
                )
                if os.path.exists(ruta_antigua):
                    os.remove(ruta_antigua)

            producto.imagen = nombre_imagen
        # Confirmamos los cambios en la BD
        db.session.commit()
        return redirect(url_for("mostrar_catalogo"))

    return render_template(
        "producto_form.html", form=form, titulo="Editar Producto", producto=producto
    )


# 4. DELETE: Eliminar un producto de la BD (exclusivamente por POST, para que nadie elimine cualquier producto a partir de la barra de navegación)
@app.route("/producto/<int:prod_id>/eliminar", methods=["POST"])
@admin_required
def eliminar_producto(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for("mostrar_catalogo"))


@app.route("/producto/<int:prod_id>")
def ver_producto(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    respuesta = make_response(
        render_template("producto_detalle.html", producto=producto)
    )
    # Crea la cookie
    respuesta.set_cookie(
        "ultimo_visto",
        value=producto.nombre,
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        samesite="Lax",
    )

    return respuesta


@app.route("/carrito/anadir/<int:prod_id>", methods=["POST"])
@login_required
def anadir_al_carrito(prod_id):
    # Se puede hacer esto para mostrar el nombre, pero como el esacio del carrito es pequeño (4KB) solo guardamos el id del producto, y no hace falta este codigo
    # producto = db.get_or_404(Producto, prod_id)
    # Activamos la persistencia para que no se borre al cerrar el navegador
    session.permanent = True

    # Si el usuario aún no tiene carrito en su sesión, inicializamos una lista vacía
    if "carrito" not in session:
        session["carrito"] = []

    # Guardamos SOLO el ID del producto
    session["carrito"].append(prod_id)

    # IMPORTANTE: Al mutar una lista interna, avisamos a Flask para que re-firme la sesión
    session.modified = True

    # Lanzamos un mensaje de confirmación de un solo uso
    flash("Añadido producto al carrito", "exito")

    return redirect(url_for("mostrar_catalogo"))


# 2. Ver el contenido del carrito
@app.route("/carrito")
@login_required
def ver_carrito():
    # Obtenemos la lista de IDs (o una lista vacía si no hay carrito)
    ids_carrito = session.get("carrito", [])

    # Consultamos en la base de datos los productos cuyos IDs estén en la lista
    if ids_carrito:
        productos_carrito = Producto.query.filter(Producto.id.in_(ids_carrito)).all()
    else:
        productos_carrito = []

    return render_template("carrito.html", productos=productos_carrito)


# 3. Vaciar el carrito (vía POST)
@app.route("/carrito/vaciar", methods=["POST"])
def vaciar_carrito():
    # Eliminamos únicamente la clave 'carrito' de la sesión
    session.pop("carrito", None)
    flash("Has vaciado tu carrito de la compra.", "info")
    return redirect(url_for("mostrar_catalogo"))


# Eliminar un producto del carrito
@app.route("/carrito/eliminar/<int:prod_id>", methods=["POST"])
def eliminar_del_carrito(prod_id):
    if "carrito" in session and prod_id in session["carrito"]:
        # 1. Buscar el producto en la base de datos para obtener su nombre
        producto = Producto.query.get(prod_id)
        nombre_producto = producto.nombre if producto else "Producto desconocido"

        # 2. Eliminar del carrito
        session["carrito"].remove(prod_id)
        session.modified = True

        # 3. Usar una f-string (la 'f' antes de las comillas) para inyectar la variable
        flash(
            f"Has vaciado, de tu carrito, el producto siguiente: {nombre_producto}.",
            "info",
        )
    return redirect(url_for("ver_carrito"))


# 1. REGISTRO DE NUEVOS CLIENTES
@app.route("/registro", methods=["GET", "POST"])
def registro():
    # Si el usuario ya tiene sesión iniciada, lo enviamos al catálogo
    if current_user.is_authenticated:
        return redirect(url_for("mostrar_catalogo"))

    form = RegistroForm()
    if form.validate_on_submit():
        nuevo_usuario = Usuario(
            username=form.username.data,
            email=form.email.data,
            rol="cliente",  # Todo registro público nace con rol 'cliente'
        )
        nuevo_usuario.set_password(form.password.data)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("¡Cuenta creada con éxito! Ya puedes iniciar sesión.", "exito")
        return redirect(url_for("login"))

    return render_template("registro.html", form=form)


# 2. INICIO DE SESIÓN (LOGIN)
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("mostrar_catalogo"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data).first()

        # Comprobamos que el correo exista y que el hash coincida con la contraseña
        if usuario and usuario.check_password(form.password.data):
            # Registra al usuario en la sesión (y crea cookie persistente si marcó 'remember')
            login_user(usuario, remember=form.remember.data)
            flash(f"¡Bienvenido de nuevo, {usuario.username}!", "exito")

            # Si venía redirigido desde una ruta protegida (parámetro ?next=...), lo devolvemos allí
            siguiente_pagina = request.args.get("next")
            if siguiente_pagina and siguiente_pagina.startswith("/"):
                return redirect(siguiente_pagina)
            return redirect(url_for("mostrar_catalogo"))
        else:
            flash("Correo electrónico o contraseña incorrectos.", "error")

    return render_template("login.html", form=form)


# 3. CIERRE DE SESIÓN (LOGOUT)
@app.route("/logout")
@login_required
def logout():
    logout_user()  # Elimina el ID del usuario de la cookie session
    session.pop("carrito", None)
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for("mostrar_catalogo"))


# 4. PERFIL DEL USUARIO
@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    passwd = CambiarPassword()

    if passwd.validate_on_submit():
        if current_user.check_password(passwd.password_actual.data):
            current_user.set_password(passwd.new_password.data)
            db.session.commit()
            flash("Contraseña cambiada con éxito", "exito")
        else:
            flash("La contraseña actual es incorrecta.", "error")
    return render_template("perfil.html", passwd=passwd)


@app.route("/admin/usuarios")
@admin_required
def users():
    users_all = Usuario.query.all()

    return render_template("usuarios.html", users=users_all)


@app.route("/admin/usuario/<int:user_id>/cambiar-rol")
@admin_required
def change_rol(user_id):
    # Pista de seguridad para cambiar_rol(user_id) dentro de app/main.py:
    usuario = db.get_or_404(Usuario, user_id)

    # Evitamos que el administrador actual se quite el permiso a sí mismo por accidente
    if usuario.id == current_user.id:
        flash("No puedes cambiar tu propio rol de administrador.", "error")
    else:
        usuario.rol = "admin" if usuario.rol == "cliente" else "cliente"
        db.session.commit()
        flash(f"Rol de {usuario.username} actualizado a {usuario.rol}.", "exito")
    return redirect(url_for("users"))


if __name__ == "__main__":
    app.run(debug=True)
