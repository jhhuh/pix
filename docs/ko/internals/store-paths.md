# 스토어 경로 계산

Nix 스토어 경로는 다음과 같은 형태의 문자열입니다:

```
/nix/store/<hash>-<name>
```

`<hash>`는 160비트 (20바이트) 해시를 Nix base32로 인코딩한 정확히 32자입니다.

## 알고리즘

```
                              ┌──────────┐
  content ──── sha256 ──────> │  내부    │
  (또는 source의 NAR 해시)     │  해시    │
                              │ (32 B)   │
                              └────┬─────┘
                                   │
                                   v
  ┌────────────────────────────────────────────────────┐
  │ 핑거프린트 문자열:                                    │
  │ "<type>:sha256:<hex(inner_hash)>:/nix/store:<name>"│
  └───────────────────────┬────────────────────────────┘
                          │
                      sha256
                          │
                          v
                    ┌──────────┐
                    │ 32 바이트 │
                    └────┬─────┘
                         │
                  XOR-폴드하여 20바이트로
                         │
                         v
                    ┌──────────┐
                    │ 20 바이트 │
                    └────┬─────┘
                         │
                  Nix base32 인코딩
                         │
                         v
      /nix/store/<32자>-<name>
```

## 타입 프리픽스

핑거프린트의 `<type>`은 이 경로가 어떤 종류의 스토어 객체를 가리키는지 결정합니다.

### `text` — 텍스트 파일

`builtins.toFile`과 `pkgs.writeText`에서 사용. 내부 해시는 `sha256(content)`.

```
text:sha256:<hex>:/nix/store:<name>
```

참조가 있는 경우 (텍스트 파일이 다른 스토어 경로에 의존):

```
text:/nix/store/...-dep1:/nix/store/...-dep2:sha256:<hex>:/nix/store:<name>
```

참조는 정렬되어 `:` 구분자로 추가됩니다. 참조가 없으면 타입은 그냥 `text`입니다 — 뒤에 콜론이 붙지 않습니다.

### `source` — 소스 경로

`builtins.path`, `builtins.filterSource`, 그리고 경로 임포트(`./foo`)에서 사용. 내부 해시는 NAR 직렬화의 SHA-256입니다.

```
source:sha256:<hex>:/nix/store:<name>
```

참조가 있을 수도 있습니다 (자기 자신의 스토어 경로를 포함하는 경로의 자기 참조):

```
source:/nix/store/...-self:sha256:<hex>:/nix/store:<name>
```

### `output:<name>` — Derivation 출력

비고정 출력 derivation의 출력에 사용. 내부 해시는 `hashDerivationModulo`에서 옵니다.

```
output:out:sha256:<hex>:/nix/store:<name>
```

다중 출력 derivation의 경우:

```
output:lib:sha256:<hex>:/nix/store:<name>
output:dev:sha256:<hex>:/nix/store:<name>
```

### 고정 출력 derivation

고정 출력 derivation (`fetchurl` 등)은 2단계 과정을 사용합니다:

1. 중간 디스크립터 계산: `fixed:out:<method><algo>:<hex>:`
2. 디스크립터 해싱: `inner_hash = sha256(descriptor)`
3. `output:out`을 타입으로 사용

**예외:** `recursive` + `sha256`은 소스 경로로 직접 처리됩니다 (`make_source_store_path`와 동일).

## 이름 제약

스토어 객체 이름은:

- 비어있으면 안 됨
- `.`으로 시작하면 안 됨
- 다음 문자만 포함: `a-z A-Z 0-9 + - . _ ? =`
- 211자를 초과하면 안 됨

## 풀이 예제

`builtins.toFile "hello.txt" "hello"`의 스토어 경로 계산:

```python
from pix.hash import sha256, compress_hash
from pix.base32 import encode

content = b"hello"

# 1단계: 내부 해시
inner = sha256(content)
# 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824

# 2단계: 핑거프린트
fp = f"text:sha256:{inner.hex()}:/nix/store:hello.txt"
# text:sha256:2cf24dba...938b9824:/nix/store:hello.txt

# 3단계: 핑거프린트 해싱
fp_hash = sha256(fp.encode())

# 4단계: 압축
compressed = compress_hash(fp_hash, 20)

# 5단계: 인코딩
encoded = encode(compressed)  # 32자

# 6단계: 조합
path = f"/nix/store/{encoded}-hello.txt"
```
