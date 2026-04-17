# LangExec

A backend platform for executing code in multiple programming languages inside fully isolated Docker containers - no local language runtimes required.

## Supported Languages

| Language | Status |
|----------|--------|
| Python   | ✅ Supported |

## How It Works

1. Client sends a `POST /execute` request with source code and target language.
2. The API writes the code to a shared volume and spawns a sandboxed executor container.
3. Output is streamed back in real time as newline-delimited JSON (NDJSON).
4. The container is removed immediately after execution completes or times out.

## API

### `POST /execute`

**Request**
```json
{
  "language": "python",
  "execution_params": "",
  "code": "print('hello, world')"
}
```

**Response** — `application/x-ndjson`

One JSON object per line, newline-delimited:

| Event type | Payload |
|------------|---------|
| `output`   | `{"type": "output", "content": "..."}` |
| `exit`     | `{"type": "exit", "return_code": 0}` |
| `timeout`  | `{"type": "timeout"}` |
| `error`    | `{"type": "error", "message": "..."}` |

## Security

Executor containers are maximally restricted at runtime:

- **No network** — `network_disabled=true`, containers cannot make outbound or inbound connections.
- **Read-only filesystem** — root filesystem is mounted read-only; only `/tmp` is writable (via `tmpfs`, `noexec`, `nosuid`).
- **Non-root user** — code runs as an unprivileged `executor` user inside the container.
- **Dropped capabilities** — all Linux capabilities are dropped (`cap_drop: ALL`).
- **No privilege escalation** — `no-new-privileges` security option is enforced.
- **Resource limits** — CPU, memory, swap, and PID count are all capped.
- **Execution timeout** — containers that exceed the time limit are killed with SIGKILL and the client receives a `timeout` event.
- **Input validation** — code is capped at 64 KB; `execution_params` is restricted to alphanumeric characters, spaces, hyphens, dots, and underscores.

## Build & Run

### Prerequisites

- Docker
- Docker Compose

### 1. Build executor images

```bash
docker build -f dockerfiles/python.Dockerfile -t lang-exec-python-executor:latest dockerfiles/
```

### 2. Create the code volume directory

```bash
mkdir -p tmp/code
```

### 3. Start the application

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Example request

```bash
curl -N -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"language": "python", "execution_params": "", "code": "print(\"hello, world\")"}'
```
