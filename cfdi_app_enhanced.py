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

# Configuración de la página
st.set_page_config(
    page_title="Procesador Avanzado de CFDIs",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

def process_xml_files_enhanced(uploaded_files, file_type):
    """Procesa archivos XML subidos y retorna DataFrame con todas las características"""
    all_data = []
    all_pdfs = []
    
    if not uploaded_files:
        return None, []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            status_text.text(f"Procesando {i+1}/{len(uploaded_files)}: {uploaded_file.name}")
            progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Leer el archivo XML
            xml_content = uploaded_file.read()
            
            # Procesar con satcfdi
            cfdi = CFDI.from_string(xml_content)
            json_data = json.loads(cfdi.json_str())
            
            # Generar PDF del CFDI
            try:
                pdf_bytes = cfdi.pdf_bytes()
                all_pdfs.append({
                    'filename': uploaded_file.name.replace('.xml', '.pdf'),
                    'content': pdf_bytes
                })
            except Exception as e:
                st.warning(f"No se pudo generar PDF para {uploaded_file.name}: {e}")
            
            # Extraer información
            fecha = json_data.get('Fecha', '')
            if fecha:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                mes = fecha_obj.strftime('%Y-%m')
                fecha_formato = fecha_obj.strftime('%d/%m/%Y')
            else:
                mes = ''
                fecha_formato = ''
            
            tipo_comprobante = json_data.get('TipoDeComprobante', '')
            folio = json_data.get('Folio', '')
            uuid = json_data.get('Complemento', {}).get('TimbreFiscalDigital', {}).get('UUID', '')
            emisor_rfc = json_data.get('Emisor', {}).get('Rfc', '')
            emisor_nombre = json_data.get('Emisor', {}).get('Nombre', '')
            receptor_rfc = json_data.get('Receptor', {}).get('Rfc', '')
            receptor_nombre = json_data.get('Receptor', {}).get('Nombre', '')
            subtotal_cfdi = float(json_data.get('SubTotal', 0))
            total_cfdi = float(json_data.get('Total', 0))
            
            # Procesar conceptos
            conceptos = json_data.get('Conceptos', [])
            
            for concepto in conceptos:
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
                    'Concepto_Descripcion': concepto.get('Descripcion', ''),
                    'Cantidad': float(concepto.get('Cantidad', 1)),
                    'Unidad': concepto.get('Unidad', ''),
                    'Valor_Unitario': float(concepto.get('ValorUnitario', 0)),
                    'Clave_ProdServ': concepto.get('ClaveProdServ', ''),
                    'Categoria': file_type
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
    
    return pd.DataFrame(all_data) if all_data else None, all_pdfs

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
                    st.session_state.df_emitidos, st.session_state.pdfs_emitidos = process_xml_files_enhanced(
                        uploaded_emitidos, "Emitidos"
                    )
                
                if st.session_state.df_emitidos is not None:
                    st.success(f"✅ {len(st.session_state.df_emitidos)} conceptos procesados")
                    st.success(f"📄 {len(st.session_state.pdfs_emitidos)} PDFs generados")
        
        if st.session_state.df_emitidos is not None:
            # Mostrar métricas
            st.subheader("📊 Resumen Emitidos")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("CFDIs Únicos", len(st.session_state.df_emitidos['UUID'].unique()))
            with col2:
                st.metric("Total Conceptos", len(st.session_state.df_emitidos))
            with col3:
                st.metric("Ingresos Subtotal", f"${st.session_state.df_emitidos['Ingresos_Subtotal'].sum():,.2f}")
            with col4:
                st.metric("IVA Ingresos", f"${st.session_state.df_emitidos['Ingresos_IVA'].sum():,.2f}")
            
            # Mostrar datos
            st.subheader("📋 Datos Detallados")
            st.dataframe(st.session_state.df_emitidos, use_container_width=True, height=300)
            
            # Botones de descarga
            col1, col2 = st.columns(2)
            
            with col1:
                excel_data = create_enhanced_excel(st.session_state.df_emitidos, "Emitidos", "Emitidos")
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
                    st.session_state.df_recibidos, st.session_state.pdfs_recibidos = process_xml_files_enhanced(
                        uploaded_recibidos, "Recibidos"
                    )
                
                if st.session_state.df_recibidos is not None:
                    st.success(f"✅ {len(st.session_state.df_recibidos)} conceptos procesados")
                    st.success(f"📄 {len(st.session_state.pdfs_recibidos)} PDFs generados")
        
        if st.session_state.df_recibidos is not None:
            # Mostrar métricas
            st.subheader("📊 Resumen Recibidos")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("CFDIs Únicos", len(st.session_state.df_recibidos['UUID'].unique()))
            with col2:
                st.metric("Total Conceptos", len(st.session_state.df_recibidos))
            with col3:
                total_ingresos = st.session_state.df_recibidos['Ingresos_Subtotal'].sum()
                total_egresos = st.session_state.df_recibidos['Egresos_Subtotal'].sum()
                st.metric("Ingresos/Egresos", f"${(total_ingresos + total_egresos):,.2f}")
            with col4:
                total_iva = (st.session_state.df_recibidos['Ingresos_IVA'].sum() + 
                           st.session_state.df_recibidos['Egresos_IVA'].sum())
                st.metric("Total IVA", f"${total_iva:,.2f}")
            
            # Mostrar datos
            st.subheader("📋 Datos Detallados")
            st.dataframe(st.session_state.df_recibidos, use_container_width=True, height=300)
            
            # Botones de descarga
            col1, col2 = st.columns(2)
            
            with col1:
                excel_data = create_enhanced_excel(st.session_state.df_recibidos, "Recibidos", "Recibidos")
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
