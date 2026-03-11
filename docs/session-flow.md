# Session Flow

```mermaid
flowchart TD
    U[Telegram user] --> C[Telegram chat\nchat_id]
    C --> B[home-agent\ntelegram_reader]
    B --> M{Known chat_id?}
    M -- No --> S1[POST /session]
    S1 --> SID[Store chat_id -> session_id]
    M -- Yes --> SID
    SID --> S2[POST /session/{session_id}/message]
    S2 --> O[OpenCode server]
    O --> DB[(OpenCode session history\nopencode.db)]
    O --> R[Assistant response]
    R --> B
    B --> C
```

- Telegram provides the `chat_id`.
- `home-agent` maps each `chat_id` to one persistent OpenCode `session_id`.
- OpenCode keeps the conversation history in its own session storage.
