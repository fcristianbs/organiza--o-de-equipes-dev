import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import db, User, Project, Task, TaskBlock, MeetingReport, Note, Attachment, Message
from app import get_database_uri

# Carrega variáveis do arquivo .env
load_dotenv()

def migrate():
    target_url = get_database_uri()
    if not target_url or target_url == "sqlite:///database.db":
        print("[!] ERRO: Nenhuma configuracao de banco online foi encontrada no arquivo .env!")
        print("Por favor, adicione as credenciais do seu banco no arquivo .env:")
        print("Opcao 1: DATABASE_URL=\"mysql+pymysql://usuario:senha@host:3306/banco\"")
        print("Opcao 2: Preencher DB_TYPE, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME no .env")
        sys.exit(1)

    # Identificar banco local SQLite
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sqlite_path = os.path.join(base_dir, "instance", "database.db")
    if not os.path.exists(sqlite_path):
        sqlite_path = os.path.join(base_dir, "database.db")

    if not os.path.exists(sqlite_path):
        print(f"[!] Banco de dados local SQLite nao encontrado em {sqlite_path}.")
        print("Apenas criando a estrutura de tabelas no banco remoto...")
        sqlite_engine = None
    else:
        print(f"[+] Banco local encontrado: {sqlite_path}")
        sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")

    print(f"[+] Conectando ao banco de dados remoto ({target_url.split('@')[-1] if '@' in target_url else target_url})...")
    target_engine = create_engine(target_url)

    # 1. Criar estrutura de tabelas no banco de destino
    print("[+] Criando estrutura de tabelas no banco de destino...")
    db.metadata.create_all(bind=target_engine)
    print("[OK] Tabelas criadas com sucesso.")

    if not sqlite_engine:
        print("[OK] Processo concluido! Nenhuns dados para migrar.")
        return

    # Prepare Sessions
    LocalSession = sessionmaker(bind=sqlite_engine)
    TargetSession = sessionmaker(bind=target_engine)

    local_session = LocalSession()
    target_session = TargetSession()

    models = [User, Project, Task, TaskBlock, MeetingReport, Note, Attachment, Message]

    try:
        print("[+] Migrando dados do SQLite para o banco online...")
        for model in models:
            records = local_session.query(model).all()
            print(f"  -> Migrando {len(records)} registros da tabela '{model.__tablename__}'...")
            
            for record in records:
                # Criar nova instância do modelo para a sessão de destino
                data = {column.name: getattr(record, column.name) for column in model.__table__.columns}
                target_session.merge(model(**data))
            
            target_session.commit()
            print(f"  [OK] Tabela '{model.__tablename__}' migrada com sucesso.")

        # Se o banco remoto for PostgreSQL, ajustar as sequences dos IDs auto-incrementáveis
        if "postgresql" in target_engine.dialect.name:
            print("[+] Ajustando sequencias de auto-incremento no PostgreSQL...")
            with target_engine.connect() as conn:
                for model in models:
                    table_name = model.__tablename__
                    conn.execute(text(f"""
                        SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                               COALESCE((SELECT MAX(id) FROM {table_name}), 1), 
                               EXISTS(SELECT 1 FROM {table_name}));
                    """))
                conn.commit()
            print("[OK] Sequencias ajustadas com sucesso.")

        print("\n=======================================================")
        print(" MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print(" Todos os dados locais foram copiados para o banco online.")
        print("=======================================================\n")

    except Exception as e:
        target_session.rollback()
        print(f"\n[!] ERRO DURANTE A MIGRAÇÃO: {e}")
        raise e
    finally:
        local_session.close()
        target_session.close()

if __name__ == "__main__":
    migrate()
