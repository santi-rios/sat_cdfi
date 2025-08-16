"""
Modelos básicos para DIOT (Declaración Informativa de Operaciones con Terceros)
"""
from enum import Enum

class Periodo(Enum):
    ENERO = "01"
    FEBRERO = "02"
    MARZO = "03"
    ABRIL = "04"
    MAYO = "05"
    JUNIO = "06"
    JULIO = "07"
    AGOSTO = "08"
    SEPTIEMBRE = "09"
    OCTUBRE = "10"
    NOVIEMBRE = "11"
    DICIEMBRE = "12"
    ENERO_MARZO = "04"
    ABRIL_JUNIO = "05"
    JULIO_SEPTIEMBRE = "06"
    OCTUBRE_DICIEMBRE = "07"

class TipoTercero(Enum):
    PROVEEDOR_NACIONAL = "04"
    PROVEEDOR_EXTRANJERO = "05"
    PROVEEDOR_GLOBAL = "15"

class TipoOperacion(Enum):
    OTROS = "03"
    ARRENDAMIENTO_DE_INMUEBLES = "06"
    PRESTACION_DE_SERVICIOS_PROFESIONALES = "85"

class Pais(Enum):
    ESTADOS_UNIDOS = "USA"
    CANADA = "CAN"
    MEXICO = "MEX"
    ESPAÑA = "ESP"
    ALEMANIA = "DEU"
    FRANCIA = "FRA"
    REINO_UNIDO = "GBR"
    JAPON = "JPN"
    CHINA = "CHN"
    BRAZIL = "BRA"

class DatosIdentificacion:
    def __init__(self, rfc, razon_social, ejercicio, periodo):
        self.rfc = rfc
        self.razon_social = razon_social
        self.ejercicio = ejercicio
        self.periodo = periodo

class ProveedorTercero:
    def __init__(self, tipo_tercero, tipo_operacion, rfc=None, id_fiscal=None, 
                 nombre=None, pais=None, nacionalidad=None, 
                 iva16=0, iva16_na=0, iva0=0, iva_exento=0, iva_rfn=0, iva_import16=0):
        self.tipo_tercero = tipo_tercero
        self.tipo_operacion = tipo_operacion
        self.rfc = rfc
        self.id_fiscal = id_fiscal
        self.nombre = nombre
        self.pais = pais
        self.nacionalidad = nacionalidad
        self.iva16 = iva16
        self.iva16_na = iva16_na
        self.iva0 = iva0
        self.iva_exento = iva_exento
        self.iva_rfn = iva_rfn
        self.iva_import16 = iva_import16

class DatosComplementaria:
    def __init__(self, folio_anterior, fecha_anterior):
        self.folio_anterior = folio_anterior
        self.fecha_anterior = fecha_anterior

class DIOT:
    def __init__(self, datos_identificacion, proveedores=None, datos_complementaria=None):
        self.datos_identificacion = datos_identificacion
        self.proveedores = proveedores or []
        self.datos_complementaria = datos_complementaria
    
    def generar_txt(self):
        """Genera el contenido del archivo TXT para DIOT"""
        lineas = []
        
        # Header con datos de identificación
        header = f"DIOT|{self.datos_identificacion.rfc}|{self.datos_identificacion.razon_social}|{self.datos_identificacion.ejercicio}|{self.datos_identificacion.periodo.value}"
        lineas.append(header)
        
        # Líneas de proveedores
        for proveedor in self.proveedores:
            linea = f"{proveedor.tipo_tercero.value}|{proveedor.tipo_operacion.value}|"
            
            if proveedor.rfc:
                linea += f"{proveedor.rfc}||||||"
            else:
                linea += f"|{proveedor.id_fiscal or ''}|{proveedor.nombre or ''}|{proveedor.pais.value if proveedor.pais else ''}|{proveedor.nacionalidad or ''}||"
            
            linea += f"{proveedor.iva16:.2f}|{proveedor.iva16_na:.2f}|{proveedor.iva0:.2f}|{proveedor.iva_exento:.2f}|{proveedor.iva_rfn:.2f}|{proveedor.iva_import16:.2f}"
            lineas.append(linea)
        
        return "\n".join(lineas)
