import sqlite3
import bcrypt
from datetime import datetime

DATABASE_NAME = 'hotel_estada_feliz.db'

# --- Configurações Iniciais e Criação de DB ---
def init_db():
    """Cria e popula o banco de dados SQLite com dados iniciais."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Tabela PERFIS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS perfis (
            id INTEGER PRIMARY KEY,
            nome_perfil VARCHAR(50) UNIQUE NOT NULL
        )
    ''')
    
    # Tabela USUÁRIOS
    # Nota: A coluna 'senha_hash' é usada para armazenar a senha criptografada.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            nome_completo VARCHAR(150),
            email VARCHAR(100) UNIQUE NOT NULL,
            senha_hash VARCHAR(100) NOT NULL,
            perfil_id INTEGER,
            FOREIGN KEY (perfil_id) REFERENCES perfis(id)
        )
    ''')
    
    # Tabela QUARTOS (Simplificada para a funcionalidade principal)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quartos (
            numero_quarto VARCHAR(10) PRIMARY KEY,
            capacidade_maxima INTEGER NOT NULL,
            preco_diaria_base REAL NOT NULL,
            status_limpeza VARCHAR(20) DEFAULT 'Limpo'
        )
    ''')

    # Tabela RESERVAS
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservas (
            id_reserva INTEGER PRIMARY KEY,
            numero_quarto VARCHAR(10) NOT NULL,
            nome_hospede TEXT NOT NULL,
            data_checkin DATE NOT NULL,
            data_checkout DATE NOT NULL,
            status_reserva VARCHAR(30) NOT NULL,
            valor_total REAL NOT NULL,
            FOREIGN KEY (numero_quarto) REFERENCES quartos(numero_quarto)
        )
    ''')

    # Inserir Perfis
    perfis = [
        (1, 'Administrador'), 
        (2, 'Recepcionista'), 
        (3, 'Camareira'), 
        (4, 'Hóspede')
    ]
    cursor.executemany("INSERT OR IGNORE INTO perfis VALUES (?, ?)", perfis)

    # Função auxiliar para gerar hash de senha
    def hash_password(password):
        # O bcrypt espera um bytestring, por isso o .encode('utf-8')
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Inserir Usuário Administrador (Senha: 'admin123')
    admin_hash = hash_password('admin123')
    admin_user = ('Admin Hotel', 'admin@hotel.com', admin_hash, 1)
    
    # Inserir Usuário Hóspede (Senha: 'hospede123')
    hospede_hash = hash_password('hospede123')
    hospede_user = ('Hóspede', 'hospede@hotel.com', hospede_hash, 4)

    # Inserir Usuário Camareira (Senha: 'camareira123')
    camareira_hash = hash_password('camareira123')
    camareira_user = ('Camareira', 'camareira@hotel.com', camareira_hash, 4)

    # Inserir Usuário Recepcionista (Senha: 'recepcionista123')
    recepcionista_hash = hash_password('recepcionista123')
    recepcionista_user = ('Recepcionista', 'recepcionista@hotel.com', recepcionista_hash, 4)

    try:
        cursor.execute("INSERT INTO usuarios (nome_completo, email, senha_hash, perfil_id) VALUES (?, ?, ?, ?)", admin_user)
        cursor.execute("INSERT INTO usuarios (nome_completo, email, senha_hash, perfil_id) VALUES (?, ?, ?, ?)", hospede_user)
        cursor.execute("INSERT INTO usuarios (nome_completo, email, senha_hash, perfil_id) VALUES (?, ?, ?, ?)", camareira_user)
        cursor.execute("INSERT INTO usuarios (nome_completo, email, senha_hash, perfil_id) VALUES (?, ?, ?, ?)", recepcionista_user)
    except sqlite3.IntegrityError:
        print("Usuários Admin e Hóspede já existem.")


    # Inserir Quartos de Exemplo
    quartos = [
        ('101', 2, 150.00, 'Limpo'),
        ('102', 2, 150.00, 'Limpo'),
        ('201', 4, 250.00, 'Limpo'),
        ('305', 1, 100.00, 'Sujo'),
    ]
    cursor.executemany("INSERT OR IGNORE INTO quartos VALUES (?, ?, ?, ?)", quartos)


    conn.commit()
    conn.close()

# --- Funções de Autenticação e Usuário ---

def get_user_by_email(email):
    """Busca um usuário por email."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Permite acessar colunas por nome
    cursor = conn.cursor()
    cursor.execute("SELECT u.*, p.nome_perfil FROM usuarios u JOIN perfis p ON u.perfil_id = p.id WHERE u.email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def check_password(hashed_password, password):
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    # Ambas as strings devem ser bytestrings para bcrypt.checkpw
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Funções de CRUD de Reserva ---

def get_all_reservas():
    """Retorna todas as reservas."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservas ORDER BY data_checkin DESC")
    reservas = cursor.fetchall()
    conn.close()
    # Converte rows para lista de dicionários para fácil manipulação no Flask
    return [dict(reserva) for reserva in reservas]

def get_reserva_by_id(reserva_id):
    """Retorna uma reserva específica pelo ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservas WHERE id_reserva = ?", (reserva_id,))
    reserva = cursor.fetchone()
    conn.close()
    return dict(reserva) if reserva else None

def get_quartos_disponiveis(checkin_date_str, checkout_date_str):
    """
    Retorna a lista de todos os quartos que não têm reservas 
    conflitantes no período especificado.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Encontrar quartos reservados no período
    # Conflito acontece se:
    # (reserva.checkin < novo.checkout) AND (reserva.checkout > novo.checkin)
    cursor.execute('''
        SELECT DISTINCT numero_quarto FROM reservas
        WHERE status_reserva NOT IN ('Cancelada') 
        AND (
            (data_checkin < ?) AND (data_checkout > ?)
        )
    ''', (checkout_date_str, checkin_date_str))
    
    reserved_rooms = [row['numero_quarto'] for row in cursor.fetchall()]
    
    # 2. Selecionar todos os quartos E excluir os reservados
    if reserved_rooms:
        # Cria uma string de placeholders para a cláusula NOT IN
        placeholders = ', '.join('?' for _ in reserved_rooms)
        sql_query = f"SELECT * FROM quartos WHERE numero_quarto NOT IN ({placeholders})"
        cursor.execute(sql_query, reserved_rooms)
    else:
        cursor.execute("SELECT * FROM quartos")

    quartos = cursor.fetchall()
    conn.close()
    return [dict(quarto) for quarto in quartos]


def add_reserva(numero_quarto, nome_hospede, data_checkin, data_checkout, valor_total):
    """Cria uma nova reserva e a insere no DB."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    status = 'Confirmada' # Reserva é criada como confirmada
    
    # Validação de Datas
    try:
        checkin = datetime.strptime(data_checkin, '%Y-%m-%d').date()
        checkout = datetime.strptime(data_checkout, '%Y-%m-%d').date()
        if checkin >= checkout:
            return False, "Data de check-out deve ser posterior à data de check-in."
        if checkin < datetime.now().date():
            # Permite reservas no passado para fins de teste/histórico, mas idealmente bloqueia
            pass 
    except ValueError:
        return False, "Formato de data inválido."

    try:
        cursor.execute('''
            INSERT INTO reservas 
            (numero_quarto, nome_hospede, data_checkin, data_checkout, status_reserva, valor_total) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (numero_quarto, nome_hospede, data_checkin, data_checkout, status, valor_total))
        conn.commit()
        conn.close()
        return True, "Reserva realizada com sucesso!"
    except sqlite3.IntegrityError as e:
        conn.close()
        return False, f"Erro ao adicionar reserva: {e}"


def delete_reserva(reserva_id):
    """Deleta uma reserva específica pelo ID."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reservas WHERE id_reserva = ?", (reserva_id,))
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()
    return rows_deleted > 0

def get_room_price(numero_quarto):
    """Obtém o preço base da diária de um quarto."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT preco_diaria_base FROM quartos WHERE numero_quarto = ?", (numero_quarto,))
    price = cursor.fetchone()
    conn.close()
    return price[0] if price else None

# Inicializa o DB na primeira execução do módulo
init_db()