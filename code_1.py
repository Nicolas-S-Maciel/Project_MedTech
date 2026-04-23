import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pandas as pd

# --- CONFIGURAÇÃO DA API (SEGURANÇA MÁXIMA) ---
@st.cache_resource
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    # Lendo as credenciais do cofre (Secrets)
    credenciais = dict(st.secrets["gcp_service_account"])
    
    # Tratamento da chave privada para evitar erros de formatação (\n)
    if "\\n" in credenciais["private_key"]:
        credenciais["private_key"] = credenciais["private_key"].replace("\\n", "\n")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, scope)
    client = gspread.authorize(creds)
    
    # Buscando o link da planilha do Secrets
    link_da_planilha = st.secrets["spreadsheet_url"]
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

# --- INICIALIZAÇÃO E CONEXÃO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

try:
    sh = connect_sheet()
    base = sh.worksheet("BASE_DE_DADOS")
    aba_usuarios = sh.worksheet("USUARIOS") 
except Exception as e:
    st.error(f"Erro de conexão. Verifique o link e as credenciais no Secrets do Streamlit.")
    st.stop()

# --- USUÁRIOS FIXOS DA CLÍNICA ---
usuarios_fixos = {
    "admin": {"senha": st.secrets["senhas_clinica"]["admin"], "nivel": "total"},
    "medico": {"senha": st.secrets["senhas_clinica"]["medico"], "nivel": "escrita"}
}

