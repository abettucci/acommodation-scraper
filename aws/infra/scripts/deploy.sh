#!/bin/bash
# Deploy Accommodation Scraper Infrastructure
#
# Usage:
#   ./deploy.sh [dev|prod] [create|update|delete]
#
# Required environment variables:
#   TELEGRAM_BOT_TOKEN      - Your Telegram bot token
#   GOOGLE_PLACES_API_KEY   - Google Places API key
#
# Optional environment variables:
#   AWS_REGION              - AWS region (default: us-east-1)
#   LAMBDA_LAYER_ARN        - Lambda layer ARN
#
# Examples:
#   TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy ./deploy.sh dev create
#   TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy ./deploy.sh dev update
#   ./deploy.sh dev delete

set -e

# Configuration
PROJECT_NAME="accommodation-scraper"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Parse arguments
ENVIRONMENT="${1:-dev}"
ACTION="${2:-update}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    echo "❌ Invalid environment: $ENVIRONMENT"
    echo "   Valid options: dev, prod"
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(create|update|delete)$ ]]; then
    echo "❌ Invalid action: $ACTION"
    echo "   Valid options: create, update, delete"
    exit 1
fi

# Check required secrets for create/update
if [[ "$ACTION" != "delete" ]]; then
    if [[ -z "$TELEGRAM_BOT_TOKEN" ]]; then
        echo "❌ TELEGRAM_BOT_TOKEN environment variable is required"
        echo ""
        echo "Usage:"
        echo "  TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy ./deploy.sh ${ENVIRONMENT} ${ACTION}"
        exit 1
    fi
    
    if [[ -z "$GOOGLE_PLACES_API_KEY" ]]; then
        echo "❌ GOOGLE_PLACES_API_KEY environment variable is required"
        echo ""
        echo "Usage:"
        echo "  TELEGRAM_BOT_TOKEN=xxx GOOGLE_PLACES_API_KEY=yyy ./deploy.sh ${ENVIRONMENT} ${ACTION}"
        exit 1
    fi
fi

# Set variables
STACK_NAME="${PROJECT_NAME}-${ENVIRONMENT}"
TEMPLATE_FILE="$(dirname "$0")/../template.yaml"

echo "============================================"
echo "Accommodation Scraper Infrastructure"
echo "============================================"
echo "Environment: ${ENVIRONMENT}"
echo "Stack Name:  ${STACK_NAME}"
echo "Action:      ${ACTION}"
echo "Region:      ${AWS_REGION}"
echo "============================================"

# Check AWS credentials
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
    exit 1
fi

# Validate template
echo ""
echo "📋 Validating CloudFormation template..."
aws cloudformation validate-template \
    --template-body file://${TEMPLATE_FILE} \
    --region ${AWS_REGION} > /dev/null
echo "✅ Template is valid"

# Execute action
case $ACTION in
    create|update)
        echo ""
        echo "🚀 Deploying stack: ${STACK_NAME}"
        
        # Deploy with parameters from environment variables
        aws cloudformation deploy \
            --stack-name ${STACK_NAME} \
            --template-file ${TEMPLATE_FILE} \
            --parameter-overrides \
                Environment=${ENVIRONMENT} \
                ProjectName=${PROJECT_NAME} \
                TelegramBotToken=${TELEGRAM_BOT_TOKEN} \
                GooglePlacesApiKey=${GOOGLE_PLACES_API_KEY} \
                LambdaLayerArn=${LAMBDA_LAYER_ARN:-} \
            --capabilities CAPABILITY_NAMED_IAM \
            --no-fail-on-empty-changeset \
            --tags Project=${PROJECT_NAME} Environment=${ENVIRONMENT} \
            --region ${AWS_REGION}
        
        echo "✅ Stack deployed successfully!"
        ;;
    
    delete)
        echo ""
        echo "⚠️  WARNING: This will delete the stack and ALL resources!"
        echo "    Stack: ${STACK_NAME}"
        read -p "    Are you sure? (yes/no): " CONFIRM
        
        if [[ "$CONFIRM" != "yes" ]]; then
            echo "❌ Aborted"
            exit 0
        fi
        
        echo ""
        echo "🗑️  Deleting stack: ${STACK_NAME}"
        
        aws cloudformation delete-stack \
            --stack-name ${STACK_NAME} \
            --region ${AWS_REGION}
        
        echo ""
        echo "⏳ Waiting for stack deletion..."
        aws cloudformation wait stack-delete-complete \
            --stack-name ${STACK_NAME} \
            --region ${AWS_REGION}
        
        echo "✅ Stack deleted successfully!"
        ;;
esac

# Show outputs (if not delete)
if [[ "$ACTION" != "delete" ]]; then
    echo ""
    echo "📋 Stack Outputs:"
    aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --query 'Stacks[0].Outputs' \
        --output table \
        --region ${AWS_REGION} 2>/dev/null || echo "   (no outputs yet)"
    
    echo ""
    echo "📝 Next steps:"
    echo "   1. Get the webhook URL from outputs above"
    echo "   2. Set Telegram webhook:"
    echo "      curl \"https://api.telegram.org/bot\${TELEGRAM_BOT_TOKEN}/setWebhook?url=<WEBHOOK_URL>\""
fi

echo ""
echo "============================================"
echo "Deployment complete!"
echo "============================================"
