# pix.daemon

Nix 데몬 Unix 소켓 클라이언트. `/nix/var/nix/daemon-socket/socket`을 통해 Nix 워커 프로토콜로 통신합니다.

프로토콜 상세는 [내부 구조: 데몬 프로토콜](../internals/daemon-protocol.md)을 참고하세요.

## 클래스

### `DaemonConnection`

Nix 데몬 연결을 위한 컨텍스트 매니저.

```python
from pix.daemon import DaemonConnection

with DaemonConnection() as conn:
    # conn 사용...
    pass

# 또는 커스텀 소켓 경로:
with DaemonConnection("/custom/socket/path") as conn:
    pass
```

**생성자:**

```python
DaemonConnection(socket_path: str | None = None)
```

| 매개변수 | 기본값 | 설명 |
|----------|--------|------|
| `socket_path` | `/nix/var/nix/daemon-socket/socket` | Unix 소켓 경로 |

**속성:**

| 속성 | 타입 | 설명 |
|------|------|------|
| `daemon_version` | `int` | 핸드셰이크 후 프로토콜 버전 (예: `293` = 1.37) |

---

## 오퍼레이션

### `is_valid_path(path: str) -> bool`

스토어 경로가 Nix 스토어에 존재하고 유효한지 확인합니다.

```python
with DaemonConnection() as conn:
    conn.is_valid_path("/nix/store/...-hello-2.12.2")  # True
    conn.is_valid_path("/nix/store/aaaa...-nope")       # False
```

---

### `query_valid_paths(paths: list[str], substitute: bool = False) -> set[str]`

배치 유효성 확인. 유효한 경로의 부분 집합을 반환합니다.

```python
with DaemonConnection() as conn:
    valid = conn.query_valid_paths([
        "/nix/store/...-hello",
        "/nix/store/...-nonexistent",
    ])
    # {'/nix/store/...-hello'}
```

| 매개변수 | 설명 |
|----------|------|
| `substitute` | `True`이면 누락된 경로의 대체를 시도 |

---

### `query_path_info(path: str) -> PathInfo`

유효한 스토어 경로의 메타데이터를 조회합니다.

**예외:** 경로가 유효하지 않으면 `NixDaemonError` 발생.

```python
with DaemonConnection() as conn:
    info = conn.query_path_info("/nix/store/...-hello-2.12.2")
    info.deriver       # '/nix/store/...-hello-2.12.2.drv'
    info.nar_hash       # 'sha256:1abc...'
    info.nar_size       # 53856
    info.references     # ['/nix/store/...-glibc', ...]
    info.sigs           # ['cache.nixos.org-1:abc...']
```

---

### `add_text_to_store(name: str, content: str, references: list[str] | None = None) -> str`

텍스트 문자열을 Nix 스토어에 추가합니다. 스토어 경로를 반환합니다.

`builtins.toFile`과 같습니다 — 주어진 내용으로 일반 파일을 생성합니다.

```python
with DaemonConnection() as conn:
    path = conn.add_text_to_store("hello.txt", "hello world")
    # '/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt'

    # 참조 포함 (텍스트가 다른 스토어 경로에 의존):
    path = conn.add_text_to_store(
        "wrapper.sh",
        "#!/bin/sh\nexec /nix/store/...-program/bin/prog",
        references=["/nix/store/...-program"]
    )
```

---

### `build_paths(paths: list[str], build_mode: int = 0) -> None`

하나 이상의 스토어 경로를 빌드합니다. Derivation의 경우 `<drv-path>^<output>` 구문을 사용합니다.

**예외:** 빌드 실패 시 `NixDaemonError` 발생.

```python
with DaemonConnection() as conn:
    # derivation 출력 빌드
    conn.build_paths(["/nix/store/...-hello.drv^out"])

    # 여러 경로 대체/빌드
    conn.build_paths([
        "/nix/store/...-hello.drv^out",
        "/nix/store/...-world.drv^out",
    ])
```

| `build_mode` | 의미 |
|---|---|
| `0` | 일반 (빌드 또는 대체) |
| `1` | 수리 |
| `2` | 검사 |

---

## 데이터 클래스

### `PathInfo`

`query_path_info`가 반환하는 데이터.

```python
@dataclass
class PathInfo:
    deriver: str            # 이것을 생성한 .drv 경로, 또는 ""
    nar_hash: str           # 문자열로 된 NAR 해시
    references: list[str]   # 이것이 의존하는 스토어 경로
    registration_time: int  # Unix 타임스탬프
    nar_size: int           # NAR 직렬화의 바이트 크기
    sigs: list[str]         # 서명
```

## 예외

### `NixDaemonError`

프로토콜 오류, 잘못된 경로, 빌드 실패 등에서 발생합니다.

```python
from pix.daemon import DaemonConnection, NixDaemonError

with DaemonConnection() as conn:
    try:
        conn.query_path_info("/nix/store/invalid-path")
    except NixDaemonError as e:
        print(f"데몬 오류: {e}")
```
