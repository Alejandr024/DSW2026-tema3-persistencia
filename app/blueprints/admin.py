# Archivo: app/blueprints/admin.py
import os
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user
from werkzeug.utils import secure_filename
from app.models import db, login_manager, Producto
from app.forms import ProductoForm, Usuario

# Todas las rutas de gestión colgarán de /admin/...
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# GUARDIÁN DEL BLUEPRINT: Protege automáticamente TODAS las rutas de admin.py
@admin_bp.before_request
def verificar_permisos_admin():
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    if not current_user.es_admin:
        abort(403)


@admin_bp.route("/producto/nuevo", methods=["GET", "POST"])
def crear_producto():
    form = ProductoForm()
    if form.validate_on_submit():
        nombre_imagen = None
        if form.archivo_imagen.data:
            archivo = form.archivo_imagen.data
            nombre_imagen = secure_filename(archivo.filename)
            # Usamos current_app.config en lugar de app.config
            carpeta_subidas = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(carpeta_subidas, exist_ok=True)
            archivo.save(os.path.join(carpeta_subidas, nombre_imagen))

        nuevo_prod = Producto(
            nombre=form.nombre.data,
            precio=form.precio.data,
            disponible=form.disponible.data,
            imagen=nombre_imagen,
        )
        db.session.add(nuevo_prod)
        db.session.commit()
        flash("Producto creado correctamente.", "exito")
        return redirect(url_for("public.mostrar_catalogo"))

    return render_template("producto_form.html", form=form, titulo="Nuevo Producto")


@admin_bp.route("/producto/<int:prod_id>/editar", methods=["GET", "POST"])
def editar_producto(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    form = ProductoForm(obj=producto)

    if form.validate_on_submit():
        producto.nombre = form.nombre.data
        producto.precio = form.precio.data
        producto.disponible = form.disponible.data

        if form.archivo_imagen.data:
            archivo = form.archivo_imagen.data
            nombre_imagen = secure_filename(archivo.filename)
            carpeta_subidas = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(carpeta_subidas, exist_ok=True)
            archivo.save(os.path.join(carpeta_subidas, nombre_imagen))

            if producto.imagen and producto.imagen != nombre_imagen:
                ruta_antigua = os.path.join(carpeta_subidas, producto.imagen)
                if os.path.exists(ruta_antigua):
                    os.remove(ruta_antigua)

            producto.imagen = nombre_imagen

        db.session.commit()
        flash("Producto actualizado con éxito.", "exito")
        return redirect(url_for("public.mostrar_catalogo"))

    return render_template(
        "producto_form.html", form=form, titulo="Editar Producto", producto=producto
    )


@admin_bp.route("/producto/<int:prod_id>/eliminar", methods=["POST"])
def eliminar_producto(prod_id):
    producto = db.get_or_404(Producto, prod_id)
    db.session.delete(producto)
    db.session.commit()
    flash(f"Producto '{producto.nombre}' eliminado.", "info")
    return redirect(url_for("public.mostrar_catalogo"))


@admin_bp.route("/usuarios")
def users():
    users_all = Usuario.query.all()

    return render_template("usuarios.html", users=users_all)


@admin_bp.route("/admin/usuario/<int:user_id>/cambiar-rol", methods=["POST"])
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
    return redirect(url_for("admin.users"))
