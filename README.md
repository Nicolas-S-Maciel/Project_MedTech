# 🏥 Sistema de Prontuário Eletrônico & Evolução Médica

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google_Sheets-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)
![Projeto Acadêmico](https://img.shields.io/badge/Projeto-Acadêmico_SENAI-red?style=for-the-badge)

Um sistema web completo, responsivo e seguro para gestão de clínicas, prontuários de pacientes e controle de evoluções médicas. Este projeto utiliza o **Streamlit** para a interface gráfica e transforma o **Google Sheets** em um banco de dados na nuvem em tempo real, garantindo baixo custo de infraestrutura e alta acessibilidade.

---

## 🎓 Contexto Acadêmico

Este projeto foi idealizado e desenvolvido como atividade prática para o curso superior de **Análise e Desenvolvimento de Sistemas (ADS)** do **SENAI**. A aplicação foi criada especificamente para a disciplina de **Engenharia de Software**, com o objetivo central de projetar e desenvolver uma solução de software funcional e aplicável à realidade de uma clínica médica, utilizando ferramentas acessíveis como o Google Planilhas.

---

## 📑 Índice
1. [Sobre o Projeto](#-sobre-o-projeto)
2. [Funcionalidades Principais](#-funcionalidades-principais)
3. [A Arquitetura e o Papel do Gspread](#-a-arquitetura-e-o-papel-do-gspread)
4. [Tecnologias Utilizadas](#-tecnologias-utilizadas)
5. [Como Executar Localmente](#-como-executar-localmente)
6. [Deploy e Segurança](#-deploy-e-segurança)

---

## 💡 Sobre o Projeto

Este painel foi desenvolvido para facilitar a rotina médica, permitindo o registro rápido de atendimentos e o acompanhamento do histórico dos pacientes. Com um design adaptável (funciona perfeitamente em computadores, tablets e celulares), a plataforma elimina a necessidade de papéis físicos e centraliza as informações de forma segura, simulando o ambiente real de uma clínica ou hospital.

---

## 🚀 Funcionalidades Principais

- **🔐 Sistema de Autenticação por Níveis:**
  - **Administrador:** Acesso total. Cria evoluções, gerencia contas de pacientes e pode excluir registros em caso de erro.
  - **Médico/Equipe:** Permissão de escrita. Visualiza o histórico e lança novas evoluções.
  - **Paciente:** Acesso restrito (somente leitura). Pode consultar seu próprio histórico médico após criar uma conta.
- **📝 Formulário Completo de Evolução:** Registro detalhado com suporte a Categoria, Relato, Sinais e Exames, Diagnóstico e Conduta/Plano.
- **🪪 Geração Automática de IDs:** Novos pacientes recebem identificadores sequenciais automáticos (ex: `P001`, `P002`).
- **🔍 Busca Dinâmica:** Consulta rápida de histórico através do ID do paciente, exibindo os dados de forma cronológica e organizada.

---

## 🌉 A Arquitetura e o Papel do Gspread

Para que este projeto atendesse aos requisitos da disciplina de Engenharia de Software sem a necessidade de hospedar um banco de dados relacional complexo, optamos por utilizar a API do Google Sheets. 

Nesse cenário, a biblioteca **`gspread`** foi **absolutamente essencial**. Ela atuou como a ponte principal entre a lógica do Python e a nuvem do Google. Graças ao `gspread`, conseguimos manipular a planilha como um verdadeiro banco de dados: lendo registros, buscando pacientes, gravando novas evoluções e deletando linhas instantaneamente através de métodos simples e eficazes diretamente no código.

---

## 🛠️ Tecnologias Utilizadas

- **[Python](https://www.python.org/)**: Linguagem base do projeto.
- **[Streamlit](https://streamlit.io/)**: Framework utilizado para construir todo o front-end web de forma ágil.
- **[Gspread](https://docs.gspread.org/)**: Biblioteca Python responsável pela comunicação direta com a API do Google Sheets.
- **[Pandas](https://pandas.pydata.org/)**: Essencial para manipulação dos dados extraídos da planilha, facilitando filtros e buscas avançadas.
- **[OAuth2Client](https://oauth2client.readthedocs.io/)**: Gerenciamento da autenticação segura com os servidores do Google.

---

## 💻 Como Executar Localmente

### Pré-requisitos
- Python instalado na máquina.
- Uma conta de serviço do Google Cloud (GCP) com acesso à API do Google Sheets e do Google Drive.
- O arquivo `.json` com suas chaves privadas do GCP.

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git](https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git)
   cd NOME_DO_REPOSITORIO
