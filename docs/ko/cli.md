# CLI 레퍼런스

pix를 Python 모듈로 실행합니다:

```bash
python -m pix <command> [options]
```

## 명령어

### `hash-path` — 경로의 NAR 해시

파일 또는 디렉터리의 NAR 직렬화에 대한 SHA-256 해시를 계산합니다. `nix hash path`와 동일합니다.

```bash
python -m pix hash-path <path> [--base32]
```

| 플래그 | 설명 |
|--------|------|
| `--base32` | 16진수 대신 Nix base32로 출력 |

**예제:**

```bash
$ python -m pix hash-path ./pix/base32.py
sha256:0a43087...

$ python -m pix hash-path ./pix/base32.py --base32
sha256:1l1a9cfyhln3s40sb9b2w2h4z8p3566xkbs84vk819h3107ahkvl

$ python -m pix hash-path ./my-directory --base32
sha256:1vrbglcwc4gpln263rg69jq6vgq8p3ibspdg7lzyxcyc0ryg5wn2
```

!!! note "참고"
    `hash-path`는 원시 파일 바이트가 아니라 **NAR 직렬화**를 해싱합니다. 파일 타입 메타데이터와 디렉터리의 경우 정렬된 엔트리 이름이 포함됩니다. 원시 콘텐츠 해싱에는 `hash-file`을 사용하세요.

---

### `hash-file` — 파일의 플랫 SHA-256

파일의 원시 바이트를 해싱합니다 (NAR 래핑 없음). `nix hash file`과 동일합니다.

```bash
python -m pix hash-file <path> [--base32]
```

**예제:**

```bash
$ echo -n "hello" > /tmp/hello.txt
$ python -m pix hash-file /tmp/hello.txt --base32
sha256:094qif9n4cq4fdg459qzbhg1c6wywawwaaivx0k0x8xhbyx4vwic
```

---

### `store-path` — 스토어 경로 계산

로컬 파일 또는 디렉터리의 Nix 스토어 경로를 계산합니다. `builtins.path`나 `filterSource`를 통해 추가된 것처럼 계산합니다.

```bash
python -m pix store-path <path> [--name NAME]
```

| 플래그 | 설명 |
|--------|------|
| `--name` | 스토어 객체 이름 지정 (기본값: 경로의 basename) |

**예제:**

```bash
$ python -m pix store-path ./my-source
/nix/store/pagr3c3r57k8h9zqhb89cqihhc9sbz03-my-source

$ python -m pix store-path ./my-source --name custom-name
/nix/store/abc123...-custom-name
```

---

### `drv-show` — `.drv`를 JSON으로 파싱

Nix 스토어의 `.drv` 파일을 파싱하여 포맷된 JSON으로 표시합니다. `nix derivation show`와 동일합니다.

```bash
python -m pix drv-show <drv-path>
```

**예제:**

```bash
$ python -m pix drv-show /nix/store/...-hello-2.12.2.drv
{
  "outputs": {
    "out": {
      "path": "/nix/store/...-hello-2.12.2",
      "hashAlgo": "",
      "hash": ""
    }
  },
  "inputDrvs": {
    "/nix/store/...-bash.drv": ["out"],
    "/nix/store/...-stdenv.drv": ["out"]
  },
  "inputSrcs": ["/nix/store/...-default-builder.sh"],
  "platform": "x86_64-linux",
  "builder": "/nix/store/...-bash/bin/bash",
  "args": ["-e", "/nix/store/...-default-builder.sh"],
  "env": {"name": "hello", "version": "2.12.2", ...}
}
```

---

### `path-info` — 스토어 경로 정보 조회

Nix 데몬에서 스토어 경로의 메타데이터를 조회합니다. 실행 중인 데몬이 필요합니다.

```bash
python -m pix path-info <store-path>
```

**예제:**

```bash
$ python -m pix path-info /nix/store/...-hello-2.12.2
deriver: /nix/store/...-hello-2.12.2.drv
nar-hash: sha256:1abc...
nar-size: 53856
references: /nix/store/...-glibc /nix/store/...-hello-2.12.2
sigs: cache.nixos.org-1:abc123...
```

---

### `is-valid` — 스토어 경로 유효성 확인

스토어 경로가 존재하고 유효한지 확인합니다. 유효하면 종료 코드 0, 아니면 1을 반환합니다.

```bash
python -m pix is-valid <store-path>
```

**예제:**

```bash
$ python -m pix is-valid /nix/store/...-hello-2.12.2
valid

$ python -m pix is-valid /nix/store/aaaa...-nonexistent
invalid
```

---

### `add-text` — 스토어에 텍스트 추가

텍스트 문자열을 Nix 스토어에 추가합니다. `builtins.toFile`과 같습니다. content가 `-`이거나 생략되면 stdin에서 읽습니다.

```bash
python -m pix add-text <name> [content]
```

**예제:**

```bash
$ python -m pix add-text hello.txt "hello world"
/nix/store/qbfcv31xi1wjisxwl4b2nk1a8jqxbcf5-hello.txt

$ echo "from stdin" | python -m pix add-text piped.txt
/nix/store/...-piped.txt
```

---

### `build` — 스토어 경로 빌드

Nix 데몬을 통해 하나 이상의 derivation 출력을 빌드합니다.

```bash
python -m pix build <path>...
```

**예제:**

```bash
$ python -m pix build /nix/store/...-hello-2.12.2.drv^out
build succeeded
```
