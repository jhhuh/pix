# pix.nar

NAR (Nix Archive) 직렬화 및 해싱.

NAR은 결정론적 아카이브 형식입니다. tar와 달리, 타임스탬프, 소유권, 퍼미션(실행 비트만 보존)에 관계없이 동일한 파일시스템 내용에 대해 항상 동일한 바이트 시퀀스를 생성합니다.

와이어 형식 명세는 [내부 구조: NAR 형식](../internals/nar-format.md)을 참고하세요.

## 함수

### `nar_serialize(path: str | Path) -> bytes`

파일시스템 경로 (파일, 디렉터리, 심링크)를 NAR 바이트로 직렬화합니다.

```python
from pix.nar import nar_serialize

# 단일 파일 직렬화
nar = nar_serialize("/tmp/hello.txt")

# 디렉터리 직렬화 (엔트리는 이름순 정렬)
nar = nar_serialize("/path/to/my-source")
```

**동작:**

- **일반 파일**: 내용과 실행 플래그와 함께 직렬화
- **심링크**: 심링크 대상으로 직렬화 (해석하지 않음)
- **디렉터리**: 이름순 사전식 정렬, 재귀 처리
- **기타 타입**: `ValueError` 발생

### `nar_hash(path: str | Path) -> bytes`

NAR 직렬화의 SHA-256 해시를 계산합니다. 32바이트 원시 바이트를 반환합니다.

`nix hash path`가 계산하는 것과 같습니다.

```python
from pix.nar import nar_hash

digest = nar_hash("./my-file.txt")  # 32 바이트
digest.hex()
# 'a1b2c3d4...'
```

### `nar_hash_hex(path: str | Path) -> str`

`nar_hash`와 동일하지만 16진수 문자열을 직접 반환합니다.

```python
from pix.nar import nar_hash_hex

nar_hash_hex("./my-file.txt")
# 'a1b2c3d4...'
```

## 다른 모듈과의 조합

NAR 해싱은 소스 임포트의 스토어 경로를 계산하는 첫 번째 단계입니다:

```python
from pix.nar import nar_hash
from pix.store_path import make_source_store_path

h = nar_hash("./my-project")
path = make_source_store_path("my-project", h)
# '/nix/store/abc123...-my-project'
```
