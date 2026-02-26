# 내부 구조

Nix가 실제로 어떻게 동작하는지 — 형식, 프로토콜, 알고리즘을 이를 재구현한 Python 코드를 통해 설명합니다.

각 페이지는 개념 설명과 이를 구현하는 pix 소스 코드에 대한 안내를 함께 제공합니다. 페이지를 읽은 다음 코드를 읽으면 이해가 될 것입니다.

## 여기서 시작하세요

| 페이지 | 답하는 질문 |
|--------|-----------|
| [스토어 경로](store-paths.md) | Nix는 `/nix/store/<hash>-<name>`을 어떻게 계산하나? 왜 32자인가? |
| [NAR 형식](nar-format.md) | NAR 아카이브 안에는 무엇이 있나? 왜 tar가 아닌가? |
| [데몬 프로토콜](daemon-protocol.md) | `nix build`와 `nix-store`는 데몬과 어떻게 통신하나? |
| [Derivation](derivations.md) | `.drv` 파일에는 무엇이 있나? `hashDerivationModulo`는 순환 의존성을 어떻게 해결하나? |
| [Base32 인코딩](base32.md) | Nix는 왜 표준 base32를 사용하지 않나? 무엇이 다른가? |
| [오버레이와 부트스트랩](overlays.md) | 오버레이는 고정점을 통해 어떻게 합성되나? stdenv는 GCC를 어떻게 처음부터 빌드하나? |

## 전체 그림

`nix build nixpkgs#hello`를 실행하면, pix가 다루는 수준에서 다음과 같은 일이 일어납니다:

```
1. Nix가 표현식을 평가 → Derivation 생성

2. Derivation은 ATerm으로 직렬화되어 .drv 파일로 저장
   (derivation.py로 이를 다시 파싱할 수 있음)

3. .drv의 출력 경로는 hashDerivationModulo를 통해 계산:
   - 출력 경로를 비운 .drv를 해싱
   - 그 해시를 make_store_path의 핑거프린트로 사용
   (derivation.py + store_path.py)

4. .drv가 Unix 소켓 프로토콜을 통해 데몬으로 전송
   (daemon.py가 이 프로토콜을 구현)

5. 데몬이 빌드 수행:
   - 입력 소스 실현 (같은 방식으로 NAR 해시를 사용하여
     스토어 경로 계산 — nar.py + store_path.py)
   - 빌더 실행
   - 출력을 스토어 데이터베이스에 등록

6. 데몬을 통해 결과를 조회할 수 있음:
   - is_valid_path, query_path_info
   - NAR 해시와 참조가 기록됨
```

각 단계에 대응하는 pix 모듈이 있습니다. 코드가 충분히 짧아 전체 흐름을 추적할 수 있습니다.
