# 🏗️ Arquitetura do Sistema Samantha

Samantha é uma assistente virtual inteligente, multicanal e extensível, construída sobre uma **arquitetura de microsserviços** e um **núcleo NLP multiagente**.  
A arquitetura atual reflete:

- Uso de **LLMs multi‑provider** (OpenAI, Gemini, Claude) via Strategy Pattern.  
- Núcleo NLP em `ms-nlp-processor` operando com **LangGraph** e integração opcional com **LangFlow**.  
- Clientes e conectores independentes, como a CLI interativa (`ms-cli-interface`).  
- Scripts de infraestrutura para provisionamento rápido (ex.: criação de usuários).  

> Sempre que o ambiente Python precisar ser usado manualmente, ative o virtualenv: `source .venv/bin/activate`.

---

## 1. 📂 Visão Geral de Pastas

```text
/data/dev/samantha
├─ main.py                      # Script raiz que delega para a CLI
├─ README.md
├─ docs/                        # Reservado para documentação complementar
├─ infrastructure/
│  └─ create_user.py            # Script para provisionar contas no banco local
├─ services/
│  ├─ ms-cli-interface/
│  │  ├─ app.py                 # Entrada assíncrona da CLI
│  │  ├─ README.md
│  │  └─ src/
│  │     ├─ config.py           # Configurações e .env da CLI
│  │     └─ nlp_client.py       # Cliente HTTPX para o ms-nlp-processor
│  └─ ms-nlp-processor/         # Serviço FastAPI + LangGraph (FOCO)
│     ├─ .env / .env.example
│     ├─ requirements.txt
│     ├─ Dockerfile / fly.toml / start.sh
│     └─ src/
│        ├─ api.py              # FastAPI endpoints
│        ├─ processor.py        # `NLPProcessor`
│        ├─ main.py             # Entrypoint Uvicorn
│        ├─ auth.py / security.py
│        ├─ llm_providers.py
│        ├─ llm_managers.py
│        ├─ agents/
│        ├─ tools/
│        └─ database/
└─ .windsurf/                   # Documentação viva (este arquivo + samantha.md)
```

**Pastas não utilizadas** (`docs/`, futuros microsserviços) permanecem reservadas para expansão.

---

## 2. 🧩 Tipos de Sistemas e Canais

1. **Interfaces de usuário (front-ends / canais):** bots de WhatsApp, Slack, e-mail ou webhooks externos. Cada canal converte mensagens para um payload HTTP e chama `ms-nlp-processor`.  
2. **Cliente oficial (ms-cli-interface):** terminal interativo com feedback colorido, autenticação simplificada e histórico local.  
3. **Núcleo cognitivo (ms-nlp-processor):** FastAPI + LangGraph. É onde vivem agentes, ferramentas, gerenciadores LLM e bancos.  
4. **Scripts de infraestrutura:** utilitários Python (ex.: `infrastructure/create_user.py`) para preparar dados locais.

---

## 3. 💬 Cliente CLI (`services/ms-cli-interface`)

- `app.py`: inicializa `SamanthaCLI`, controla sinais, imprime painéis Rich e coleta entradas com `prompt_toolkit`.  
- `src/nlp_client.py`: cliente `httpx.AsyncClient` que chama `POST /process`, injeta cabeçalhos `Authorization` + `X-User-Email` quando necessário.  
- `src/config.py`: centraliza variáveis (`NLP_SERVICE_URL`, `CLI_TIMEOUT`, etc.) lidas do `.env`.  
- Execução via `python -m services.ms-cli-interface --email ...` ou `python main.py` (delegando para `app.main()`).

---

## 4. 🧠 Núcleo NLP (`services/ms-nlp-processor`)

### 4.1 Estrutura principal

