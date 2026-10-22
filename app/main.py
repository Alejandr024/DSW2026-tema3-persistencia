from flask import Flask
from app.models import db, Producto

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
def hello():
    return "Hello, World!"


@app.route("/test.db")
def test_db():
    productos = Producto.query.all()
    return f"Todos los producto: {productos}"


@app.route("/nuevo-producto/<string:nombre>/<float:precio>")
def nuevo_producto(nombre, precio):
    nuevo_producto = Producto(nombre=nombre, precio=precio)
    db.session.add(nuevo_producto)
    db.session.commit()
    return f"Producto agregado a la BD. Nombre: {nuevo_producto.nombre} Precio: {nuevo_producto.precio}"


if __name__ == "__main__":
    app.run(debug=True)
