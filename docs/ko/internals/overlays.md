# 오버레이와 부트스트랩 고정점

Nix의 오버레이 시스템은 nixpkgs가 100,000개 이상의 패키지를 단일 속성 집합으로 합성하는 방법이자, stdenv 부트스트랩이 도구 체인을 처음부터 재구축하는 방법입니다. 핵심 메커니즘은 **고정점 평가(fixed-point evaluation)**: 오버레이는 아직 존재하지 않는 최종 결과를 참조하며, 지연 평가(laziness)가 이를 가능하게 합니다.

이 페이지에서는 네 가지 Python 구현을 통해 이론을 탐구합니다. 각 구현은 패턴이 어떻게 동작하는지, 그리고 어떻게 깨질 수 있는지를 다르게 보여줍니다.

## Nix 오버레이 모델

오버레이는 두 개의 인자를 받는 함수입니다:

```nix
overlay = final: prev: {
  tools = mkTools { shell = prev.shell; };
};
```

| 인자 | 의미 | 용도 |
|------|------|------|
| `final` | 완성된 결과 (모든 오버레이 적용 후) | 지연 바인딩: `final.gcc`는 가장 파생된 버전을 얻음 |
| `prev` | 이전 레이어 (이 오버레이 적용 전) | 빌드 의존성: `prev.shell`은 이 오버라이드 이전의 버전을 얻음 |

오버레이는 `lib.composeExtensions`를 통해 단일 함수로 합성되고, `lib.fix`를 통해 평가됩니다:

```nix
fix = f: let x = f x; in x;
```

결과 `x`가 `f`에 자기 자신의 인자로 전달됩니다 — 순환 정의이지만 Nix가 지연 평가이기 때문에 동작합니다. 속성 접근이 필요할 때 평가를 트리거합니다.

### 왜 두 개의 인자가 필요한가?

인자 하나로는 충분하지 않습니다. 3단계 부트스트랩을 생각해 보세요:

```
Stage 0:  shell-v0, tools-v0, app (shell + tools 사용)
Stage 1:  tools-v1 (stage0의 shell로 재빌드)
Stage 2:  shell-v1 (stage1의 tools로 재빌드)
```

Stage 2는 `shell`을 오버라이드하고 `prev.tools` (= stage 1의 tools)로 빌드합니다. 그런데 stage 1의 `tools` 오버라이드는 `prev.shell` (= stage 0의 shell)로 빌드되었습니다. 만약 stage 1이 `prev.shell` 대신 `final.shell`을 사용했다면, stage 2의 오버라이드를 보게 되는데 — 이것은 stage 1의 tools에 의존합니다 — 순환이 생깁니다.

```
                    ┌──────────── 순환! ────────────┐
                    │                                │
                    v                                │
final.shell ──> stage2.shell(final.tools)           │
                    │                                │
                    v                                │
            final.tools ──> stage1.tools(final.shell)┘
```

`prev` 인자가 순환을 끊습니다: 각 오버라이드는 최종 값이 아닌 *이전* 단계의 값으로 빌드합니다. `final` 인자는 열린 재귀(open recursion)를 제공합니다: `app`과 같이 오버라이드되지 않은 패키지는 `final.shell`과 `final.tools`를 참조하여 최신 오버라이드를 자동으로 가져옵니다.

---

## 네 가지 Python 구현

네 가지 패턴 모두 **완전한 7단계 nixpkgs 부트스트랩**을 구현합니다 — 부트스트랩 씨앗부터 `hello-2.12.2`까지 196개 derivation, 모두 실제 nixpkgs와 **해시 완전 일치**.

