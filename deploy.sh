#!/usr/bin/env bash
# SaveX deploy: ./deploy.sh            -> pull, install, migrate, restart
#               ./deploy.sh rollback   -> return to the commit before the last deploy
set -euo pipefail

cd "$(dirname "$0")"
SERVICE="savex"
PREV_FILE=".deploy_prev_commit"

compose() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
    else
        docker-compose "$@"
    fi
}

has_compose_file() {
    [[ -f docker-compose.yml || -f docker-compose.yaml || -f compose.yml || -f compose.yaml ]]
}

install_deps() {
    if has_compose_file; then
        echo "==> Building docker images"
        compose build
        return
    fi
    if [[ -f venv/bin/activate ]]; then
        # shellcheck disable=SC1091
        source venv/bin/activate
    fi
    echo "==> Installing Python dependencies"
    python3 -m pip install --upgrade pip -q
    python3 -m pip install -r requirements.txt -q
}

migrate() {
    if [[ -f alembic.ini ]]; then
        echo "==> Running alembic migrations"
        if has_compose_file; then
            compose run --rm bot alembic upgrade head
        else
            alembic upgrade head
        fi
    else
        echo "==> No alembic.ini, skipping migrations"
    fi
}

restart() {
    mkdir -p storage/temp
    if has_compose_file; then
        echo "==> Restarting via docker compose"
        compose up -d --remove-orphans
        compose ps
    else
        echo "==> Restarting systemd service '$SERVICE'"
        sudo systemctl restart "$SERVICE"
        sleep 2
        sudo systemctl --no-pager --lines=15 status "$SERVICE" || true
    fi
}

if [[ "${1:-}" == "rollback" ]]; then
    if [[ ! -s "$PREV_FILE" ]]; then
        echo "No $PREV_FILE found; use: git reset --hard <commit> && ./deploy.sh" >&2
        exit 1
    fi
    target="$(cat "$PREV_FILE")"
    echo "==> Rolling back to $target"
    git reset --hard "$target"
    install_deps
    restart
    echo "==> Rollback done: $(git log -1 --oneline)"
    exit 0
fi

git rev-parse HEAD > "$PREV_FILE"
echo "==> Pulling latest code (was $(git log -1 --oneline))"
git pull --ff-only
install_deps
migrate
restart
echo "==> Deployed: $(git log -1 --oneline)"
