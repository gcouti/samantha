# 🏗️ Arquitetura do Sistema Samantha

Samantha é uma assistente virtual inteligente, multicanal e extensível, construída sobre uma **arquitetura de microsserviços** e um **núcleo NLP multi‑agente**.  
A arquitetura atual foi simplificada e atualizada para refletir:

- Uso de **LLMs multi‑provider** (OpenAI, Gemini, Claude) via Strategy Pattern  
- Núcleo NLP em `ms-nlp-processor` com **agentes especializados + ferramentas**  
- Orquestração opcional via **LangFlow** e **LangGraph**  
- Remoção de módulos/agents antigos (ex: `greeting_agent`, `task_agent`, `weather_agent`, `llm_integration.py`, `langgraph_integration.py`)

---

## 1. 📂 Visão Geral de Pastas (Relevante)

```text
/data/dev/samantha
├─ main.py
├─ README.md
├─ .windsurf/
│  ├─ samantha.md
│  └─ arquitecture.md   ← ESTE DOCUMENTO
└─ services/
   ├─ ms-nlp-processor/
   │  ├─ app.py
   │  ├─ requirements.txt
   │  ├─ .env.example
   │  └─ src/
   │     ├─ api.py
   │     ├─ processor.py
   │     ├─ llm_providers.py
   │     ├─ llm_managers.py
   │     ├─ agents/
   │     │  ├─ __init__.py
   │     │  ├─ base_agent.py
   │     │  ├─ general_agent.py
   │     │  ├─ langflow_agent.py
   │     │  └─ tool_agent.py
   │     └─ tools/
   │        ├─ __init__.py
   │        ├─ base_tool.py
   │        ├─ shell_tool.py
   │        └─ weather_tool.py
   ├─ ms-cli-interface/           (não detalhado aqui)
   ├─ ms-external-data/           (não detalhado aqui)
   ├─ ms-nlp-processor/           ← FOCO ATUAL
   └─ ms-task-scheduler/          (não detalhado aqui)
```


## 2. 🌐 Camada de Interfaces (Canais / Front‑ends)

Esta camada continua sendo composta por adaptadores/microsserviços específicos (WhatsApp, Slack, e‑mail, etc.), que **não são detalhados neste documento**, mas possuem um papel claro:

- Recebem mensagens dos usuários
- Normalizam em um payload de texto + metadados
- Chamam o serviço `ms-nlp-processor` via HTTP (FastAPI) no endpoint `/process`

---

## 3. 🧠 Núcleo NLP: `ms-nlp-processor`

O serviço **ms-nlp-processor** é o cérebro conversacional da Samantha:

- Expõe uma API HTTP (FastAPI) em `src/api.py`
- Orquestra agentes e ferramentas em `src/processor.py`
- Usa múltiplos provedores LLM através de Strategy Pattern:
  - OpenAI, Gemini, Claude (e extensível para outros)

### 3.1 API (`src/api.py`)

Principais endpoints:

- `POST /process`
  - Request:  
    - `text`: texto do usuário  
    - `context`: dicionário opcional de contexto  
    - `thread_id`: ID de conversa (para workflows com estado, ex: LangGraph)
  - A API **não decide mais qual engine usar**.  
    Ela delega tudo para `NLPProcessor.process_text`, que decide internamente.
- `GET /agents`
  - Lista dinamicamente os agentes presentes em `src/agents/`  
  - Ignora `__init__.py` e `base_agent.py`  
  - Faz import dinâmico para extrair `description` de cada agente.
- `GET /flows`
  - Lista fluxos disponíveis do LangFlow (quando configurado).
- `GET /health`
  - Indica se LLM, LangFlow e LangGraph estão disponíveis.
- `GET /conversation/{thread_id}`
  - Retorna histórico de conversas quando LangGraph está em uso.

### 3.2 Processor (`src/processor.py`)

`NLPProcessor` é o orquestrador central.  
Responsabilidades:

- Inicializar **LLMManager**, **LangFlowManager** e **LangGraphManager**
- Montar a cadeia de agentes:

  ```text
  ToolAgent → GeneralAgent → LangFlowAgent → UnknownAgent
  ```

- Método principal:

  ```python
  async def process_text(self, text: str, thread_id: str = "default") -> Dict[str, Any]
  ```

  - (Neste momento) está **forçado** a usar `"llm_agents"` como método principal  
    (há um TODO para reativar seleção inteligente de `llm_agents` / `langflow` / `langgraph`)
  - Processa:
    1. Classificação de intenção + entidades (via LLMManager)
    2. Passagem pela cadeia de agents
    3. Retorno de resposta + metadados (intent, agent, confidence, etc.)

---

## 4. 🤖 Agentes (`src/agents/`)

Agentes seguem o padrão **Chain of Responsibility** (classe base `BaseAgent`).

Agentes atuais:

- `GeneralAgent`
  - Agente genérico, LLM‑powered.
  - Responde perguntas gerais, “small talk”, etc.
- `ToolAgent`
  - Agente responsável por invocar **ferramentas** (`tools/`).
  - Ex.: executar comandos de sistema seguros, buscar clima real, etc.
- `LangFlowAgent`
  - Encaminha requisições para workflows definidos no **LangFlow**.
