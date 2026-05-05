#!/bin/bash
# server_repair.sh — Strangeness IS emergency repair
# Fixes: venv packages, .env, systemd service, nginx check
set -e

APP_DIR=/home/ubuntu/strangeness-is
VENV_PIP=$APP_DIR/venv/bin/pip
VENV_PYTHON=$APP_DIR/venv/bin/python
VENV_GUNICORN=$APP_DIR/venv/bin/gunicorn
SERVICE=/etc/systemd/system/strangeness.service

echo ""
echo "========================================"
echo " Strangeness IS — Server Repair"
echo "========================================"

echo ""
echo "[A] App directory..."
mkdir -p $APP_DIR $APP_DIR/data
echo "    OK: $APP_DIR"

echo ""
echo "[B] Checking .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "    .env MISSING — creating with placeholder values"
    cat > $APP_DIR/.env << 'ENVEOF'
ADMIN_KEY=ChangeMe123!
OPENAI_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ORACLE=
STRIPE_PRICE_INVESTIGATOR=
STRIPE_PRICE_CHRONICLER=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
AGENT_EMAIL=
SITE_URL=https://strangenessis.com
DATA_DIR=/home/ubuntu/strangeness-is/data
PORT=5000
GA_MEASUREMENT_ID=
GA_API_SECRET=
ENVEOF
    echo "    Created .env — ADMIN_KEY=ChangeMe123! (change this!)"
else
    echo "    .env exists"
    AKVAL=$(grep "^ADMIN_KEY=" $APP_DIR/.env | cut -d= -f2- | tr -d '[:space:]')
    if [ -z "$AKVAL" ]; then
        echo "    ADMIN_KEY was empty — setting to: ChangeMe123!"
        sed -i 's/^ADMIN_KEY=.*/ADMIN_KEY=ChangeMe123!/' $APP_DIR/.env
    else
        echo "    ADMIN_KEY set (${AKVAL:0:3}***)"
    fi
fi

echo ""
echo "[C] Checking virtualenv..."
if [ ! -f "$VENV_PIP" ]; then
    echo "    venv missing — creating..."
    python3 -m venv $APP_DIR/venv
    echo "    venv created"
else
    echo "    venv exists at $APP_DIR/venv"
fi

echo ""
echo "[D] Installing packages into venv..."
$VENV_PIP install --upgrade pip -q
$VENV_PIP install flask flask-cors openai python-dotenv gunicorn schedule requests stripe pytz -q
$VENV_PIP install -r $APP_DIR/requirements.txt -q
echo "    Packages installed into venv"

echo ""
echo "[E] Verifying key packages in venv..."
$VENV_PIP show pytz stripe flask gunicorn 2>&1 | grep "^Name:"

echo ""
echo "[F] Writing systemd service..."
cat > $SERVICE << SVCEOF
[Unit]
Description=Strangeness IS Flask Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_GUNICORN --workers 2 --bind 127.0.0.1:5000 --timeout 120 app:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF
echo "    Service file written (using venv gunicorn)"

echo ""
echo "[G] Starting service..."
systemctl daemon-reload
systemctl enable strangeness
systemctl restart strangeness
sleep 5
STATUS=$(systemctl is-active strangeness)
echo "    Status: $STATUS"

if [ "$STATUS" != "active" ]; then
    echo ""
    echo "    SERVICE FAILED — crash log:"
    journalctl -u strangeness -n 30 --no-pager
    exit 1
fi

echo ""
echo "[H] Flask health check..."
sleep 2
RESULT=$(curl -s --max-time 8 http://localhost:5000/health 2>&1)
if echo "$RESULT" | grep -q '"ok"'; then
    echo "    FLASK IS UP: $RESULT"
else
    echo "    Flask not responding: $RESULT"
    journalctl -u strangeness -n 15 --no-pager
fi

echo ""
echo "[I] Nginx..."
if systemctl is-active nginx > /dev/null 2>&1; then
    echo "    nginx: active"
else
    echo "    nginx not running — starting..."
    systemctl start nginx && echo "    nginx started"
fi

echo ""
echo "========================================"
AKVAL=$(grep "^ADMIN_KEY=" $APP_DIR/.env | cut -d= -f2- | tr -d '[:space:]')
echo " REPAIR COMPLETE"
echo ""
echo " Admin password : $AKVAL"
echo " Admin URL      : https://strangenessis.com/admin.html"
echo " Health check   : https://api.strangenessis.com/health"
echo ""
echo " To change password:"
echo "   nano $APP_DIR/.env"
echo "   sudo systemctl restart strangeness"
echo "========================================"
