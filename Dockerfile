# Usamos una imagen oficial de Python ligera
FROM python:3.14-slim

# Instalar sudo (requerido por VS Code Dev Containers para ajustar el UID dinámicamente)
RUN apt-get update && apt-get install -y sudo && rm -rf /var/lib/apt/lists/*

# Crear el usuario vscode con UID 1000 y darle permisos de sudo sin contraseña
RUN useradd -m -s /bin/bash -u 1000 vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
    
# Instalamos uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Cambiar la propiedad de la carpeta de trabajo antes de copiar archivos
RUN chown -R vscode:vscode /app

# Cambiamos al usuario vscode para las siguientes instrucciones
USER vscode

# 1. Copiamos nuestro archivo de dependencias AL CONTENEDOR
COPY pyproject.toml .

# 2. Sincronizamos el proyecto. 
# uv creará automáticamente un entorno virtual y descargará Flask
RUN uv sync

EXPOSE 5000

# 3. Ejecutamos nuestra app usando 'uv run' para que use el entorno virtual
CMD ["uv", "run", "python", "run.py"]