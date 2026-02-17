# pix.hash

Nix 스토어 경로 계산을 위한 해시 유틸리티.

## 함수

### `sha256(data: bytes) -> bytes`

SHA-256 다이제스트를 계산합니다. `hashlib.sha256`의 얇은 래퍼입니다.

```python
from pix.hash import sha256

sha256(b"hello")
# b',\xf2M\xba_\xb0\xa3\x0e...' (32 바이트)
```

### `sha256_hex(data: bytes) -> str`

SHA-256 다이제스트를 16진수 문자열로 계산합니다.

```python
from pix.hash import sha256_hex

sha256_hex(b"hello")
# '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
```

### `compress_hash(hash_bytes: bytes, size: int) -> bytes`

해시를 더 짧은 길이로 XOR-폴드합니다.

Nix가 스토어 경로 해시를 위해 SHA-256 (32 바이트)을 160비트 (20 바이트)로 줄이는 방법입니다. 이것은 단순 잘라내기(truncation)가 **아닙니다** — 입력의 모든 바이트가 XOR을 통해 출력에 기여합니다.

**알고리즘:**

```python
result = bytearray(size)       # 0으로 초기화
for i, b in enumerate(hash_bytes):
    result[i % size] ^= b      # 각 바이트를 해당 위치에 XOR
```

**예제:**

```python
from pix.hash import compress_hash, sha256

digest = sha256(b"hello")           # 32 바이트
compressed = compress_hash(digest, 20)  # 20 바이트

# 다이제스트의 바이트 0..19가 바이트 20..31과 XOR됨
# compressed[0] = digest[0] ^ digest[20]
# compressed[1] = digest[1] ^ digest[21]
# ...
# compressed[11] = digest[11] ^ digest[31]
# compressed[12..19] = digest[12..19]  (폴딩 불필요)
```

!!! info "참고"
    XOR-폴드는 잘라내기보다 더 많은 엔트로피를 보존합니다. 원본 해시의 모든 비트가 압축된 출력에 영향을 줍니다.
