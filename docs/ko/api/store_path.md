# pix.store_path

Nix 스토어 경로를 계산합니다. 스토어 경로는 `/nix/store/<hash>-<name>` 형태이며, `<hash>`는 160비트 해시를 Nix base32로 인코딩한 32자입니다.

전체 알고리즘은 [내부 구조: 스토어 경로](../internals/store-paths.md)를 참고하세요.

## 상수

### `STORE_DIR`

```python
STORE_DIR = "/nix/store"
```

### `HASH_BYTES`

```python
HASH_BYTES = 20  # 160비트
```

## 함수

### `make_store_path(type_prefix: str, inner_hash: bytes, name: str) -> str`

저수준 스토어 경로 계산. 대부분의 호출자는 아래의 타입별 헬퍼를 사용해야 합니다.

핑거프린트 `<type>:sha256:<hex>:/nix/store:<name>`을 계산하고, SHA-256으로 해싱한 뒤, 20바이트로 XOR-폴드하고, Nix base32로 인코딩합니다.

```python
from pix.store_path import make_store_path
from pix.hash import sha256

h = sha256(b"some content")
path = make_store_path("text", h, "example.txt")
```

---

### `make_text_store_path(name: str, content: bytes, references: list[str] | None = None) -> str`

텍스트 파일의 스토어 경로. `builtins.toFile` 또는 `pkgs.writeText`와 동일합니다.

내부 해시는 `sha256(content)`입니다. 타입 프리픽스는 참조가 추가된 `text`입니다.

```python
from pix.store_path import make_text_store_path

# 단순 텍스트 파일
path = make_text_store_path("hello.txt", b"hello world")
# '/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt'

# 다른 스토어 경로를 참조하는 텍스트 파일
path = make_text_store_path(
    "script.sh",
    b"#!/bin/sh\nexec /nix/store/...-bash/bin/bash",
    references=["/nix/store/...-bash"]
)
```

---

### `make_source_store_path(name: str, nar_hash: bytes, references: list[str] | None = None) -> str`

소스 디렉터리 또는 파일의 스토어 경로. Nix에서 `builtins.path`, `filterSource`, 또는 경로 임포트(`./foo`)를 사용할 때 일어나는 것입니다.

내부 해시는 NAR 직렬화의 SHA-256입니다.

```python
from pix.store_path import make_source_store_path
from pix.nar import nar_hash

h = nar_hash("./my-project")
path = make_source_store_path("my-project", h)
```

---

### `make_fixed_output_path(name: str, hash_algo: str, content_hash: bytes, recursive: bool = False) -> str`

고정 출력 derivation 결과의 스토어 경로 (`fetchurl`, `fetchgit` 등).

```python
from pix.store_path import make_fixed_output_path

# 플랫 파일 (sha256를 사용하는 fetchurl)
path = make_fixed_output_path("source.tar.gz", "sha256", hash_bytes)

# 재귀적 (fetchgit, fetchFromGitHub)
path = make_fixed_output_path("source", "sha256", nar_hash_bytes, recursive=True)
```

!!! note "참고"
    `recursive=True`와 `sha256`의 조합에서는 소스 경로로 직접 계산됩니다 (`make_source_store_path`와 동일). 다른 조합에서는 중간 해시가 먼저 계산됩니다.

---

### `make_output_path(drv_hash: bytes, output_name: str, name: str) -> str`

derivation의 모듈러 해시(`hash_derivation_modulo`에서 얻은)를 기반으로 한 derivation 출력의 스토어 경로.

```python
from pix.store_path import make_output_path

path = make_output_path(drv_hash, "out", "hello-2.12.2")
```
