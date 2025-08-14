#!/bin/bash
# Script de despliegue para CFDI Processor

echo "🐳 DESPLEGANDO PROCESADOR DE CFDIs EN DOCKER"
echo "=============================================="

# Verificar que Docker esté corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    echo "Por favor inicia Docker y vuelve a intentar"
    exit 1
fi

echo "✅ Docker está corriendo"

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p uploads output

# Construir imagen
echo "🔨 Construyendo imagen Docker..."
docker-compose build

# Verificar si el contenedor ya existe
if [ "$(docker ps -aq -f name=cfdi-processor-app)" ]; then
    echo "🔄 Deteniendo contenedor existente..."
    docker-compose down
fi

# Iniciar aplicación
echo "🚀 Iniciando aplicación..."
docker-compose up -d

# Esperar a que la aplicación inicie
echo "⏳ Esperando a que la aplicación inicie..."
sleep 10

# Verificar estado
if [ "$(docker ps -q -f name=cfdi-processor-app)" ]; then
    echo ""
    echo "✅ ¡APLICACIÓN DESPLEGADA EXITOSAMENTE!"
    echo "=============================================="
    echo "🌐 La aplicación está disponible en:"
    echo ""
    echo "   http://localhost:8501"
    echo "   http://$(hostname -I | awk '{print $1}'):8501"
    echo ""
    echo "📱 Acceso desde otros dispositivos en la red:"
    echo "   http://[TU_IP_LOCAL]:8501"
    echo ""
    echo "🔧 Comandos útiles:"
    echo "   docker-compose logs -f    # Ver logs"
    echo "   docker-compose down       # Detener aplicación"
    echo "   docker-compose restart    # Reiniciar aplicación"
    echo ""
else
    echo "❌ Error: La aplicación no se pudo iniciar"
    echo "Revisa los logs con: docker-compose logs"
fi
