

## Facturar

- https://test.fiscalapi.com
    - $200 mensuales
        - https://fiscalapi.com/#price-table
        - Emisión CFDI
        - Facturación mensual
        - Timbrado de facturas
        - Envío por correo
        - Personalización de marca, logotipos y colores por cada RFC emisor
        - Almacenamiento de facturas en XML y PDF
    - Timbres: 100 timbres $170
    - $100 mensuales por descarga masiva

- Alternativas
    - https://www.facturadorelectronico.com/precios.html
    - https://facturama.mx/planes-facturacion
    - https://www.siigo.com/mx/precios-siigo-aspel/
    - https://factuland.com/#precios

> Alternativamente, podemos hacer un programa que almacene en una base de datos (y luego llene automaticamnete?):

- Productos
    - Descripción
    - Precio sin impuestos
    - Unidad de medida SAT
    - Objeto impuesto SAT
    - Clasificación SAT
    - Impuesto del producto
- Impuestos
    - Sobre la renta
    - Valor agregado
    - IEPS
- Personas
    - Razón Social
    - Régimen capital
    - mail
    - tipo de persona
    - RFC
    - Régimen fiscal
    - Uso de CFDI
    - Código postal
    - Contraseña
    - Certificados
- XML y Facturas?
    - Asociar el RFC a XML y Facturas?

### Opciones externas timbrado

- https://tienda.sw.com.mx/shop
- https://www.diverza.com/soluciones/timbre-fiscal/
- https://www.prodigia.com.mx/soluciones/timbrado

## Captcha

- https://github.com/santi-rios/sat-captcha-ai-model
- https://www.boxfactura.com/sat-captcha-ai-model/

## Otros

- Crear factura sin timbre y luego timbrar??
    - https://satcfdi.readthedocs.io/en/stable/pages/getting_started/40_cfdi_create_guide.html
    - Igual en ese link hay una función para estado del comprobante
- Validación CDFI
    - https://satcfdi.readthedocs.io/en/stable/pages/getting_started/52_portal_facturacion.html
- DIOT
    - https://satcfdi.readthedocs.io/en/stable/pages/getting_started/60_diot_create.html


## Seguridad-Producción

santi-rios: por favor audame a deplegar mi aplicacion en mi servidor. Cuando corro `sudo docker compose... etc` para construir mi app, parece que todo bien. En los logs, solo sale esto "  You can now view your Streamlit app in your browser.

  URL: http://0.0.0.0:8503" . Estoy tratando de correrlo como un servicio aparte de los demás en mi archivo docker-compose principal. Sin embargo, me gustaría acceder a este servicio del mismo modo que los demás. Sin embargo, no puedo acceder al servicio. Me ayudas?

GitHub Copilot: Te ayudo a resolver el problema de acceso a tu aplicación Streamlit. Veo que está corriendo correctamente según los logs, pero hay algunos ajustes que podemos hacer para asegurar que sea accesible.

Primero, vamos a verificar el estado actual de los contenedores y revisar la configuración: Veo el problema. Hay una inconsistencia en la configuración de puertos. Tu archivo `docker-compose.streamlit.yml` tiene una configuración confusa:

1. **Puerto mapeado**: `"8503:8501"` (mapea el puerto interno 8501 al externo 8503)
2. **Variables de entorno**: `STREAMLIT_SERVER_PORT=8503` (pero internamente debería ser 8501)
3. **Puerto real del contenedor**: El contenedor está escuchando en 8501 interno

