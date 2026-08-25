# Arquitetura da NOVA

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DESKTOP (pywebview/WebView2 / Browser SPA)           │
│   Frontend SPA (ES modules + Web Speech) ── HTTP/WS ──► Backend FastAPI │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
        ┌───────────────┬────────────┼────────────┬─────────────┬─────────────┐
        ▼               ▼            ▼            ▼             ▼             ▼
    ChatRunner      NovaAgent    TaskManager   EventBus    VoiceManager  DeviceManager
        │               │            │            │             │             │
        └───────► ContextBuilder    │            ├── confirm   ├── Windows   ├── Local PC
                (system prompt +    │            ├── tool_call │   SAPI TTS  ├── ESP32
                 histórico DB +     │            ├── task_upd  └── WebSpeech ├── Mobile
                 memórias)          │            └── emergency               └── IoT
                                    │
                           ToolExecutor ──► ToolRegistry (40+ tools)
                                │
                    PermissionManager → ConfirmationService → AuditLog
```

## Fluxo do Agente (Loop Autônomo)

1. `ChatRunner.start_chat(text)` persiste a mensagem do usuário, cria uma **Task** e dispara o agente em uma `asyncio.Task`.
2. A cada iteração, `ContextBuilder` monta as mensagens: system prompt (identidade, regras, política de conteúdo não-confiável) + histórico do banco + memórias relevantes + notas de runtime.
3. O LLM responde com texto final OU `tool_calls`.
4. Cada tool call passa pelo `ToolExecutor`: validação de args → `stop_event` → gate de permissão (auto / confirmação via UI / negado) → execução com timeout → resultado estruturado `{success, data|error, recoverable}` → auditoria.
5. Resultados voltam como mensagens `role:"tool"` para a próxima iteração.
6. **Detecção de loop**: contador de `(tool, args)` idênticos; após N repetições injeta nota de aviso e depois aborta com explicação.
7. Sem tool calls = resposta final → tarefa `completed`, evento `chat_final`, síntese de voz (TTS) opcional.

## Camadas

| Camada | Módulo | Responsabilidade |
|---|---|---|
| Interface | `frontend/`, `run.py` | SPA escura estilizada (Outfit/JetBrains Mono) + janela nativa WebView2 |
| API | `backend/app/api/` | REST (`/api/*`) + WebSocket (`/ws`) |
| Agente | `backend/app/agent/` | Loop principal, subagentes especializados, contexto, prompts, TaskManager |
| Tools | `backend/app/tools/` | Registry, executor, builtin tools (visão, mouse, teclado, winman, terminal, browser, voz, dispositivos, memória) |
| Percepção | `backend/app/tools/builtin/screen.py` | Captura multi-camada (MSS -> ImageGrab -> Canvas), OCR e detecção de elementos de UI |
| Voz | `backend/app/voice/` | Windows SAPI TTS, transcrição de áudio, push-to-talk, cancelamento instantâneo |
| Dispositivos | `backend/app/devices/` | DeviceManager, drivers para Local PC, ESP32, Mobile e IoT |
| Segurança | `backend/app/security/`, `audit/` | Permissões (10 categorias), confirmações, classificador SAFE/WARNING/DANGEROUS, auditoria |
| Memória | `backend/app/memory/` | Curto prazo, conversação, longo prazo, memória procedural (procedimentos aprendidos) |
| LLM | `backend/app/llm/` | Cliente compatível com Ollama Cloud (MiniMax M3), OpenAI, OpenRouter, Groq com failover |
| Plugins | `plugins/`, `backend/app/plugins/` | Plugins com manifesto `plugin.json` carregados dinamicamente |

## Decisões Técnicas

- **FastAPI + WebSocket**: eventos push (confirmações, progresso de tasks, logs, voz) exigem canal duplex; REST fica para consultas.
- **Captura Resiliente de Tela**: Fallback multi-nível (MSS -> PIL ImageGrab -> Canvas virtual de tela) garante que a NOVA nunca quebre em sessões remotas, bloqueadas ou CI.
- **Subagentes Especializados**: `BaseAgent` serve como alicerce para agentes focados em pesquisa, automação desktop, codificação e hardware IoT.
- **Voz Integrada**: Suporte direto a Windows SAPI para fala sem dependência externa, mais Web Speech API no navegador.
- **Procedural Memory**: Permite gravar e consultar receitas operacionais passo a passo no banco de dados SQLite.