- `src/api.py`: FastAPI com middlewares (CORS + sessões) e endpoints `/process`, `/agents`, `/flows`, `/health`, `/conversation/{thread_id}`, além dos fluxos de autenticação Google/Gmail.  
- `src/processor.py`: instancia `LLMManager`, `LangFlowManager` e `LangGraphManager`. Atualmente força o método `"langgraph"` até que a seleção automática seja reativada.  
- `src/llm_providers.py`: Strategy + Factory para conectar OpenAI, Gemini e Claude (cada provider declara `generate_response`, `is_available`, etc.).  
- `src/llm_managers.py`: ponto mais rico; define `LLMManager`, `LangFlowManager` e `LangGraphManager` (com o grafo de estados, agentes e integração com ferramentas).  
- `src/database/`: SQLAlchemy (`database.py`, `models.py`, `crud.py`) e SQLite embutido (`samantha_users.db`) para armazenar contas e `notes_path`.  
- `auth.py` + `security.py`: geração/validação de JWTs, configuração OAuth (Google/Apple) e helpers para extrair o e-mail autenticado.

### 4.2 API (`src/api.py`)

- `POST /process`: recebe `text`, `context`, `thread_id` e `email` opcional.  
  - Valida JWT via `get_current_user_email` e compara com o corpo.  
  - Chama `await nlp_processor.process_text(...)` e devolve `ProcessResponse` com `metadata` detalhado (intent, entities, método, etc.).  
- `GET /agents`: usa `agents.utils.collect_agent_descriptions` para inspecionar dinamicamente os arquivos em `src/agents/`.  
- `GET /flows`: lista fluxos disponíveis no LangFlow (quando `LANGFLOW_URL` está configurado).  
- `GET /health`: status geral (LLM, LangFlow, LangGraph).  
- `GET /conversation/{thread_id}`: histórico baseado na memória do LangGraph (`MemorySaver`).  
- Endpoints auxiliares: `/gmail/login`, `/gmail/callback`, `/test-token/{email}`, etc., que dependem de `tools.gmail_tool`.

### 4.3 Processor & Managers

- `NLPProcessor.process_text(text, thread_id, email)`  
  - (temporário) `processing_method = "langgraph"`.  
  - Redireciona para `LangGraphManager.process_text`, que constrói o estado inicial (`AgentState`) com mensagens, email e metadados.  
- `LangGraphManager`  
  - Monta um `StateGraph` com nós: `check_user`, `orchestrator_agent`, `general_agent`, `tools`, `configuration_node`, `handle_notes_path_update_node`, `authentication_required_node`, `wait_for_input_node`.  
  - Usa `MemorySaver` para checkpoints e permite `get_conversation_history`.  
  - Faz binding de ferramentas ao provider atual (`llm_with_tools = provider.client.bind_tools(...)`).  
- `LLMManager`  
  - Responsável por invocar diretamente o provider preferido (fallback automático) quando o fluxo dispensa LangGraph.  
- `LangFlowManager`  
  - Cliente `aiohttp` para executar flows em servidores LangFlow externos (`/api/v1/run/{flow_id}`), retornando metadados quando flows estão disponíveis.

### 4.4 Agentes (`src/agents/`)

| Arquivo | Papel |
| --- | --- |
| `base_agent.py` | Classe abstrata com `can_handle`, `handle`, encadeamento e sanitização de JSON. |
| `general_agent.py` | Agente default; usa o provider atual (com ferramentas bindadas) para responder mensagens e decidir tool calls. |
| `orchestrator_agent.py` | Descreve os agentes disponíveis e decide qual caminho seguir (general, calendar, websearch, email, etc.). Ele prepara prompts ricos para o LangGraph. |
| `configuration_agent.py` | Pergunta ou confirma configurações essenciais (ex.: `notes_path`). |
| `utils.py` | Descobre agentes e ferramentas dinamicamente para exposição via API. |

> Agentes antigos (`ToolAgent`, `LangFlowAgent`, etc.) foram removidos. Hoje a orquestração acontece no LangGraph usando `GeneralAgent` + ferramentas bindadas.

### 4.5 Ferramentas (`src/tools/`)

