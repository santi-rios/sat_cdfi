#!/bin/bash
# Script avanzado de despliegue para CFDI Processor

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 PROCESADOR DE CFDIs - DESPLIEGUE AVANZADO${NC}"
echo "=================================================="

# Función para mostrar ayuda
show_help() {
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones:"
    echo "  simple     Despliegue simple (solo Streamlit)"
    echo "  nginx      Despliegue con Nginx (recomendado para producción)"
    echo "  ssl        Despliegue con Nginx + SSL"
    echo "  update     Actualizar aplicación existente"
    echo "  stop       Detener aplicación"
    echo "  logs       Mostrar logs"
    echo "  status     Mostrar estado"
    echo "  help       Mostrar esta ayuda"
    echo ""
}

# Verificar Docker
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Error: Docker no está corriendo${NC}"
        echo "Por favor inicia Docker y vuelve a intentar"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker está corriendo${NC}"
}

# Obtener IP local
get_local_ip() {
    if command -v hostname > /dev/null 2>&1; then
        LOCAL_IP=$(hostname -I | awk '{print $1}')
    elif command -v ip > /dev/null 2>&1; then
        LOCAL_IP=$(ip route get 1 | awk '{print $7; exit}')
    else
        LOCAL_IP="tu_ip_local"
    fi
}

# Despliegue simple
deploy_simple() {
    echo -e "${BLUE}🚀 Iniciando despliegue simple...${NC}"
    
    mkdir -p uploads output
    docker-compose -f docker-compose.yml down
    docker-compose -f docker-compose.yml build
    docker-compose -f docker-compose.yml up -d
    
    sleep 10
    
    if [ "$(docker ps -q -f name=cfdi-processor-app)" ]; then
        echo -e "${GREEN}✅ ¡Aplicación desplegada exitosamente!${NC}"
        echo ""
        echo -e "${YELLOW}🌐 Acceso a la aplicación:${NC}"
        echo "   Local: http://localhost:8501"
        echo "   Red:   http://${LOCAL_IP}:8501"
    else
        echo -e "${RED}❌ Error en el despliegue${NC}"
        docker-compose -f docker-compose.yml logs
    fi
}

# Despliegue con Nginx
deploy_nginx() {
    echo -e "${BLUE}🚀 Iniciando despliegue con Nginx...${NC}"
    
    mkdir -p uploads output
    docker-compose -f docker-compose-nginx.yml down
    docker-compose -f docker-compose-nginx.yml build
    docker-compose -f docker-compose-nginx.yml up -d
    
    sleep 15
    
    if [ "$(docker ps -q -f name=cfdi-processor-app)" ]; then
        echo -e "${GREEN}✅ ¡Aplicación con Nginx desplegada exitosamente!${NC}"
        echo ""
        echo -e "${YELLOW}🌐 Acceso a la aplicación:${NC}"
        echo "   Local: http://localhost"
        echo "   Red:   http://${LOCAL_IP}"
        echo ""
        echo -e "${BLUE}ℹ️  Ventajas de Nginx:${NC}"
        echo "   • Mejor rendimiento"
        echo "   • Soporte para archivos grandes"
        echo "   • Fácil configuración SSL"
    else
        echo -e "${RED}❌ Error en el despliegue${NC}"
        docker-compose -f docker-compose-nginx.yml logs
    fi
}

# Función principal
main() {
    check_docker
    get_local_ip
    
    case "${1:-simple}" in
        simple)
            deploy_simple
            ;;
        nginx)
            deploy_nginx
            ;;
        update)
            echo -e "${YELLOW}🔄 Actualizando aplicación...${NC}"
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
            ;;
        stop)
            echo -e "${YELLOW}🛑 Deteniendo aplicación...${NC}"
            docker-compose down
            docker-compose -f docker-compose-nginx.yml down
            ;;
        logs)
            docker-compose logs -f
            ;;
        status)
            docker-compose ps
            ;;
        help)
            show_help
            ;;
        *)
            echo -e "${RED}❌ Opción no válida: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
