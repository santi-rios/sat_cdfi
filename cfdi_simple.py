
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧾 PROCESADOR SIMPLE DE CFDIs 
===============================
Script súper fácil para convertir XMLs de CFDIs a Excel

INSTRUCCIONES:
1. Coloca este archivo en la carpeta donde están tus CFDIs
2. Asegúrate de tener las carpetas "emitidas" y "recibidas" con los XMLs
3. Ejecuta este archivo (doble clic o python cfdi_simple.py)
4. Los archivos Excel se generarán automáticamente

AUTOR: Tu Sistema de CFDIs
FECHA: 2025
"""

import os
import sys
import pandas as pd
import json
import glob
from datetime import datetime

# Verificar que tenemos las librerías necesarias
try:
    from satcfdi.cfdi import CFDI
    from satcfdi import render
    print("✅ Librerías de CFDI encontradas")
except ImportError:
    print("❌ ERROR: Faltan librerías de CFDI")
    print("Instala con: pip install satcfdi pandas openpyxl")
    input("Presiona Enter para cerrar...")
    sys.exit(1)

def procesar_xmls_simple(directorio, nombre_salida):
    """Función simple para procesar XMLs"""
    print(f"🔍 Buscando archivos XML en: {directorio}")
    
    if not os.path.exists(directorio):
        print(f"❌ No se encontró el directorio: {directorio}")
        return None
    
    # Buscar archivos XML
    archivos_xml = glob.glob(os.path.join(directorio, "*.xml"))
    
    if not archivos_xml:
        print(f"⚠️ No se encontraron archivos XML en: {directorio}")
        return None
    
    print(f"📄 Encontrados {len(archivos_xml)} archivos XML")
    
    datos = []
    errores = 0
    
    for i, archivo in enumerate(archivos_xml, 1):
        try:
            print(f"⏳ Procesando {i}/{len(archivos_xml)}: {os.path.basename(archivo)}")
            
            # Cargar CFDI
            cfdi = CFDI.from_file(archivo)
            json_data = json.loads(render.json_str(cfdi))
            
            # Extraer información básica
            fecha = json_data.get('Fecha', '')
            mes = ''
            if fecha:
                try:
                    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                    mes = fecha_obj.strftime('%Y-%m')
                except:
                    mes = fecha[:7] if len(fecha) >= 7 else ''
            
            tipo = json_data.get('TipoDeComprobante', '')
            uuid = json_data.get('Complemento', {}).get('TimbreFiscalDigital', {}).get('UUID', '')
            
            # Procesar conceptos
            conceptos = json_data.get('Conceptos', [])
            
            for concepto in conceptos:
                fila = {
                    'Archivo': os.path.basename(archivo),
                    'UUID': uuid,
                    'Mes': mes,
                    'Tipo_Comprobante': tipo,
                    'Monto': float(concepto.get('Importe', 0)),
                    'Concepto': concepto.get('Descripcion', ''),
                    'Ingresos_Subtotal': 0,
                    'Ingresos_IVA': 0,
                    'Ingresos_Retencion_ISR': 0,
                    'Ingresos_Retencion_IVA': 0,
                    'Egresos_Subtotal': 0,
                    'Egresos_IVA': 0,
                    'Egresos_Total': 0
                }
                
                # Clasificar por tipo de comprobante
                if tipo.startswith('I'):  # Ingreso
                    fila['Ingresos_Subtotal'] = float(concepto.get('Importe', 0))
                    
                    # Calcular impuestos
                    impuestos = concepto.get('Impuestos', {})
                    traslados = impuestos.get('Traslados', {})
                    retenciones = impuestos.get('Retenciones', {})
                    
                    # IVA trasladado
                    for traslado in traslados.values():
                        if '002' in str(traslado.get('Impuesto', '')):
                            fila['Ingresos_IVA'] += float(traslado.get('Importe', 0))
                    
                    # Retenciones
                    for retencion in retenciones.values():
                        impuesto = str(retencion.get('Impuesto', ''))
                        if '001' in impuesto:  # ISR
                            fila['Ingresos_Retencion_ISR'] += float(retencion.get('Importe', 0))
                        elif '002' in impuesto:  # IVA
                            fila['Ingresos_Retencion_IVA'] += float(retencion.get('Importe', 0))
                
                elif tipo.startswith('E'):  # Egreso
                    subtotal = float(concepto.get('Importe', 0))
                    fila['Egresos_Subtotal'] = subtotal
                    
                    # IVA de egresos
                    impuestos = concepto.get('Impuestos', {})
                    traslados = impuestos.get('Traslados', {})
                    for traslado in traslados.values():
                        if '002' in str(traslado.get('Impuesto', '')):
                            fila['Egresos_IVA'] += float(traslado.get('Importe', 0))
                    
                    fila['Egresos_Total'] = fila['Egresos_Subtotal'] + fila['Egresos_IVA']
                
                datos.append(fila)
        
        except Exception as e:
            errores += 1
            print(f"❌ Error en {os.path.basename(archivo)}: {e}")
    
    if datos:
        # Crear Excel
        df = pd.DataFrame(datos)
        
        try:
            with pd.ExcelWriter(nombre_salida, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='CFDIs', index=False)
                
                # Crear hoja de resumen
                resumen = {
                    'Concepto': ['Total CFDIs', 'Total Conceptos', 'Archivos con Error'],
                    'Cantidad': [len(df['UUID'].unique()), len(df), errores],
                    'Ingresos_Subtotal': [df['Ingresos_Subtotal'].sum(), '', ''],
                    'Ingresos_IVA': [df['Ingresos_IVA'].sum(), '', ''],
                    'Egresos_Total': [df['Egresos_Total'].sum(), '', '']
                }
                pd.DataFrame(resumen).to_excel(writer, sheet_name='Resumen', index=False)
            
            print(f"✅ Excel creado: {nombre_salida}")
            print(f"📊 Conceptos procesados: {len(datos)}")
            print(f"📄 CFDIs únicos: {len(df['UUID'].unique())}")
            if errores > 0:
                print(f"⚠️ Archivos con errores: {errores}")
            
            return df
        
        except Exception as e:
            print(f"❌ Error creando Excel: {e}")
            return None
    else:
        print("❌ No se pudieron procesar archivos")
        return None

def main():
    """Función principal"""
    print("="*60)
    print("🧾 PROCESADOR SIMPLE DE CFDIs")
    print("="*60)
    print("Convierte archivos XML de CFDIs a formato Excel")
    print()
    
    # Verificar directorios
    dir_emitidas = "emitidas"
    dir_recibidas = "recibidas"
    
    # Procesar emitidas
    print("📤 PROCESANDO CFDIs EMITIDOS")
    print("-" * 40)
    df_emitidos = procesar_xmls_simple(dir_emitidas, "CFDIs_Emitidos.xlsx")
    
    print()
    print("📥 PROCESANDO CFDIs RECIBIDOS")
    print("-" * 40)
    df_recibidos = procesar_xmls_simple(dir_recibidas, "CFDIs_Recibidos.xlsx")
    
    print()
    print("="*60)
    print("🎉 PROCESAMIENTO COMPLETADO")
    print("="*60)
    
    archivos_generados = []
    if df_emitidos is not None:
        archivos_generados.append("CFDIs_Emitidos.xlsx")
    if df_recibidos is not None:
        archivos_generados.append("CFDIs_Recibidos.xlsx")
    
    if archivos_generados:
        print("📁 Archivos Excel generados:")
        for archivo in archivos_generados:
            print(f"   • {archivo}")
        print()
        print("✨ ¡Listo! Puedes abrir los archivos Excel para ver los resultados.")
    else:
        print("❌ No se generaron archivos Excel")
        print("Verifica que existan las carpetas 'emitidas' y/o 'recibidas' con archivos XML")
    
    print()
    input("Presiona Enter para cerrar...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Procesamiento cancelado por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        input("Presiona Enter para cerrar...")