- `UnknownAgent`
  - Fallback final quando nenhum outro agente assume.

> **Agents removidos**  
> - `GreetingAgent`, `TaskAgent`, `WeatherAgent` foram removidos.  
>   - Suas capacidades foram substituídas por LLM + `GeneralAgent` e `ToolAgent` + `WeatherTool`.

---

## 5. 🛠️ Ferramentas (`src/tools/`)

As ferramentas materializam capacidades que podem ser executadas pelos agentes (principalmente `ToolAgent`).

- `BaseTool`
  - Interface base para todas as tools.
  - Implementa:
    - Validação de parâmetros (`get_schema` + `validate_parameters`)
    - Checagem de comandos perigosos.
- `ShellTool`
  - Executa comandos de **shell seguros** (via `asyncio.subprocess`).
  - Possui whitelist de comandos permitidos e blacklist de comandos perigosos.
  - Exemplos:
    - `ls`, `pwd`, `whoami`, `df`, `free`, `grep`, etc.
- `WeatherTool`
  - Busca informações de **clima real** usando APIs externas:
    - OpenWeatherMap
    - WeatherAPI.com
    - weather.gov (fallback para EUA)
  - Substitui completamente o antigo `WeatherAgent`.
- `ToolManager`
  - Registra ferramentas (`ShellTool`, `WeatherTool`, etc.)
  - Fornece:
    - `execute_tool(name, params)`
    - `list_tools()`
    - `get_tool_schemas()`

`ToolAgent` usa `ToolManager` + LLM (`LLMManager`) para:

1. Entender a intenção do usuário
2. Escolher a tool apropriada
3. Definir parâmetros
4. Executar a tool
5. Traduzir o resultado em resposta natural em português

---

## 6. 🧬 LLM Multi‑Provider (`src/llm_providers.py` + `src/llm_managers.py`)

### 6.1 Strategy Pattern de Provedores (`llm_providers.py`)

- `LLMProvider` (Enum):
  - `OPENAI`, `GEMINI`, `CLAUDE`
- `LLMConfig`:
  - Modelo, temperatura, max_tokens, api_key (carregada de env)
- `BaseLLMProvider`:
  - Interface abstrata (`generate_response`, `is_available`)
- Implementações:
  - `OpenAIProvider`
  - `GeminiProvider`
  - `ClaudeProvider`
- `LLMProviderFactory`:
  - Cria instâncias de providers
  - Descobre quais provedores estão disponíveis com base em:
    - libs instaladas
    - variáveis de ambiente (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `CLAUDE_API_KEY`)

### 6.2 LLMManager + LangGraphManager (`llm_managers.py`)

- `LLMManager`
  - Usa providers do `LLMProviderFactory` com **fallback automático**.
  - Exposto para:
    - Classificar intenção (`classify_intent`)
    - Selecionar agente (`select_agent`)
    - Gerar respostas (`generate_response`)
- `LangFlowManager`
  - Cliente para chamar APIs do LangFlow (`/api/v1/run/{flow_id}`, `/api/v1/flows`).
- `LangGraphManager`
  - Implementa workflows com **LangGraph**:
    - Nodes:
      - `classify_intent`
      - `select_agent`
      - `process_with_agent`
      - `generate_response`
    - Usa `LLMManager` internamente (não depende mais de `langgraph_integration.py` antigo).
  - Fornece:
    - `process_text(text, thread_id)`
    - `get_conversation_history(thread_id)`

---

## 7. 🔐 Configuração & Dependências

### 7.1 `.env.example` (ms-nlp-processor)

- Provedores LLM:
  - `OPENAI_API_KEY`
  - `GEMINI_API_KEY`
  - `CLAUDE_API_KEY`
- Clima:
  - `OPENWEATHER_API_KEY`
  - `WEATHERAPI_KEY`
- LangFlow:
  - `LANGFLOW_URL`
- Serviço:
  - `SERVICE_HOST`, `SERVICE_PORT`
- Preferência de LLM:
  - `PREFERRED_LLM_PROVIDER = openai | gemini | claude`

### 7.2 `requirements.txt` (ms-nlp-processor)

Inclui, entre outros:

- `fastapi`, `uvicorn`, `pydantic`, `python-dotenv`, `aiohttp`
- `langchain`, `langchain-openai`, `langchain-google-genai`, `langchain-anthropic`
- `langgraph`, `openai`, `google-generativeai`, `anthropic`

---

## 8. 🧩 Resumo da Arquitetura Atual

- Arquitetura **multi‑agente + multi‑LLM** com microsserviços.
- `ms-nlp-processor` centraliza:
  - LLM multi‑provider (OpenAI/Gemini/Claude) com Strategy + Factory
  - Agentes (General, Tool, LangFlow, Unknown)
  - Tools (Shell, Weather, etc.)
  - Orquestração opcional com LangFlow e LangGraph.
- Agentes antigos baseados em regras (saudação, tarefa, clima) foram **removidos** em favor de:
  - LLM + GeneralAgent
  - Tools (WeatherTool) + ToolAgent

Esta é a **foto atual** da arquitetura da Samantha, refletindo apenas o que existe hoje no código, sem referências a pastas/módulos apagados.

