from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_session import Session # Para gerenciar sessões no servidor
from controller import (
    authenticate_user, 
    logout_user, 
    login_required, 
    profile_required, 
    handle_create_reservation, 
    get_reservas_data,
    handle_delete_reservation,
    set_theme_cookie,
    get_theme_from_cookie,
    handle_room_availability,
    get_reservas_hospede,
    get_quartos_data,
    handle_update_quarto_status
)
from datetime import datetime,timedelta

# --- Configuração do App Flask ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'uma_chave_secreta_muito_forte_e_aleatoria' # Necessário para Session

# Configuração da Sessão no Servidor (pode ser o Flask-Session simples)
# Usando o padrão Flask-Session para simplificar o exemplo, mas a sessão 
# já usa cookies criptografados.
app.config['SESSION_TYPE'] = 'filesystem' # Armazena sessão em um arquivo
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1) # Tempo de vida da sessão

Session(app)


# --- Rotas de Autenticação ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Exibe e processa o formulário de login."""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if authenticate_user(email, password):
            flash(f'Bem-vindo(a), {session.get("user_name")} ({session.get("user_profile")})!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login falhou. Verifique seu e-mail e senha.', 'danger')
            
    # Obtém o tema do cookie para aplicar na página de login
    current_theme = get_theme_from_cookie(request)
    return render_template('login.html', theme=current_theme)

@app.route('/logout')
@login_required
def logout():
    """Realiza o logout do usuário."""
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

# --- Rotas Principais ---

@app.route('/')
@login_required
def home():
    """Painel principal do usuário logado."""
    user_profile = session.get('user_profile', 'Desconhecido')
    user_name = session.get('user_name', 'Usuário')
    
    # Obtém o tema do cookie para aplicar na página Home
    current_theme = get_theme_from_cookie(request)
    
    return render_template('home.html', user_name=user_name, user_profile=user_profile, theme=current_theme)

# --- Rotas de Reserva (CRUD) ---

# IDs de Perfil permitidos para gerenciar reservas: Administrador (1) e Recepcionista (2)
@app.route('/reservar', methods=['GET', 'POST'])
@login_required
@profile_required(allowed_profiles=[1, 2]) 
def reservar():
    """Cria, lista e deleta reservas."""
    
    # Tratar Ação de Criação de Reserva (POST)
    if request.method == 'POST':
        success, message = handle_create_reservation(request.form)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        # Redireciona para GET para evitar reenvio do formulário
        return redirect(url_for('reservar'))
    
    # Tratar Ação GET (Visualizar Formulário e Lista de Reservas)
    reservas = get_reservas_data()
    
    # Obter dados para o formulário de pesquisa de quartos
    quartos_disponiveis = []
    
    # Default para a pesquisa de disponibilidade
    default_checkin = (datetime.now()).strftime('%Y-%m-%d')
    default_checkout = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Se houver parâmetros de pesquisa na URL, busca a disponibilidade
    checkin_date = request.args.get('checkin', default_checkin)
    checkout_date = request.args.get('checkout', default_checkout)
    
    if checkin_date and checkout_date:
        quartos_disponiveis, error_msg = handle_room_availability(checkin_date, checkout_date)
        if error_msg:
             flash(error_msg, 'warning')
        
    return render_template('reservar.html', 
        reservas=reservas, 
        quartos_disponiveis=quartos_disponiveis,
        default_checkin=default_checkin,
        default_checkout=default_checkout,
        search_checkin=checkin_date,
        search_checkout=checkout_date
    )

@app.route('/reservar/delete/<int:reserva_id>', methods=['POST'])
@login_required
@profile_required(allowed_profiles=[1, 2])
def deletar_reserva(reserva_id):
    """Deleta uma reserva específica."""
    success, message = handle_delete_reservation(reserva_id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('reservar'))

# --- Rotas de Cookies ---

@app.route('/set_theme/<theme>', methods=['GET'])
@login_required
def set_theme(theme):
    """Define a preferência de tema e retorna para a página anterior."""
    response = redirect(request.referrer or url_for('home'))
    return set_theme_cookie(response, theme)

# --- Rotas da Camareira ---
@app.route('/quartos', methods=['GET', 'POST'])
@login_required
@profile_required(allowed_profiles=[3])  # Apenas Camareira
def quartos():
    if request.method == 'POST':
        numero_quarto = request.form['numero_quarto']
        novo_status = request.form['status_limpeza']
        success, message = handle_update_quarto_status(numero_quarto, novo_status)
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('quartos'))

    quartos = get_quartos_data()
    return render_template('quartos.html', quartos=quartos, theme=get_theme_from_cookie(request))


# --- Rotas do Hóspede ---
@app.route('/minhas_reservas')
@login_required
@profile_required(allowed_profiles=[4])  # Apenas Hóspede
def minhas_reservas():
    nome_hospede = session.get('user_name')
    reservas = get_reservas_hospede(nome_hospede)
    return render_template('minhas_reservas.html', reservas=reservas, theme=get_theme_from_cookie(request))

# --- Rodar o App ---
if __name__ == '__main__':
    app.run(debug=True, port=5006)