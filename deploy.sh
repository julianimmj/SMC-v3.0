#!/bin/bash
# Deploy to Streamlit Community Cloud

echo "🚀 Preparando deploy para Streamlit Community Cloud..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Inicializando repositório git..."
    git init
    git config user.name "Seu Nome"
    git config user.email "seu@email.com"
fi

# Add files
echo "📝 Adicionando arquivos..."
git add .
git commit -m "SMC Cloud Screener v3.0 - Initial commit"

echo ""
echo "=============================================="
echo "PASSOS PARA DEPLOY NO STREAMLIT COMMUNITY CLOUD:"
echo "=============================================="
echo ""
echo "1. Crie um repositório no GitHub:"
echo "   https://github.com/new"
echo ""
echo "2. Faça push do código:"
echo "   git remote add origin https://github.com/SEU_USUARIO/smc-cloud-screener.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3. Acesse o Streamlit Community Cloud:"
echo "   https://share.streamlit.io"
echo ""
echo "4. Clique em 'New app' e conecte ao seu repositório:"
echo "   - Repository: SEU_USUARIO/smc-cloud-screener"
echo "   - Branch: main"
echo "   - Main file path: app.py"
echo ""
echo "5. Clique em 'Deploy'!"
echo ""
echo "=============================================="
echo ""
echo "Para deploy no Google Cloud Run:"
echo "   gcloud run deploy smc-screener --source ."
echo ""
