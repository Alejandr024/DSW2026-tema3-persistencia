# Archivo: app/blueprints/public.py
from flask import (
    Blueprint,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
    abort,
)
from flask_login import login_required
from app.models import db, Producto

# Creamos el Blueprint 'public' sin prefijo de URL (cuelga directamente de /)
public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    return redirect(url_for("public.mostrar_catalogo"))


@public_bp.route("/catalogo")
def mostrar_catalogo():
    productos = Producto.query.all()
    ultimo = request.cookies.get("ultimo_visto")
    return render_template(
        "catalogo.html", lista_productos=productos, ultimo_visto=ultimo
    )


@public_bp.route("/producto/<int:prod_id>")
def ver_producto(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    respuesta = make_response(
        render_template("producto_detalle.html", producto=producto)
    )
    respuesta.set_cookie(
        "ultimo_visto",
        value=producto.nombre,
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        samesite="Lax",
    )
    return respuesta


@public_bp.route("/limpiar-historial")
def limpiar_historial():
    respuesta = make_response(redirect(url_for("public.mostrar_catalogo")))
    respuesta.delete_cookie("ultimo_visto")
    return respuesta


# --- RUTAS DEL CARRITO (Requieren haber iniciado sesión) ---


@public_bp.route("/carrito/anadir/<int:prod_id>", methods=["POST"])
@login_required
def anadir_al_carrito(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    session.permanent = True
    if "carrito" not in session:
        session["carrito"] = []
        if producto.disponible:
            session["carrito"].append(producto.id)
            session.modified = True
            flash(f"¡{producto.nombre} añadido al carrito!", "exito")
    return redirect(url_for("public.mostrar_catalogo"))


@public_bp.route("/carrito")
@login_required
def ver_carrito():
    ids_carrito = session.get("carrito", [])
    # Creamos la varibale para guardar el total a pagar del carrito
    total = 0
    # guardamos la cantidades de cada producto
    cantidades = {}
    # Consultamos en la base de datos los productos cuyos IDs estén en la lista
    if ids_carrito:
        productos_carrito = Producto.query.filter(Producto.id.in_(ids_carrito)).all()
        for prod in productos_carrito:
            # contamos la cantidad en ese producto
            cantidad = ids_carrito.count(prod.id)
            # guardamos la cantidad
            cantidades[prod.id] = cantidad
            # sumamos su total al total a pagar
            total += prod.precio * cantidad
    else:
        productos_carrito = []
    return render_template(
        "carrito.html", productos=productos_carrito, total=total, cantidades=cantidades
    )


# Eliminar un producto del carrito
@public_bp.route("/carrito/eliminar/<int:prod_id>", methods=["POST"])
@login_required
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
    return redirect(url_for("public.ver_carrito"))


@public_bp.route("/carrito/vaciar", methods=["POST"])
@login_required
def vaciar_carrito():
    session.pop("carrito", None)
    flash("Has vaciado tu carrito de la compra.", "info")
    return redirect(url_for("public.mostrar_catalogo"))


@public_bp.route("/tema/<string:modo>")
def cambiar_tema(modo):
    if modo not in ("claro", "oscuro"):
        return abort(404)

    respuesta = make_response(redirect(url_for("public.mostrar_catalogo")))
    respuesta.set_cookie("tema", modo, max_age=30 * 24 * 60 * 60)
    return respuesta