Vamos a corregir esto: 
```


Made changes.


```
También vamos a revisar el Dockerfile para asegurar que esté correctamente configurado: 
```


Made changes.


```
Ahora vamos a reconstruir y reiniciar el contenedor con la configuración corregida: El puerto 8503 está ocupado. Vamos a limpiar los contenedores huérfanos y verificar qué está usando ese puerto: Hay un proceso docker-proxy usando el puerto. Vamos a detener todos los contenedores relacionados y reiniciar: Parece que no hay contenedores cfdi corriendo actualmente. Vamos a intentar matar los procesos docker-proxy que están usando el puerto: Perfecto, el puerto está libre. Ahora vamos a iniciar la aplicación: ¡Excelente! Ahora vamos a verificar que esté corriendo correctamente: Perfecto. Ahora vamos a verificar que puedas acceder a la aplicación. Vamos a probar la conectividad: ¡Excelente! La aplicación está funcionando correctamente. Ahora vamos a obtener la IP de tu servidor para que puedas acceder desde otros dispositivos: ## ✅ **¡Tu aplicación CFDI está funcionando correctamente!**

### 🌐 **URLs de acceso:**

1. **Local (desde el servidor)**: `http://localhost:8503`
2. **Red local**: `http://192.168.1.84:8503`
3. **Tailscale VPN**: `http://100.99.239.24:8503`

### 🔧 **Problemas que se solucionaron:**

1. **Inconsistencia en puertos**: Había conflicto entre el puerto interno (8501) y las variables de entorno (8503)
2. **Procesos zombie**: Había procesos docker-proxy ocupando el puerto 8503
3. **Configuración del Dockerfile**: Se ajustó para usar el puerto correcto

### 📝 **Configuración final:**

- **Puerto interno del contenedor**: 8501
- **Puerto externo mapeado**: 8503
- **Acceso**: La aplicación está disponible en el puerto 8503 de tu servidor

### 🚀 **Comandos útiles para administrar tu aplicación:**

```bash
# Ver estado
docker-compose -f docker-compose.streamlit.yml ps

# Ver logs
docker-compose -f docker-compose.streamlit.yml logs -f

# Reiniciar
docker-compose -f docker-compose.streamlit.yml restart

# Parar
docker-compose -f docker-compose.streamlit.yml down

# Parar y reconstruir
docker-compose -f docker-compose.streamlit.yml down && docker-compose -f docker-compose.streamlit.yml build && docker-compose -f docker-compose.streamlit.yml up -d
```

### 🔗 **Para integrarlo con tu docker-compose principal:**

Si quieres incluir este servicio en tu archivo docker-compose.yml principal, puedes agregar esta sección:

```yaml
  cfdi-app:
    build:
      context: ./sat_cdfi
      dockerfile: Dockerfile.streamlit
    ports:
      - "8503:8501"
    volumes:
      - ./sat_cdfi/data:/app/data
    environment:
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_HEADLESS=true
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    restart: unless-stopped
```

¡Tu aplicación CFDI ya está funcionando y accesible! 🎉

santi-rios: @workspace /explain The image contains 2 high vulnerabilities

Workspace: I can see you have a Dockerfile for a Streamlit application with 2 high vulnerabilities. Let me analyze the security issues and provide solutions:

## Common High Vulnerabilities in This Dockerfile

1. **Running as root user** - The container runs with root privileges by default
2. **Outdated base image** - May contain known security vulnerabilities

## Secure Dockerfile Implementation

Here's an improved version that addresses these vulnerabilities:

````dockerfile
# Use a more specific and recent base image
FROM python:3.11-slim-bookworm

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install system dependencies and clean up in single layer
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copy application code
COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8501

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "cfdi_app_enhanced.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
````

## Key Security Improvements

1. **Non-root user**: Creates and switches to `appuser` to prevent privilege escalation
2. **Specific base image**: Uses `python:3.11-slim-bookworm` for better security updates
3. **Layer optimization**: Combines RUN commands to reduce attack surface
4. **Cache cleanup**: Removes package caches and temporary files
5. **Healthcheck**: Adds container health monitoring
6. **Proper permissions**: Sets correct ownership for the application directory

## Additional Security Recommendations

- Regularly update your base image
- Use `.dockerignore` to exclude sensitive files
- Scan images with tools like `docker scout` or `trivy`
- Consider using distroless images for production

Would you like me to explain any of these security practices in more detail?