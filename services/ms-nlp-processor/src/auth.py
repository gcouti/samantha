import os
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

load_dotenv()

# Carrega as credenciais do Google a partir de variáveis de ambiente
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Carrega as credenciais da Apple a partir de variáveis de ambiente
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")
APPLE_CLIENT_SECRET = os.getenv("APPLE_CLIENT_SECRET")

# Cria a instância do OAuth
oauth = OAuth()

# Registra o provedor do Google
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

# Registra o provedor da Apple
if APPLE_CLIENT_ID and APPLE_CLIENT_SECRET:
    oauth.register(
        name='apple',
        client_id=APPLE_CLIENT_ID,
        client_secret=APPLE_CLIENT_SECRET,
        server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'name email',
            'response_mode': 'form_post', # A Apple exige isso
        }
    )
