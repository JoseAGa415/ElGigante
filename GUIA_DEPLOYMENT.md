# Guía de Despliegue - Actualización con Mejoras Responsive

## Resumen de Cambios

Esta actualización incluye:
1. ✅ Sistema de catación para partidas
2. ✅ Campos de ubicación (percha, fila) en Lote
3. ✅ Optimización mobile para detalles de compradores
4. ✅ Upload de comprobantes de pago
5. ✅ **NUEVO**: Diseño responsive ~90% (mobile-friendly)
6. ✅ **NUEVO**: Estilos de impresión profesionales

**Migraciones pendientes:**
- 0031_compra_comprobante.py
- 0032_add_ubicacion_fields.py
- 0033_lote_ubicacion_fields.py
- 0034_catacion_partida.py

**NOTA**: Esta actualización es **solo frontend** (HTML/CSS/JS). No requiere migraciones adicionales.

---

## PASOS PARA DESPLIEGUE EN SERVIDOR

### 1. Verificación Local (ANTES de subir)

```bash
# En tu máquina local
cd "c:\Users\titig\Desktop\Aplicacion prueba"

# Verificar que no hay errores
python manage.py check

# Verificar migraciones aplicadas
python manage.py showmigrations beneficio

# Ver commits pendientes
git log --oneline -5

# Asegurarse de que todo está commiteado
git status
```

### 2. Subir Cambios a GitHub

```bash
# Push al repositorio remoto
git push origin main
```

### 3. Conectarse al Servidor

```bash
# Conectar por SSH
ssh usuario@inprocaf.com
# (Reemplaza 'usuario' con tu usuario real)
```

### 4. Backup de Base de Datos (IMPORTANTE)

```bash
# Navegar al directorio del proyecto
cd /ruta/del/proyecto

# Crear backup de la base de datos SQLite
cp db.sqlite3 backup_db_$(date +%Y%m%d_%H%M%S).sqlite3

# Verificar que el backup se creó
ls -lh backup_db_*.sqlite3
```

### 5. Actualizar Código desde GitHub

```bash
# Pull de los últimos cambios
git pull origin main

# Verificar los archivos que cambiaron
git log --oneline -5
```

### 6. Aplicar Migraciones

```bash
# Activar entorno virtual (si aplica)
source venv/bin/activate   # o el comando según tu configuración

# Aplicar migraciones
python manage.py migrate beneficio

# Deberías ver:
# Applying beneficio.0031_compra_comprobante... OK
# Applying beneficio.0032_add_ubicacion_fields... OK
# Applying beneficio.0033_lote_ubicacion_fields... OK
# Applying beneficio.0034_catacion_partida... OK
```

### 7. Verificar Migraciones Aplicadas

```bash
# Confirmar que todas las migraciones están aplicadas
python manage.py showmigrations beneficio | tail -10

# Deberías ver todas con [X]
```

### 8. Configurar Directorio de Media (Para Comprobantes)

```bash
# Crear directorio para comprobantes si no existe
mkdir -p media/comprobantes
chmod 755 media/comprobantes
chown www-data:www-data media/comprobantes  # Ajustar según tu usuario web

# Verificar permisos
ls -ld media/comprobantes
```

### 9. Recolectar Archivos Estáticos

```bash
# Recolectar archivos estáticos (CSS, JS, etc.)
python manage.py collectstatic --noinput
```

### 10. Reiniciar Gunicorn

```bash
# Reiniciar el servicio Gunicorn
sudo systemctl restart gunicorn

# Verificar que se reinició correctamente
sudo systemctl status gunicorn

# Si ves "active (running)" en verde, está bien
```

### 11. Verificar Nginx (Opcional)

```bash
# Verificar configuración de Nginx
sudo nginx -t

# Si todo está bien, reiniciar Nginx
sudo systemctl reload nginx
```

### 12. Verificación Post-Despliegue

Abre tu navegador y verifica:

#### Funcionalidad Base:
1. **Página de inicio**: http://inprocaf.com/
2. **Crear partida**: Verifica que los campos de percha y fila aparecen
3. **Detalle de partida**: Verifica que el botón "Catar Partida" aparece
4. **Crear catación**: Verifica que "Partida" aparece en el dropdown de tipo de muestra
5. **Agregar compra**: Verifica que el campo de comprobante aparece
6. **Detalle comprador (móvil)**: Verifica el layout horizontal compacto

#### Nuevas Mejoras Responsive (IMPORTANTE):
7. **Lista de Lotes (móvil)**:
   - Abre en celular o usa herramientas dev (F12 → toggle device mode)
   - Verifica que se muestra vista de tarjetas en lugar de tabla
   - Los botones son fáciles de tocar (mínimo 44px)
   - Tarjetas con colores según estado (verde=completo, rojo=error, azul=procesando)

8. **Lista de Cataciones (móvil)**:
   - Verifica vista de tarjetas en móvil
   - Puntaje prominente visible
   - Botones touch-friendly

9. **Dashboard y Resumen**:
   - Gráficos se ajustan al tamaño de pantalla
   - En móvil, gráficos más pequeños pero legibles
   - Leyendas y tooltips adaptados

