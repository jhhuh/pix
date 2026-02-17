# API 레퍼런스

각 모듈은 하나의 Nix 개념을 자체적으로 완결된 형태로 구현합니다. 외부 의존성 없이 표준 라이브러리만 사용합니다.

## 모듈

| 모듈 | 줄 수 | 구현 내용 |
|------|-------|----------|
| [`pix.base32`](base32.md) | ~40 | Nix base32 인코딩 — 커스텀 알파벳, 역순 비트 추출 |
| [`pix.hash`](hash.md) | ~20 | SHA-256 래퍼 + XOR-폴드 압축 |
| [`pix.nar`](nar.md) | ~80 | NAR 아카이브 직렬화 (파일, 디렉터리, 심링크) |
| [`pix.store_path`](store_path.md) | ~70 | text, source, fixed-output, derivation 출력의 스토어 경로 핑거프린팅 |
| [`pix.derivation`](derivation.md) | ~250 | ATerm 파서/시리얼라이저 + `hashDerivationModulo` |
| [`pix.daemon`](daemon.md) | ~270 | Unix 소켓 클라이언트: 핸드셰이크, stderr 드레이닝, 스토어 오퍼레이션 |

## pixpkgs 모듈

| 모듈 | 줄 수 | 구현 내용 |
|------|-------|----------|
| [`pixpkgs.drv`](pixpkgs.md#drv) | ~140 | `drv()` 생성자 + `Package` 데이터클래스 — `mkDerivation` 등가물 |
| [`pixpkgs.package_set`](pixpkgs.md#packageset) | ~30 | `call()`을 가진 `PackageSet` — `callPackage` 등가물 |
| [`pixpkgs.realize`](pixpkgs.md#realize) | ~30 | `.drv`를 스토어에 쓰고 데몬으로 빌드 |

## 의존성 그래프

```
pixpkgs
  drv ─────────── derivation + store_path
  package_set     (독립적 — inspect만 사용)
  realize ──────── daemon

pix
  daemon  (독립적 — 와이어 프로토콜만)

  store_path ─── hash
      │            │
      └── base32   │
                   │
  nar ─────────────┘

  derivation ─── hash
```

순환 의존성 없음. `daemon`은 완전히 독립적입니다 — 로컬 해시 계산 없이 바이너리 프로토콜을 직접 사용합니다.

## 코드 읽기

모듈들은 위에서 아래로 읽도록 설계되어 있습니다. 각 파일은 형식이나 프로토콜을 설명하는 docstring으로 시작한 다음, 가장 직관적인 방식으로 구현합니다.

알고리즘이 _왜_ 그런 방식으로 동작하는지 이해하려면 [내부 구조](../internals/index.md) 섹션을 참고하세요. _어떻게_ 구현되어 있는지 보려면 소스를 직접 읽으세요 — 전부 `pix/`와 `pixpkgs/`에 있습니다.
