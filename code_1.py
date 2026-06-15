import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash # NOVO IMPORT
import time # NOVO IMPORT AQUI

# --- CONFIGURAÇÃO DA API ---
@st.cache_resource
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    credenciais = dict(st.secrets["gcp_service_account"])
    if "\\n" in credenciais["private_key"]:
        credenciais["private_key"] = credenciais["private_key"].replace("\\n", "\n")
        
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, scope)
    client = gspread.authorize(creds)
    link_da_planilha = "https://docs.google.com/spreadsheets/d/16AddnMv5ZrMW29jEYJKUTQe1ondtwfPUkcaLMsVV3K8/edit"
    return client.open_by_url(link_da_planilha)

# --- FUNÇÃO GERADORA DE ID ---
def gerar_novo_id(base):
    try:
        dados = base.get_all_records()
        if not dados: return "P001"
        df = pd.DataFrame(dados)
        if 'ID_Paciente' not in df.columns: return "P001"
        ids_existentes = df['ID_Paciente'].dropna().astype(str).tolist()
        numeros = [int(id_p[1:]) for id_p in ids_existentes if id_p.startswith('P') and id_p[1:].isdigit()]
        if not numeros: return "P001"
        return f"P{max(numeros) + 1:03d}"
    except Exception:
        return "P001"
    
# --- FUNÇÃO PARA PREVENIR INJEÇÃO NO GOOGLE SHEETS ---
def proteger_dados(texto):
    texto_str = str(texto)
    # Se o texto começar com um caractere de fórmula, adicionamos uma aspa simples
    if texto_str.startswith(('=', '+', '-', '@')):
        return "'" + texto_str
    return texto_str

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

try:
    sh = connect_sheet()
    base = sh.worksheet("BASE_DE_DADOS")
    aba_usuarios = sh.worksheet("USUARIOS") 
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

usuarios_fixos = {
    "admin": {"senha": st.secrets["senhas_clinica"]["admin"], "nivel": "total"},
    "medico": {"senha": st.secrets["senhas_clinica"]["medico"], "nivel": "escrita"}
}

# --- PROTEÇÃO 5: TIMEOUT DE SESSÃO ---
TEMPO_MAXIMO_INATIVIDADE = 600 # 300 segundos = 5 minutos (Ajuste como preferir)

# Só inicia a contagem e a verificação SE o usuário já estiver logado
if st.session_state.get('logado', False):
    
    # Se ele acabou de fazer o login, cria o cronômetro agora (zerado)
    if 'ultimo_acesso' not in st.session_state:
        st.session_state['ultimo_acesso'] = time.time()
        
    tempo_atual = time.time()
    tempo_inativo = tempo_atual - st.session_state['ultimo_acesso']
    
    if tempo_inativo > TEMPO_MAXIMO_INATIVIDADE:
        # Passou do tempo: Expulsa e limpa o cronômetro
        st.session_state['logado'] = False
        del st.session_state['ultimo_acesso'] 
        st.error("⏳ Sua sessão expirou por inatividade. Faça login novamente.")
        time.sleep(3)
        st.rerun()
    else:
        # Se interagiu a tempo, renova o cronômetro
        st.session_state['ultimo_acesso'] = tempo_atual

