# Guia de Despliegue - Sistema de Procesamiento de Café

Esta guía detalla los pasos para desplegar la aplicación Django en un VPS Linux (Ubuntu/Debian recomendado) usando Gunicorn y Nginx.

## 1. Requisitos Previos del Servidor

Instalar paquetes del sistema necesarios:

```bash
sudo apt update
sudo apt install python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl
```

## 2. Configuración del Proyecto

### 2.1 Clonar el repositorio / Copiar archivos
Asumiremos que el proyecto estará en `/var/www/inprocaf`.

```bash
mkdir -p /var/www/inprocaf
# Copia tus archivos aquí
cd /var/www/inprocaf
```

### 2.2 Entorno Virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2.3 Variables de Entorno
Crea el archivo `.env` en la carpeta de configuración (`coffee_processing`).

```bash
# Copiar la plantilla
cp coffee_processing/.env.prod.example coffee_processing/.env
nano coffee_processing/.env
```

**Asegúrate de configurar:**
- `DEBUG=False`
- `SECRET_KEY` (Usa una clave larga y única)
- `ALLOWED_HOSTS` (Tu dominio e IP)
- `DATABASE_URL` (Tus credenciales de PostgreSQL)

## 3. Base de Datos (PostgreSQL)

Accede a la consola de Postgres:
```bash
sudo -u postgres psql
```

Crea la base de datos y usuario (ajusta las contraseñas según tu `.env`):
```sql
CREATE DATABASE inprocaf_db;
CREATE USER inprocaf WITH PASSWORD 'tu_contraseña_segura';
ALTER ROLE inprocaf SET client_encoding TO 'utf8';
ALTER ROLE inprocaf SET default_transaction_isolation TO 'read committed';
ALTER ROLE inprocaf SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE inprocaf_db TO inprocaf;
\q
```

Aplica las migraciones:
```bash
python manage.py migrate
python manage.py collectstatic
```

## 4. Configurar Gunicorn

Crea un archivo de servicio systemd: `sudo nano /etc/systemd/system/gunicorn.service`

```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/inprocaf
ExecStart=/var/www/inprocaf/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --bind unix:/run/gunicorn.sock \
          coffee_processing.wsgi:application

[Install]
WantedBy=multi-user.target
```
*Nota: Se recomienda usar un usuario no-root para seguridad, pero `root` se usa aquí por simplicidad. Lo ideal es crear un usuario dedicado.*

Inicia y habilita Gunicorn:
```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

## 5. Configurar Nginx

Crea un bloque de servidor: `sudo nano /etc/nginx/sites-available/inprocaf`

```nginx
server {
    listen 80;
    server_name inprocaf.com 72.62.80.238;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /var/www/inprocaf; # Asegúrate que coincida con donde collectstatic puso los archivos
    }

    location /media/ {
        root /var/www/inprocaf;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

Activa el sitio:
```bash
sudo ln -s /etc/nginx/sites-available/inprocaf /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 6. Seguridad (Opcional pero recomendado)

### Firewall (UFW)
```bash
sudo ufw allow 'Nginx Full'
```

### SSL (HTTPS) con Certbot
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d inprocaf.com
```
