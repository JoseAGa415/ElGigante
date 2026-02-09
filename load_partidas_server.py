#!/usr/bin/env python
"""
Script para cargar partidas 8-45 en el servidor
Ejecutar en el servidor con:
cd ~/ElGigante && source venv/bin/activate && python load_partidas_server.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffee_processing.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from datetime import date
from beneficio.models import Partida, SubPartida, Bodega, EtiquetaLote
from django.contrib.auth.models import User

def get_or_create_etiqueta(nombre):
    """Crear o obtener etiqueta"""
    if nombre:
        etiqueta, _ = EtiquetaLote.objects.get_or_create(nombre=nombre)
        return nombre
    return None

def crear_partida(nombre, descripcion=None):
    """Crear una partida y retornarla"""
    bodega = Bodega.objects.filter(activo=True).first()
    user = User.objects.first()

    partida = Partida.objects.create(
        nombre=nombre,
        descripcion=descripcion,
        bodega=bodega,
        creado_por=user
    )
    print(f"  Creada partida: {partida.numero_partida} - {nombre}")
    return partida

def crear_subpartida(partida, nombre, tipo_proceso, quintales, sacos=1, humedad=None,
                     score=None, taza='SANA LIMPIA', cualidades=None, etiqueta=None,
                     fecha=None, defectos=None, rb=None, rn=None):
    """Crear una subpartida"""
    user = User.objects.first()
    peso_kg = Decimal(str(quintales)) * Decimal('46')

    # Procesar etiqueta
    etiqueta_valor = get_or_create_etiqueta(etiqueta) if etiqueta else None

    subpartida = SubPartida.objects.create(
        partida=partida,
        nombre=nombre,
        tipo_proceso=tipo_proceso,
        quintales=Decimal(str(quintales)),
        peso_bruto_kg=peso_kg,
        tara_kg=Decimal('0'),
        numero_sacos=sacos,
        humedad=Decimal(str(humedad)) if humedad else None,
        score=Decimal(str(score)) if score else None,
        taza=taza,
        cualidades=cualidades,
        etiqueta=etiqueta_valor,
        fecha_ingreso=fecha,
        defectos=Decimal(str(defectos)) if defectos else None,
        rb=Decimal(str(rb)) if rb else None,
        rn=Decimal(str(rn)) if rn else None,
        creado_por=user
    )
    print(f"    + {subpartida.numero_subpartida}: {nombre} ({quintales} qq)")
    return subpartida

def main():
    print("=" * 60)
    print("CARGANDO PARTIDAS 8-45 EN EL SERVIDOR")
    print("=" * 60)

    # ============================================
    # PARTIDA 8 - CATUAI Natural
    # ============================================
    print("\n[PARTIDA 8] CATUAI Natural")
    p8 = crear_partida("CATUAI Natural", "Lotes naturales variedad Catuai")
    crear_subpartida(p8, "UVA VERDE", "NATURAL", 0.14, 1, etiqueta="natural catuai")
    crear_subpartida(p8, "CATUAI No. 2", "NATURAL", 0.13, 1, humedad=11, score=86,
                     taza="DEFECTUOSA", cualidades="CITRICO FLORAL CARAMELO CHOCOLATE (VER LA FERMENTACION Y LIMPIEZA)",
                     etiqueta="natural catuai")
    crear_subpartida(p8, "No. 4", "NATURAL", 0.24, 1, humedad=10.80, etiqueta="natural catuai",
                     fecha=date(2025, 12, 13))
    crear_subpartida(p8, "11/13-12/25", "NATURAL", 0.26, 1, humedad=10.6, etiqueta="natural catuai",
                     fecha=date(2025, 12, 23))
    p8.actualizar_totales()

    # ============================================
    # PARTIDA 9 - NANDO 1RAS
    # ============================================
    print("\n[PARTIDA 9] NANDO 1RAS")
    p9 = crear_partida("NANDO 1RAS", "Lavado primeras")
    crear_subpartida(p9, "NANDO 1RAS", "LAVADO", 1.19, 2, humedad=11.8, score=86.5,
                     cualidades="CITRICO NARANJA FLORAL CARAMELO CHOCOLATE EXELENTE",
                     etiqueta="lavado 1ras", fecha=date(2025, 12, 13))
    p9.actualizar_totales()

    # ============================================
    # PARTIDA 10 - CATUAI/FINCA Natural
    # ============================================
    print("\n[PARTIDA 10] CATUAI/FINCA Natural")
    p10 = crear_partida("CATUAI/FINCA Natural", "Naturales Catuai y Finca")
    crear_subpartida(p10, "CATUAI No.6", "NATURAL", 0.28, 1, humedad=11.6, score=87.25,
                     cualidades="F TROPICALES, CHOCOLATE, CARAMELO MANZANA CITRICO",
                     etiqueta="natural finca", fecha=date(2025, 12, 13))
    crear_subpartida(p10, "FINCA 10/01/26", "NATURAL", 0.65, 1, humedad=10.4, score=87.5,
                     cualidades="VINOSO F TROPICALES APERFUMADO CITRICO TORONIA CARAMELO CHOCOLATE F MADUROS",
                     etiqueta="natural finca", fecha=date(2026, 1, 10))
    crear_subpartida(p10, "NATURA 12/12", "NATURAL", 0.1, 1, humedad=12, score=87.25,
                     cualidades="F TROPICALES FLORAL, FRUTAS MADURAS BAYAS",
                     etiqueta="natural finca", fecha=date(2025, 12, 23))
    p10.actualizar_totales()

    # ============================================
    # PARTIDA 11 - NATURAL SANDRA
    # ============================================
    print("\n[PARTIDA 11] NATURAL SANDRA")
    p11 = crear_partida("NATURAL SANDRA", "Natural Sandra")
    crear_subpartida(p11, "NATURAL SANDRA 10/01/26", "NATURAL", 0.8, 1, humedad=13, score=87,
                     cualidades="F TROPICALES, CITRICO TORONIA CARAMELO CHOCOLATE FRUTAS MADURAS",
                     etiqueta="natural sandra", fecha=date(2026, 1, 10))
    p11.actualizar_totales()

    # ============================================
    # PARTIDA 12 - PRECIOSO LV
    # ============================================
    print("\n[PARTIDA 12] PRECIOSO LV")
    p12 = crear_partida("PRECIOSO LV", "Precioso Lavado Natural")
    crear_subpartida(p12, "NATURAL 5/01/26 LUNES PRECIOSO", "NATURAL", 1.09, 1, humedad=13.4, score=87.5,
                     cualidades="F TROPICALES, CITRICO TORONIA BAYAS FRUTOS MADURAS PECIOSO",
                     etiqueta="precioso lv", fecha=date(2026, 1, 5))
    p12.actualizar_totales()

    # ============================================
    # PARTIDA 13 - PINTON Natural
    # ============================================
    print("\n[PARTIDA 13] PINTON Natural")
    p13 = crear_partida("PINTON Natural", "Naturales Pinton y Finca")
    crear_subpartida(p13, "PINTON No.3", "NATURAL", 0.41, 1, humedad=12.4, score=87,
                     cualidades="F TROPICALES CITRICO TORONIA CARAMELO CHOCOLATE F MADURAS",
                     etiqueta="natural pinton")
    crear_subpartida(p13, "NATURA FINCA 27", "NATURAL", 0.18, 1, humedad=11.2, score=87,
                     cualidades="F TROPICALES CITRICO F MADURAS CARAMELO CHOCOLATE",
                     etiqueta="natural finca", fecha=date(2025, 12, 23))
    crear_subpartida(p13, "NATURAL FINCA 26", "NATURAL", 0.24, 1, humedad=11.5, score=87.5,
                     cualidades="FLORAL CITRICO MARACUYA F TROPICALES FRUTAS APERFUMADO",
                     etiqueta="natural finca", fecha=date(2025, 12, 26))
    p13.actualizar_totales()

    # ============================================
    # PARTIDA 14 - 1RA LAVADO
    # ============================================
    print("\n[PARTIDA 14] 1RA LAVADO")
    p14 = crear_partida("1RA LAVADO", "Primera Lavado")
    crear_subpartida(p14, "1RA LAVADO", "LAVADO", 5.66, 6, humedad=13.9, score=86.5,
                     cualidades="CITRICO CARAMELO CHOCOLATE FRUTAS BAYAS MIEL",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 10))
    p14.actualizar_totales()

    # ============================================
    # PARTIDA 15 - CHENTE Y NANDO
    # ============================================
    print("\n[PARTIDA 15] CHENTE Y NANDO")
    p15 = crear_partida("CHENTE Y NANDO", "Lavado Chente y Nando")
    crear_subpartida(p15, "CHENTE Y NANDO", "LAVADO", 2.92, 4, humedad=11.5, score=86.75,
                     cualidades="CITRICO LIMA FUTAS BAYAS, LIG FLORAL CAREMELO CHOCOLATE MIEL",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 13))
    p15.actualizar_totales()

    # ============================================
    # PARTIDA 16 - PECIOSO LV (Sandra)
    # ============================================
    print("\n[PARTIDA 16] PECIOSO LV")
    p16 = crear_partida("PECIOSO LV Sandra", "Precioso Sandra")
    crear_subpartida(p16, "SANDRA 09/01/26", "NATURAL", 0.55, 1, humedad=13.6, score=87.75,
                     cualidades="CITRICO FLORAL, BAYAS CAREMELO VINOSO PRECIOSO",
                     etiqueta="precioso lv", fecha=date(2026, 1, 9))
    crear_subpartida(p16, "SANDRA ING. AB", "NATURAL", 0.5, 1, humedad=13.1, score=87.75,
                     cualidades="CITRICO FLORLA VINOSO, CARAMELO CHOCOLATE BAYAS PECIOSO",
                     etiqueta="precioso lv", fecha=date(2026, 1, 9))
    p16.actualizar_totales()

    # ============================================
    # PARTIDA 17 - ANA 1 RAS
    # ============================================
    print("\n[PARTIDA 17] ANA 1 RAS")
    p17 = crear_partida("ANA 1 RAS", "Ana Primera")
    crear_subpartida(p17, "ANA 1 RAS", "LAVADO", 1.55, 2, humedad=12, score=86.5,
                     cualidades="CITRICO FRUTAS MIEL CARAMELO CHOCOLATE",
                     etiqueta="lavado 1ras", fecha=date(2025, 12, 18))
    p17.actualizar_totales()

    # ============================================
    # PARTIDA 18 - 1RAS PITA NEGRA GAMALIEL
    # ============================================
    print("\n[PARTIDA 18] 1RAS PITA NEGRA GAMALIEL")
    p18 = crear_partida("1RAS PITA NEGRA GAMALIEL", "Pita Negra Gamaliel")
    crear_subpartida(p18, "1RAS PITA NEGRA GAMALIEL", "LAVADO", 3.66, 4, humedad=11.1, score=86.5,
                     cualidades="CITRICO FLORAL CARAEMLO MIEL CHOCOLATE FRUTAS",
                     etiqueta="lavado 1ras")
    p18.actualizar_totales()

    # ============================================
    # PARTIDA 19 - ANA 1 RAS (Grande)
    # ============================================
    print("\n[PARTIDA 19] ANA 1 RAS")
    p19 = crear_partida("ANA 1 RAS Grande", "Ana Primera Grande")
    crear_subpartida(p19, "ANA 1 RAS", "LAVADO", 13.85, 16, humedad=11, score=86.5,
                     cualidades="CARAMELO, CHOCOLATE, FRUTAS MANZANA CITRICO LIMNA",
                     etiqueta="lavado 1ras", fecha=date(2025, 12, 29))
    p19.actualizar_totales()

    # ============================================
    # PARTIDA 20 - 1RA EMILIANO NANDO
    # ============================================
    print("\n[PARTIDA 20] 1RA EMILIANO NANDO")
    p20 = crear_partida("1RA EMILIANO NANDO", "Emiliano 19 Nando 9")
    crear_subpartida(p20, "1RA. EMILIANO 19 NANDO9", "LAVADO", 5.77, 6, humedad=11, score=86,
                     cualidades="CARAMELO CHOCOLATE CITRICO NARANJA MIEL F ROJOS",
                     etiqueta="lavado 1ras", fecha=date(2025, 12, 31))
    p20.actualizar_totales()

    # ============================================
    # PARTIDA 21 - ANA NATURAL HONEY
    # ============================================
    print("\n[PARTIDA 21] ANA NATURAL HONEY")
    p21 = crear_partida("ANA NATURAL HONEY", "Ana Natural Honey")
    crear_subpartida(p21, "ANA NATURAL HONEY", "NATURAL", 2.09, 3, humedad=11.5, score=87.5,
                     cualidades="CITRICO FLORAL F TROPICALES MARACUYA APERFUMADO - MUESTRA COMO HONEY",
                     etiqueta="natural honey", fecha=date(2025, 12, 26))
    p21.actualizar_totales()

    # ============================================
    # PARTIDA 22 - 1RA LAVADO
    # ============================================
    print("\n[PARTIDA 22] 1RA LAVADO")
    p22 = crear_partida("1RA LAVADO Enero", "Primera Lavado Enero")
    crear_subpartida(p22, "1RA LAVADO", "LAVADO", 5.5, 6, humedad=11.6, score=86.5,
                     cualidades="FRUTOS CONCERVA, MIEL CITRICO CARAMELO CHOCOLATE",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 3))
    p22.actualizar_totales()

    # ============================================
    # PARTIDA 23 - 1RAS INGRESO AB
    # ============================================
    print("\n[PARTIDA 23] 1RAS INGRESO AB")
    p23 = crear_partida("1RAS INGRESO AB", "Primeras Ingreso AB")
    crear_subpartida(p23, "1RAS INGRESO AB", "LAVADO", 3.08, 4, humedad=11.5, score=86.5,
                     cualidades="CARAMELO CHOCOLATE FRUTAS MADURAS MANZANA CITRICO",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 8))
    p23.actualizar_totales()

    # ============================================
    # PARTIDA 24 - WILSON 1 RAS
    # ============================================
    print("\n[PARTIDA 24] WILSON 1 RAS")
    p24 = crear_partida("WILSON 1 RAS", "Wilson Primera")
    crear_subpartida(p24, "WILSON 1 RAS", "LAVADO", 0.81, 1, humedad=11.6, score=84,
                     cualidades="CEREAL, NUEZ, VEGETAL CARAMELO CHOCOLATE",
                     etiqueta="lavado 1ras", fecha=date(2025, 12, 26))
    p24.actualizar_totales()

    # ============================================
    # PARTIDA 25 - 2DAS Lavado
    # ============================================
    print("\n[PARTIDA 25] 2DAS Lavado")
    p25 = crear_partida("2DAS Lavado", "Segundas Lavado")
    crear_subpartida(p25, "GAMALIES 2DAS", "LAVADO", 0.35, 1, humedad=10.8, score=86.5,
                     cualidades="MENTA, EUCALIPTO, FLORAL, MANZANA MAPLE CHOCOLATE",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 18))
    crear_subpartida(p25, "NANDO 2DAS", "LAVADO", 0.22, 1, humedad=10.6, score=87.5,
                     cualidades="FLORAL CAREMELO CHOCOLATE CITRICO F AMARILLOS BALANCEADO",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 23))
    crear_subpartida(p25, "CARLOS ERNESTO 2DAS", "LAVADO", 0.12, 1, humedad=10.5, score=86.5,
                     cualidades="CITRICO, MANZANA CARAMELO CHOCOLATE",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 26))
    crear_subpartida(p25, "ANA 2DAS", "LAVADO", 0.14, 1, humedad=10.4, score=85.5,
                     cualidades="CITRICO MIEL, MANZANA CARAMELOC HOCOLATE FRUTAS",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 18))
    crear_subpartida(p25, "2DAS", "LAVADO", 0.77, 1, humedad=10.5, score=86.5,
                     cualidades="FRUTOS AMARILLOS CITRICO NARANJA MANGO CARAEMLO CHOCOLATE LIG. FLORAL",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 29))
    crear_subpartida(p25, "EXP. PLASTICO NEGRO 2DAS.", "LAVADO", 0.12, 1, humedad=10.8, score=86.5,
                     cualidades="FRUTAS FLORAL, MIEL, CARAMELO, CHOCOLATE NARANJA",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 29))
    crear_subpartida(p25, "2DAS 6/1/26 7116", "LAVADO", 0.94, 1, humedad=10.5, score=85.5,
                     cualidades="CITRICO MIEL, MANZANA CARAMELOC HOCOLATE FRUTAS",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 6))
    crear_subpartida(p25, "2DAS INGRESO AB", "LAVADO", 0.51, 1, humedad=10.5, score=85.5,
                     cualidades="CITRICO, MANZANA CARAMELO CHOCOLATE",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 8))
    crear_subpartida(p25, "DELFINO / NANDO 2DAS", "LAVADO", 0.36, 1, humedad=11.9, score=86,
                     cualidades="CITRICO, LIG. FLORAL, FRUTAS MIEL CARAMELO FRUTAS",
                     etiqueta="lavado 2das")
    crear_subpartida(p25, "2DAS. EMILIANO19 NANDO9", "LAVADO", 0.29, 1, humedad=11, score=85.5,
                     cualidades="CITRICO MIEL, MANZANA CARAMELOC HOCOLATE FRUTAS",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 31))
    crear_subpartida(p25, "2DAS 31/12/25", "LAVADO", 0.24, 1, humedad=10.8, score=85.5,
                     cualidades="CITRICO, MANZANA CARAMELO CHOCOLATE",
                     etiqueta="lavado 2das", fecha=date(2025, 12, 31))
    crear_subpartida(p25, "2DAS 3/01/2026", "LAVADO", 0.53, 1, humedad=10.5, score=86.25,
                     cualidades="CARAMELO CHOCOLATE CITRICO FRUTOS ROJOS CIRUELA",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 3))
    p25.actualizar_totales()

    # ============================================
    # PARTIDA 26A - CARLOS ERNESTO 1RAS
    # ============================================
    print("\n[PARTIDA 26A] CARLOS ERNESTO 1RAS")
    p26a = crear_partida("CARLOS ERNESTO 1RAS", "Carlos Ernesto Primeras")
    crear_subpartida(p26a, "CARLOS ERNESTO 1RAS", "LAVADO", 2.47, 3, humedad=11.6, score=86.5,
                     cualidades="CITRICO FRUTAS, NARANJA CARAMELO CHOCOLATE, MIEL",
                     etiqueta="lavado 1ras", fecha=date(2025, 12, 26))
    p26a.actualizar_totales()

    # ============================================
    # PARTIDA 26 - 1RAS 6/01/26
    # ============================================
    print("\n[PARTIDA 26] 1RAS 6/01/26")
    p26 = crear_partida("1RAS 6/01/26 7126", "Primeras 6 Enero")
    crear_subpartida(p26, "1RAS 6/01/26 7126", "LAVADO", 5.51, 6, humedad=11.4, score=86,
                     cualidades="CDARAMELO CHOCOLATE, CITRICO NARANJA CRUTAS MADURAS CIRUELA",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 26))
    p26.actualizar_totales()

    # ============================================
    # PARTIDA 27 - 2DAS Lavado
    # ============================================
    print("\n[PARTIDA 27] 2DAS Lavado")
    p27 = crear_partida("2DAS Lavado Enero", "Segundas Enero")
    crear_subpartida(p27, "2DAS INGRESO AB", "LAVADO", 2.27, 3, humedad=10.3, score=86,
                     cualidades="FRUTAS MANZANA, CARAMELO CHOCOLATE CITRICA LIMA",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 9))
    crear_subpartida(p27, "2DAS 16/01/26", "LAVADO", 0.61, 1, humedad=13.3, score=86,
                     cualidades="CARAMELO CHOCOLATE FRUTAS MADURAS CITRICO MANZANA",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 16))
    crear_subpartida(p27, "2DA 14/01/26", "LAVADO", 0.21, 1, humedad=12.1, score=86,
                     cualidades="CITRICO NARANJA CARAMELO CHOCOLATE FRUTAS",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 14))
    p27.actualizar_totales()

    # ============================================
    # PARTIDA 28 - 1RA NANDO
    # ============================================
    print("\n[PARTIDA 28] 1RA NANDO")
    p28 = crear_partida("1RA NANDO", "Nando Primera")
    crear_subpartida(p28, "1RA NANDO", "LAVADO", 2.36, 3, humedad=13.9, score=86.5,
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 14))
    p28.actualizar_totales()

    # ============================================
    # PARTIDA 29 - PARA HONEY
    # ============================================
    print("\n[PARTIDA 29] PARA HONEY")
    p29 = crear_partida("PARA HONEY", "Carlos Mateo Para Honey")
    crear_subpartida(p29, "CARLOS MATEO 10 SACOS", "NATURAL", 4.65, 5, humedad=11.8, score=87.25,
                     cualidades="CITRICO TORONIA, MIEL F TROPICALES CUERPO CREMOSO (HONEY)",
                     etiqueta="natural honey")
    p29.actualizar_totales()

    # ============================================
    # PARTIDA 30 - 1RAS 16/01/26
    # ============================================
    print("\n[PARTIDA 30] 1RAS 16/01/26")
    p30 = crear_partida("1RAS 16/01/26", "Primeras 16 Enero")
    crear_subpartida(p30, "1RAS 16/01/26", "LAVADO", 5.6, 6, humedad=11.5, score=86.5,
                     cualidades="FRUTAS BAYA, CITRICO NARANJA CARAEMLO CHOCOLATE",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 16))
    p30.actualizar_totales()

    # ============================================
    # PARTIDA 31 - NATURAL 12/01/26
    # ============================================
    print("\n[PARTIDA 31] NATURAL 12/01/26")
    p31 = crear_partida("NATURAL 12/01/26", "Natural 12 Enero")
    crear_subpartida(p31, "NATURAL 12/01/26", "NATURAL", 2.13, 3, humedad=11.9, score=87,
                     cualidades="F TROPICALES, CITRICO TORONIA BAYAS MIEL FRUTAS MADURAS",
                     etiqueta="natural finca", fecha=date(2026, 1, 12))
    p31.actualizar_totales()

    # ============================================
    # PARTIDA 32 - PRECIOSO LV FINCA
    # ============================================
    print("\n[PARTIDA 32] PRECIOSO LV FINCA")
    p32 = crear_partida("PRECIOSO LV FINCA", "Precioso Finca Sabado")
    crear_subpartida(p32, "FINCA SABADO 10/01/26", "NATURAL", 1.89, 2, humedad=13, score=87.5,
                     cualidades="CITRICO TORONJA, F/TROPICALES, APERFUMADO PRECIOSO",
                     etiqueta="precioso lv", fecha=date(2026, 1, 10))
    p32.actualizar_totales()

    # ============================================
    # PARTIDA 33 - 1RAS ENVIO 56
    # ============================================
    print("\n[PARTIDA 33] 1RAS ENVIO 56")
    p33 = crear_partida("1RAS ENVIO 56", "Primeras Envio 56")
    crear_subpartida(p33, "1RAS. 18/01/26 ENVIO 56", "LAVADO", 9.08, 10, humedad=13.1, score=86.5,
                     cualidades="CITRICO LIMON, FRUTAS, BAYAS CARAMELO CHOCOLATE MIEL",
                     etiqueta="lavado 1ras", fecha=date(2026, 1, 18))
    p33.actualizar_totales()

    # ============================================
    # PARTIDA 34 - PITA AMARILLA
    # ============================================
    print("\n[PARTIDA 34] PITA AMARILLA")
    p34 = crear_partida("PITA AMARILLA", "Pita Amarilla Natural")
    crear_subpartida(p34, "PITA AMARILLA 3 SAQUITOS", "NATURAL", 1.25, 2, humedad=13.1, score=87,
                     cualidades="FRUTOS TROPICALES FLORAL, CARAMELO CHOCOLATE CITRICO MIEL",
                     etiqueta="natural pita")
    p34.actualizar_totales()

    # ============================================
    # PARTIDA 35 - 2DAS ENVIO 56
    # ============================================
    print("\n[PARTIDA 35] 2DAS ENVIO 56")
    p35 = crear_partida("2DAS ENVIO 56", "Segundas Envio 56")
    crear_subpartida(p35, "2DAS. 18/01/26 ENVIO 56", "LAVADO", 0.72, 1, humedad=13.5, score=86,
                     taza="DEFECTUOSA", cualidades="CARAMELO CHOCOLATE, CITRICO MIEL 1 TAZA MOHO",
                     etiqueta="lavado 2das", fecha=date(2026, 1, 18))
    p35.actualizar_totales()

    # ============================================
    # PARTIDA 36 - 3RAS ENVIO 56
    # ============================================
    print("\n[PARTIDA 36] 3RAS ENVIO 56")
    p36 = crear_partida("3RAS ENVIO 56", "Terceras Envio 56")
    crear_subpartida(p36, "3RAS. 18/01/26 ENVIO 56", "LAVADO", 0.2, 1, humedad=11.1, score=86.5,
                     cualidades="CITRICO NARANJA, LIG. FLORAL, MIEL BAYAS CARAMELO CHOCOLATE",
                     etiqueta="lavado 3ras", fecha=date(2026, 1, 18))
    p36.actualizar_totales()

    # ============================================
    # PARTIDA 37 - FINCA JUEVES
    # ============================================
    print("\n[PARTIDA 37] FINCA JUEVES")
    p37 = crear_partida("FINCA JUEVES", "Finca Jueves Natural")
    crear_subpartida(p37, "FINCA JUEVES 15/01/26", "NATURAL", 1.55, 2, humedad=13, score=87,
                     cualidades="CARAMELO, CHOCOLATE, FRUTAS MANZANA CITRICO TORONJA",
                     etiqueta="natural finca", fecha=date(2026, 1, 15))
    p37.actualizar_totales()

    # ============================================
    # PARTIDA 38 - MARTES FINCA
    # ============================================
    print("\n[PARTIDA 38] MARTES FINCA")
    p38 = crear_partida("MARTES FINCA", "Martes Finca Natural")
    crear_subpartida(p38, "MARTES 13/01/26 FINCA", "NATURAL", 1.95, 2, humedad=11.6, score=87,
                     taza="DEFECTUOSA", cualidades="CITRICO F TROPICALES, FRUTAS EN CONSERVA CHOCOLATE CARAMELO - 1 FENOL",
                     etiqueta="natural finca", fecha=date(2026, 1, 13))
    p38.actualizar_totales()

    # ============================================
    # PARTIDA 39 - NATURAL ENVIO 56
    # ============================================
    print("\n[PARTIDA 39] NATURAL ENVIO 56")
    p39 = crear_partida("NATURAL ENVIO 56", "Natural 4 Sacos Envio 56")
    crear_subpartida(p39, "NATURAL 4 SACOS 18/01/26 ENVIO 56", "NATURAL", 1.7, 2, humedad=13.7, score=87,
                     cualidades="CARAMELO CHOCOLATE, FRUTAS MADURAS CITRICO LIMA, LIG. FLORAL FRUTAS EN CONSERVA",
                     etiqueta="natural finca", fecha=date(2026, 1, 18))
    p39.actualizar_totales()

    # ============================================
    # PARTIDA 40 - FINCA ING. AB
    # ============================================
    print("\n[PARTIDA 40] FINCA ING. AB")
    p40 = crear_partida("FINCA ING. AB", "Finca Ingreso AB Natural")
    crear_subpartida(p40, "FINCA ING. AB", "NATURAL", 1.3, 2, humedad=13.4, score=87,
                     cualidades="FRUTAS BAYAS, CITRICO TORONJA, CARAMELO CHOCOLATE",
                     etiqueta="natural finca", fecha=date(2026, 1, 20))
    p40.actualizar_totales()

    # ============================================
    # PARTIDA 41 - NATURAL 17/01/26
    # ============================================
    print("\n[PARTIDA 41] NATURAL 17/01/26")
    p41 = crear_partida("NATURAL 17/01/26", "Naturales 17 Enero")
    crear_subpartida(p41, "17/01/26 B", "NATURAL", 0.49, 1, humedad=12, score=87,
                     cualidades="F TROPICALES, CITRICO CARAMELO CHOCOLATE MANZANA FRUTAS BAYAS",
                     etiqueta="natural finca", fecha=date(2026, 1, 17))
    crear_subpartida(p41, "17/01/26 A", "NATURAL", 0.73, 1, humedad=11.3, score=87,
                     cualidades="CITRICO TORONJA CARAMELO CHOCOLATE FRUTAS BAYAS",
                     etiqueta="natural finca", fecha=date(2026, 1, 17))
    p41.actualizar_totales()

    # ============================================
    # PARTIDA 42 - PINTON Natural
    # ============================================
    print("\n[PARTIDA 42] PINTON Natural")
    p42 = crear_partida("PINTON Natural Enero", "Pinton Naturales Enero")
    crear_subpartida(p42, "PINTON 17/01/26", "NATURAL", 0.49, 1, humedad=11, score=87,
                     cualidades="FLORAL, MIEL, CITRICO TORONJA CARAMELO CHOCOLATE",
                     etiqueta="natural pinton", fecha=date(2026, 1, 17))
    crear_subpartida(p42, "PINTON INGRESO AB 17/01/26", "NATURAL", 0.12, 1, humedad=10.7, score=87,
                     taza="DEFECTUOSA", cualidades="FLORAL, F TROPICALES CITRICO BAYAS FRUTAS - 1 TAZA LIG. FENOL",
                     etiqueta="natural pinton", fecha=date(2026, 1, 17))
    p42.actualizar_totales()

    # ============================================
    # PARTIDA 43 - C. MARVIN PITA NEGRA
    # ============================================
    print("\n[PARTIDA 43] C. MARVIN PITA NEGRA")
    p43 = crear_partida("C. MARVIN PITA NEGRA", "Marvin Pita Negra Envio 57")
    crear_subpartida(p43, "C. MARVIN PITA NEGRA 21 SACIS ENVIO 57", "NATURAL", 10.2, 10, humedad=12.4, score=87.25,
                     cualidades="CITRICO, MENTA CARAMELO CHOCOLATE F TROPICALES, FRUTA LIG. ASPERA",
                     etiqueta="natural pita", fecha=date(2026, 1, 22))
    p43.actualizar_totales()

    # ============================================
    # PARTIDA 44 - FINCA PITA NARANJA
    # ============================================
    print("\n[PARTIDA 44] FINCA PITA NARANJA")
    p44 = crear_partida("FINCA PITA NARANJA", "Finca 3 Sacos Pita Naranja Envio 57")
    crear_subpartida(p44, "FINCA 3 SACOS PITA NARANJA ENVIO 57", "NATURAL", 1.48, 2, humedad=11.3, score=87.5,
                     cualidades="FLORAL, F TROPICALES, BAYAS, FRUTAS CITRICO NARANJA",
                     etiqueta="natural pita", fecha=date(2026, 1, 22))
    p44.actualizar_totales()

    # ============================================
    # PARTIDA 45 - CARLOS MATEO ING. AB
    # ============================================
    print("\n[PARTIDA 45] CARLOS MATEO ING. AB")
    p45 = crear_partida("CARLOS MATEO ING. AB", "Carlos Mateo Ingreso AB")
    crear_subpartida(p45, "CARLOS MATEO ING. AB 20/01/26", "NATURAL", 2.13, 2, humedad=12.7, score=87,
                     taza="DEFECTUOSA", cualidades="MIEL, F TROPICALES MANZANA CARAMELO CHOCOLATE - 1 TAZA FENOL",
                     etiqueta="natural finca", fecha=date(2026, 1, 20))
    p45.actualizar_totales()

    # ============================================
    # RESUMEN FINAL
    # ============================================
    print("\n" + "=" * 60)
    print("RESUMEN DE CARGA")
    print("=" * 60)

    total_partidas = Partida.objects.count()
    total_subpartidas = SubPartida.objects.count()
    total_quintales = sum([float(p.peso_total_kg) / 46 for p in Partida.objects.all()])

    print(f"Total de Partidas: {total_partidas}")
    print(f"Total de SubPartidas: {total_subpartidas}")
    print(f"Total de Quintales: {total_quintales:.2f} qq")
    print("=" * 60)
    print("CARGA COMPLETADA EXITOSAMENTE!")
    print("=" * 60)

if __name__ == '__main__':
    main()