10. **Impresión (Ctrl+P)**:
    - Prueba imprimir dashboard o página de resumen
    - No debe mostrar navegación ni sidebar
    - Fondo blanco con texto negro
    - Tablas y gráficos optimizados para papel

---

## SI ALGO SALE MAL

### Error: "relation does not exist" o "no such column"

```bash
# Verificar migraciones pendientes
python manage.py showmigrations beneficio

# Si alguna no está aplicada [X], aplicarla:
python manage.py migrate beneficio

# Ver los detalles de la última migración
python manage.py sqlmigrate beneficio 0034
```

### Error: "Permission denied" en media/comprobantes

```bash
# Ajustar permisos del directorio
sudo chown -R www-data:www-data media/
sudo chmod -R 755 media/
```

### Error: Gunicorn no reinicia

```bash
# Ver logs de Gunicorn
sudo journalctl -u gunicorn -n 50

# Ver logs de errores de Django
tail -f /ruta/logs/gunicorn-error.log
```

### Error: 500 Internal Server Error

```bash
# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Ver logs de Django en modo debug (temporal)
# Editar settings.py: DEBUG = True
# Luego volver a poner DEBUG = False después de revisar
```

---

## ROLLBACK (Si necesitas revertir cambios)

### Opción 1: Revertir migraciones específicas

```bash
# Revertir a la migración anterior a 0031
python manage.py migrate beneficio 0030_auto_rename_partida_fields

# Restaurar backup de base de datos
cp backup_db_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3

# Reiniciar Gunicorn
sudo systemctl restart gunicorn
```

### Opción 2: Restaurar código anterior

```bash
# Ver commits recientes
git log --oneline -10

# Revertir al commit anterior
git reset --hard [commit-hash-anterior]

# Restaurar backup de base de datos
cp backup_db_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3

# Reiniciar Gunicorn
sudo systemctl restart gunicorn
```

---

## CHECKLIST FINAL

Antes de cerrar la sesión SSH, verifica:

### Backend y Base de Datos:
- [ ] Base de datos respaldada
- [ ] Código actualizado con git pull
- [ ] Las 4 migraciones aplicadas correctamente
- [ ] Directorio media/comprobantes creado con permisos correctos
- [ ] Archivos estáticos recolectados
- [ ] Gunicorn reiniciado y activo
- [ ] Sitio web accesible y sin errores 500

### Funcionalidades Nuevas:
- [ ] Funcionalidad de catación de partidas probada
- [ ] Botón "Catar Partida" visible en detalle de partida
- [ ] Upload de comprobantes funcional

### Responsive Design (NUEVO):
- [ ] Lista de lotes muestra tarjetas en móvil (<768px)
- [ ] Lista de cataciones muestra tarjetas en móvil
- [ ] Botones touch-friendly (mínimo 44px) funcionan bien
- [ ] Gráficos se redimensionan correctamente
- [ ] Impresión (Ctrl+P) muestra formato limpio sin navegación
- [ ] Probado en móvil real o emulador (Chrome DevTools)

---

## Contacto y Soporte

Si encuentras algún error durante el despliegue, anota:
1. El mensaje de error exacto
2. El comando que ejecutaste
3. Los logs relevantes

Y puedes consultar la documentación de Django o revisar los commits en GitHub.

---

## DETALLES DE MEJORAS RESPONSIVE

### 1. Vista de Tarjetas en Mobile
**Archivos modificados:**
- `beneficio/templates/beneficio/lotes/lista.html`
- `beneficio/templates/beneficio/catacion/lista.html`

**Qué hace:**
- En pantallas <768px, las tablas se ocultan
- Se muestran tarjetas verticales con toda la información
- Colores según estado (verde/rojo/azul)
- Botones grandes y fáciles de tocar

### 2. Gráficos Adaptativos
**Archivos modificados:**
- `beneficio/templates/beneficio/dashboard.html`
- `beneficio/templates/beneficio/resumen/resumen_beneficio.html`

**Qué hace:**
- Alturas de gráficos ajustadas por breakpoint:
  - Desktop: 350px
  - Tablet: 280px
  - Mobile: 250px
- Fuentes más pequeñas en móvil (10px vs 12px)
- Leyendas y tooltips optimizados

### 3. Estilos de Impresión
**Archivo modificado:**
- `beneficio/templates/base.html`

**Qué hace:**
- Oculta navegación, sidebar, botones
- Fondo blanco con texto negro (ahorra tinta)
- Tablas optimizadas para papel
- Formato profesional para reportes

### 4. Touch-Friendly
**Cambios globales en listas:**
- Todos los botones tienen `min-h-[44px]`
- Estándar iOS/Android Human Interface Guidelines
- Reduce errores de toque accidental

---

**Última actualización**: 2026-01-20
**Commits incluidos**: c39d24a hasta ed17a60 (7 commits nuevos)

**Commits responsive:**
- `8e9c438` - Card view para lista de lotes
- `9f7e32a` - Card view para lista de cataciones
- `2bbbc22` - Gráficos adaptativos
- `ed17a60` - Print styles globales
