import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pandas as pd

# --- CONFIGURAÇÃO DA API (ATUALIZADA PARA A NUVEM) ---
@st.cache_resource
def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    
    # Agora lemos as credenciais do "cofre" do Streamlit
    credenciais = dict(st.secrets["gcp_service_account"])
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais, scope)
    client = gspread.authorize(creds)
    link_da_planilha = "https://docs.google.com/spreadsheets/d/16AddnMv5ZrMW29jEYJKUTQe1ondtwfPUkcaLMsVV3K8/edit?gid=0#gid=0"
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
    st.error(f"Erro ao conectar na planilha. Verifique se a aba 'USUARIOS' foi criada. Erro: {e}")
    st.stop()

# --- USUÁRIOS FIXOS DA CLÍNICA ---
usuarios_fixos = {
    "admin": {"senha": "123", "nivel": "total"},
    "medico": {"senha": "456", "nivel": "escrita"}
}

# --- SISTEMA DE LOGIN E CADASTRO ---
def tela_acesso():
    st.sidebar.title("Acesso ao Sistema")
    opcao = st.sidebar.radio("Selecione:", ["Entrar", "Criar Conta (Apenas Paciente)"])
    
    try:
        dados_usuarios = aba_usuarios.get_all_records()
        df_users = pd.DataFrame(dados_usuarios)
    except:
        df_users = pd.DataFrame()
    
    if opcao == "Entrar":
        user = st.sidebar.text_input("Usuário")
        senha = st.sidebar.text_input("Senha", type="password")
        if st.sidebar.button("Entrar"):
            
            if user in usuarios_fixos and usuarios_fixos[user]["senha"] == senha:
                st.session_state['logado'] = True
                st.session_state['user'] = user
                st.session_state['nivel'] = usuarios_fixos[user]["nivel"]
                st.rerun()
                
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
                
    elif opcao == "Criar Conta (Apenas Paciente)":
        novo_user = st.sidebar.text_input("Novo Usuário")
        nova_senha = st.sidebar.text_input("Nova Senha", type="password")
        
        if st.sidebar.button("Cadastrar"):
            if novo_user and nova_senha:
                if novo_user in usuarios_fixos:
                    st.sidebar.error("Esse nome de usuário é reservado para a clínica!")
                elif not df_users.empty and 'Usuario' in df_users.columns and novo_user in df_users['Usuario'].astype(str).values:
                    st.sidebar.error("Esse nome de usuário já existe!")
                else:
                    aba_usuarios.append_row([novo_user, nova_senha, "leitura"])
                    st.sidebar.success("Conta criada! Mude para 'Entrar' para acessar.")
            else:
                st.sidebar.error("Preencha todos os campos!")

if not st.session_state['logado']:
    tela_acesso()
    st.warning("Por favor, faça login ou cadastre-se para acessar os prontuários.")
