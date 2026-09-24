import oracledb
from utilitarios.variaveis_env import safe_env_get

def conectar():
    # Configurações de conexão com o banco de dados
    user = safe_env_get("DB_USER")
    pw = safe_env_get("DB_PASS")
    dsn = safe_env_get("DB_DSN")
    
    # Conexão com o banco de dados Oracle
    connection = oracledb.connect(user=user, password=pw, dsn=dsn)
    return connection
    