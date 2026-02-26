# pix.derivation

Nix `.drv` 파일 (ATerm 형식) 파싱 및 직렬화, 출력 경로 계산을 위한 derivation 해시 계산.

ATerm 형식 명세는 [내부 구조: Derivation](../internals/derivations.md)을 참고하세요.

## 데이터 클래스

### `DerivationOutput`

```python
@dataclass
class DerivationOutput:
    path: str        # 출력 스토어 경로 (content-addressed의 경우 비어있음)
    hash_algo: str   # 일반 출력은 "", fixed-output은 "sha256" 등
    hash_value: str  # 일반 출력은 "", fixed-output은 16진수 해시
```

### `Derivation`

```python
@dataclass
class Derivation:
    outputs: dict[str, DerivationOutput]     # "out" -> DerivationOutput(...)
    input_drvs: dict[str, list[str]]         # drv_path -> ["out", ...]
    input_srcs: list[str]                    # 소스 스토어 경로
    platform: str                            # "x86_64-linux"
    builder: str                             # "/nix/store/...-bash/bin/bash"
    args: list[str]                          # 빌더 인자
    env: dict[str, str]                      # 환경 변수
```

## 함수

### `parse(drv_text: str) -> Derivation`

ATerm `.drv` 파일을 `Derivation`으로 파싱합니다.

```python
from pix.derivation import parse

drv = parse(open("/nix/store/...-hello-2.12.2.drv").read())

drv.platform       # 'x86_64-linux'
drv.builder         # '/nix/store/...-bash/bin/bash'
drv.outputs.keys()  # dict_keys(['out'])
drv.env['name']     # 'hello'
```

문자열의 이스케이프 시퀀스를 처리합니다: `\\`, `\"`, `\n`, `\r`, `\t`.

---

### `serialize(drv: Derivation) -> str`

`Derivation`을 ATerm `.drv` 형식으로 직렬화합니다.

출력은 결정론적입니다:

- 출력은 이름순 정렬
- 입력 derivation은 경로순 정렬
- 입력 소스는 정렬됨
- 환경 변수는 키순 정렬
- 문자열은 적절히 이스케이프

```python
from pix.derivation import parse, serialize

text = open("/nix/store/...-hello.drv").read()
drv = parse(text)
assert parse(serialize(drv)) == drv  # 왕복 변환
```

---

### `hash_derivation_modulo(drv: Derivation, drv_hashes: dict[str, bytes] | None = None) -> bytes`

출력 경로 계산에 사용되는 derivation의 모듈러 해시를 계산합니다.

**고정 출력 derivation** (단일 출력 `"out"`에 `hash_algo`가 설정된 경우):

```
sha256("fixed:out:<hash_algo>:<hash_value>:<output_path>")
```

**일반 derivation**: 출력 경로를 비우고 입력 derivation 경로를 모듈러 해시로 대체한 마스크 복사본을 만든 다음, 결과 ATerm을 해싱합니다.

```python
from pix.derivation import parse, hash_derivation_modulo

drv = parse(open("some.drv").read())

# 고정 출력의 경우:
h = hash_derivation_modulo(drv)

# 일반 derivation의 경우, 입력 drv 해시를 제공:
h = hash_derivation_modulo(drv, drv_hashes={
    "/nix/store/...-dep.drv": dep_hash,
})
```

!!! warning "주의"
    일반 (비고정 출력) derivation의 경우, `drv_hashes` 매개변수를 통해 모든 입력 derivation의 모듈러 해시를 제공해야 합니다. 누락된 해시는 `ValueError`를 발생시킵니다.

## 예제: 전체 derivation 검사

```python
from pix.derivation import parse
import json

drv = parse(open("/nix/store/...-hello-2.12.2.drv").read())

print(f"패키지: {drv.env.get('pname', drv.env.get('name', '?'))}")
print(f"버전: {drv.env.get('version', '?')}")
print(f"시스템: {drv.platform}")
print(f"빌더: {drv.builder}")
print(f"출력: {list(drv.outputs.keys())}")
print(f"의존성: {len(drv.input_drvs)}개 derivation, {len(drv.input_srcs)}개 소스")
```
