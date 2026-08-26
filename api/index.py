import sys
import os

# Garante que o diretório raiz do projeto esteja no PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
