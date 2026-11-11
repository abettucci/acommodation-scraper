# Accommodation Scraper

CLI para buscar hoteles, hostels y alojamientos usando la Google Places API. Exporta los resultados a CSV con informacion de precios, ubicacion, reviews y links.

**Compatible con Windows, macOS y Linux.**

## Requisitos

- Python 3.11+
- Poetry (o pip)
- API Key de Google Places

## Instalacion en Windows

### Opcion 1: Con Poetry (recomendado)

1. Instalar Python 3.11+ desde [python.org](https://www.python.org/downloads/)
   - **IMPORTANTE**: Marcar "Add Python to PATH" durante la instalacion

2. Instalar Poetry abriendo PowerShell como administrador:
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

3. Reiniciar PowerShell y navegar a la carpeta del proyecto:
```powershell
cd C:\ruta\a\accommodation-scraper
poetry install
```

4. Configurar la API Key:
```powershell
copy .env.example .env
notepad .env
# Agregar tu GOOGLE_PLACES_API_KEY
```

### Opcion 2: Con pip (alternativa)

```powershell
cd C:\ruta\a\accommodation-scraper
pip install -r requirements.txt
```

Para generar `requirements.txt` desde Poetry:
```powershell
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

## Instalacion en macOS/Linux

```bash
cd accommodation-scraper
poetry install

cp .env.example .env
# Editar .env y agregar tu GOOGLE_PLACES_API_KEY
```

## Obtener API Key de Google

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un proyecto nuevo o seleccionar uno existente
3. Habilitar la **Places API (New)**
4. Ir a **Credentials** y crear una API Key
5. (Opcional) Restringir la API Key solo a Places API

## Uso

### Windows (PowerShell o CMD)

```powershell
# Buscar hoteles en una ciudad
poetry run scraper search "hotels in Buenos Aires"

# Buscar hostels
poetry run scraper search "hostels in Mendoza"

# Buscar alojamientos tipo Airbnb
poetry run scraper search "vacation rentals in Bariloche"
```

### macOS/Linux

```bash
poetry run scraper search "hotels in Buenos Aires"
```

### Opciones de busqueda

```powershell
# Especificar archivo de salida
poetry run scraper search "hotels in Cordoba" --output hoteles_cordoba.csv

# Limitar cantidad de resultados
poetry run scraper search "hostels in Salta" --max-results 30

# Filtrar por rating minimo
poetry run scraper search "hotels in Rosario" --min-rating 4.0

# Modo economico (solo campos Pro, sin reviews/rating/precio)
poetry run scraper search "hotels in Mar del Plata" --budget-mode

# Cambiar idioma de resultados
poetry run scraper search "hotels in Buenos Aires" --language en
```

### Busqueda por radio (limitar area geografica)

Podes acotar la busqueda a un radio especifico alrededor de una ubicacion:

```powershell
# Buscar por nombre de ciudad + radio en km
poetry run scraper search "hotels" --location "Palermo, Buenos Aires" --radius 3

# Buscar por coordenadas exactas + radio
poetry run scraper search "hostels" --lat -34.5875 --lng -58.4311 --radius 5

# Combinar con otros filtros
poetry run scraper search "hotels" --location "Mendoza, Argentina" --radius 10 --min-rating 4.0
```

### Obtener coordenadas de una ciudad

```powershell
# Ver coordenadas de cualquier lugar
poetry run scraper geocode "Bariloche, Argentina"

# Output:
#   Latitud:  -41.1334
#   Longitud: -71.3103
```

### Otros comandos

```powershell
# Ver campos disponibles y costos
poetry run scraper fields

# Previsualizar resultados sin guardar
poetry run scraper preview "hotels" --location "Mendoza" --radius 10 --limit 10

# Obtener coordenadas de una ciudad
poetry run scraper geocode "San Martin de los Andes"

# Ver ayuda
poetry run scraper --help
poetry run scraper search --help
```

## Output CSV

El archivo CSV generado se puede abrir directamente en Excel (Windows) con encoding correcto.

| Columna | Descripcion |
|---------|-------------|
| name | Nombre del alojamiento |
| address | Direccion completa |
| lat | Latitud |
| lng | Longitud |
| rating | Rating de Google (1-5) |
| reviews_count | Cantidad de reviews |
| price_level | Nivel de precio ($, $$, $$$, $$$$) |
| phone | Telefono internacional |
| website | Sitio web |
| google_maps_url | Link a Google Maps |
| type | Tipo de lugar (hotel, hostel, etc) |
| top_review | Texto del review mas relevante |

## Costos de la API

Google Places API usa un modelo pay-as-you-go:

| Nivel | Campos incluidos | Costo aprox. |
|-------|------------------|--------------|
| **Pro** | Nombre, direccion, ubicacion, link | ~$32 / 1000 requests |
| **Enterprise** | + Rating, reviews, precio, telefono, web | ~$40 / 1000 requests |

- Google ofrece $200 USD de credito mensual gratis
- Usa `--budget-mode` para reducir costos usando solo campos Pro

## Ejemplos de uso

### Investigar precios en una zona especifica

```powershell
# Buscar hoteles en un radio de 3km en Palermo
poetry run scraper search "hotels" --location "Palermo, Buenos Aires" --radius 3 -o palermo_hotels.csv

# Solo los mejor valorados en el centro de Mendoza
poetry run scraper search "hotels" --location "Centro, Mendoza" --radius 2 --min-rating 4.5
```

### Comparar hostels en varias ciudades (mismo radio)

```powershell
poetry run scraper search "hostels" --location "Buenos Aires" --radius 10 -o hostels_bsas.csv
poetry run scraper search "hostels" --location "Mendoza" --radius 10 -o hostels_mendoza.csv
poetry run scraper search "hostels" --location "Bariloche" --radius 10 -o hostels_bariloche.csv
```

### Buscar cerca de un punto de interes

```powershell
# Hoteles cerca del Obelisco (coordenadas exactas)
poetry run scraper search "hotels" --lat -34.6037 --lng -58.3816 --radius 1

# Alojamientos cerca de un aeropuerto
poetry run scraper search "hotels" --location "Aeropuerto Ezeiza" --radius 5
```

### Buscar alojamientos economicos

```powershell
# Hostels en Cordoba con buen rating
poetry run scraper search "hostels" --location "Cordoba, Argentina" --radius 8 --min-rating 4.0
```

## Estructura del proyecto

```
accommodation-scraper/
├── pyproject.toml          # Dependencias
├── .env                    # API Key (no commitear)
├── .env.example            # Template
├── README.md
└── src/
    └── scraper/
        ├── __init__.py
        ├── cli.py          # Comandos CLI
        ├── client.py       # Cliente Google Places API
        ├── models.py       # Modelos de datos
        └── exporter.py     # Exportacion CSV
```

## Troubleshooting

### Windows: 'poetry' no se reconoce como comando

Agregar Poetry al PATH. Abrir PowerShell y ejecutar:
```powershell
$env:Path += ";$env:APPDATA\Python\Scripts"
```

O agregar permanentemente desde: Sistema > Variables de entorno > Path

### Windows: Caracteres raros en la consola

Usar Windows Terminal o PowerShell 7+ para mejor soporte de Unicode.
En CMD antiguo, ejecutar primero:
```cmd
chcp 65001
```

### Error: API key required

Asegurate de tener el archivo `.env` en la misma carpeta donde ejecutas el comando:

```
GOOGLE_PLACES_API_KEY=tu_api_key_aqui
```

### Error: 403 Forbidden

- Verifica que la Places API (New) este habilitada en tu proyecto
- Verifica que la API key tenga permisos para Places API

### Pocos resultados

- Intenta con queries mas especificos (ej: "hotels in Palermo Buenos Aires")
- Algunos tipos de alojamiento pueden no estar bien indexados en Google

### Windows: Error de SSL/certificados

Si hay errores de SSL, instalar certificados:
```powershell
pip install certifi
python -c "import certifi; print(certifi.where())"
```

## Licencia

MIT
