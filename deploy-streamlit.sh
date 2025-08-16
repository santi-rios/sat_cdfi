#!/bin/bash

# Script para desplegar la aplicación CFDI con Docker

echo "🚀 Desplegando aplicación CFDI con Streamlit..."

# Limpiar contenedores anteriores
echo "🧹 Limpiando contenedores anteriores..."
docker-compose -f docker-compose.streamlit.yml down --remove-orphans 2>/dev/null || true

# Construir la imagen
echo "📦 Construyendo imagen Docker..."
if docker-compose -f docker-compose.streamlit.yml build --no-cache; then
    echo "✅ Imagen construida exitosamente"
else
    echo "❌ Error al construir la imagen"
    exit 1
fi

# Probar dependencias en el contenedor
echo "🧪 Probando dependencias en el contenedor..."
if docker-compose -f docker-compose.streamlit.yml run --rm cfdi-app python test_docker_dependencies.py; then
    echo "✅ Todas las dependencias funcionan correctamente"
    deploy=true
else
    echo "❌ Algunas dependencias fallan"
    echo ""
    echo "¿Quieres continuar con el deployment de todas formas? (y/n)"
    read -r response
    if [[ "$response" == "y" || "$response" == "Y" ]]; then
        deploy=true
    else
        deploy=false
    fi
fi

if [[ "$deploy" == true ]]; then
    # Levantar el servicio
    echo "▶️ Iniciando contenedor..."
    docker-compose -f docker-compose.streamlit.yml up -d

    echo "✅ Aplicación desplegada!"
    echo "🌐 Accede en: http://localhost:8501"
else
    echo "❌ Deployment cancelado"
    exit 1
fi
echo "▶️ Iniciando contenedor..."
docker-compose -f docker-compose.streamlit.yml up -d

echo "✅ Aplicación desplegada!"
echo "🌐 Accede en: http://localhost:8501"
echo ""
echo "📋 Comandos útiles:"
echo "  - Ver logs: docker-compose -f docker-compose.streamlit.yml logs -f"
echo "  - Parar: docker-compose -f docker-compose.streamlit.yml down"
echo "  - Reiniciar: docker-compose -f docker-compose.streamlit.yml restart"
echo "  - Probar dependencias: docker-compose -f docker-compose.streamlit.yml run --rm cfdi-app python test_docker_dependencies.py"
