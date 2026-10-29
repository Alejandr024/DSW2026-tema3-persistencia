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
)
from app.models import db, Producto
from app.forms import ProductoForm
from datetime import timedelta

app = Flask(__name__)
app.config["SECRET_KEY"] = "una_contraseña_segura_al_azar"

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

with app.app_context():
    db.create_all()  # Crea las tablas en la base de datos (si no existieran)

    if not Producto.query.first():
        nuevo_producto = Producto(nombre="Teclado Mecánico RGB", precio=49.99)
        db.session.add(nuevo_producto)
        db.session.commit()
        print(">>>> Producto de prueba insertado en la BB. <<<<", nuevo_producto)


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


if __name__ == "__main__":
    app.run(debug=True)
