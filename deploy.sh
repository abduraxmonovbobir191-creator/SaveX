#!/usr/bin/env bash
# SaveX deploy: ./deploy.sh            -> pull, install, migrate, restart
#               ./deploy.sh rollback   -> return to the commit before the last deploy
#
# The server (/opt/bots) also hosts other bots, sites and apps, so this script only
# touches SaveX: its own directory, its own systemd unit and its own compose project.
# It never runs global commands (no `docker system prune`, no restarting docker,
# no killing processes by name, no system-wide pip installs).
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$APP_DIR"

# Safety: act only on the SaveX checkout this script lives in.
if [[ "$(git rev-parse --show-toplevel 2>/dev/null)" != "$APP_DIR" ]]; then
    echo "deploy.sh must live in the root of the SaveX git checkout ($APP_DIR is not one)" >&2
    exit 1
fi

SERVICE="${SAVEX_SERVICE:-savex-bot}"        # systemd unit (unique name, see DEPLOY.md)
COMPOSE_PROJECT="savex"                      # docker compose project name (containers: savex-*)
PREV_FILE=".deploy_prev_commit"

case "$SERVICE" in
    savex*) ;;
    *) echo "Refusing to manage service '$SERVICE': name must start with 'savex'" >&2; exit 1 ;;
esac

compose() {
    if docker compose version >/dev/null 2>&1; then
        docker compose -p "$COMPOSE_PROJECT" "$@"
    else
        docker-compose -p "$COMPOSE_PROJECT" "$@"
    fi
}

has_compose_file() {
    [[ -f docker-compose.yml || -f docker-compose.yaml || -f compose.yml || -f compose.yaml ]]
}

# ig.json is a local, gitignored file. It used to be tracked, so the pull that stops
# tracking it would delete it from the working tree. Keep the real file in storage/
# (gitignored) and leave a symlink at the old path so anything using it keeps working.
protect_local_files() {
    mkdir -p storage
    if [[ -f ig.json && ! -L ig.json ]]; then
        if [[ -e storage/ig.json ]]; then
            echo "==> storage/ig.json already exists; keeping ig.json as ig.json.local"
            mv ig.json ig.json.local
        else
            mv ig.json storage/ig.json
        fi
    fi
}

restore_local_files() {
    if [[ -f storage/ig.json && ! -e ig.json ]]; then
        ln -s storage/ig.json ig.json
    fi
}

install_deps() {
    if has_compose_file; then
        echo "==> Building docker images (project: $COMPOSE_PROJECT)"
        compose build
        return
    fi
    if [[ ! -f venv/bin/activate ]]; then
        echo "==> Creating virtualenv $APP_DIR/venv"
        python3 -m venv venv
    fi
    echo "==> Installing Python dependencies into $APP_DIR/venv"
    venv/bin/python -m pip install --upgrade pip -q
    venv/bin/python -m pip install -r requirements.txt -q
}

migrate() {
    if [[ -f alembic.ini ]]; then
        echo "==> Running alembic migrations"
        if has_compose_file; then
            compose run --rm bot alembic upgrade head
        else
            venv/bin/alembic upgrade head
        fi
    else
        echo "==> No alembic.ini, skipping migrations"
    fi
}

restart() {
    mkdir -p storage/temp
    if has_compose_file; then
        echo "==> Restarting via docker compose (project: $COMPOSE_PROJECT)"
        compose up -d
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
    protect_local_files
    git reset --hard "$target"
    restore_local_files
    install_deps
    restart
    echo "==> Rollback done: $(git log -1 --oneline)"
    exit 0
fi

git rev-parse HEAD > "$PREV_FILE"
echo "==> Pulling latest code (was $(git log -1 --oneline))"
protect_local_files
git pull --ff-only
restore_local_files
install_deps
migrate
restart
echo "==> Deployed: $(git log -1 --oneline)"
