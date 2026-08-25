# Plugins

Plugins adicionam ferramentas **sem modificar o núcleo**. O loader
(`backend/app/plugins/loader.py`) escaneia `plugins/*/` no boot.

## Estrutura

```
plugins/
  meu-plugin/
    plugin.json     # manifesto
    plugin.py       # código
```

`plugin.json`:

```json
{
  "name": "meu-plugin",
  "version": "1.0.0",
  "description": "Faz algo útil",
  "permissions": ["WEB", "TERMINAL"]
}
```

`plugin.py` precisa expor:

```python
def register(registry, ctx=None):
    # ctx.plugin_name, ctx.plugin_permissions disponíveis
    registry.register(Tool(...))
```

Um exemplo funcional está em `plugins/example/`.

## Regras

- Erros de plugin são logados e não derrubam a NOVA (boot continua).
- As permissões declaradas no manifesto são aplicadas normalmente pelo executor.
- Dependências externas do plugin: instale no venv do projeto e documente no README do plugin.

## Roadmap de plugins planejados

| Pasta | Ideia |
|---|---|
| discord/ | tools via bot token (ler/enviar mensagens) |
| minecraft/ | gerenciar servidor local (start/stop/log tail) |
| vscode/ | abrir workspace, ler problemas via CLI |
| obs/ | controle via websocket oficial do OBS |
