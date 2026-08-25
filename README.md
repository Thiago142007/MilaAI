# 🌸 Mila AI — Autonomous Multimodal 3D VTuber AI Assistant for Windows

<div align="center">

![Mila AI](https://img.shields.io/badge/Mila-3D%20VTuber%20AI-ff69b4?style=for-the-badge&logo=three.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?style=for-the-badge&logo=typescript&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-Express%20%2B%20WS-green?style=for-the-badge&logo=node.js&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TTS](https://img.shields.io/badge/Kokoro--82M-100%25%20Local%20TTS-purple?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

<p align="center">
  <b>Uma assistente de IA autônoma e companheira 3D VTuber interativa para Windows.</b><br>
  Conversação por voz neural local, percepção visual da tela, automação completa de mouse/teclado, memória procedural e renderização 3D em tempo real.
</p>

</div>

---

## ✨ Principais Funcionalidades

### 🎭 1. Avatar 3D VTuber Interativo (WebGL / Three.js)
- **Modelo 3D em Alta Definição:** Renderizado com Three.js e shaders otimizados (*PBR Shading, ACES Filmic Tone Mapping e sRGB Encoding*).
- **Rastreamento de Cursor em Tempo Real:** A cabeça e os olhos da Mila seguem suavemente a posição do cursor do mouse.
- **Física Secundária Procedural:** Respiração natural, balanço suave de cabelo e animação dinâmica de cauda.
- **Sincronia Labial (*Lip-Sync*):** Abertura e fechamento de boca sincronizados perfeitamente com o áudio falado.
- **Expressões Faciais:** Reações visuais em tempo real para estados de raciocínio, fala, escuta e surpresa.

### 🎙️ 2. Síntese de Voz Neural 100% Local (Kokoro-82M)
- **Zero Custo de API Externa:** Geração de voz neural de altíssima fidelidade rodando 100% localmente no seu computador via ONNX Runtime.
- **Voz Brasileira Natural:** Voz padrão `pf_dora` (Português do Brasil) + mais de 50 vozes adicionais disponíveis (Inglês, Espanhol, Francês, Japonês, etc.).
- **Carregamento Otimizado:** Modelo mantido residente em memória com suporte a aceleração por hardware (CUDA / CPU) e cache inteligente.
- **Fallback Automático:** Sistema de contingência com Web Speech API caso a reprodução de áudio seja pausada pelo navegador.

### 🧠 3. Agente de IA Autônomo e Multimodal
- **Loop de Decisão Contínuo:** `OBSERVAR → ENTENDER → PLANEJAR → EXECUTAR → VALIDAR → FINALIZAR`.
- **Percepção Visual da Tela:** Captura screenshots da sua área de trabalho e analisa elementos de interface, janelas, botões e mensagens de erro via visão computacional multimodal.
- **Memória em Múltiplas Camadas:**
  - *Memória de Curto Prazo:* Contexto ativo da conversa.
  - *Memória de Longo Prazo:* Fatos e preferências do usuário lembrados entre sessões.
  - *Memória Procedural:* Registro de rotinas e procedimentos operacionais aprendidos.

### ⚡ 4. Automação Completa do Windows
- **Controle de Mouse e Teclado:** Cliques, digitação, atalhos globais e movimentação de cursor.
- **Gerenciamento de Janelas:** Listagem de janelas abertas, foco e encerramento de processos.
- **Terminal Seguro:** Execução de comandos no PowerShell com captura estruturada de saída e tratamento de erros.
- **Gerenciamento de Arquivos:** Leitura, criação, edição e exclusão de arquivos no sistema.
- **Pesquisa na Web:** Pesquisa em tempo real para obter informações atualizadas da internet.
- **Integração com Dispositivos Externos:** Conexão com ESP32, dispositivos IoT e celulares.

### 🛡️ 5. Segurança e Parada de Emergência
- **3 Modos de Autonomia:** `manual` (solicita confirmação para tudo), `assisted` (executa ações comuns e pede confirmação para ações críticas) e `autonomous`.
- **Botão de Emergência:** Atalho global **`Ctrl + Alt + Shift + X`** para interromper imediatamente qualquer ação do agente, liberar periféricos e silenciar o áudio.

---

## 🏗️ Estrutura do Projeto

```
MilaAI/
├── src/
│   ├── client/                  # Interface Web e Motor 3D Three.js
│   │   ├── avatar/              # vrmEngine.js (Motor de renderização 3D, física e shaders)
│   │   ├── js/                  # app.js (Lógica da interface, WebSocket, áudio e fala)
│   │   ├── css/                 # Estilos Glassmorphism e tema escuro
│   │   ├── models/              # Modelos 3D (Gawr Gura / Mila) e animações FBX
│   │   └── index.html           # Página principal
│   └── server/                  # Backend Node.js / TypeScript
│       ├── agent/               # Loop autônomo do agente e gerenciador de tarefas
│       ├── control/             # Automação do Windows (mouse, teclado, janelas)
│       ├── devices/             # Gerenciamento de dispositivos externos (IoT/ESP32)
│       ├── llm/                 # Cliente LLM (Ollama, OpenAI, MiniMax, Round-Robin)
│       ├── memory/              # Gerenciador de memória de longo prazo e procedural
│       ├── perception/          # Captura e análise visual de tela
│       ├── tools/               # Registro de mais de 25 ferramentas do sistema
│       ├── voice/               # Bridge do Kokoro-82M TTS Worker
│       ├── config.ts            # Configurações e variáveis de ambiente
│       └── server.ts            # Servidor Express & WebSocket Hub
├── backend/                     # Módulos Python e Engine do Kokoro-82M
│   └── app/voice/               # Motor neural Kokoro ONNX, áudio e pré-processador
├── scripts/                     # Scripts de build, exportação de modelos e utilitários
├── INICIAR.bat                  # Executável de 1 clique para Windows
├── package.json                 # Dependências do Node.js
├── requirements.txt             # Dependências do Python
└── .env.example                 # Exemplo de configuração de ambiente
```

---

## 🚀 Como Iniciar

### 📋 Pré-requisitos
- **Windows 10 ou 11 (64-bit)**
- **Node.js 18+** ([Download](https://nodejs.org/))
- **Python 3.11+** ([Download](https://www.python.org/))

---

### ⚡ Modo 1: Inicialização em 1 Clique (Recomendado)

Basta dar um duplo clique no arquivo:
```cmd
INICIAR.bat
```
O script cuidará automaticamente de:
1. Instalar as dependências do Node.js (`npm install`).
2. Criar o ambiente virtual Python (`.venv`) e instalar as dependências de IA/Voz (`kokoro-onnx`, `soundfile`, `numpy`).
3. Criar o arquivo `.env` a partir do `.env.example` (se ainda não existir).
4. Liberar a porta `8765`.
5. Iniciar o servidor e abrir a interface 3D no seu navegador padrão (`http://127.0.0.1:8765`).

---

### 🛠️ Modo 2: Inicialização Manual

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/Thiago142007/MilaAI.git
   cd MilaAI
   ```

2. **Instale as dependências do Node.js:**
   ```bash
   npm install
   ```

3. **Configure o ambiente virtual Python:**
   ```bash
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente:**
   ```bash
   copy .env.example .env
   ```
   *Edite o arquivo `.env` e insira suas credenciais de LLM.*

5. **Inicie o servidor de desenvolvimento:**
   ```bash
   npm run dev
   ```

6. **Acesse no navegador:**
   Abra [http://127.0.0.1:8765](http://127.0.0.1:8765).

---

## ⚙️ Configurações (`.env`)

```ini
# Configurações do Servidor
NOVA_HOST=127.0.0.1
NOVA_PORT=8765

# Provedor de IA (Ollama / OpenAI / MiniMax)
NOVA_LLM_BASE_URL=https://ollama.com
NOVA_LLM_PROTOCOL=ollama
NOVA_LLM_API_KEY=sua_chave_aqui
NOVA_LLM_MODEL=minimax-m3:cloud
NOVA_LLM_VISION_MODEL=minimax-m3:cloud

# Síntese de Voz Local (Kokoro-82M)
TTS_VOICE=pf_dora
TTS_SPEED=1.0
TTS_VOLUME=1.0
TTS_DEVICE=auto
TTS_CACHE_ENABLED=true

# Autonomia e Atalhos
NOVA_AUTONOMY_MODE=assisted
NOVA_AGENT_MAX_STEPS=25
NOVA_EMERGENCY_HOTKEY=ctrl+alt+shift+x
```

---

## 🧩 Modos de Uso e Atalhos

| Atalho / Ação | Função |
|---|---|
| `Enter` | Enviar mensagem para a Mila |
| `Botão Microfone` | Reconhecimento de fala via voz (*Speech-to-Text*) |
| `Botão ⚙️ (Configurações)` | Ajustar voz do Kokoro, velocidade, volume e dispositivo de áudio |
| `Botão 🔊` | Alternar ativação de fala da assistente |
| `Ctrl + Alt + Shift + X` | **Parada de Emergência Global** (cancela tarefas e silencia áudio imediatamente) |

---

## 📄 Licença

Distribuído sob a licença **MIT**. Veja [`LICENSE`](./LICENSE) para mais informações.
