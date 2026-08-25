# Voice Subsystem (STT & TTS)

NOVA integrates speech perception and vocal response capabilities for Windows.

## Architecture

```
User Voice / Microphone
      │
      ▼
Speech To Text (Web Speech API / Audio Blob Transcribe)
      │
      ▼
NOVA Agent Reasoning & Tool Execution
      │
      ▼
Text To Speech (Windows SAPI / Browser SpeechSynthesis)
      │
      ▼
Computer Speakers
```

## Features

1. **Push-To-Talk & Voice Activation**: Click the microphone icon in the chat or hold Push-to-Talk to speak in natural Portuguese (or any configured language).
2. **Audio Wave Visualization**: Real-time visual feedback pulse when listening.
3. **Text-To-Speech (TTS)**:
   - Primary: Windows SAPI native speech synthesis via `voice.speak(text)`.
   - Frontend: Web SpeechSynthesis with language selection and rate control.
4. **Speech Interruption**: Instant cancellation via the UI "Silenciar" button or emergency stop (`Ctrl+Alt+Shift+X`).

## Tools

| Tool | Parameters | Description |
|---|---|---|
| `voice.speak` | `text: string`, `wait?: boolean` | Speaks a text message aloud through the computer speakers. |
| `voice.status` | None | Returns the status and driver availability of the voice module. |

## API Endpoints

- `GET /api/voice/status` - Checks microphone and TTS subsystem readiness.
- `POST /api/voice/tts` - Triggers speech synthesis for the given text.
- `POST /api/voice/stop` - Interrupts any ongoing vocal playback.
- `POST /api/voice/transcribe` - Transcribes an uploaded audio recording.
