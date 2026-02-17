# pix.base32

Nix 전용 base32 인코딩 및 디코딩.

!!! warning "주의"
    이것은 RFC 4648 base32가 **아닙니다**. Nix는 다른 알파벳과 다른 비트 추출 순서를 사용합니다. 전체 비교는 [내부 구조: Base32](../internals/base32.md)를 참고하세요.

## 상수

### `CHARS`

```python
CHARS = "0123456789abcdfghijklmnpqrsvwxyz"
```

32자의 Nix base32 알파벳. 빠진 문자: `e`, `o`, `t`, `u`.

## 함수

### `encode(data: bytes) -> str`

바이트를 Nix base32 문자열로 인코딩합니다.

**출력 길이:** `n` 입력 바이트에 대해 `ceil(n * 8 / 5)` 문자.

| 입력 크기 | 출력 크기 | 용도 |
|----------|----------|------|
| 20 바이트 | 32 문자 | 스토어 경로 해시 |
| 32 바이트 | 52 문자 | SHA-256 다이제스트 |

```python
from pix.base32 import encode

encode(b"\x00" * 20)
# '00000000000000000000000000000000'

import hashlib
digest = hashlib.sha256(b"hello").digest()
encode(digest)
# '094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic'
```

### `decode(s: str) -> bytes`

Nix base32 문자열을 바이트로 디코딩합니다.

**예외:** 문자열에 Nix base32 알파벳에 없는 문자가 포함되면 `ValueError` 발생.

```python
from pix.base32 import decode

decode("094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic")
# b',\xf2M\xba_\xb0\xa3\x0e&\xe8;*\xc5\xb9\xe2\x9e\x1b\x16\x1e\\\x1f\xa7B^s\x043b\x93\x8b\x98$'

decode("00000000000000000000000000000000")
# b'\x00' * 20
```

### 왕복 변환

encode와 decode는 역연산입니다:

```python
from pix.base32 import encode, decode

data = b"any bytes here"
assert decode(encode(data)) == data
```
