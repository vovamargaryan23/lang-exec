# LangExec

A backend platform for executing code in multiple programming languages inside fully isolated Docker containers - no local language runtimes required.

## Supported Languages

| Language | Version |
|----------|---------|
| Python   | 3.10 |
| Java     | 17 (JDK) |

## How It Works

1. Client sends a `POST /execute` request with source code and target language.
2. The API writes the code to a shared volume and acquires a pre-warmed executor container from the pool.
3. Output is streamed back in real time as newline-delimited JSON (NDJSON).
4. The container is retired and replaced asynchronously after execution completes or times out.

## API

### `POST /execute`

**Request**
```json
{
  "language": "python",
  "code": "print('hello, world')"
}
```

**Response** - `application/x-ndjson`

One JSON object per line. The stream always ends with either an `exit` or `timeout` event.

| Event type | Payload | When |
|---|---|---|
| `output` | `{"type": "output", "content": "..."}` | stdout/stderr from the process |
| `exit` | `{"type": "exit", "return_code": 0}` | process exited (any code) |
| `timeout` | `{"type": "timeout"}` | execution exceeded the time limit |
| `infrastructure_error` | `{"type": "infrastructure_error", "message": "..."}` | Docker-level failure mid-stream |

**Error responses** (before streaming starts)

| Status | Condition |
|---|---|
| `400` | Unknown or unsupported language |
| `422` | Missing field, or code exceeds 64 KB |
| `503` | No containers available (pool exhausted or Docker unreachable) |

### `GET /health`

Returns application status and per-language pool statistics.

```json
{
  "status": "ok",
  "pools": {
    "python": { "idle": 2, "capacity": 3, "max_concurrent": 8, "in_use": 1 },
    "java":   { "idle": 3, "capacity": 3, "max_concurrent": 8, "in_use": 0 }
  }
}
```

## Container Pool

Each language has a dedicated pool of pre-warmed containers. Containers start before the first request arrives, eliminating runtime startup latency. After each execution the used container is discarded and a fresh one is created asynchronously in the background - never reused.

Two settings control concurrency per pool:

- `EXEC_POOL_SIZE` - number of pre-warmed idle containers (default `3`)
- `EXEC_POOL_OVERFLOW` - additional containers that can be created on demand for burst traffic (default `5`)

The hard concurrency limit per pool is `EXEC_POOL_SIZE + EXEC_POOL_OVERFLOW`.

## Security

Executor containers are maximally restricted at runtime:

- **No network** - containers cannot make any outbound or inbound connections.
- **Read-only filesystem** - root filesystem is mounted read-only; only `/tmp` is writable (via `tmpfs`, `noexec`, `nosuid`).
- **Non-root user** - code runs as an unprivileged `executor` user inside the container.
- **Dropped capabilities** - all Linux capabilities are dropped.
- **No privilege escalation** - `no-new-privileges` security option is enforced.
- **Resource limits** - CPU, memory (no swap beyond RAM limit), and PID count are all capped.
- **Execution timeout** - containers that exceed the time limit are killed with SIGKILL and the client receives a `{"type": "timeout"}` event.
- **Input validation** - code payload is capped at 64 KB.

## Build & Run

### Prerequisites

- Docker
- Docker Compose

### 1. Create the code volume directory

```bash
mkdir -p tmp/code
```

### 2. Start the application

```bash
docker compose up --build
```

This builds all images (application, python-executor, java-executor) and starts the stack. The API will be available at `http://localhost:8000`.

### Example requests

**Python**
```bash
curl -N -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"language": "python", "code": "print(\"hello, world\")"}'
```

**Java**
```bash
curl -N -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"language": "java", "code": "class Main { public static void main(String[] a) { System.out.println(\"hello, world\"); } }"}'
```

## Configuration

All settings can be overridden via environment variables or a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `DOCKER_SOCK_PATH` | `unix:///var/run/docker.sock` | Docker socket path |
| `EXEC_POOL_SIZE` | `3` | Pre-warmed containers per language |
| `EXEC_POOL_OVERFLOW` | `5` | Burst capacity on top of pool size |
| `EXEC_TIMEOUT` | `10` | Execution time limit in seconds |
| `EXEC_MEM_LIMIT` | `128` | Memory limit per container in MB |
| `EXEC_CPU_LIMIT` | `1` | CPU cores available per container |
| `EXEC_PIDS_LIMIT` | `64` | Max processes/threads per container |
| `VOLUME_PATH` | `/media/code` | Path inside executor containers |
| `CODE_VOLUME_HOST_PATH` | *(same as `VOLUME_PATH`)* | Host path for the shared code volume |
