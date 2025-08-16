#!/usr/bin/env python3
"""
Script de prueba para verificar que WeasyPrint funcione en el contenedor Docker
"""

def test_weasyprint():
    """Prueba básica de WeasyPrint"""
    try:
        from weasyprint import HTML, CSS
        print("✅ WeasyPrint importado correctamente")
        
        # Crear un HTML simple
        html_content = """
        <html>
        <head>
            <title>Prueba WeasyPrint</title>
            <style>
                body { font-family: Arial, sans-serif; }
                h1 { color: #1f77b4; }
            </style>
        </head>
        <body>
            <h1>🧾 Prueba de WeasyPrint en Docker</h1>
            <p>Si puedes leer esto, WeasyPrint está funcionando correctamente en el contenedor.</p>
            <ul>
                <li>✅ Python 3.11</li>
                <li>✅ WeasyPrint instalado</li>
                <li>✅ Dependencias del sistema correctas</li>
            </ul>
        </body>
        </html>
        """
        
        # Generar PDF
        html_doc = HTML(string=html_content)
        pdf_bytes = html_doc.write_pdf()
        
        if pdf_bytes:
            print(f"✅ PDF generado exitosamente ({len(pdf_bytes)} bytes)")
            return True
        else:
            print("❌ Error: PDF generado está vacío")
            return False
        
    except ImportError as e:
        print(f"❌ Error al importar WeasyPrint: {e}")
        return False
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")
        return False

def test_other_packages():
    """Prueba otros paquetes importantes"""
    packages = [
        ("streamlit", "st"),
        ("pandas", "pd"), 
        ("plotly.express", "px"),
        ("satcfdi.cfdi", "CFDI"),
        ("PyPDF2", "PdfMerger")
    ]
    
    for package_name, import_name in packages:
        try:
            if "." in import_name:
                module_parts = import_name.split(".")
                module = __import__(package_name)
                for part in module_parts[1:]:
                    module = getattr(module, part)
            else:
                __import__(package_name)
            print(f"✅ {package_name} - OK")
        except ImportError as e:
            print(f"❌ {package_name} - ERROR: {e}")

if __name__ == "__main__":
    print("🐳 Prueba de dependencias en contenedor Docker")
    print("=" * 50)
    
    print("\n📦 Probando paquetes Python:")
    test_other_packages()
    
    print("\n📄 Probando WeasyPrint:")
    test_weasyprint()
    
    print("\n🎉 Prueba completada")
