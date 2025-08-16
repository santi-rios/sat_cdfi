#!/bin/bash

# Script para desplegar la aplicación CFDI con Docker

echo "🚀 Desplegando aplicación CFDI con Streamlit..."

# Construir la imagen
echo "📦 Construyendo imagen Docker..."
docker-compose -f docker-compose.streamlit.yml build

# Levantar el servicio
echo "▶️ Iniciando contenedor..."
docker-compose -f docker-compose.streamlit.yml up -d

echo "✅ Aplicación desplegada!"
echo "🌐 Accede en: http://localhost:8501"
echo ""
echo "📋 Comandos útiles:"
echo "  - Ver logs: docker-compose -f docker-compose.streamlit.yml logs -f"
echo "  - Parar: docker-compose -f docker-compose.streamlit.yml down"
echo "  - Reiniciar: docker-compose -f docker-compose.streamlit.yml restart"
