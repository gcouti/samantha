# samantha

This is a python program, it is a conversational agent that can integrate tools and build a lot of things. Its structure are build to have multiple conversational interfaces, like whatsapp, slack, or any integratable chat. 

We can develop tools to initetgrate to it and execute programs and plugins

## Roadmap Features

Organizar reuniões:
* Resume os e-mails do dia
* Salva as preferencias no obsidian
  * Nome, apelido
  * Contatos: emails, telefones
  * Preferências de comunicação
  * Datas Comemorativas
  * Tempo desde a ultima conversa
  * Frequência de contato
  * Interesses e hobbies
  * Contexto de relacionamento
  * Histórico de interações
  * Preferências de comunicação
  * Estilo de comunicação
  * Nível de formalidade preferido
  * Tonelagem e humor preferidos
  * Preferências de tempo de resposta
  * Preferências de canais de comunicação
  * Preferências de frequência de contato
  * Preferências de estilo de reunião
  * Preferências de duração de reuniões     
  * Preferências de tipo de reunião (formal, informal, técnica, estratégica)
  * Preferências de objetivos de reunião
  * Preferências de estrutura de agenda
  * Preferências de pós-reunião (follow-ups, ações, relatórios)
  * Preferências de acompanhamento pós-reunião
  * Preferências de feedback pós-reunião
* Resume as anotações, separa a lista de todo's 
* Identifica responsáveis e prazos
* Não apenas cria, comunica, verifica se alguém tem algum problema com o horário e explicia o motivo daquela reunião
* Gera resumo estruturado da reunião focado nos seus interesses
* Agrupa atividades, tarefas e decisões do dia
* Gera relatório diário personalizado
* Destaca prioridades e próximos passos
* Identifica gargalos e impedimentos
* Sugere ações baseadas nos resultados
* Exporta em vários formatos (PDF, CSV, etc.)
* Integra com calendários e sistemas de gestão
* Permite compartilhamento automático com a equipe
* Armazena histórico de relatórios para referência futura
* Permite busca e filtragem por período e assunto   
* Ajuda a cobrar os responsáveis por tarefas pendentes
* Gera lembretes automáticos para prazos próximos
* Mantém controle de progresso das tarefas ao longo do tempo
* Fornece visão geral do status de todas as atividades
* Permite exportar relatórios para análise de desempenho
* Integra com ferramentas de productividade como Trello, Asana ou Notion
* Oferece relatórios personalizáveis por projeto ou período
* Permite configurar alertas e notificações personalizadas
* Permite criar templates de relatórios para padronização
* Oferece relatórios de produtividade e métricas de equipe
* Permite gerar relatórios de benchmarking de performance
* Oferece insights e sugestões baseadas em padrões de produtividade 

* ### Tipos dagente para recuperar preferencias do usuário
        # agente para verificar se a resposta final é correta
        # agente para verificar se a resposta precisa ser atualziada, se é uma pergunta que leva em consideração o tempo e a informação perece: Exemplo qual foi o resultado do jogo do galo
        # agente para verificar se precisa de mais informações para completar a resposta

### Web Search

To perform a web search, simply ask a question that requires information from the internet. The agent will automatically use the `WebSearchTool` to find the answer.

**Example:**

```
python -m services.ms-cli-interface --email your_email@example.com "Qual a capital da Australia?"
```