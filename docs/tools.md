# Ferramentas da NOVA

NOVA conta com mais de 40 ferramentas registradas nativamente, organizadas por categorias de permissão e nível de risco.

## Categorias

### 1. Percepção e Visão (`category="vision"`)
- `screen.screenshot`: Captura JPEG da tela inteira (resiliente com multi-tier fallback MSS/ImageGrab/Canvas).
- `vision.describe_screen`: Envia screenshot para o modelo de visão responder perguntas sobre a tela.
- `vision.read_text`: Extrai todo o texto legível da interface.
- `vision.find_element`: Localiza elementos visuais na tela (botões, campos, ícones) e retorna coordenadas (x, y).

### 2. Controle do Computador (`category="computer"`)
- `computer.mouse_move`: Move o cursor para (x, y).
- `computer.click`: Clica em (x, y) com botão (left/right/middle) e contagem de cliques.
- `computer.drag`: Arrasta de (x1, y1) para (x2, y2).
- `computer.scroll`: Rola a roda do mouse (positivo para cima, negativo para baixo).
- `computer.type`: Digita texto no teclado.
- `computer.press_key`: Pressiona uma tecla individual (enter, esc, tab, f5...).
- `computer.hotkey`: Pressiona combinação de teclas (ex: `['ctrl', 'shift', 't']`).
- `window.list`: Lista todas as janelas abertas com título e PID.
- `window.focus`: Traz uma janela para o primeiro plano.
- `window.minimize`: Minimiza uma janela.
- `window.maximize`: Maximiza uma janela.
- `window.close`: Fecha uma janela.

### 3. Aplicativos (`category="apps"`)
- `apps.open`: Abre um aplicativo (ex: Discord, VS Code, Bloco de Notas, Chrome).
- `apps.list_installed`: Lista aplicativos comuns instalados no Windows.

### 4. Sistema de Arquivos (`category="fs"`)
- `fs.list`: Lista arquivos e subdiretórios de um caminho.
- `fs.read`: Lê conteúdo textual de um arquivo.
- `fs.write`: Grava conteúdo em um arquivo.
- `fs.copy`: Copia arquivo de origem para destino.
- `fs.move`: Move/renomeia arquivo.
- `fs.delete`: Exclui arquivo (sempre exige confirmação do usuário).

### 5. Terminal e Linha de Comando (`category="terminal"`)
- `terminal.execute`: Executa comando no PowerShell ou CMD com classificação automática de segurança (SAFE / WARNING / DANGEROUS).

### 6. Navegação e Web (`category="web"`)
- `web.search`: Pesquisa na internet via DuckDuckGo, Tavily ou Brave Search.
- `browser.open`: Abre uma URL no navegador automatizado (Playwright).
- `browser.click`: Clica em seletor CSS no navegador.
- `browser.type`: Digita em campo de formulário web.
- `browser.extract_text`: Extrai texto estruturado da página aberta.
- `browser.screenshot`: Captura screenshot da página web atual.

### 7. Voz e Áudio (`category="voice"`)
- `voice.speak`: Fala texto em voz alta via Windows SAPI / autofala.
- `voice.status`: Retorna estado dos sintetizadores e microfone.

### 8. Dispositivos Externos (`category="devices"`)
- `device.list`: Lista dispositivos disponíveis (PC local, ESP32, celular, IoT).
- `device.status`: Consulta telemetria e estado de saúde de um dispositivo.
- `device.connect`: Conecta ao endpoint de um dispositivo externo.
- `device.send`: Envia comandos ou pacotes de dados para o dispositivo.

### 9. Memória e Procedimentos (`category="memory"`)
- `memory.remember`: Guarda fato ou preferência na memória de longo prazo.
- `memory.recall`: Busca fatos salvos por palavras-chave.
- `memory.save_procedure`: Grava rotina ou procedimento operacional de múltiplos passos.
- `memory.get_procedure`: Recupera instruções passo a passo de um procedimento salvo.