# --- SISTEMA DE LOGIN E CADASTRO ---
def tela_acesso():
    st.sidebar.title("🔐 MedTech Access")
    opcao = st.sidebar.radio("Selecione:", ["Entrar", "Criar Conta"])
    
    try:
        dados_usuarios = aba_usuarios.get_all_records()
        df_users = pd.DataFrame(dados_usuarios)
    except:
        df_users = pd.DataFrame()
    
    if opcao == "Entrar":
        user = st.sidebar.text_input("Usuário (Nome Completo)")
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            # Login Admin/Médico
            if user in usuarios_fixos and usuarios_fixos[user]["senha"] == senha:
                st.session_state['logado'] = True
                st.session_state['user'] = user
                st.session_state['nivel'] = usuarios_fixos[user]["nivel"]
                st.rerun()
            # Login Paciente
            elif not df_users.empty and 'Usuario' in df_users.columns:
                user_match = df_users[(df_users['Usuario'].astype(str) == user) & (df_users['Senha'].astype(str) == senha)]
                if not user_match.empty:
                    st.session_state['logado'] = True
                    st.session_state['user'] = user
                    st.session_state['nivel'] = user_match.iloc[0]['Nivel']
                    st.rerun()
                else:
                    st.sidebar.error("Usuário ou Senha incorretos.")
            else:
                st.sidebar.error("Usuário ou Senha incorretos.")
                
    elif opcao == "Criar Conta":
        st.sidebar.info("Pacientes: Cadastrem-se com seu Nome Completo.")
        novo_user = st.sidebar.text_input("Nome Completo")
        nova_senha = st.sidebar.text_input("Nova Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            if novo_user and nova_senha:
                if novo_user in usuarios_fixos:
                    st.sidebar.error("Esse nome de usuário é reservado!")
                else:
                    aba_usuarios.append_row([novo_user, nova_senha, "leitura"])
                    st.sidebar.success("Conta criada! Alterne para 'Entrar'.")

# --- FLUXO PRINCIPAL ---
if not st.session_state['logado']:
    tela_acesso()
    st.warning("Por favor, faça login para acessar o sistema.")
else:
    st.title("🩺 Painel de Evolução Médica")
    st.sidebar.success(f"Logado: {st.session_state['user']}")
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- CONSULTA DE PRONTUÁRIOS ---
    st.header("🔍 Consultar Prontuário")
    all_data = base.get_all_records()
    df = pd.DataFrame(all_data)

    if st.session_state['nivel'] == "leitura":
        # Filtro automático para pacientes
        st.write(f"Exibindo histórico de: **{st.session_state['user']}**")
        paciente_df = df[df['Nome_Completo'].astype(str).str.contains(st.session_state['user'], case=False, na=False)]
    else:
        # Busca manual para médicos/admin
        busca = st.text_input("Busque por ID (P001) ou Nome do Paciente")
        if busca:
            paciente_df = df[
                (df['ID_Paciente'].astype(str).str.contains(busca, case=False, na=False)) |
                (df['Nome_Completo'].astype(str).str.contains(busca, case=False, na=False))
            ]
        else:
            paciente_df = pd.DataFrame()

    if not paciente_df.empty:
        ultima = paciente_df.iloc[-1]
        st.subheader(f"👤 Paciente: {ultima.get('Nome_Completo')} ({ultima.get('ID_Paciente')})")
        
        st.divider()
        st.subheader("📜 Histórico Completo")
        for index, registro in paciente_df.sort_values(by='Data/Hora', ascending=False).iterrows():
            with st.expander(f"{registro.get('Data/Hora')} - {registro.get('Categoria')}"):
                st.write(f"**Relato:** {registro.get('Relato')}")
                st.write(f"**Sinais/Exames:** {registro.get('Sinais/Exames')}")
                st.write(f"**Diagnóstico:** {registro.get('Diagnóstico')}")
                st.write(f"**Conduta:** {registro.get('Conduta')}")
                
                # Exclusão só para Admin
                if st.session_state['nivel'] == "total":
                    if st.button("🗑️ Excluir Registro", key=f"del_{index}"):
                        celula = base.find(registro['Data/Hora'], in_column=3)
                        base.delete_rows(celula.row)
                        st.success("Registro removido!")
                        st.rerun()
    elif 'busca' in locals() and busca:
        st.warning("Nenhum paciente encontrado.")

    # --- NOVO LANÇAMENTO (Só Admin/Médico) ---
    if st.session_state['nivel'] in ["total", "escrita"]:
        st.divider()
        st.header("📝 Nova Evolução")
        tipo_paciente = st.radio("Selecione:", ["Evolução (Existente)", "Novo Paciente"], horizontal=True)

        with st.form("form_evolucao"):
            if tipo_paciente == "Novo Paciente":
                id_paciente = gerar_novo_id(base)
                st.info(f"ID gerado: {id_paciente}")
                nome_paciente = st.text_input("Nome Completo *")
            else:
                id_paciente = st.text_input("ID do Paciente *", placeholder="Ex: P001")
                nome_paciente = st.text_input("Nome (Opcional - auto preenchimento)")

            cat = st.selectbox("Categoria", ["Médica", "Enfermagem", "Fisioterapia", "Outros"])
            relato = st.text_area("Relato *")
            sinais = st.text_area("Sinais e Exames")
            diag = st.text_input("Diagnóstico")
            conduta = st.text_area("Conduta/Plano")
            
            if st.form_submit_button("Salvar no Prontuário"):
                if id_paciente and relato:
                    if tipo_paciente == "Evolução (Existente)" and not nome_paciente:
                        filtro = df[df['ID_Paciente'].astype(str) == id_paciente]
                        nome_paciente = filtro.iloc[-1].get('Nome_Completo', 'Desconhecido') if not filtro.empty else "Desconhecido"
                    
                    data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    base.append_row([id_paciente, nome_paciente, data_hora, cat, relato, sinais, diag, conduta])
                    st.success("Salvo com sucesso!")
                    st.rerun()
                else:
                    st.error("Campos obrigatórios: ID e Relato.")

    # --- GESTÃO DE CONTAS (Exclusivo Admin) ---
    if st.session_state['nivel'] == "total":
        st.divider()
        st.header("👥 Gerenciar Usuários")
        try:
            usuarios_cadastrados = aba_usuarios.get_all_records()
            if usuarios_cadastrados:
                for idx, row in pd.DataFrame(usuarios_cadastrados).iterrows():
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"👤 **{row['Usuario']}** | Nível: {row['Nivel']}")
                    if col2.button("🗑️", key=f"user_del_{idx}"):
                        cel = aba_usuarios.find(str(row['Usuario']), in_column=1)
                        aba_usuarios.delete_rows(cel.row)
                        st.rerun()
        except Exception:
            pass
