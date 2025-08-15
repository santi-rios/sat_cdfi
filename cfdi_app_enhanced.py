import streamlit as st
import pandas as pd
import json
import glob
import os
from datetime import datetime
import zipfile
import tempfile
import io
from PyPDF2 import PdfMerger
from satcfdi.cfdi import CFDI
from satcfdi import render

# Configuración de la página
st.set_page_config(
    page_title="Procesador Avanzado de CFDIs",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

def process_xml_files_enhanced(uploaded_files, file_type):
    """
    Procesa archivos XML subidos y retorna DataFrame con todas las características
    OPTIMIZADO: Acceso directo sin conversión JSON
    """
    all_data = []
    all_pdfs = []
    unique_claves_prodserv = set()  # Para recopilar claves únicas
    
    if not uploaded_files:
        return None, [], []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"Procesando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Leer el archivo XML
            xml_content = uploaded_file.read()
            
            # Procesar con satcfdi - ACCESO DIRECTO SIN JSON
            cfdi = CFDI.from_string(xml_content)
            
            # Generar PDF del CFDI
            try:
                pdf_bytes = render.pdf_bytes(cfdi)
                all_pdfs.append({
                    'filename': uploaded_file.name.replace('.xml', '.pdf'),
                    'content': pdf_bytes
                })
            except Exception as e:
                st.warning(f"No se pudo generar PDF para {uploaded_file.name}: {e}")
            
            # Extraer información DIRECTAMENTE del objeto CFDI
            fecha = cfdi.get('Fecha', '')
            if fecha:
                # La fecha ya viene como datetime desde satcfdi 4.7.5
                if isinstance(fecha, str):
                    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                else:
                    fecha_obj = fecha
                mes = fecha_obj.strftime('%Y-%m')
                fecha_formato = fecha_obj.strftime('%d/%m/%Y')
            else:
                mes = ''
                fecha_formato = ''
            
            tipo_comprobante = str(cfdi.get('TipoDeComprobante', ''))
            folio = str(cfdi.get('Folio', ''))
            uuid = str(cfdi.get('Complemento', {}).get('TimbreFiscalDigital', {}).get('UUID', ''))
            emisor_rfc = str(cfdi.get('Emisor', {}).get('Rfc', ''))
            emisor_nombre = str(cfdi.get('Emisor', {}).get('Nombre', ''))
            receptor_rfc = str(cfdi.get('Receptor', {}).get('Rfc', ''))
            receptor_nombre = str(cfdi.get('Receptor', {}).get('Nombre', ''))
            subtotal_cfdi = float(cfdi.get('SubTotal', 0))
            total_cfdi = float(cfdi.get('Total', 0))
            
            # Procesar conceptos DIRECTAMENTE
            conceptos = cfdi.get('Conceptos', [])
            
            for concepto in conceptos:
                # Recopilar clave única para el checklist - convertir a string
                clave_prodserv = str(concepto.get('ClaveProdServ', ''))
                if clave_prodserv:
                    unique_claves_prodserv.add(clave_prodserv)
                
                row = {
                    'Archivo_XML': uploaded_file.name,
                    'UUID': uuid,
                    'Folio': folio,
                    'Fecha': fecha_formato,
                    'Mes': mes,
                    'Tipo_Comprobante': tipo_comprobante,
                    'Emisor_RFC': emisor_rfc,
                    'Emisor_Nombre': emisor_nombre,
                    'Receptor_RFC': receptor_rfc,
                    'Receptor_Nombre': receptor_nombre,
                    'SubTotal_CFDI': subtotal_cfdi,
                    'Total_CFDI': total_cfdi,
                    'Monto_Concepto': float(concepto.get('Importe', 0)),
                    'Concepto_Descripcion': str(concepto.get('Descripcion', '')),
                    'Cantidad': float(concepto.get('Cantidad', 1)),
                    'Unidad': str(concepto.get('Unidad', '')),
                    'Valor_Unitario': float(concepto.get('ValorUnitario', 0)),
                    'Clave_ProdServ': clave_prodserv,
                    'Categoria': file_type,
                    'Deducible': False  # Campo inicial para marcar deducibilidad
                }
                
                # Inicializar campos de impuestos
                row.update({
                    'Ingresos_Subtotal': 0,
                    'Ingresos_IVA': 0,
                    'Ingresos_Retencion_IVA': 0,
                    'Ingresos_Retencion_ISR': 0,
                    'Egresos_Subtotal': 0,
                    'Egresos_IVA': 0,
                    'Egresos_Total': 0
                })
                
                # Procesar impuestos según tipo de comprobante
                if tipo_comprobante.startswith('I'):  # Ingreso
                    subtotal = float(concepto.get('Importe', 0))
                    row['Ingresos_Subtotal'] = subtotal
                    
                    impuestos = concepto.get('Impuestos', {})
                    
                    # IVA trasladado
                    traslados = impuestos.get('Traslados', {})
                    iva_trasladado = 0
                    for key, traslado in traslados.items():
                        if '002' in key:  # 002 es IVA
                            iva_trasladado += float(traslado.get('Importe', 0))
                    row['Ingresos_IVA'] = iva_trasladado
                    
                    # Retenciones
                    retenciones = impuestos.get('Retenciones', {})
                    retencion_iva = 0
                    retencion_isr = 0
                    
                    for key, retencion in retenciones.items():
                        if '002' in key:  # IVA
                            retencion_iva += float(retencion.get('Importe', 0))
                        elif '001' in key:  # ISR
                            retencion_isr += float(retencion.get('Importe', 0))
                    
                    row['Ingresos_Retencion_IVA'] = retencion_iva
                    row['Ingresos_Retencion_ISR'] = retencion_isr
                
                elif tipo_comprobante.startswith('E'):  # Egreso
                    subtotal = float(concepto.get('Importe', 0))
                    row['Egresos_Subtotal'] = subtotal
                    
                    impuestos = concepto.get('Impuestos', {})
                    traslados = impuestos.get('Traslados', {})
                    iva_trasladado = 0
                    for key, traslado in traslados.items():
                        if '002' in key:
                            iva_trasladado += float(traslado.get('Importe', 0))
                    row['Egresos_IVA'] = iva_trasladado
                    row['Egresos_Total'] = subtotal + iva_trasladado
                
                all_data.append(row)
                
        except Exception as e:
            st.error(f"Error procesando {uploaded_file.name}: {e}")
    
    status_text.text("✅ Procesamiento completado")
    progress_bar.empty()
    
    return pd.DataFrame(all_data) if all_data else None, all_pdfs, sorted(list(unique_claves_prodserv))

def create_enhanced_excel(df, filename, sheet_name):
    """Crea un Excel con múltiples hojas y formato mejorado"""
    if df is None or df.empty:
        return None
    
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Hoja principal con todos los datos
        df.to_excel(writer, sheet_name=f'Detalle_{sheet_name}', index=False)
        
        # Hoja de resumen por mes
        if 'Mes' in df.columns and not df['Mes'].isna().all():
            resumen_mes = df.groupby(['Mes']).agg({
                'Monto_Concepto': 'sum',
                'Ingresos_Subtotal': 'sum',
                'Ingresos_IVA': 'sum',
                'Ingresos_Retencion_IVA': 'sum',
                'Ingresos_Retencion_ISR': 'sum',
                'Egresos_Subtotal': 'sum',
                'Egresos_IVA': 'sum',
                'Egresos_Total': 'sum',
                'UUID': 'count'
            }).reset_index()
            resumen_mes.rename(columns={'UUID': 'Num_CFDIs'}, inplace=True)
            resumen_mes.to_excel(writer, sheet_name='Resumen_Mensual', index=False)
        
        # Hoja de totales generales
        totales_data = {
            'Concepto': ['TOTAL GENERAL'],
            'Num_CFDIs_Unicos': [len(df['UUID'].unique())],
            'Total_Conceptos': [len(df)],
            'Monto_Total': [df['Monto_Concepto'].sum()],
            'Ingresos_Subtotal': [df['Ingresos_Subtotal'].sum()],
            'Ingresos_IVA': [df['Ingresos_IVA'].sum()],
            'Ingresos_Retencion_IVA': [df['Ingresos_Retencion_IVA'].sum()],
            'Ingresos_Retencion_ISR': [df['Ingresos_Retencion_ISR'].sum()],
            'Egresos_Subtotal': [df['Egresos_Subtotal'].sum()],
            'Egresos_IVA': [df['Egresos_IVA'].sum()],
            'Egresos_Total': [df['Egresos_Total'].sum()]
        }
        df_totales = pd.DataFrame(totales_data)
        df_totales.to_excel(writer, sheet_name='Totales_Generales', index=False)
        
        # Formatear todas las hojas
        for sheet_name_ws in writer.sheets:
            worksheet = writer.sheets[sheet_name_ws]
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    return buffer.getvalue()

def merge_pdfs(pdf_list):
    """Fusiona múltiples PDFs en uno solo"""
    if not pdf_list:
        return None
    
    merger = PdfMerger()
    
    for pdf_info in pdf_list:
        try:
            pdf_buffer = io.BytesIO(pdf_info['content'])
            merger.append(pdf_buffer)
        except Exception as e:
            st.warning(f"Error agregando PDF {pdf_info['filename']}: {e}")
    
    output_buffer = io.BytesIO()
    merger.write(output_buffer)
    merger.close()
    
    return output_buffer.getvalue()

def apply_deducibility_filter(df, selected_claves):
    """
    Aplica el filtro de deducibilidad basado en las claves seleccionadas
    """
    if df is None or df.empty:
        return df
    
    # Crear una copia del DataFrame
    df_filtered = df.copy()
    
    # Marcar como deducible los conceptos con claves seleccionadas
    df_filtered['Deducible'] = df_filtered['Clave_ProdServ'].isin(selected_claves)
    
    return df_filtered

def create_data_filter_ui(df):
    """
    Crea una interfaz para filtrar los datos por diferentes criterios
    """
    if df is None or df.empty:
        st.warning("No hay datos disponibles para filtrar.")
        return df
    
    st.subheader("🔍 Filtros de Datos")
    
    with st.expander("Configurar Filtros", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # Filtro por RFC Receptor
            receptores_unicos = sorted(df['Receptor_RFC'].dropna().unique())
            selected_receptores = st.multiselect(
                "RFC Receptor:",
                options=receptores_unicos,
                default=[]
            )
            
            # Filtro por RFC Emisor
            emisores_unicos = sorted(df['Emisor_RFC'].dropna().unique())
            selected_emisores = st.multiselect(
                "RFC Emisor:",
                options=emisores_unicos,
                default=[]
            )
            
            # Filtro por Tipo de Comprobante
            tipos_comprobante = sorted(df['Tipo_Comprobante'].dropna().unique())
            selected_tipos = st.multiselect(
                "Tipo de Comprobante:",
                options=tipos_comprobante,
                default=[]
            )
        
        with col2:
            # Filtro por rango de fechas
            fecha_inicio = None
            fecha_fin = None
            
            if 'Fecha' in df.columns and not df['Fecha'].isna().all():
                fechas_validas = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce').dropna()
                if not fechas_validas.empty:
                    fecha_min = fechas_validas.min().date()
                    fecha_max = fechas_validas.max().date()
                    
                    fecha_inicio = st.date_input(
                        "Fecha Inicio:",
                        value=fecha_min,
                        min_value=fecha_min,
                        max_value=fecha_max
                    )
                    
                    fecha_fin = st.date_input(
                        "Fecha Fin:",
                        value=fecha_max,
                        min_value=fecha_min,
                        max_value=fecha_max
                    )
            
            # Filtro por monto mínimo
            monto_min = st.number_input(
                "Monto Mínimo:",
                min_value=0.0,
                value=0.0,
                step=100.0
            )
            
            # Filtro por deducibilidad
            filtro_deducible = st.selectbox(
                "Mostrar solo:",
                options=["Todos", "Solo Deducibles", "Solo No Deducibles"]
            )
    
    # Aplicar filtros
    df_filtered = df.copy()
    
    if selected_receptores:
        df_filtered = df_filtered[df_filtered['Receptor_RFC'].isin(selected_receptores)]
    
    if selected_emisores:
        df_filtered = df_filtered[df_filtered['Emisor_RFC'].isin(selected_emisores)]
    
    if selected_tipos:
        df_filtered = df_filtered[df_filtered['Tipo_Comprobante'].isin(selected_tipos)]
    
    if fecha_inicio is not None and fecha_fin is not None:
        # Convertir fechas del DataFrame para comparación
        df_fechas = pd.to_datetime(df_filtered['Fecha'], format='%d/%m/%Y', errors='coerce')
        # Manejo seguro de tipos de fecha de Streamlit
        try:
            # Convertir a string y luego a timestamp para manejar todos los tipos
            inicio_str = str(fecha_inicio)
            fin_str = str(fecha_fin)
            inicio_ts = pd.Timestamp(inicio_str)
            fin_ts = pd.Timestamp(fin_str)
            mask_fecha = (df_fechas >= inicio_ts) & (df_fechas <= fin_ts)
            df_filtered = df_filtered[mask_fecha]
        except (TypeError, ValueError):
            # Si hay problemas con las fechas, simplemente no aplicar el filtro
            pass
    
    if monto_min > 0:
        df_filtered = df_filtered[df_filtered['Monto_Concepto'] >= monto_min]
    
    if filtro_deducible == "Solo Deducibles":
        df_filtered = df_filtered[df_filtered['Deducible'] == True]
    elif filtro_deducible == "Solo No Deducibles":
        df_filtered = df_filtered[df_filtered['Deducible'] == False]
    
    # Mostrar resumen del filtrado
    if len(df_filtered) != len(df):
        st.info(f"📊 Mostrando {len(df_filtered)} de {len(df)} registros ({len(df_filtered)/len(df)*100:.1f}%)")
    
    return df_filtered

def create_custom_export_ui(df):
    """
    Crea una interfaz para exportar subconjuntos personalizados de datos
    """
    if df is None or df.empty:
        return
    
    st.subheader("📤 Exportación Personalizada")
    
    with st.expander("Configurar Exportación", expanded=False):
        # Seleccionar columnas
        todas_columnas = df.columns.tolist()
        columnas_seleccionadas = st.multiselect(
            "Seleccionar Columnas:",
            options=todas_columnas,
            default=['UUID', 'Fecha', 'Emisor_RFC', 'Receptor_RFC', 'Monto_Concepto', 'Clave_ProdServ', 'Deducible']
        )
        
        # Nombre del archivo
        nombre_archivo = st.text_input(
            "Nombre del archivo:",
            value="datos_cfdi_personalizado"
        )
        
        # Formato de exportación
        formato_export = st.selectbox(
            "Formato:",
            options=["Excel (.xlsx)", "CSV (.csv)"]
        )
        
        if st.button("🚀 Generar Exportación Personalizada"):
            if not columnas_seleccionadas:
                st.error("Debes seleccionar al menos una columna.")
                return
            
            # Crear DataFrame con las columnas seleccionadas
            df_export = df[columnas_seleccionadas].copy()
            
            if formato_export == "Excel (.xlsx)":
                # Crear Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_export.to_excel(writer, sheet_name='Datos_Personalizados', index=False)
                
                st.download_button(
                    label="📥 Descargar Excel Personalizado",
                    data=buffer.getvalue(),
                    file_name=f"{nombre_archivo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            elif formato_export == "CSV (.csv)":
                # Crear CSV
                csv_data = df_export.to_csv(index=False, encoding='utf-8-sig')
                
                st.download_button(
                    label="📥 Descargar CSV Personalizado",
                    data=csv_data,
                    file_name=f"{nombre_archivo}.csv",
                    mime="text/csv"
                )
            
            st.success(f"✅ Archivo {formato_export} preparado para descarga!")
            st.info(f"📊 Exportando {len(df_export)} filas y {len(df_export.columns)} columnas")

def main():
    st.title("🧾 Procesador Avanzado de CFDIs")
    st.markdown("### Convierte XMLs a Excel y genera PDFs consolidados")
    
    # Sidebar con información
    st.sidebar.header("📋 Características")
    st.sidebar.markdown("""
    ✅ **Excel con múltiples hojas:**
    - Detalle completo
    - Resumen mensual
    - Totales generales
    
    ✅ **Generación de PDFs:**
    - PDF individual por CFDI
    - PDF consolidado fusionado
    
    ✅ **Campos completos:**
    - Información fiscal completa
    - Desglose de impuestos
    - Datos de emisor/receptor
    """)
    
    # Tabs principales
    tab1, tab2, tab3 = st.tabs(["📤 CFDIs Emitidos", "📥 CFDIs Recibidos", "📊 Consolidado"])
    
    # Variables de sesión
    if 'df_emitidos' not in st.session_state:
        st.session_state.df_emitidos = None
    if 'df_recibidos' not in st.session_state:
        st.session_state.df_recibidos = None
    if 'pdfs_emitidos' not in st.session_state:
        st.session_state.pdfs_emitidos = []
    if 'pdfs_recibidos' not in st.session_state:
        st.session_state.pdfs_recibidos = []
    if 'claves_emitidos' not in st.session_state:
        st.session_state.claves_emitidos = []
    if 'claves_recibidos' not in st.session_state:
        st.session_state.claves_recibidos = []
    
    with tab1:
        st.header("📤 CFDIs Emitidos")
        
        uploaded_emitidos = st.file_uploader(
            "📁 Selecciona archivos XML de CFDIs emitidos",
            type=['xml'],
            accept_multiple_files=True,
            key="emitidos"
        )
        
        if uploaded_emitidos:
            if st.button("🚀 Procesar CFDIs Emitidos", key="btn_emitidos"):
                with st.spinner("Procesando CFDIs emitidos..."):
                    result = process_xml_files_enhanced(uploaded_emitidos, "Emitidos")
                    # La función ahora retorna 3 valores: df, pdfs, claves_unicas
                    st.session_state.df_emitidos, st.session_state.pdfs_emitidos, st.session_state.claves_emitidos = result
                
                if st.session_state.df_emitidos is not None:
                    st.success(f"✅ {len(st.session_state.df_emitidos)} conceptos procesados")
                    st.success(f"📄 {len(st.session_state.pdfs_emitidos)} PDFs generados")
                    st.success(f"🔑 {len(st.session_state.claves_emitidos)} claves de productos/servicios encontradas")
        
        if st.session_state.df_emitidos is not None:
            # Checklist de deducibilidad
            if 'claves_emitidos' in st.session_state and st.session_state.claves_emitidos:
                st.subheader("✅ Seleccionar Servicios Deducibles")
                
                with st.expander("Configurar Deducibilidad", expanded=True):
                    st.info("💡 Selecciona las claves de productos/servicios que son deducibles de impuestos:")
                    
                    # Crear columnas para mostrar las claves organizadamente
                    n_claves = len(st.session_state.claves_emitidos)
                    n_cols = min(3, n_claves)  # Máximo 3 columnas
                    cols = st.columns(n_cols)
                    
                    selected_claves = []
                    for i, clave in enumerate(st.session_state.claves_emitidos):
                        col_idx = i % n_cols
                        with cols[col_idx]:
                            if st.checkbox(f"� {clave}", key=f"clave_emit_{clave}"):
                                selected_claves.append(clave)
                    
                    if st.button("💾 Aplicar Configuración de Deducibilidad", key="apply_deduct_emit"):
                        # Aplicar el filtro de deducibilidad
                        st.session_state.df_emitidos = apply_deducibility_filter(
                            st.session_state.df_emitidos, selected_claves
                        )
                        st.success(f"✅ Configuración aplicada: {len(selected_claves)} claves marcadas como deducibles")
                        st.rerun()
            
            # Filtros de datos
            df_filtered = create_data_filter_ui(st.session_state.df_emitidos)
            
            # Mostrar métricas
            st.subheader("📊 Resumen Emitidos")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("CFDIs Únicos", len(df_filtered['UUID'].unique()))
            with col2:
                st.metric("Total Conceptos", len(df_filtered))
            with col3:
                st.metric("Ingresos Subtotal", f"${df_filtered['Ingresos_Subtotal'].sum():,.2f}")
            with col4:
                st.metric("IVA Ingresos", f"${df_filtered['Ingresos_IVA'].sum():,.2f}")
            
            # Mostrar métricas adicionales de deducibilidad
            if 'Deducible' in df_filtered.columns:
                col5, col6 = st.columns(2)
                with col5:
                    deducibles = df_filtered[df_filtered['Deducible'] == True]
                    st.metric("💰 Gastos Deducibles", f"${deducibles['Monto_Concepto'].sum():,.2f}")
                with col6:
                    st.metric("📊 % Deducible", f"{len(deducibles)/len(df_filtered)*100:.1f}%")
            
            # Mostrar datos filtrados
            st.subheader("📋 Datos Detallados")
            st.dataframe(df_filtered, use_container_width=True, height=300)
            
            # Exportación personalizada
            create_custom_export_ui(df_filtered)
            
            # Botones de descarga tradicionales
            st.subheader("📥 Descargas Tradicionales")
            col1, col2 = st.columns(2)
            
            with col1:
                excel_data = create_enhanced_excel(df_filtered, "Emitidos", "Emitidos")
                if excel_data:
                    st.download_button(
                        label="📊 Descargar Excel Completo",
                        data=excel_data,
                        file_name="CFDIs_Emitidos_Completo.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col2:
                if st.session_state.pdfs_emitidos:
                    merged_pdf = merge_pdfs(st.session_state.pdfs_emitidos)
                    if merged_pdf:
                        st.download_button(
                            label="📄 Descargar PDF Consolidado",
                            data=merged_pdf,
                            file_name="CFDIs_Emitidos_Consolidado.pdf",
                            mime="application/pdf"
                        )
    
    with tab2:
        st.header("📥 CFDIs Recibidos")
        
        uploaded_recibidos = st.file_uploader(
            "📁 Selecciona archivos XML de CFDIs recibidos",
            type=['xml'],
            accept_multiple_files=True,
            key="recibidos"
        )
        
        if uploaded_recibidos:
            if st.button("🚀 Procesar CFDIs Recibidos", key="btn_recibidos"):
                with st.spinner("Procesando CFDIs recibidos..."):
                    result = process_xml_files_enhanced(uploaded_recibidos, "Recibidos")
                    # La función ahora retorna 3 valores: df, pdfs, claves_unicas
                    st.session_state.df_recibidos, st.session_state.pdfs_recibidos, st.session_state.claves_recibidos = result
                
                if st.session_state.df_recibidos is not None:
                    st.success(f"✅ {len(st.session_state.df_recibidos)} conceptos procesados")
                    st.success(f"📄 {len(st.session_state.pdfs_recibidos)} PDFs generados")
                    st.success(f"🔑 {len(st.session_state.claves_recibidos)} claves de productos/servicios encontradas")
        
        if st.session_state.df_recibidos is not None:
            # Checklist de deducibilidad
            if 'claves_recibidos' in st.session_state and st.session_state.claves_recibidos:
                st.subheader("✅ Seleccionar Servicios Deducibles")
                
                with st.expander("Configurar Deducibilidad", expanded=True):
                    st.info("💡 Selecciona las claves de productos/servicios que son deducibles de impuestos:")
                    
                    # Crear columnas para mostrar las claves organizadamente
                    n_claves = len(st.session_state.claves_recibidos)
                    n_cols = min(3, n_claves)  # Máximo 3 columnas
                    cols = st.columns(n_cols)
                    
                    selected_claves = []
                    for i, clave in enumerate(st.session_state.claves_recibidos):
                        col_idx = i % n_cols
                        with cols[col_idx]:
                            if st.checkbox(f"� {clave}", key=f"clave_rec_{clave}"):
                                selected_claves.append(clave)
                    
                    if st.button("💾 Aplicar Configuración de Deducibilidad", key="apply_deduct_rec"):
                        # Aplicar el filtro de deducibilidad
                        st.session_state.df_recibidos = apply_deducibility_filter(
                            st.session_state.df_recibidos, selected_claves
                        )
                        st.success(f"✅ Configuración aplicada: {len(selected_claves)} claves marcadas como deducibles")
                        st.rerun()
            
            # Filtros de datos
            df_filtered = create_data_filter_ui(st.session_state.df_recibidos)
            
            # Mostrar métricas
            st.subheader("📊 Resumen Recibidos")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("CFDIs Únicos", len(df_filtered['UUID'].unique()))
            with col2:
                st.metric("Total Conceptos", len(df_filtered))
            with col3:
                total_ingresos = df_filtered['Ingresos_Subtotal'].sum()
                total_egresos = df_filtered['Egresos_Subtotal'].sum()
                st.metric("Ingresos/Egresos", f"${(total_ingresos + total_egresos):,.2f}")
            with col4:
                total_iva = (df_filtered['Ingresos_IVA'].sum() + 
                           df_filtered['Egresos_IVA'].sum())
                st.metric("Total IVA", f"${total_iva:,.2f}")
            
            # Mostrar métricas adicionales de deducibilidad
            if 'Deducible' in df_filtered.columns:
                col5, col6 = st.columns(2)
                with col5:
                    deducibles = df_filtered[df_filtered['Deducible'] == True]
                    st.metric("💰 Gastos Deducibles", f"${deducibles['Monto_Concepto'].sum():,.2f}")
                with col6:
                    st.metric("📊 % Deducible", f"{len(deducibles)/len(df_filtered)*100:.1f}%")
            
            # Mostrar datos filtrados
            st.subheader("📋 Datos Detallados")
            st.dataframe(df_filtered, use_container_width=True, height=300)
            
            # Exportación personalizada
            create_custom_export_ui(df_filtered)
            
            # Botones de descarga tradicionales
            st.subheader("📥 Descargas Tradicionales")
            col1, col2 = st.columns(2)
            
            with col1:
                excel_data = create_enhanced_excel(df_filtered, "Recibidos", "Recibidos")
                if excel_data:
                    st.download_button(
                        label="📊 Descargar Excel Completo",
                        data=excel_data,
                        file_name="CFDIs_Recibidos_Completo.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col2:
                if st.session_state.pdfs_recibidos:
                    merged_pdf = merge_pdfs(st.session_state.pdfs_recibidos)
                    if merged_pdf:
                        st.download_button(
                            label="📄 Descargar PDF Consolidado",
                            data=merged_pdf,
                            file_name="CFDIs_Recibidos_Consolidado.pdf",
                            mime="application/pdf"
                        )
    
    with tab3:
        st.header("📊 Resumen Consolidado")
        
        if st.session_state.df_emitidos is not None or st.session_state.df_recibidos is not None:
            # Crear DataFrame consolidado
            df_consolidado = pd.DataFrame()
            
            if st.session_state.df_emitidos is not None:
                df_consolidado = pd.concat([df_consolidado, st.session_state.df_emitidos], ignore_index=True)
            
            if st.session_state.df_recibidos is not None:
                df_consolidado = pd.concat([df_consolidado, st.session_state.df_recibidos], ignore_index=True)
            
            if not df_consolidado.empty:
                # Métricas consolidadas
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total CFDIs", len(df_consolidado['UUID'].unique()))
                with col2:
                    st.metric("Total Conceptos", len(df_consolidado))
                with col3:
                    total_ingresos = df_consolidado['Ingresos_Subtotal'].sum()
                    st.metric("Total Ingresos", f"${total_ingresos:,.2f}")
                with col4:
                    total_egresos = df_consolidado['Egresos_Subtotal'].sum()
                    st.metric("Total Egresos", f"${total_egresos:,.2f}")
                
                # Gráfico mejorado (arreglando el error)
                st.subheader("📈 Análisis por Mes y Categoría")
                
                if 'Mes' in df_consolidado.columns and not df_consolidado['Mes'].isna().all():
                    # Crear datos para el gráfico de forma más segura
                    chart_data = df_consolidado.groupby(['Mes', 'Categoria']).agg({
                        'Ingresos_Subtotal': 'sum',
                        'Egresos_Subtotal': 'sum'
                    }).reset_index()
                    
                    # Crear gráfico usando plotly para mejor control
                    import plotly.express as px
                    
                    # Crear datos para gráfico
                    chart_melted = pd.melt(
                        chart_data, 
                        id_vars=['Mes', 'Categoria'], 
                        value_vars=['Ingresos_Subtotal', 'Egresos_Subtotal'],
                        var_name='Tipo', 
                        value_name='Monto'
                    )
                    
                    if not chart_melted.empty:
                        fig = px.bar(
                            chart_melted, 
                            x='Mes', 
                            y='Monto', 
                            color='Categoria',
                            facet_col='Tipo',
                            title="Ingresos y Egresos por Mes y Categoría"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # Tabla resumen
                st.subheader("📋 Tabla Resumen")
                st.dataframe(df_consolidado, use_container_width=True, height=400)
                
                # Descargas consolidadas
                st.subheader("💾 Descargas Consolidadas")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel consolidado
                    excel_consolidado = create_enhanced_excel(df_consolidado, "Consolidado", "Todos")
                    if excel_consolidado:
                        st.download_button(
                            label="📊 Excel Consolidado",
                            data=excel_consolidado,
                            file_name="CFDIs_Consolidado_Completo.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                
                with col2:
                    # PDF consolidado de todos
                    all_pdfs = st.session_state.pdfs_emitidos + st.session_state.pdfs_recibidos
                    if all_pdfs:
                        merged_all_pdf = merge_pdfs(all_pdfs)
                        if merged_all_pdf:
                            st.download_button(
                                label="📄 PDF Consolidado Total",
                                data=merged_all_pdf,
                                file_name="CFDIs_Todos_Consolidado.pdf",
                                mime="application/pdf"
                            )
                
                with col3:
                    # Mostrar estadísticas adicionales
                    st.info(f"""
                    **Estadísticas:**
                    - CFDIs Emitidos: {len(st.session_state.pdfs_emitidos)}
                    - CFDIs Recibidos: {len(st.session_state.pdfs_recibidos)}
                    - Total PDFs: {len(all_pdfs)}
                    """)
        else:
            st.info("Procesa algunos CFDIs para ver el resumen consolidado")
            st.markdown("""
            **Para comenzar:**
            1. Ve a la pestaña de **CFDIs Emitidos** o **CFDIs Recibidos**
            2. Sube tus archivos XML
            3. Haz clic en **Procesar**
            4. Regresa aquí para ver el consolidado
            """)

if __name__ == "__main__":
    try:
        import plotly.express as px
    except ImportError:
        st.error("Por favor instala plotly: pip install plotly")
    
    main()
