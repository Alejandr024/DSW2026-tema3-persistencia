from flask import Flask, render_template, url_for, redirect
from app.models import db, Producto
from app.forms import ProductoForm


app = Flask(__name__)
app.config["SECRET_KEY"] = "una_contraseña_segura_al_azar"

# Configuracion de la base de datos (En local= SQLite)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tienda.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

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
    return render_template("catalogo.html", lista_productos=productos)


# 2. CREATE: Mostrar formulario y guardar un nuevo producto en la BD
@app.route("/producto/nuevo", methods=["GET", "POST"])
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        # Llega con POST
        nuevo_prod = Producto(
            nombre=form.nombre.data,
            precio=form.precio.data,
            disponible=form.disponible.data,
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
        # Modificamos directamente los atributos del objeto recuperado de la BD
        producto.nombre = form.nombre.data
        producto.precio = form.precio.data
        producto.disponible = form.disponible.data

        # Confirmamos los cambios en la BD
        db.session.commit()
        return redirect(url_for("mostrar_catalogo"))

    return render_template("producto_form.html", form=form, titulo="Editar Producto")


# 4. DELETE: Eliminar un producto de la BD (exclusivamente por POST, para que nadie elimine cualquier producto a partir de la barra de navegación)
@app.route("/producto/<int:prod_id>/eliminar", methods=["POST"])
def eliminar_producto(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    db.session.delete(producto)
    db.session.commit()
    return redirect(url_for("mostrar_catalogo"))


@app.route("/nuevo-producto/<string:nombre>/<float:precio>")
def nuevo_producto(nombre, precio):
    nuevo_producto = Producto(nombre=nombre, precio=precio)
    db.session.add(nuevo_producto)
    db.session.commit()
    return f"Producto agregado a la BD. Nombre: {nuevo_producto.nombre} Precio: {nuevo_producto.precio}"


if __name__ == "__main__":
    app.run(debug=True)
