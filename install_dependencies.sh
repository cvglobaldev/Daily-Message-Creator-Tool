#!/bin/bash
# Install Dependencies for Daily Message Creator Tool
echo "📦 Installing Python dependencies..."
echo "This may take a few minutes..."
echo ""

# Install pip if not available
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --break-system-packages
fi

# Install dependencies from pyproject.toml
echo "Installing required packages..."
python3 -m pip install --break-system-packages \
    email-validator>=2.2.0 \
    flask-dance>=7.1.0 \
    flask>=3.1.1 \
    flask-sqlalchemy>=3.1.1 \
    google-genai>=1.26.0 \
    gunicorn>=23.0.0 \
    psycopg2-binary>=2.9.10 \
    pydantic>=2.11.7 \
    requests>=2.32.4 \
    flask-login>=0.6.3 \
    oauthlib>=3.3.1 \
    pyjwt>=2.10.1 \
    sqlalchemy>=2.0.41 \
    werkzeug>=3.1.3 \
    flask-wtf>=1.2.2 \
    wtforms>=3.2.1 \
    pytz>=2025.2

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "To start the application, run:"
echo "  python3 main.py"
