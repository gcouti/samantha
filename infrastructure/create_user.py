#!/usr/bin/env python3
"""
Script para criar um novo usuário no banco de dados.

Uso:
    python -m scripts.create_user --email email@exemplo.com --notes_path /caminho/para/notas
"""
import argparse
import sys
import os

# Adiciona o diretório raiz ao path para permitir importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal, init_db
from database.models import Account

def create_user(email: str, notes_path: str = None) -> Account:
    """
    Cria um novo usuário no banco de dados.
    
    Args:
        email: Email do usuário (deve ser único)
        notes_path: Caminho para as notas do usuário (opcional)
        
    Returns:
        Account: O objeto Account criado
    """
    db = SessionLocal()
    try:
        # Verifica se o usuário já existe
        existing_user = db.query(Account).filter(Account.email == email).first()
        if existing_user:
            print(f"Erro: Já existe um usuário com o email {email}")
            return None
        
        # Cria o novo usuário
        new_user = Account(
            email=email,
            notes_path=notes_path
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"Usuário criado com sucesso! ID: {new_user.id}, Email: {new_user.email}")
        return new_user
        
    except Exception as e:
        db.rollback()
        print(f"Erro ao criar usuário: {e}")
        return None
    finally:
        db.close()

def main():
    # Configura o parser de argumentos
    parser = argparse.ArgumentParser(description='Cria um novo usuário no banco de dados')
    parser.add_argument('--email', type=str, required=True, help='Email do usuário')
    parser.add_argument('--notes_path', type=str, help='Caminho para as notas do usuário (opcional)')
    
    args = parser.parse_args()
    
    # Inicializa o banco de dados
    init_db()
    
    # Cria o usuário
    user = create_user(args.email, args.notes_path)
    
    if user:
        print(f"\nDetalhes do usuário:")
        print(f"ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Caminho das notas: {user.notes_path}")

if __name__ == "__main__":
    main()