소스: [`experiments/`](https://github.com/jhhuh/pix/tree/master/experiments) — 각 하위 폴더는 부트스트랩과 테스트 파일을 포함한 자체 완결 구조입니다.

### 해시 완전 검증

실험은 Nix 스토어의 실제 `.drv` 파일에서 196개 derivation을 모두 재구성합니다:

| 단계 | 신규 패키지 | 누적 | 주요 빌드 |
|------|:---:|:---:|---|
| stage0 | 4 | 4 | busybox, tarball, bootstrap-tools, stage0-stdenv |
| stage1 | 8 | 12 | binutils-wrapper, gcc-wrapper, gnu-config |
| stage-xgcc | 6 | 18 | xgcc-14.3.0, gmp, mpfr, isl, libmpc |
| stage2 | 44 | 62 | glibc-2.40, binutils, bison, perl (libc 전환) |
| stage3 | 23 | 85 | gcc-14.3.0, linux-headers (컴파일러 전환) |
| stage4 | 19 | 104 | coreutils, bash 재빌드 (도구 전환) |
| final | 63 | 167 | stdenv-linux, gcc-wrapper, coreutils, findutils... |
| hello | 29 | **196** | **hello-2.12.2**, curl, openssl, perl |

모든 derivation이 실제 nixpkgs와 **바이트 동일**합니다 — 모든 `.drv` 경로와 출력 경로가 정확히 일치합니다. 이것은 nixpkgs를 재현하기 위한 것이 아닙니다; **검증 전략**입니다. Nix derivation 해시는 입력으로부터 순수하게 계산되므로, 출력 경로를 비교하는 것만으로 전체 해시 파이프라인(ATerm 직렬화, `hashDerivationModulo`, `make_output_path`, `make_text_store_path`)을 검증할 수 있습니다 — 아무것도 빌드하지 않고.

### A: 클래스 상속

```python
class Stage0(PackageSet):
    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        return {dp: packages[dp] for dp in stages[0]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return dict(self._own_packages)

class Stage1(Stage0):
    @cached_property
    def _prev(self) -> Stage0:
        return Stage0()  # prev = 별도 인스턴스

    @cached_property
    def _own_packages(self) -> dict[str, Package]:
        return {dp: packages[dp] for dp in stages[1]}

    @cached_property
    def all_packages(self) -> dict[str, Package]:
        return {**self._prev.all_packages, **self._own_packages}

# 8개 클래스: Stage0 → Stage1 → StageXgcc → Stage2 → Stage3 → Stage4 → Final → Pkgs
```

**`final`** = `self`. Python의 MRO가 가장 파생된 오버라이드로 해석 — Nix의 `final`과 동일.

**`prev`** = `self._prev`. 부모 클래스의 새 인스턴스를 생성하는 `@cached_property`.

**교훈:** 첫 시도에서는 `self`만 사용하고 `_prev`가 없었습니다 — 아래 [무한 재귀 함정](#infinite-recursion-trap)을 참조하세요.

### B: `__getattr__` 체인

```python
base = StageSet(stage_idx=0)          # 4개 패키지
s1   = OverlaySet(base, stage_idx=1)  # 8개 추가
s2   = OverlaySet(s1, stage_idx=2)    # 6개 추가
...
top  = OverlaySet(s6, stage_idx=7)    # hello 추가
```

**`final`** = `_set_final()`을 통해 체인 아래로 전파되는 공유 참조.

**`prev`** = `_prev` 링크. 각 `OverlaySet`이 이전 레이어를 래핑합니다.

**교훈:** `_final` 참조는 가변 공유 상태입니다. 같은 `AttrSet`을 두 개의 다른 체인에 합성하면, 두 번째 `_set_final()`이 첫 번째를 오염시킵니다.

### C: 지연 고정점

```python
result = fix(compose_overlays([
    base_overlay,          # stage0: 4개 패키지
    stage1_overlay,        # +8
    stage_xgcc_overlay,    # +6
    stage2_overlay,        # +44
    stage3_overlay,        # +23
    stage4_overlay,        # +19
    final_overlay,         # +63
    hello_overlay,         # +29 = 196개 총합
]))
```

**`final`** = `fix()`가 오버레이 함수에 전달하는 `LazyAttrSet`. 속성 접근이 썽크 평가를 트리거합니다.

**`prev`** = 이전 레이어들의 썽크 딕셔너리. 접근: `prev["name"]()`.

**교훈:** 같은 개념에 두 가지 API: `final.attr` (속성 접근) vs `prev["name"]()` (딕셔너리 조회 + 호출). 문자열 키의 오타는 임포트 시가 아닌 런타임에 실패합니다.

### D: 클래스 데코레이터

```python
class Stage0(PackageSet):
    @cached_property
    def _own_packages(self): ...
    @cached_property
    def all_packages(self): return dict(self._own_packages)

@stage_overlay(1)
class Stage1(Stage0): pass

@stage_overlay(2)
class StageXgcc(Stage1): pass

# ... @stage_overlay(7) class Pkgs(Final): pass 까지
```

**`final`** = `self` — 패턴 A와 같은 MRO 기반 지연 바인딩.

**`prev`** = `self._prev` — `@stage_overlay` 데코레이터가 자동으로 주입.

**교훈:** 데코레이터가 모든 배관(`_prev` 생성, `@cached_property` 래핑)을 숨기지만, `type(cls.__name__, (cls,), attrs)`로 동적 클래스를 생성합니다. 데코레이트된 `Stage1`은 작성한 클래스가 아닙니다 — 생성된 서브클래스입니다.

---

## 무한 재귀 함정 { #infinite-recursion-trap }

가장 교훈적인 실패는 실험 A에서 발생했습니다. 첫 시도에서는 모든 곳에서 `self`를 사용했습니다:

```python
class Stage1(Stage0):
    @cached_property
    def tools(self):
        return drv(name="tools-v1", deps=[self.shell], ...)  # ← self.shell

class Stage2(Stage1):
    @cached_property
    def shell(self):
        return drv(name="shell-v1", deps=[self.tools], ...)  # ← self.tools
```

자연스러워 보이지만 `RecursionError`를 발생시킵니다.

### 순환

`Stage2().app`에 접근하면:

```
Stage2().app
  → self.shell                  (MRO → Stage2.shell)
    → self.tools                (MRO → Stage1.tools)
      → self.shell              (MRO → Stage2.shell)
        → self.tools            (MRO → Stage1.tools)
          → ...                 RecursionError!
```

Stage2.shell은 `self.tools`가 필요합니다. Stage1.tools는 `self.shell`이 필요합니다. 둘 다 MRO를 통해 가장 파생된 오버라이드로 해석됩니다. 이 순환은 근본적인 것입니다 — 코드의 버그가 아니라 `final`과 `prev`를 단일 참조로 혼합한 결과입니다.

### `super()`가 도움이 되지 않는 이유

Python의 `super()`는 메서드를 조회하는 클래스를 변경하지만, `self`는 가장 파생된 인스턴스로 남습니다:

```python
class Stage2(Stage1):
    @cached_property
    def shell(self):
        # super().tools → Stage1.tools.__get__(self, Stage2)
        # 하지만 Stage1.tools는 self.shell을 사용 → Stage2.shell → 순환!
        return drv(deps=[super().tools])
```

### `@cached_property`가 도움이 되지 않는 이유

`@cached_property`는 첫 접근 시 결과를 `instance.__dict__`에 저장합니다. 하지만 재귀는 첫 계산 *중에* 발생합니다 — 값이 캐시되기 전에:

```
self.shell  [계산 시작 — 아직 캐시 안 됨]
  → self.tools  [계산 시작 — 아직 캐시 안 됨]
    → self.shell  [아직 계산 중 — 반환할 캐시된 값 없음]
      → RecursionError
```

캐시는 *이미 계산된* 값에 대해서만 순환을 끊을 수 있습니다. 초기 계산 중에는 순환을 끊을 수 없습니다.

### 근본 원인

Nix 오버레이는 두 개의 인자가 있습니다. Python의 `self`는 하나입니다. 해결책: `self._prev`를 두 번째로 추가합니다.

```python
class Stage2(Stage1):
    @cached_property
    def _prev(self):
        return Stage1()  # ← 이전 단계의 별도 인스턴스

    @cached_property
    def shell(self):
        return drv(deps=[self._prev.tools])  # ← final이 아닌 prev
```

이제 `self._prev.tools`는 `Stage1()` 인스턴스를 생성하고, 그 인스턴스 자체에서 `tools`를 해석합니다 (Stage2 인스턴스가 아닌), 순환을 끊습니다.

!!! note "경험 법칙"
    **오버라이드된 메서드**는 빌드 의존성에 `self._prev.X`를 사용합니다 (이전 단계의 값).
    **상속된 메서드**는 `self.X`를 사용합니다 — 지연 바인딩이 열린 재귀를 무료로 제공합니다.

    Nix에서도 같은 규칙이 적용됩니다: 오버레이는 재빌드할 입력에 `prev.X`를, 최종 버전을 원하는 속성에 `final.X`를 사용합니다.

---

## 비교

|                          | A: 상속 | B: `__getattr__` | C: 지연 고정점 | D: 데코레이터 |
|--------------------------|:-:|:-:|:-:|:-:|
| `final` 메커니즘         | `self` (MRO) | `_final` 참조 | `LazyAttrSet` 프록시 | `self` (MRO) |
| `prev` 메커니즘          | `self._prev` (수동) | `_prev` 체인 | `prev` 딕셔너리 | `self._prev` (자동) |
| IDE 자동완성             | 가능 | 불가 | 불가 | 부분적 |
| 타입 검사                | 가능 | 불가 | 불가 | 부분적 |
| 동적 합성                | 불가 | 가능 | 가능 | 불가 |
| 재귀 안전성              | 함정 (문서화) | 무한루프 | 감지 + 진단 | 안전 (데코레이터) |
| Nix 충실도               | 낮음 | 중간 | 높음 | 중간 |
| 메모리 (7단계)           | 7개 인스턴스 트리 | 1개 체인 | 1개 고정점 | 7개 인스턴스 트리 |

### pixpkgs 권장 패턴

**패턴 A (클래스 상속)**가 pixpkgs의 권장 패턴입니다. 표준 구현은 `pixpkgs/bootstrap.py`에 있습니다.

1. **대규모에서 IDE 지원은 필수.** 수천 개의 패키지에서 개발자는 자동완성, 정의로 이동, 타입 검사가 필요합니다.
2. **`PackageSet.call()`을 통한 `callPackage`**는 임의의 수의 패키지로 확장됩니다 (각각 별도 파일).
3. **부트스트랩 단계는 고정** — 동적 합성은 이점 없이 복잡성만 추가합니다.
4. **사용자 수준 커스터마이징**은 `Package.override()` (개별 패키지) 또는 서브클래싱 (셋 수준 변경)으로 작동합니다.
5. **"정적 합성"은 기능** — 부트스트랩 체인을 명시적이고 검사 가능하게 만듭니다.

### 언제 무엇을 사용할 것인가

- **A** — 프로덕션 패키지 셋에 권장. 완전한 IDE 지원, 타입 검사, `callPackage`가 대규모 패키지 수로 확장.
- **B** — 오버레이를 동적으로 합성해야 할 때 (플러그인 시스템).
- **C** — Nix 의미론을 충실하게 모델링할 때 (교육용, Nix 코드 포팅).
- **D** — A의 최소 보일러플레이트 변형이지만, 동적 클래스 생성이 디버깅을 복잡하게 함.

---

## 부록: nixpkgs stdenv 부트스트랩

실제 nixpkgs stdenv 부트스트랩은 7단계의 체인이며, 각 단계는 특수화된 오버레이입니다. 닭과 달걀 문제를 해결합니다: GCC를 빌드하려면 glibc가 필요하지만, glibc를 빌드하려면 GCC가 필요합니다.

### 씨앗

모든 것은 단일 사전 빌드 타볼에서 시작합니다: `bootstrap-tools`. GCC, coreutils, binutils, bash 등 125개의 바이너리와 glibc 및 지원 라이브러리를 포함합니다. 이것이 유일한 외부 바이너리 의존성입니다 — 다른 모든 패키지는 소스에서 재빌드됩니다.

### 단계

| 단계 | 오버라이드 대상 | 주요 빌드 |
|------|----------------|-----------|
| **0** | 없음 (씨앗) | bootstrap-tools를 컴파일러로 사용하는 더미 stdenv |
| **1** | gcc-wrapper, fetchurl | 소스에서 Binutils, perl |
| **xgcc** | gcc (첫 재빌드) | 소스에서 GCC (하지만 부트스트랩 glibc에 링크됨) |
| **2** | **glibc** | xgcc로 컴파일된 실제 glibc-2.40 (**libc 전환**) |
| **3** | **gcc** (최종) | 실제 glibc로 컴파일된 최종 GCC (**컴파일러 전환**) |
| **4** | coreutils, bash, sed, grep, ... | 소스에서 모든 표준 도구 (**도구 전환**) |
| **최종** | 모든 것 조립 | 프로덕션 stdenv — bootstrap-tools에 대한 참조 없음 |

### 세 번의 전환

부트스트랩은 점진적 교체를 통해 순환 의존성을 해결합니다:

```
bootstrap-tools (사전 빌드)
        │
   ┌────┴────┐
   │ Stage 1 │  소스에서 binutils
   └────┬────┘
   ┌────┴────┐
   │  xgcc   │  소스에서 GCC (하지만 부트스트랩 glibc에 링크)
   └────┬────┘
   ┌────┴─────────────────────────┐
   │ Stage 2: LIBC 전환           │  xgcc가 실제 glibc 컴파일
   └────┬─────────────────────────┘
   ┌────┴─────────────────────────┐
   │ Stage 3: 컴파일러 전환        │  실제 glibc가 최종 GCC 컴파일
   └────┬─────────────────────────┘
   ┌────┴─────────────────────────┐
   │ Stage 4: 도구 전환            │  최종 GCC가 coreutils, bash, ... 재빌드
   └────┬─────────────────────────┘
   ┌────┴────┐
   │  최종   │  모든 구성요소 소스에서, 부트스트랩 참조 없음
   └─────────┘
```

**Stage xgcc**가 가장 미묘합니다. xgcc 바이너리 자체는 bootstrap-tools의 쓰레기에 링크되어 있지만 — 그것은 중요하지 않습니다. 중요한 것은 *xgcc가 내보내는 코드*입니다. 그 코드는 stage 2에서 빌드된 실제 glibc에 대해 실행됩니다.

### 실제 오버레이 패턴

각 단계는 오버레이입니다: 일부 패키지를 오버라이드하고 나머지는 이전 단계에서 상속합니다. Stage 2는 glibc를 오버라이드하지만 xgcc 단계에서 xgcc를 상속합니다. Stage 3은 gcc를 오버라이드하지만 stage 2에서 glibc를 상속합니다.

이것이 정확히 우리의 실험이 보여주는 패턴입니다:

- `prev.tools` → "이전 단계의 컴파일러로 glibc를 빌드"
- `final.gcc` → "hello가 gcc를 사용할 때 가장 파생된 버전을 얻음"

최종 stdenv는 `disallowedRequisites`로 완전성을 강제합니다: 최종 출력에서 bootstrap-tools에 대한 참조가 있으면 빌드 실패입니다. 이는 부트스트랩이 완전함을 보장합니다 — 모든 구성요소가 소스에서 재빌드되었습니다.

### hello 패키지

표준 테스트: 부트스트랩이 작동하는 `hello`를 생산할 수 있는가?

```
hello-2.12.2.drv
  builder: bash-5.3p3     (stage 4에서 재빌드)
  stdenv:  stdenv-linux    (최종 stdenv)
  source:  hello-2.12.2.tar.gz (fetchurl로 가져옴)
```

클로저의 196개 derivation — 부트스트랩 씨앗부터 hello까지 — 모두 오버레이 체인을 통해 단일 bootstrap-tools 타볼로 추적됩니다. 네 가지 실험과 표준 `pixpkgs/bootstrap.py`가 전체 체인을 재구성하며, 실제 nixpkgs와 해시가 완전히 일치합니다.
