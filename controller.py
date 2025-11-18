from model import get_user_by_email, check_password, add_reserva, get_all_reservas, delete_reserva, get_room_price, get_quartos_disponiveis
from flask import session, redirect, url_for, request, flash, make_response
from functools import wraps
from datetime import datetime, timedelta
from model import get_all_quartos, update_quarto_status, get_reservas_by_hospede

# Dicionário de Perfis para facilitar a Autorização
PERFIS = {
    1: 'Administrador',
    2: 'Recepcionista',
    3: 'Camareira',
    4: 'Hóspede'
}

# --- Funções de Autenticação e Sessão ---

def authenticate_user(email, password):
    """Tenta autenticar o usuário e inicia a sessão em caso de sucesso."""
    user = get_user_by_email(email)
    
    if user and check_password(user['senha_hash'], password):
        # Autenticação bem-sucedida, armazena dados na sessão
        session['logged_in'] = True
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_name'] = user['nome_completo']
        session['user_profile'] = PERFIS.get(user['perfil_id'], 'Desconhecido')
        session['profile_id'] = user['perfil_id']
        return True
    return False

def logout_user():
    """Limpa a sessão do usuário."""
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('user_profile', None)
    session.pop('profile_id', None)


# --- Decorador para Autorização ---

def login_required(f):
    """Decorador para proteger rotas. Requer login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Você precisa estar logado para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def profile_required(allowed_profiles):
    """Decorador para restringir acesso a perfis específicos (usando ID do perfil)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            profile_id = session.get('profile_id')
            if profile_id not in allowed_profiles:
                flash('Acesso negado. Seu perfil não tem permissão para esta ação.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Lógica de Negócio para Reservas ---

def handle_create_reservation(form):
    """Processa o formulário de nova reserva."""
    try:
        numero_quarto = form['numero_quarto']
        nome_hospede = form['nome_hospede']
        data_checkin_str = form['data_checkin']
        data_checkout_str = form['data_checkout']
        
        checkin = datetime.strptime(data_checkin_str, '%Y-%m-%d')
        checkout = datetime.strptime(data_checkout_str, '%Y-%m-%d')
        
        if checkin >= checkout:
            return False, "Data de check-out deve ser posterior à data de check-in."

        # 1. Calcular Preço e Valor Total
        price_per_night = get_room_price(numero_quarto)
        if price_per_night is None:
             return False, "Quarto não encontrado ou preço não definido."

        duration = (checkout - checkin).days
        valor_total = price_per_night * duration

        # 2. Tentar Adicionar a Reserva no Model
        success, message = add_reserva(
            numero_quarto, nome_hospede, data_checkin_str, data_checkout_str, valor_total
        )
        
        return success, message

    except ValueError:
        return False, "Erro no formato das datas ou valores. Verifique os campos."
    except Exception as e:
        # Loga o erro real (para fins de debug)
        print(f"Erro ao criar reserva: {e}")
        return False, "Ocorreu um erro inesperado ao processar a reserva."

def get_reservas_data():
    """Obtém todas as reservas para exibição."""
    # Note: Em um sistema real, aqui haveria filtros e paginação.
    return get_all_reservas()

def handle_delete_reservation(reserva_id):
    """Processa a requisição de exclusão de reserva."""
    try:
        success = delete_reserva(reserva_id)
        if success:
            return True, "Reserva deletada com sucesso."
        else:
            return False, "Reserva não encontrada ou erro ao deletar."
    except Exception as e:
        print(f"Erro ao deletar reserva: {e}")
        return False, "Ocorreu um erro inesperado ao deletar a reserva."

def handle_room_availability(checkin, checkout):
    """Busca a disponibilidade de quartos baseado nas datas."""
    try:
        # Formato de data YYYY-MM-DD é o padrão do HTML input type="date"
        checkin_dt = datetime.strptime(checkin, '%Y-%m-%d')
        checkout_dt = datetime.strptime(checkout, '%Y-%m-%d')
        
        if checkin_dt >= checkout_dt:
            return [], "Data de check-out deve ser posterior à data de check-in."

        quartos = get_quartos_disponiveis(checkin, checkout)
        return quartos, ""
        
    except ValueError:
        return [], "Formato de data inválido. Use AAAA-MM-DD."

# --- Lógica de Cookies (Preferências) ---

def set_theme_cookie(response, theme):
    """Define o cookie de preferência de tema (cor de fundo)."""
    # Expira em 30 dias
    response.set_cookie('theme', theme, expires=datetime.now() + timedelta(days=30))
    return response

def get_theme_from_cookie(request):
    """Obtém a preferência de tema do cookie."""
    return request.cookies.get('theme', 'light') # 'light' é o padrão

def get_quartos_data():
    """Obtém todos os quartos para exibição da camareira."""
    return get_all_quartos()

def handle_update_quarto_status(numero_quarto, novo_status):
    """Atualiza status de limpeza de um quarto."""
    success = update_quarto_status(numero_quarto, novo_status)
    if success:
        return True, "Status atualizado com sucesso!"
    else:
        return False, "Erro ao atualizar status do quarto."

def get_reservas_hospede(nome_hospede):
    """Obtém reservas de um hóspede específico."""
    return get_reservas_by_hospede(nome_hospede)