- `base_tool.py`: helpers de validação e saneamento.  
- `shell_tool.py`: execução controlada de comandos whitelisted (`ls`, `pwd`, `df`, etc.).  
- `weather_tool.py`: integra OpenWeatherMap, WeatherAPI e weather.gov como fallback.  
- `gmail_tool.py`: fluxo OAuth, listagem e busca de e-mails via Gmail API (usado pela API e pelo LangGraph).  
- `web_search_tool.py`: busca web (LangChain integração).  
- `note_tool.py`: `ObsidianGitHubTool` para ler/anotar notas num repositório GitHub; requer que o usuário informe `notes_path`.  
- `tool_manager.py`: registro/execução das ferramentas (mantido para usos diretos); o LangGraph utiliza `ToolNode` com as mesmas funções.

### 4.6 Banco e Autenticação

- `database/models.py`: modelo `Account` (id, email, notes_path).  
- `database/crud.py`: helpers `get_user_by_email`, `update_user_notes_path`.  
- `infrastructure/create_user.py`: script CLI que chama `init_db()` e insere contas (útil para testes locais).  
- `auth.py` / `security.py`:  
  - `create_access_token`, `verify_jwt_token`, integrações OAuth (Google/Apple).  
  - `get_current_user_email` garante o e-mail extraído do token.  
  - Em ambiente *dev*, tokens `email@example.com:any` são aceitos para facilitar a CLI.

---

## 5. 🛠️ Scripts e Documentação de Suporte

- `infrastructure/create_user.py`: provisiona usuários e já configura `notes_path`.  
- `.windsurf/samantha.md`: guia operacional (roadmap, ideação).  
- `docs/`: reservado para guias futuros (atualmente vazio).  
- `README.md` (raiz): visão geral do produto e roadmap de features (integrável com calendar, web search, notas, etc.).

---

## 6. 🔗 Funções e Componentes Importantes

| Área | Função / Método | Descrição rápida |
| --- | --- | --- |
| API | `process_text` (`src/api.py`) | Endpoint principal, valida headers, chama `NLPProcessor`, retorna `ProcessResponse`. |
| Processamento | `NLPProcessor.process_text` (`src/processor.py`) | Seleciona o método (`langgraph`, `langflow`, `llm`) e delega execução. |
| LangGraph | `LangGraphManager.process_text` (`src/llm_managers.py`) | Constroi `AgentState`, executa `StateGraph`, agrega mensagens/ferramentas e devolve resposta final. |
| LangGraph Nodes | `_check_user_node`, `_configuration_router`, `_handle_notes_path_update_node` | Garantem autenticação, coleta de configuração (ex.: GitHub notes) e atualizam o banco. |
| Agentes | `GeneralAgent.handle`, `OrchestratorAgent.handle` | O primeiro conversa diretamente com o usuário/LLM; o segundo decide qual capacidade melhor responde. |
| Ferramentas | `ShellTool.execute`, `WeatherTool.get_weather`, `GmailTool.search_gmail_dynamic`, `ObsidianGitHubTool.read_note` | Capacidades externas invocadas via LangGraph/LLM. |
| Segurança | `create_access_token` (`auth.py`), `verify_jwt_token` (`security.py`) | Geração e verificação de JWTs usados pela CLI e pelo serviço HTTP. |
| Banco | `get_user_by_email`, `update_user_notes_path` (`database/crud.py`) | Persistem preferências como repositório de notas. |

---

## 7. 🧩 Resumo

- Arquitetura **multiagente + multi‑LLM**, com LangGraph como orquestrador padrão.  
- `ms-nlp-processor` concentra endpoints HTTP, agentes, ferramentas e integrações externas (Gmail, WebSearch, GitHub/Obsidian, clima, shell).  
- `ms-cli-interface` fornece um cliente oficial simples e autenticado para testes locais ou demonstrações.  
- Scripts de infraestrutura garantem bootstrap rápido (criação de usuários, configuração de notas).  
- Documentação viva mantém o inventário de pastas, tipos de sistemas e funções críticas atualizados, servindo como referência central para evolução da Samantha.

