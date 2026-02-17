# pix

**읽기 쉬운 Python으로 Nix 내부 구조를 탐구합니다.**

Nix의 핵심 알고리즘 — 스토어 경로 해싱, NAR 직렬화, derivation 파싱, 데몬 와이어 프로토콜 — 은 수십 개의 C++ 소스 파일에 걸쳐 묻혀 있습니다. pix는 각각을 간결한 Python으로 재구현하여 로직을 직접 읽고, 수정하고, 한 줄씩 따라갈 수 있게 합니다.

모든 모듈은 실제 `nix` CLI와 동일한 출력을 생성하며, 테스트 스위트로 검증됩니다. 코드 자체가 문서이고, 이 페이지들은 그에 대한 해설입니다.

## Nix 내부에는 무엇이 있는가

`nix build`를 실행하면 내부적으로 많은 일이 일어납니다. pix는 이를 한 번에 하나씩 이해할 수 있는 조각으로 나눕니다:

| 개념 | Nix가 하는 일 | pix 모듈 | 문서 |
|------|-------------|----------|------|
| **Base32** | 스토어 경로 해시를 위한 커스텀 인코딩 — RFC 4648이 아님 | [`base32.py`](api/base32.md) | [차이점](internals/base32.md) |
| **해시 압축** | SHA-256 (32 B)을 160비트 (20 B)로 XOR-폴드 | [`hash.py`](api/hash.md) | [스토어 경로 계산에서](internals/store-paths.md) |
| **NAR** | 결정론적 아카이브 형식 — 타임스탬프 없음, uid 없음, 오직 콘텐츠만 | [`nar.py`](api/nar.md) | [와이어 형식 명세](internals/nar-format.md) |
| **스토어 경로** | 핑거프린트 문자열로부터 `/nix/store/<hash>-<name>` 계산 | [`store_path.py`](api/store_path.md) | [전체 알고리즘](internals/store-paths.md) |
| **Derivation** | ATerm 형식의 `.drv` 파일; `hashDerivationModulo`로 순환 의존성 해결 | [`derivation.py`](api/derivation.md) | [형식 + 해싱](internals/derivations.md) |
| **데몬 프로토콜** | uint64-LE 프레이밍, stderr 로그 스트림, 오퍼레이션 옵코드를 사용하는 Unix 소켓 | [`daemon.py`](api/daemon.md) | [프로토콜 명세](internals/daemon-protocol.md) |

## pixpkgs — pix 위에 쌓기

내부 구조를 이해했다면, pixpkgs는 그 위에 nixpkgs 스타일의 패키지 세트를 구축하는 방법을 보여줍니다. Nix 패턴을 Python 관용구로 매핑합니다:

| Nix 패턴 | Python 관용구 | pixpkgs 모듈 |
|----------|-------------|-------------|
| `mkDerivation` | `drv()` 함수 → `Package` 데이터클래스 | [`drv.py`](api/pixpkgs.md#drv) |
| `callPackage` | `inspect.signature` + `getattr` | [`package_set.py`](api/pixpkgs.md#packageset) |
| 문자열 보간 (`${pkg}`) | 출력 경로를 반환하는 `__str__` | [`drv.py`](api/pixpkgs.md#package) |
| `pkg.override` | 병합된 kwargs로 `drv()` 재호출 | [`drv.py`](api/pixpkgs.md#packageoverride) |
| `nix-store --realize` | `realize()` → 데몬 `add_text_to_store` + `build_paths` | [`realize.py`](api/pixpkgs.md#realize) |

자세한 내용은 [pixpkgs API 레퍼런스](api/pixpkgs.md)를 참고하세요.

## 읽는 순서

모듈들은 서로 의존합니다. 아래에서부터 시작하세요:

```
pix (Nix 내부 구조):
  1. base32.py        ← 가장 단순: 인코딩만
  2. hash.py          ← 함수 하나: XOR-폴드
  3. nar.py           ← 직렬화 형식, hash 사용
  4. store_path.py    ← 핵심 알고리즘, base32 + hash 사용
  5. derivation.py    ← 파싱 + hashDerivationModulo 트릭
  6. daemon.py        ← 독립적: Unix 소켓 와이어 프로토콜

pixpkgs (패키지 세트 레이어, pix 사용):
  7. drv.py           ← drv() + Package: mkDerivation 등가물
  8. package_set.py   ← PackageSet.call(): callPackage 등가물
  9. realize.py       ← .drv를 스토어에 쓰고 데몬으로 빌드
```

각 pix 파일은 자체적으로 완결되며 150줄 미만입니다. 전체 코드베이스를 한 번에 읽을 수 있습니다.

## 직접 해보기

```bash
nix develop

# pix가 nix와 정확히 같은 해시를 계산하는지 확인
python -m pix hash-path ./pix/base32.py --base32
nix hash path ./pix/base32.py --type sha256 --base32
# 같은 출력

# 스토어 경로 계산 후 데몬을 통해 검증
python -m pix store-path ./pix --name pix-source
python -m pix add-text hello.txt "hello world"
python -m pix drv-show /nix/store/...-hello.drv
```

## 검증

```bash
pytest tests/ pixpkgs/tests/ -v   # 41개 테스트, 모두 실제 nix와 비교
```

## 이 문서 사용법

- **[내부 구조](internals/index.md)** — 여기서 시작하세요. 다이어그램, 헥스 덤프, 프로토콜 트레이스와 함께 _Nix가 어떻게 동작하는지_ 설명합니다.
- **[API 레퍼런스](api/index.md)** — 각 모듈의 함수 시그니처와 사용 예제.
- **[CLI 레퍼런스](cli.md)** — 빠른 실험을 위한 `python -m pix` 명령어.
