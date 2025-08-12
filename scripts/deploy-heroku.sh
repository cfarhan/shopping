#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Heroku deployment of Shopping App${NC}"

# Configuration
APP_NAME=${1:-""}
EXTERNAL_DATABASE_URL=""

# Parse flags
shift || true
while [[ $# -gt 0 ]]; do
  case $1 in
    --database-url)
      EXTERNAL_DATABASE_URL="$2"
      shift 2
      ;;
    --help)
      echo "Usage: ./deploy-heroku.sh <app-name> [--database-url postgresql://USER:PASS@HOST:PORT/DB]"
      exit 0
      ;;
    *)
      echo -e "${YELLOW}Ignoring unknown option: $1${NC}"
      shift
      ;;
  esac
done

if [ -z "$APP_NAME" ]; then
    echo -e "${RED}❌ Please provide an app name${NC}"
    echo -e "${YELLOW}Usage: ./deploy-heroku.sh your-app-name [--database-url postgresql://...]${NC}"
    exit 1
fi

check_dependencies() {
    echo -e "${YELLOW}📋 Checking dependencies...${NC}"
    command -v heroku >/dev/null || { echo -e "${RED}❌ Missing heroku CLI${NC}"; exit 1; }
    command -v git >/dev/null || { echo -e "${RED}❌ Missing git${NC}"; exit 1; }
    echo -e "${GREEN}✅ All dependencies are installed${NC}"
}

create_heroku_app() {
    echo -e "${YELLOW}🏗️ Creating Heroku app...${NC}"
    if heroku apps:info $APP_NAME &> /dev/null; then
        echo -e "${YELLOW}⚠️ App $APP_NAME already exists${NC}"
    else
        heroku create $APP_NAME
        echo -e "${GREEN}✅ Heroku app created: $APP_NAME${NC}"
    fi

    # Set monorepo buildpack and web root
    heroku buildpacks:clear -a $APP_NAME || true
    heroku buildpacks:add -a $APP_NAME https://github.com/lstoll/heroku-buildpack-monorepo || true
    heroku buildpacks:add -a $APP_NAME heroku/python
    heroku config:set -a $APP_NAME APP_BASE="shopping"
}

maybe_add_postgres() {
    if [ -z "$EXTERNAL_DATABASE_URL" ]; then
        echo -e "${YELLOW}🐘 Adding Heroku Postgres (since no external DB URL provided)...${NC}"
        if heroku addons:info -a $APP_NAME heroku-postgresql &> /dev/null; then
            echo -e "${YELLOW}⚠️ Postgres addon already exists${NC}"
        else
            heroku addons:create heroku-postgresql:mini -a $APP_NAME
            echo -e "${GREEN}✅ Postgres addon added${NC}"
        fi
    else
        echo -e "${YELLOW}⏭️ Skipping Heroku Postgres. Using external DATABASE_URL${NC}"
    fi
}

set_config_vars() {
    echo -e "${YELLOW}⚙️ Setting configuration variables...${NC}"
    SECRET_KEY=${SECRET_KEY:-$(python3 -c "import secrets; print(secrets.token_hex(32))")}
    JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(python3 -c "import secrets; print(secrets.token_hex(32))")}
    heroku config:set -a $APP_NAME SECRET_KEY="$SECRET_KEY" JWT_SECRET_KEY="$JWT_SECRET_KEY" FLASK_ENV=production
    if [ -n "$STRIPE_SECRET_KEY" ] && [ -n "$STRIPE_PUBLISHABLE_KEY" ]; then
        heroku config:set -a $APP_NAME STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY" STRIPE_PUBLISHABLE_KEY="$STRIPE_PUBLISHABLE_KEY"
    fi
    if [ -n "$EXTERNAL_DATABASE_URL" ]; then
        heroku config:set -a $APP_NAME DATABASE_URL="$EXTERNAL_DATABASE_URL"
        echo -e "${GREEN}✅ Set external DATABASE_URL for Heroku${NC}"
    fi
}

deploy_app() {
    echo -e "${YELLOW}🚀 Deploying to Heroku...${NC}"
    if ! git remote | grep heroku &> /dev/null; then
        heroku git:remote -a $APP_NAME
    fi
    git add .
    git commit -m "Deploy to Heroku (monorepo)" --allow-empty
    git push heroku HEAD:main
    echo -e "${GREEN}✅ App deployed successfully${NC}"
}

run_migrations() {
    echo -e "${YELLOW}🗃️ Running database migrations...${NC}"
    heroku run -a $APP_NAME "cd shopping && flask db upgrade" || true
    echo -e "${GREEN}✅ Database migrations complete${NC}"
}

main() {
    echo -e "${GREEN}Starting Heroku deployment for: $APP_NAME${NC}"
    check_dependencies
    create_heroku_app
    maybe_add_postgres
    set_config_vars
    deploy_app
    run_migrations
    APP_URL="https://$APP_NAME.herokuapp.com"
    echo -e "${YELLOW}📋 Deployment Information:${NC}"
    echo -e "${GREEN}App URL:${NC} $APP_URL"
    echo -e "${GREEN}Health Check:${NC} $APP_URL/health"
}

main "$@" 