import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pandas as pd

# --- CONFIGURAÇÃO DA API ---
@st.cache_resource
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    credenciais = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, scope)
    client = gspread.authorize(creds)
    
    # PROTEÇÃO: Buscando o link direto do Cofre (Secrets)
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
    st.error("Erro de conexão. Verifique o link da planilha no Secrets.")
    st.stop()

usuarios_fixos = {
    "admin": {"senha": st.secrets["senhas_clinica"]["admin"], "nivel": "total"},
    "medico": {"senha": st.secrets["senhas_clinica"]["medico"], "nivel": "escrita"}
}

# --- SISTEMA DE LOGIN E CADASTRO ---
def tela_acesso():
    st.sidebar.title("🩺 MedTech Access")
    opcao = st.sidebar.radio("Selecione:", ["Entrar", "Criar Conta"])
    
    try:
        dados_usuarios = aba_usuarios.get_all_records()
        df_users = pd.DataFrame(dados_usuarios)
    except:
        df_users = pd.DataFrame()
    
    if opcao == "Entrar":
        user = st.sidebar.text_input("Usuário (Seu Nome Completo)")
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            if user in usuarios_fixos and usuarios_fixos[user]["senha"] == senha:
                st.session_state['logado'] = True
                st.session_state['user'] = user
                st.session_state['nivel'] = usuarios_fixos[user]["nivel"]
                st.rerun()
            elif not df_users.empty:
                user_match = df_users[(df_users['Usuario'] == user) & (df_users['Senha'].astype(str) == senha)]
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
        st.sidebar.info("Pacientes: Usem seu Nome Completo como usuário.")
        novo_user = st.sidebar.text_input("Nome Completo")
        nova_senha = st.sidebar.text_input("Nova Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            if novo_user and nova_senha:
                aba_usuarios.append_row([novo_user, nova_senha, "leitura"])
                st.sidebar.success("Conta criada!")

if not st.session_state['logado']:
    tela_acesso()
    st.info("Bem-vindo ao MedTech. Faça login para acessar seu prontuário.")
else:
    st.title("🩺 Painel de Evolução Médica")
    st.sidebar.success(f"Usuário: {st.session_state['user']}")
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- LÓGICA DE CONSULTA INTELIGENTE ---
    st.header("🔍 Consulta de Prontuário")
    
    all_data = base.get_all_records()
    df = pd.DataFrame(all_data)

    # Se for PACIENTE, o sistema filtra AUTOMATICAMENTE pelo nome dele
    if st.session_state['nivel'] == "leitura":
        st.write(f"Exibindo histórico para: **{st.session_state['user']}**")
        paciente_df = df[df['Nome_Completo'].str.contains(st.session_state['user'], case=False, na=False)]
    else:
        # Se for Médico/Admin, ele pode buscar por ID ou NOME
        busca = st.text_input("Busque por ID ou Nome do Paciente", placeholder="Ex: P001 ou João Silva")
        if busca:
            paciente_df = df[
                (df['ID_Paciente'].astype(str).str.contains(busca, case=False, na=False)) |
                (df['Nome_Completo'].str.contains(busca, case=False, na=False))
            ]
        else:
            paciente_df = pd.DataFrame()

    # Exibição dos resultados
    if not paciente_df.empty:
        ultima = paciente_df.iloc[-1]
        st.subheader(f"👤 Paciente: {ultima['Nome_Completo']} ({ultima['ID_Paciente']})")
        
        with st.expander("Ver Evolução mais recente", expanded=True):
            st.info(f"**Data:** {ultima['Data/Hora']} | **Categoria:** {ultima['Categoria']}")
            st.write(f"**Relato:** {ultima['Relato']}")
            st.write(f"**Diagnóstico:** {ultima['Diagnóstico']}")
        
        st.divider()
        st.subheader("📜 Histórico Completo")
        for index, registro in paciente_df.sort_values(by='Data/Hora', ascending=False).iterrows():
            with st.expander(f"{registro['Data/Hora']} - {registro['Categoria']}"):
                st.write(registro['Relato'])
                if st.session_state['nivel'] == "total":
                    if st.button("🗑️ Excluir", key=f"del_{index}"):
                        celula = base.find(registro['Data/Hora'], in_column=3)
                        base.delete_rows(celula.row)
                        st.rerun()
    elif st.session_state['nivel'] != "leitura" and busca:
        st.warning("Nenhum registro encontrado para esta busca.")

    # --- LANÇAMENTO (MÉDICO/ADMIN) ---
    if st.session_state['nivel'] in ["total", "escrita"]:
        st.divider()
        st.header("📝 Nova Evolução")
        # ... (restante do código de formulário que você já tem)