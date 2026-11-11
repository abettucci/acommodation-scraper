# AWS Deployment Guide

Guía para deployar el Accommodation Scraper en AWS con Telegram Bot.

## Arquitectura

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Telegram      │────▶│   API Gateway    │────▶│     Lambda      │
│   (Webhook)     │     │   (HTTP API)     │     │  (telegram_bot) │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │ Secrets Manager  │◀─────────────┤
                        │ - Telegram Token │              │
                        │ - Google API Key │              │
                        └──────────────────┘              │
                                                          ▼
                                                ┌─────────────────┐
                                                │ Google Places   │
                                                │     API         │
                                                └─────────────────┘
```

## Pre-requisitos

1. **Cuenta AWS** con permisos para CloudFormation, Lambda, API Gateway, Secrets Manager
2. **Telegram Bot Token** de [@BotFather](https://t.me/BotFather)
3. **Google Places API Key** de [Google Cloud Console](https://console.cloud.google.com/)
4. **AWS CLI** configurado
5. **Docker** instalado (para construir la Lambda Layer)

## Configuración de GitHub Secrets

En tu repositorio de GitHub, ir a **Settings > Secrets and variables > Actions** y configurar:

| Secret | Descripción | Requerido |
|--------|-------------|-----------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key | ✅ |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key | ✅ |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | ✅ |
| `GOOGLE_PLACES_API_KEY` | API key de Google Places | ✅ |
| `LAMBDA_LAYER_ARN` | ARN de la Lambda Layer | ❌ (opcional, se crea después) |

**Importante**: Los secrets se pasan como variables de entorno al workflow, nunca se guardan en archivos del repositorio.

## Deployment Manual

### 1. Construir Lambda Layer

```bash
cd aws/layers/dependencies
./build.sh
```

### 2. Publicar Layer en AWS

```bash
aws lambda publish-layer-version \
  --layer-name accommodation-scraper-dependencies \
  --description "Dependencies for accommodation-scraper" \
  --zip-file fileb://output/layer.zip \
  --compatible-runtimes python3.11
```

Guardar el ARN de la layer para el siguiente paso.

### 3. Deploy CloudFormation Stack

Usar el script de deploy que lee secrets de variables de entorno:

```bash
# Dev environment
cd aws/infra/scripts
TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy ./deploy.sh dev create

# Update existing stack
TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy ./deploy.sh dev update

# Con Lambda Layer (opcional)
TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy LAMBDA_LAYER_ARN=arn:aws:... ./deploy.sh dev update
```

O directamente con AWS CLI:

```bash
aws cloudformation deploy \
  --template-file aws/infra/template.yaml \
  --stack-name accommodation-scraper-dev \
  --parameter-overrides \
    Environment=dev \
    TelegramBotToken=$TELEGRAM_BOT_TOKEN \
    GooglePlacesApiKey=$GOOGLE_PLACES_API_KEY \
  --capabilities CAPABILITY_NAMED_IAM
```

### 4. Deploy Lambda Code

```bash
# Empaquetar
mkdir -p dist
cp -r aws/lambdas/telegram_bot/* dist/
cp -r aws/lambdas/shared dist/
cd dist && zip -r ../lambda.zip . && cd ..

# Deploy
aws lambda update-function-code \
  --function-name accommodation-scraper-dev-telegram-bot \
  --zip-file fileb://lambda.zip
```

### 5. Configurar Webhook de Telegram

Obtener la URL del webhook:

```bash
aws cloudformation describe-stacks \
  --stack-name accommodation-scraper-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`TelegramWebhookUrl`].OutputValue' \
  --output text
```

Configurar el webhook:

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WEBHOOK_URL>"
```

## Deployment con GitHub Actions

Los workflows se ejecutan automáticamente:

1. **`build-layer.yml`**: Se ejecuta cuando cambia `aws/layers/**`
2. **`deploy-infra.yml`**: Se ejecuta cuando cambia `aws/infra/**`
3. **`deploy-lambdas.yml`**: Se ejecuta cuando cambia `aws/lambdas/**`

También se pueden ejecutar manualmente desde la pestaña "Actions" en GitHub.

## Comandos del Bot

Una vez deployado, el bot responde a:

- `/start` o `/ayuda` - Muestra ayuda
- `/buscar [tipo] en [ciudad] [radio]km` - Busca alojamientos

Ejemplos:
```
/buscar hoteles en Mendoza 10km
/buscar hostels en Palermo, Buenos Aires 3km
/buscar alojamientos en Bariloche 5km
```

## Costos Estimados

| Servicio | Costo estimado |
|----------|----------------|
| Lambda | ~$0.20/mes (primeras 1M requests gratis) |
| API Gateway | ~$1/mes (primeras 1M requests gratis) |
| Secrets Manager | ~$0.80/mes (2 secrets) |
| Google Places API | $200 crédito gratis/mes |

**Total estimado**: < $5/mes para uso moderado

## Troubleshooting

### Error 403 en Google Places API

- Verificar que Places API (New) esté habilitada
- Verificar que la API key no tenga restricciones de IP
- Verificar billing habilitado en Google Cloud

### Lambda timeout

- Aumentar timeout en CloudFormation (default: 60s)
- Verificar conectividad a Google API

### Webhook no responde

- Verificar URL del webhook con `getWebhookInfo`
- Revisar logs en CloudWatch
