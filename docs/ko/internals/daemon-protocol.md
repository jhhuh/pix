# Nix 데몬 프로토콜

Nix 데몬 (`nix-daemon`)은 Unix 도메인 소켓에서 수신 대기하며 클라이언트에 스토어 오퍼레이션을 제공합니다. pix는 이 프로토콜의 클라이언트를 순수 Python으로 구현합니다.

## 연결

**소켓 경로:** `/nix/var/nix/daemon-socket/socket`

`SOCK_STREAM` Unix 도메인 소켓입니다. 각 클라이언트는 순차적 요청/응답 교환을 위한 전용 연결을 받습니다.

## 와이어 형식

와이어의 모든 값은 리틀엔디안 인코딩을 사용하며, 8바이트 경계로 패딩됩니다:

| 타입 | 인코딩 |
|------|--------|
| `uint64` | 8바이트, 리틀엔디안 |
| `bool` | uint64 (0 = false, 0이 아닌 값 = true) |
| `string` | uint64(길이) + 바이트 + 8바이트까지 제로 패딩 |
| `string list` | uint64(개수) + 개수 × string |

[NAR 형식](nar-format.md)과 같은 문자열 인코딩입니다.

## 핸드셰이크

```
클라이언트                                       데몬
  │                                               │
  ├─── uint64(WORKER_MAGIC_1 = 0x6e697863) ─────>│
  │                                               │
  │<── uint64(WORKER_MAGIC_2 = 0x6478696f) ──────┤
  │<── uint64(daemon_protocol_version) ───────────┤
  │                                               │
  ├─── uint64(client_protocol_version) ──────────>│
  ├─── uint64(0)  [CPU 친화성, 폐기됨] ──────────>│
  ├─── uint64(0)  [공간 예약, 폐기됨] ────────────>│
  │                                               │
  │<── string(nix_version)  [proto >= 1.33] ─────┤
  │<── uint64(trusted)      [proto >= 1.35] ─────┤
  │                                               │
  │<── STDERR_LAST ──────────────────────────────┤
  │                                               │
```

**매직 넘버:**

| 상수 | 값 | ASCII |
|------|-----|-------|
| `WORKER_MAGIC_1` | `0x6e697863` | `nixc` |
| `WORKER_MAGIC_2` | `0x6478696f` | `dxio` |

**프로토콜 버전**은 `(major << 8) | minor`로 인코딩됩니다. pix는 버전 `1.37` = `0x0125` = `293`을 사용합니다.

**신뢰 상태** (프로토콜 >= 1.35):

| 값 | 의미 |
|----|------|
| 0 | 알 수 없음 |
| 1 | 신뢰됨 |
| 2 | 신뢰되지 않음 |

## 요청/응답 패턴

핸드셰이크 후 각 오퍼레이션은 다음 패턴을 따릅니다:

```
클라이언트                                       데몬
  │                                               │
  ├─── uint64(opcode) ──────────────────────────>│
  ├─── <오퍼레이션별 데이터> ────────────────────>│
  │                                               │
  │<── stderr 메시지 ──────────────────────────────┤
  │<── STDERR_LAST ──────────────────────────────┤
  │<── <오퍼레이션별 응답> ────────────────────────┤
  │                                               │
```

## Stderr 메시지 스트림

요청과 응답 사이에 데몬은 로그 메시지 스트림을 보냅니다. 응답을 읽기 전에 클라이언트는 이를 반드시 소진(drain)해야 합니다.

각 메시지는 uint64 메시지 타입으로 시작합니다:

| 타입 | 값 | 내용 |
|------|-----|------|
| `STDERR_LAST` | `0x616c7473` | 스트림 끝 — 다음에 응답을 읽음 |
| `STDERR_NEXT` | `0x6f6c6d67` | 로그 줄: `string(message)` |
| `STDERR_ERROR` | `0x63787470` | 오류: `string(type) uint64(level) string(name) string(msg) uint64(n_traces) {uint64(pos) string(trace)}*` |
| `STDERR_START_ACTIVITY` | `0x53545254` | 활동 시작: `uint64(id) uint64(level) uint64(type) string(text) fields uint64(parent)` |
| `STDERR_STOP_ACTIVITY` | `0x53544f50` | 활동 종료: `uint64(id)` |
| `STDERR_RESULT` | `0x52534c54` | 활동 결과: `uint64(id) uint64(type) fields` |

**필드** (활동 메시지에서 사용):

```
uint64(count)
{
  uint64(type)     0 = uint64 값, 1 = string 값
  <value>
}*
```

!!! warning "반드시 stderr를 소진해야 함"
    오퍼레이션 응답을 읽기 전에 `STDERR_LAST`까지 모든 stderr 메시지를 **반드시** 읽어야 합니다. 그렇지 않으면 프로토콜이 비동기화됩니다.

## 오퍼레이션

### `IsValidPath` (opcode 1)

스토어 경로가 유효한지 확인합니다.

```
요청:  string(path)
응답: bool(valid)
```

### `AddTextToStore` (opcode 8)

텍스트 파일을 스토어에 추가합니다.

```
요청:  string(name) string(content) string_list(references)
응답: string(store_path)
```

### `BuildPaths` (opcode 9)

하나 이상의 경로를 빌드합니다.

```
요청:  string_list(paths) uint64(build_mode)
응답: uint64(result)
```

빌드 모드: 0 = 일반, 1 = 수리, 2 = 검사.

경로는 불투명 스토어 경로이거나 derivation 출력을 위한 `<drv-path>^<output>`일 수 있습니다.

### `QueryPathInfo` (opcode 26)

스토어 경로의 메타데이터를 조회합니다.

```
요청:  string(path)
응답: bool(valid)
          [valid인 경우:]
          string(deriver)
          string(nar_hash)
          string_list(references)
          uint64(registration_time)
          uint64(nar_size)
          bool(ultimate)
          string_list(sigs)
          string(content_address)
```

### `QueryValidPaths` (opcode 31)

배치 유효성 확인.

```
요청:  string_list(paths) bool(substitute)
응답: string_list(valid_paths)
```

## 프로토콜 버전 히스토리

| 버전 | 변경 사항 |
|------|----------|
| 1.11 | 핸드셰이크에 공간 예약 플래그 |
| 1.14 | 핸드셰이크에 CPU 친화성 |
| 1.16 | 경로 정보에 `ultimate` 플래그 |
| 1.17 | `QueryPathInfo`가 예외 대신 유효성 bool 반환 |
| 1.25 | 경로 정보에 콘텐츠 주소 필드 |
| 1.30 | `BuildPaths`에 DerivedPath 직렬화 |
| 1.33 | 핸드셰이크 후 데몬이 nix 버전 문자열 전송 |
| 1.35 | 핸드셰이크 후 데몬이 신뢰 상태 전송 |
| 1.37 | pix가 사용하는 현재 버전 |