# --- LOGIN E CADASTRO ---
def tela_acesso():
    st.sidebar.title("命 MedTech Access")
    opcao = st.sidebar.radio("Selecione:", ["Entrar", "Criar Conta"])
    
    try:
        df_users = pd.DataFrame(aba_usuarios.get_all_records())
    except:
        df_users = pd.DataFrame()
    
    if opcao == "Entrar":
        user = st.sidebar.text_input("Usuário (Nome Completo)")
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            
            # Verifica usuários fixos (Admin/Médico) que vêm do st.secrets
            if user in usuarios_fixos and usuarios_fixos[user]["senha"] == senha:
                st.session_state.update({'logado': True, 'user': user, 'nivel': usuarios_fixos[user]["nivel"]})
                st.rerun()
                
            # Verifica usuários do banco de dados (Pacientes)
            elif not df_users.empty and 'Usuario' in df_users.columns:
                # Localiza a linha do usuário específico
                user_row = df_users[df_users['Usuario'].astype(str) == user]
                
                if not user_row.empty:
                    # Extrai o hash que está salvo na planilha
                    hash_salvo = str(user_row.iloc[0]['Senha'])
                    
                    # Compara a senha digitada com o hash salvo
                    if check_password_hash(hash_salvo, senha):
                        st.session_state.update({'logado': True, 'user': user, 'nivel': user_row.iloc[0]['Nivel']})
                        st.rerun()
                    else:
                        st.sidebar.error("Dados incorretos.")
                else: 
                    st.sidebar.error("Dados incorretos.")
                
    elif opcao == "Criar Conta":
        st.sidebar.info("Pacientes: Usem seu Nome Completo como usuário.")
        n_user = st.sidebar.text_input("Nome Completo")
        n_senha = st.sidebar.text_input("Nova Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            if n_user and n_senha:
                # 1. Gera um hash irreversível da senha
                senha_hash = generate_password_hash(n_senha)
                
                # 2. Salva o hash na planilha, e não mais a senha pura
                aba_usuarios.append_row([n_user, senha_hash, "leitura"])
                st.sidebar.success("Conta criada! Vá em 'Entrar'.")

if not st.session_state['logado']:
    tela_acesso()
else:
    st.title("命 Painel de Evolução Médica")
    st.sidebar.write(f"Usuário: **{st.session_state['user']}**")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- LÓGICA DE CONSULTA ---
    st.header("🔍 Histórico do Paciente")
    all_data = base.get_all_records()
    df = pd.DataFrame(all_data)

    # 1. DEFINIÇÃO DO FILTRO (Quem estamos buscando?)
    if st.session_state['nivel'] == "leitura":
        # Paciente busca a si mesmo
        termo_busca = st.session_state['user']
        st.subheader(f"👤 Seu Prontuário: {termo_busca}")
    else:
        # Médico/Admin digita o nome
        termo_busca = st.text_input("Digite o Nome Completo do Paciente", placeholder="Ex: João Silva", key="input_busca")

    # 2. EXECUÇÃO DA BUSCA
    if df.empty or 'Nome_Completo' not in df.columns:
        paciente_df = pd.DataFrame()
        if termo_busca:
            st.info("O banco de dados está vazio ou não possui a coluna 'Nome_Completo'.")
    else:
        if termo_busca:
            # .str.strip() remove espaços acidentais no início ou fim
            # regex=False garante a segurança contra o Ponto 4
            paciente_df = df[df['Nome_Completo'].astype(str).str.contains(termo_busca.strip(), case=False, na=False, regex=False)]
        else:
            paciente_df = pd.DataFrame()

    # 3. EXIBIÇÃO DOS RESULTADOS (A parte que pode ter sumido)
    if not paciente_df.empty:
        st.write(f"Encontrado(s) {len(paciente_df)} registro(s):")
        st.dataframe(paciente_df, use_container_width=True)
    else:
        if termo_busca:
            st.warning(f"Nenhum registro encontrado para '{termo_busca}'. Verifique se o nome está correto na planilha.")

    # --- LANÇAMENTO (Só Admin/Médico) ---
    if st.session_state['nivel'] in ["total", "escrita"]:
        st.divider()
        st.header("📝 Nova Evolução")
        tipo = st.radio("Ação:", ["Evolução (Existente)", "Novo Paciente"], horizontal=True)

        with st.form("form_evolucao"):
            if tipo == "Novo Paciente":
                id_paciente = gerar_novo_id(base)
                st.write(f"ID Gerado para o Banco: **{id_paciente}**")
                nome_p = st.text_input("Nome Completo do Paciente *")
            else:
                nome_p = st.text_input("Nome Completo do Paciente (Para localizar ID) *")
                id_paciente = ""

            cat = st.selectbox("Categoria", ["Médica", "Enfermagem", "Fisioterapia", "Outros"])
            relato = st.text_area("Relato Clínico *")
            sinais = st.text_area("Sinais e Exames")
            diag = st.text_input("Diagnóstico/Hipótese")
            conduta = st.text_area("Conduta")
            
            if st.form_submit_button("Salvar Registro"):
                if nome_p and relato:
                    pode_salvar = True # Variável para controlar se podemos prosseguir
                    
                    if tipo == "Evolução (Existente)":
                        # Verifica se o banco tem dados
                        if not df.empty and 'Nome_Completo' in df.columns:
                            # Busca o paciente (com proteção regex e ignorando espaços acidentais)
                            busca_id = df[df['Nome_Completo'].astype(str).str.contains(nome_p.strip(), case=False, na=False, regex=False)]
                            
                            if busca_id.empty:
                                # Se não achou, exibe erro e BLOQUEIA o salvamento
                                st.error(f"❌ Paciente '{nome_p}' não encontrado no banco de dados! O registro NÃO foi salvo. Verifique a ortografia ou selecione a ação 'Novo Paciente'.")
                                pode_salvar = False
                            else:
                                # Se achou, pega o ID corretamente
                                id_paciente = busca_id.iloc[-1]['ID_Paciente']
                        else:
                            st.error("O banco de dados está vazio. Selecione a ação 'Novo Paciente' primeiro.")
                            pode_salvar = False
                    
                    # Só executa o salvamento se não houve erros
                    if pode_salvar:
                        data_agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        
                        # Usando o filtro de proteção (Passo 1) em todos os campos
                        linha_segura = [
                            proteger_dados(id_paciente), 
                            proteger_dados(nome_p.strip()), 
                            proteger_dados(data_agora), 
                            proteger_dados(cat), 
                            proteger_dados(relato), 
                            proteger_dados(sinais), 
                            proteger_dados(diag), 
                            proteger_dados(conduta)
                        ]
                        
                        base.append_row(linha_segura)
                        st.success("✅ Registro salvo com sucesso!")
                        
                        # Pequena pausa para o usuário ler a mensagem de sucesso antes de recarregar a página
                        import time
                        time.sleep(1.5) 
                        st.rerun()

    # --- GERENCIAR USUÁRIOS (SÓ ADMIN) ---
    if st.session_state['nivel'] == "total":
        st.divider()
        st.header("👥 Gerenciar Usuários")
        try:
            users_list = aba_usuarios.get_all_records()
            if users_list:
                for i, u_row in pd.DataFrame(users_list).iterrows():
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"👤 **{u_row['Usuario']}** (Nível: {u_row['Nivel']})")
                    if c2.button("Excluir Conta", key=f"user_{i}"):
                        cel_u = aba_usuarios.find(str(u_row['Usuario']))
                        aba_usuarios.delete_rows(cel_u.row)
                        st.success(f"Usuário {u_row['Usuario']} removido.")
                        st.rerun()
        except:
            st.info("Nenhum usuário para gerenciar.")
