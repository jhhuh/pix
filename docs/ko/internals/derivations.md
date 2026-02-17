# Derivation

Derivation은 Nix의 빌드 단위입니다. 입력, 빌더, 환경 변수로부터 하나 이상의 스토어 경로를 생성하는 방법을 설명합니다. Derivation은 Nix 스토어에 ATerm 형식의 `.drv` 파일로 저장됩니다.

## ATerm 형식

`.drv` 파일은 단일 ATerm 표현식입니다:

```
Derive(
  [("out","/nix/store/...-hello","",""), ...],       # 출력
  [("/nix/store/...-dep.drv",["out"]), ...],         # 입력 derivation
  ["/nix/store/...-source", ...],                    # 입력 소스
  "x86_64-linux",                                    # 플랫폼
  "/nix/store/...-bash/bin/bash",                    # 빌더
  ["--", "-e", "..."],                               # 인자
  [("key","value"), ...]                             # 환경
)
```

### 필드

| # | 필드 | 타입 | 설명 |
|---|------|------|------|
| 1 | outputs | `[(name, path, hashAlgo, hash)]` | 출력 이름-경로 매핑 |
| 2 | inputDrvs | `[(drvPath, [outputNames])]` | Derivation 의존성 |
| 3 | inputSrcs | `[path]` | 소스 파일 의존성 |
| 4 | platform | `string` | 빌드 플랫폼 (예: `x86_64-linux`) |
| 5 | builder | `string` | 빌더 실행 파일 경로 |
| 6 | args | `[string]` | 빌더 명령줄 인자 |
| 7 | env | `[(key, value)]` | 빌더의 환경 변수 |

### 출력

각 출력은 4-튜플입니다:

```
("name", "path", "hashAlgo", "hash")
```

| 필드 | 일반 출력 | 고정 출력 |
|------|----------|----------|
| `name` | `"out"`, `"lib"`, `"dev"` 등 | `"out"` |
| `path` | `/nix/store/...-name` | `/nix/store/...-name` |
| `hashAlgo` | `""` | `"sha256"`, `"r:sha256"` 등 |
| `hash` | `""` | 기대 콘텐츠의 16진수 해시 |

`hashAlgo`의 `r:` 프리픽스는 재귀적 (NAR 해시)을 의미합니다. 없으면 플랫 파일 콘텐츠의 해시입니다.

### 문자열 이스케이프

ATerm의 문자열은 다음 이스케이프 시퀀스를 사용합니다:

| 이스케이프 | 문자 |
|-----------|------|
| `\\` | 백슬래시 |
| `\"` | 큰따옴표 |
| `\n` | 줄바꿈 |
| `\r` | 캐리지 리턴 |
| `\t` | 탭 |

### 정렬

정규 직렬화에서:

- 출력은 출력 이름순 정렬
- 입력 derivation은 `.drv` 경로순 정렬
- 입력 소스는 정렬됨
- 환경 변수는 키순 정렬
- 인자는 원래 순서 유지

## `hashDerivationModulo`

이것은 Nix가 출력 경로를 결정하는 해시를 계산하는 데 사용하는 알고리즘입니다. 순환 의존성을 해결하기 위해 존재합니다 — 출력 경로는 derivation 해시에 의존하지만, derivation은 자신의 출력 경로를 포함합니다.

### 고정 출력 derivation

`hashAlgo`가 설정된 단일 출력 `"out"`을 가진 derivation의 경우:

```
hash = sha256("fixed:out:<hashAlgo>:<hashValue>:")
```

이것은 고정 출력 derivation이 빌드 의존성이 변경되어도 안정적인 해시를 가진다는 것을 의미합니다 — 기대 출력 해시만 중요합니다.

### 일반 derivation

다른 모든 derivation의 경우:

1. **출력 경로 비우기**: 모든 출력 경로를 `""`로 대체
2. **입력 drv 경로 대체**: 각 입력 derivation에 대해 `.drv` 경로를 해당 입력의 16진수 인코딩된 `hashDerivationModulo`로 대체
3. **직렬화**: 마스크된 derivation을 ATerm으로 변환
4. **해싱**: `sha256(serialized_masked_drv)`

```
┌─────────────────────────────────────────┐
│ 원본 .drv                               │
│                                         │
│ outputs: ("out", "/nix/store/abc-x")    │
│ inputDrvs: ("/nix/store/def.drv",["out"])│
│ ...                                     │
└──────────────────┬──────────────────────┘
                   │
            마스크 & 대체
                   │
                   v
┌─────────────────────────────────────────┐
│ 마스크된 .drv                            │
│                                         │
│ outputs: ("out", "")        ← 비워짐     │
│ inputDrvs: ("a1b2c3...",["out"]) ← 해시  │
│ ...                                     │
└──────────────────┬──────────────────────┘
                   │
            ATerm 문자열로 직렬화
                   │
                   v
            sha256(aterm_string)
                   │
                   v
           derivation 해시 (32 바이트)
```

### 출력 경로 계산

`hashDerivationModulo`에서 derivation 해시를 얻으면:

```python
from pix.store_path import make_output_path

output_path = make_output_path(drv_hash, "out", "hello-2.12.2")
# /nix/store/<hash>-hello-2.12.2
```

타입 프리픽스는 `output:<output-name>`이므로 핑거프린트는 다음과 같습니다:

```
output:out:sha256:<hex(drv_hash)>:/nix/store:hello-2.12.2
```

## 실제 예제

최소 derivation (`builtins.derivation { name = "hello"; builder = "/bin/sh"; args = ["-c" "echo hello > $out"]; system = "x86_64-linux"; }`):

```
Derive(
  [("out","/nix/store/...-hello","","")],
  [],
  [],
  "x86_64-linux",
  "/bin/sh",
  ["-c","echo hello > $out"],
  [("builder","/bin/sh"),
   ("name","hello"),
   ("out","/nix/store/...-hello"),
   ("system","x86_64-linux")]
)
```

환경에는 명시적 환경 변수와 자동으로 추가된 것들 (`builder`, `out`, `system`, `name`)이 모두 포함됩니다.
