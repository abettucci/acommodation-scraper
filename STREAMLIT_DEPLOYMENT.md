# Streamlit Cloud Deployment Guide

Guía para deployar la aplicación web en Streamlit Cloud (gratis).

## Pre-requisitos

1. Cuenta en [Streamlit Cloud](https://streamlit.io/cloud) (gratis con GitHub)
2. Repositorio en GitHub con el código
3. Google Places API Key

## Deployment en Streamlit Cloud

### 1. Subir código a GitHub

Asegurate de que la carpeta `streamlit/` esté en tu repositorio.

### 2. Conectar con Streamlit Cloud

1. Ir a [share.streamlit.io](https://share.streamlit.io/)
2. Click en "New app"
3. Seleccionar tu repositorio
4. Configurar:
   - **Branch**: `main`
   - **Main file path**: `streamlit/app.py`
   - **App URL**: elegir nombre personalizado

### 3. Configurar Secrets (opcional)

Si querés que la API key esté pre-cargada:

1. En Streamlit Cloud, ir a tu app
2. Click en "Settings" > "Secrets"
3. Agregar:

```toml
GOOGLE_PLACES_API_KEY = "tu_api_key_aqui"
```

**Nota**: Los usuarios también pueden ingresar su propia API key en la UI.

### 4. Deploy

Click en "Deploy" y esperar ~2 minutos.

## Ejecución Local

```bash
cd streamlit

# Instalar dependencias
pip install -r requirements.txt

# Crear archivo .env (opcional)
echo "GOOGLE_PLACES_API_KEY=tu_api_key" > .env

# Ejecutar
streamlit run app.py
```

Abrir http://localhost:8501

## Estructura de la App

```
streamlit/
├── app.py                 # Aplicación principal
├── requirements.txt       # Dependencias
└── .streamlit/
    └── config.toml       # Configuración de Streamlit
```

## Funcionalidades

- 🔍 Búsqueda por tipo de alojamiento
- 📍 Filtro por ubicación y radio
- ⭐ Filtro por rating mínimo
- 🗺️ Mapa interactivo con resultados
- 📊 Tabla con todos los datos
- 📥 Descarga de CSV
- 🏨 Cards con detalle de cada lugar

## Personalización

### Cambiar tema

Editar `streamlit/.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

### Agregar más campos

Editar la función `search_places()` en `app.py` para incluir más campos de la API.

## Costos

- **Streamlit Cloud**: Gratis para apps públicas
- **Google Places API**: $200 crédito gratis/mes

## Troubleshooting

### Error 403 Forbidden

- Verificar API key válida
- Verificar Places API (New) habilitada
- Verificar billing en Google Cloud

### App no carga

- Verificar requirements.txt tiene todas las dependencias
- Revisar logs en Streamlit Cloud dashboard

### Mapa no aparece

- Verificar que los lugares tengan coordenadas
- Algunas búsquedas pueden no devolver lat/lng
