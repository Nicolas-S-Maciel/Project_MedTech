codepy

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
            if user in usuarios_fixos and usuarios_fixos[user]["senha"] == senha:
                st.session_state.update({'logado': True, 'user': user, 'nivel': usuarios_fixos[user]["nivel"]})
                st.rerun()
            elif not df_users.empty and 'Usuario' in df_users.columns:
                match = df_users[(df_users['Usuario'].astype(str) == user) & (df_users['Senha'].astype(str) == senha)]
                if not match.empty:
                    st.session_state.update({'logado': True, 'user': user, 'nivel': match.iloc[0]['Nivel']})
                    st.rerun()
                else: st.sidebar.error("Dados incorretos.")
                
    elif opcao == "Criar Conta":
        st.sidebar.info("Pacientes: Usem seu Nome Completo como usuário.")
        n_user = st.sidebar.text_input("Nome Completo")
        n_senha = st.sidebar.text_input("Nova Senha", type="password")
        if st.sidebar.button("Cadastrar"):
            if n_user and n_senha:
                aba_usuarios.append_row([n_user, n_senha, "leitura"])
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

    if st.session_state['nivel'] == "leitura":
        paciente_df = df[df['Nome_Completo'].astype(str).str.contains(st.session_state['user'], case=False, na=False)]
        st.subheader(f"👤 Seu Prontuário: {st.session_state['user']}")
    else:
        nome_busca = st.text_input("Digite o Nome Completo do Paciente", placeholder="Ex: João Silva")
        paciente_df = df[df['Nome_Completo'].astype(str).str.contains(nome_busca, case=False, na=False)] if nome_busca else pd.DataFrame()

    if not paciente_df.empty:
        for index, registro in paciente_df.sort_values(by='Data/Hora', ascending=False).iterrows():
            with st.expander(f"📅 {registro.get('Data/Hora')} - {registro.get('Categoria')} (ID: {registro.get('ID_Paciente')})"):
                st.write(f"**Relato:** {registro.get('Relato')}")
                st.write(f"**Sinais e Exames:** {registro.get('Sinais/Exames')}")
                st.write(f"**Diagnóstico:** {registro.get('Diagnóstico')}")
                st.write(f"**Conduta:** {registro.get('Conduta')}")
                
                # --- GERENCIAR PRONTUÁRIOS (SÓ ADMIN) ---
                if st.session_state['nivel'] == "total":
                    if st.button("🗑️ Excluir Este Registro", key=f"del_reg_{index}"):
                        try:
                            # Localiza a linha exata na planilha pela Data/Hora
                            celula = base.find(str(registro['Data/Hora']))
                            base.delete_rows(celula.row)
                            st.success("Registro removido com sucesso!")
                            st.rerun()
                        except:
                            st.error("Não foi possível excluir este registro.")

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
                    if tipo == "Evolução (Existente)":
                        busca_id = df[df['Nome_Completo'].astype(str).str.contains(nome_p, case=False, na=False)]
                        id_paciente = busca_id.iloc[-1]['ID_Paciente'] if not busca_id.empty else "P000"
                    
                    data_agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    base.append_row([id_paciente, nome_p, data_agora, cat, relato, sinais, diag, conduta])
                    st.success("Salvo com sucesso!")
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
