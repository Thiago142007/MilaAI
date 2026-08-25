# Sistema de Memória da NOVA

NOVA implementa um sistema de memória em camadas:

```
┌────────────────────────────────────────────────────────┐
│                   SISTEMA DE MEMÓRIA                   │
├───────────────────┬────────────────────────────────────┤
│ SHORT TERM        │ Contexto imediato da iteração      │
│ CONVERSATION      │ Histórico completo das mensagens   │
│ LONG TERM         │ Fatos e preferências persistentes  │
│ PROCEDURAL        │ Procedimentos e rotinas aprendidas │
│ TASK MEMORY       │ Estado e passos das tarefas ativas │
└───────────────────┴────────────────────────────────────┘
```

## Memória Procedural (Procedural Memory)

Permite que a NOVA aprenda e guarde rotinas operacionais (ex: "como abrir e configurar o servidor Minecraft", "como debugar e compilar o projeto X").

### Estrutura de Procedimento
```json
{
  "name": "iniciar_servidor_minecraft",
  "description": "Rotina para iniciar o servidor local de Minecraft",
  "steps": [
    "Abrir terminal no diretório do servidor",
    "Executar java -Xmx4G -jar server.jar nogui",
    "Aguardar log 'Done' aparecer no console"
  ]
}
```

## Filtros e Consultas
- API: `GET /api/memory?kind=procedure`, `GET /api/memory/procedures`
- Tools: `memory.save_procedure`, `memory.get_procedure`, `memory.remember`, `memory.recall`
- Na interface: aba **Memory** com abas dedicadas para Fatos, Preferências do Usuário e Procedimentos.
