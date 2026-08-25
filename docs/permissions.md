# Permissões e Confirmações

## Categorias

```
SCREEN_READ  FILE_READ  FILE_WRITE  FILE_DELETE  TERMINAL
WEB  MOUSE_CONTROL  KEYBOARD_CONTROL  APPLICATION_CONTROL  DEVICE_CONTROL
```

Cada tool declara as categorias que precisa. O gate acontece dentro do `ToolExecutor`, sempre.

## Modos de autonomia

| Modo | Auto-permitido | Precisa confirmação |
|---|---|---|
| MANUAL | SCREEN_READ, FILE_READ | todo o resto |
| ASSISTED | + WEB, MOUSE_CONTROL, KEYBOARD_CONTROL | FILE_WRITE, FILE_DELETE, TERMINAL, APPLICATION_CONTROL, DEVICE_CONTROL |
| AUTONOMOUS | tudo, exceto... | FILE_DELETE (sempre), terminal DANGEROUS (sempre) |

Troque no seletor do topo da UI (`set_mode` via WS) ou `POST /api/permissions/mode`.

## Grants (liberações pontuais)

Quando a UI mostra `[Permitir uma vez]` / `[Permitir para esta tarefa]`:

- `allow_once`: vale para a execução imediata
- `allow_task`: gravado na tabela `grants(scope='task', task_id=...)` - válido só naquela tarefa
- Sessão: `POST /api/permissions/grant {category, scope:"session"}` - até reiniciar

`FILE_DELETE` ignora grants e modos: sempre confirmação explícita.

## Classificação de comandos de terminal

`safety.classify_command()` aplica regex sobre o comando:

- **DANGEROUS**: `rm -rf`, `del /s`, `format X:`, `shutdown`, `reg delete/add`, `Remove-Item -Recurse -Force`, `diskpart`, `cipher /w`, `vssadmin delete shadows`, ...
- **WARNING**: `del`, `taskkill`, `pip install`, `git push/reset --hard`, `curl`, `iex/-encodedcommand`, `setx`, `schtasks`, ...
- **SAFE**: todo o resto (leituras)

DANGEROUS exige confirmação mesmo em modo autonomous.

## Auditoria

Todo evento relevante vai para `audit_log` (tela Logs → aba Auditoria):

```
ts | category | action | detail(JSON)
```

Detalhes passam por `redact_secrets()` antes de gravar: padrões `sk-…`, `ghp_…`, `Bearer …`,
`password=/senha=/token=` viram `[REDACTED]`. A mesma redação é aplicada aos logs de runtime.

## Emergency Stop

Três gatilhos equivalentes:
1. botão **STOP NOVA** na barra inferior;
2. hotkey global `Ctrl+Alt+Shift+X` (configurável em `.env`);
3. `POST /api/emergency-stop` / WS `{"type":"emergency_stop"}`.

Efeito: cancela todas as coroutines do agente, o `stop_event` faz novas tools serem recusadas,
status vira EMERGENCY STOP até `reset-emergency`.
