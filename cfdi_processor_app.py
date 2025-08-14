
import streamlit as st
import pandas as pd
import json
import glob
import os
from datetime import datetime
import zipfile
import tempfile
from satcfdi.cfdi import CFDI
from satcfdi import render

# Configuración de la página
st.set_page_config(
    page_title="Procesador de CFDIs",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función para procesar XMLs
def process_xml_files_streamlit(uploaded_files, file_type):
    """Procesa archivos XML subidos y retorna DataFrame"""
    all_data = []
    
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
            json_data = json.loads(render.json_str(cfdi))
            
            # Extraer información
            fecha = json_data.get('Fecha', '')
            if fecha:
                fecha_obj = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                mes = fecha_obj.strftime('%Y-%m')
            else:
                mes = ''
            
            tipo_comprobante = json_data.get('TipoDeComprobante', '')
            folio = json_data.get('Folio', '')
            uuid = json_data.get('Complemento', {}).get('TimbreFiscalDigital', {}).get('UUID', '')
            emisor_rfc = json_data.get('Emisor', {}).get('Rfc', '')
            receptor_rfc = json_data.get('Receptor', {}).get('Rfc', '')
            
            # Procesar conceptos
            conceptos = json_data.get('Conceptos', [])
            
            for concepto in conceptos:
                row = {
                    'Archivo_XML': uploaded_file.name,
                    'UUID': uuid,
                    'Folio': folio,
                    'Mes': mes,
                    'Tipo': tipo_comprobante,
                    'Emisor_RFC': emisor_rfc,
                    'Receptor_RFC': receptor_rfc,
                    'Monto': float(concepto.get('Importe', 0)),
                    'Concepto': concepto.get('Descripcion', ''),
                    'Categoria': file_type  # Emitidos o Recibidos
                }
                
                # Procesar impuestos
                if tipo_comprobante.startswith('I'):  # Ingreso
                    subtotal = float(concepto.get('Importe', 0))
                    row['Ingresos_Subtotal'] = subtotal
                    
                    impuestos = concepto.get('Impuestos', {})
                    
                    # IVA trasladado
                    traslados = impuestos.get('Traslados', {})
                    iva_trasladado = 0
                    for key, traslado in traslados.items():
                        if '002' in key:
                            iva_trasladado += float(traslado.get('Importe', 0))
                    row['Ingresos_IVA'] = iva_trasladado
                    
                    # Retenciones
                    retenciones = impuestos.get('Retenciones', {})
                    retencion_iva = 0
                    retencion_isr = 0
                    
                    for key, retencion in retenciones.items():
                        if '002' in key:
                            retencion_iva += float(retencion.get('Importe', 0))
                        elif '001' in key:
                            retencion_isr += float(retencion.get('Importe', 0))
                    
                    row['Ingresos_Retencion_IVA'] = retencion_iva
                    row['Ingresos_Retencion_ISR'] = retencion_isr
                    row['Egresos_Subtotal'] = 0
                    row['Egresos_IVA'] = 0
                    row['Egresos_Total'] = 0
                
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
                    
                    row['Ingresos_Subtotal'] = 0
                    row['Ingresos_IVA'] = 0
                    row['Ingresos_Retencion_IVA'] = 0
                    row['Ingresos_Retencion_ISR'] = 0
                
                all_data.append(row)
                
        except Exception as e:
            st.error(f"Error procesando {uploaded_file.name}: {e}")
    
    status_text.text("✅ Procesamiento completado")
    progress_bar.empty()
    
    return pd.DataFrame(all_data) if all_data else None

# Interfaz principal
def main():
    st.title("🧾 Procesador de CFDIs")
    st.markdown("### Convierte archivos XML de CFDIs a formato Excel")
    
    # Sidebar
    st.sidebar.header("📋 Instrucciones")
    st.sidebar.markdown("""
    1. **Sube archivos XML** de CFDIs emitidos y/o recibidos
    2. **Procesa** los archivos automáticamente
    3. **Descarga** los archivos Excel generados
    4. **Visualiza** resúmenes y estadísticas
    """)
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📤 CFDIs Emitidos", "📥 CFDIs Recibidos", "📊 Resumen Consolidado"])
    
    # Variables de sesión
    if 'df_emitidos' not in st.session_state:
        st.session_state.df_emitidos = None
    if 'df_recibidos' not in st.session_state:
        st.session_state.df_recibidos = None
    
    with tab1:
        st.header("📤 CFDIs Emitidos")
        
        uploaded_emitidos = st.file_uploader(
            "Selecciona archivos XML de CFDIs emitidos",
            type=['xml'],
            accept_multiple_files=True,
            key="emitidos"
        )
        
        if uploaded_emitidos:
            if st.button("🚀 Procesar CFDIs Emitidos", key="btn_emitidos"):
                with st.spinner("Procesando CFDIs emitidos..."):
                    st.session_state.df_emitidos = process_xml_files_streamlit(uploaded_emitidos, "Emitidos")
                
                if st.session_state.df_emitidos is not None:
                    st.success(f"✅ {len(st.session_state.df_emitidos)} conceptos procesados")
        
        if st.session_state.df_emitidos is not None:
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
            
            st.subheader("📋 Datos Detallados")
            st.dataframe(st.session_state.df_emitidos, use_container_width=True)
            
            # Botón de descarga
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                st.session_state.df_emitidos.to_excel(writer, sheet_name='CFDIs_Emitidos', index=False)
            
            st.download_button(
                label="📁 Descargar Excel - CFDIs Emitidos",
                data=excel_buffer.getvalue(),
                file_name="CFDIs_Emitidos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with tab2:
        st.header("📥 CFDIs Recibidos")
        
        uploaded_recibidos = st.file_uploader(
            "Selecciona archivos XML de CFDIs recibidos",
            type=['xml'],
            accept_multiple_files=True,
            key="recibidos"
        )
        
        if uploaded_recibidos:
            if st.button("🚀 Procesar CFDIs Recibidos", key="btn_recibidos"):
                with st.spinner("Procesando CFDIs recibidos..."):
                    st.session_state.df_recibidos = process_xml_files_streamlit(uploaded_recibidos, "Recibidos")
                
                if st.session_state.df_recibidos is not None:
                    st.success(f"✅ {len(st.session_state.df_recibidos)} conceptos procesados")
        
        if st.session_state.df_recibidos is not None:
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
                total_iva = st.session_state.df_recibidos['Ingresos_IVA'].sum() + st.session_state.df_recibidos['Egresos_IVA'].sum()
                st.metric("Total IVA", f"${total_iva:,.2f}")
            
            st.subheader("📋 Datos Detallados")
            st.dataframe(st.session_state.df_recibidos, use_container_width=True)
            
            # Botón de descarga
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                st.session_state.df_recibidos.to_excel(writer, sheet_name='CFDIs_Recibidos', index=False)
            
            st.download_button(
                label="📁 Descargar Excel - CFDIs Recibidos",
                data=excel_buffer.getvalue(),
                file_name="CFDIs_Recibidos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
                
                # Gráficos
                st.subheader("📈 Análisis por Mes")
                
                if 'Mes' in df_consolidado.columns:
                    resumen_mes = df_consolidado.groupby(['Mes', 'Categoria']).agg({
                        'Ingresos_Subtotal': 'sum',
                        'Egresos_Subtotal': 'sum'
                    }).reset_index()
                    
                    st.bar_chart(data=resumen_mes.set_index(['Mes', 'Categoria']))
                
                # Descarga consolidada
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_consolidado.to_excel(writer, sheet_name='Consolidado', index=False)
                    
                    if st.session_state.df_emitidos is not None:
                        st.session_state.df_emitidos.to_excel(writer, sheet_name='Emitidos', index=False)
                    
                    if st.session_state.df_recibidos is not None:
                        st.session_state.df_recibidos.to_excel(writer, sheet_name='Recibidos', index=False)
                
                st.download_button(
                    label="📁 Descargar Excel Consolidado",
                    data=excel_buffer.getvalue(),
                    file_name="CFDIs_Consolidado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("Procesa algunos CFDIs para ver el resumen consolidado")

if __name__ == "__main__":
    import io
    main()