else:
    # --- PAINEL PRINCIPAL ---
    st.title("🩺 Painel de Evolução Médica")
    st.sidebar.success(f"Logado: {st.session_state['user']} ({st.session_state['nivel']})")
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- CONSULTA DE PRONTUÁRIOS ---
    st.header("🔍 Consultar Prontuário")
    id_busca = st.text_input("Digite o ID do Paciente", placeholder="Ex: P001")

    if id_busca:
        all_data = base.get_all_records()
        if all_data:
            df = pd.DataFrame(all_data)
            paciente_df = df[df['ID_Paciente'].astype(str) == id_busca]

            if not paciente_df.empty:
                ultima = paciente_df.iloc[-1]
                st.subheader(f"👤 Paciente: {ultima.get('Nome_Completo', 'N/A')}")
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Data/Hora:** {ultima.get('Data/Hora', 'N/A')}")
                    st.info(f"**Categoria:** {ultima.get('Categoria', 'N/A')}")
                
                st.markdown(f"**Relato:** {ultima.get('Relato', '')} \n\n --- \n\n **Sinais/Exames:** {ultima.get('Sinais/Exames', '')} \n\n --- \n\n **Diagnóstico:** {ultima.get('Diagnóstico', '')} \n\n --- \n\n **Conduta:** {ultima.get('Conduta', '')}")
                
                st.divider()
                st.subheader("📜 Histórico Completo")
                for index, registro in paciente_df.sort_values(by='Data/Hora', ascending=False).iterrows():
                    with st.expander(f"{registro.get('Data/Hora', '')} - {registro.get('Categoria', '')}"):
                        st.write(f"**Relato:** {registro.get('Relato', '')}")
                        st.write(f"**Sinais/Exames:** {registro.get('Sinais/Exames', '')}")
                        st.write(f"**Diagnóstico:** {registro.get('Diagnóstico', '')}")
                        st.write(f"**Conduta:** {registro.get('Conduta', '')}")
                        
                        # Admin apaga prontuários
                        if st.session_state['nivel'] == "total":
                            if st.button("🗑️ Excluir Registro", key=f"del_pront_{index}"):
                                celula = base.find(registro['Data/Hora'], in_column=3)
                                base.delete_rows(celula.row)
                                st.success("Registro removido!")
                                st.rerun()
            else:
                st.warning("Paciente não encontrado.")

    # --- NOVO LANÇAMENTO (Só Admin/Médico) ---
    if st.session_state['nivel'] in ["total", "escrita"]:
        st.divider()
        st.header("📝 Nova Evolução")
        tipo_paciente = st.radio("Selecione:", ["Evolução (Existente)", "Novo Paciente"], horizontal=True)

        with st.form("form_evolucao"):
            if tipo_paciente == "Novo Paciente":
                id_paciente = gerar_novo_id(base)
                st.info(f"Novo ID gerado: {id_paciente}")
                nome_paciente = st.text_input("Nome Completo *")
            else:
                id_paciente = st.text_input("ID do Paciente *", placeholder="Ex: P001")
                nome_paciente = st.text_input("Nome Completo (Deixe em branco para auto-preencher)")

            cat = st.selectbox("Categoria", ["Médica", "Enfermagem", "Fisioterapia", "Outros"])
            relato = st.text_area("Relato *")
            sinais = st.text_area("Sinais e Exames")
            diag = st.text_input("Diagnóstico")
            conduta = st.text_area("Conduta/Plano")
            
            if st.form_submit_button("Salvar no Prontuário"):
                if id_paciente and relato:
                    if tipo_paciente == "Evolução (Existente)" and not nome_paciente:
                        try:
                            df_temp = pd.DataFrame(base.get_all_records())
                            filtro = df_temp[df_temp['ID_Paciente'].astype(str) == id_paciente]
                            nome_paciente = filtro.iloc[-1].get('Nome_Completo', 'Não informado') if not filtro.empty else "Não informado"
                        except:
                            nome_paciente = "Não informado"
                    
                    if not nome_paciente: nome_paciente = "Paciente não identificado"

                    data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    base.append_row([id_paciente, nome_paciente, data_hora, cat, relato, sinais, diag, conduta])
                    
                    st.success(f"Salvo com sucesso! ID: {id_paciente}")
                    st.balloons()
                else:
                    st.error("ID e Relato são obrigatórios!")

    # --- GERENCIAMENTO DE CONTAS (EXCLUSIVO ADMIN) ---
    if st.session_state['nivel'] == "total":
        st.divider()
        st.header("👥 Gerenciar Contas de Pacientes")
        
        try:
            usuarios_cadastrados = aba_usuarios.get_all_records()
            if not usuarios_cadastrados:
                st.info("Nenhuma conta de paciente criada na planilha.")
            else:
                df_gestao = pd.DataFrame(usuarios_cadastrados)
                
                # Criando uma tabelinha visual com botões de excluir
                for index, row in df_gestao.iterrows():
                    col_u1, col_u2, col_u3 = st.columns([2, 1, 1])
                    with col_u1:
                        st.write(f"**Usuário:** {row['Usuario']}")
                    with col_u2:
                        st.write(f"Nível: {row['Nivel']}")
                    with col_u3:
                        if st.button(f"🗑️ Excluir Conta", key=f"user_del_{index}"):
                            try:
                                celula_user = aba_usuarios.find(str(row['Usuario']), in_column=1)
                                aba_usuarios.delete_rows(celula_user.row)
                                st.success(f"Conta '{row['Usuario']}' removida!")
                                st.rerun()
                            except:
                                st.error("Erro ao excluir.")
        except Exception as e:
            st.error(f"Erro ao carregar usuários: {e}")