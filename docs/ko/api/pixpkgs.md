# pixpkgs

pix의 저수준 프리미티브 위에 구축된 nixpkgs 스타일 패키지 세트. Nix 패턴을 Python 관용구로 매핑합니다.

## `drv()`

```python
from pixpkgs import drv

pkg = drv(
    name="hello",
    builder="/bin/sh",
    args=["-c", "echo hello > $out"],
)
```

### 시그니처

```python
def drv(
    name: str,
    builder: str,
    system: str = "x86_64-linux",
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    output_names: list[str] | None = None,
    deps: list[Package] | None = None,
    srcs: list[str] | None = None,
) -> Package
```

### 매개변수

| 매개변수 | 기본값 | 설명 |
|---------|--------|------|
| `name` | — | 패키지 이름 (스토어 경로 접미사가 됨) |
| `builder` | — | 빌더 실행 파일 경로 |
| `system` | `"x86_64-linux"` | 빌드 플랫폼 |
| `args` | `[]` | 빌더 인자 |
| `env` | `{}` | 추가 환경 변수 |
| `output_names` | `["out"]` | 출력 이름 |
| `deps` | `[]` | 패키지 의존성 (`inputDrvs`로 추가됨) |
| `srcs` | `[]` | 입력 소스 스토어 경로 |

### 파이프라인

`drv()`는 내부적으로 전체 6단계 derivation 파이프라인을 실행합니다:

```
1. 빈 출력 경로로 Derivation 생성
2. 입력 derivation 해시 수집 (mask_outputs=False)
3. hashDerivationModulo (자신에 대해 mask_outputs=True)
4. make_output_path → 출력 경로를 .outputs와 .env에 채움
5. ATerm으로 직렬화
6. make_text_store_path → .drv 스토어 경로 계산
```

Nix의 `derivation` 내장 함수가 하는 것과 동일하게 표준 환경 변수(`name`, `builder`, `system`, 출력 이름)가 자동으로 추가됩니다.

## `Package`

`drv()`가 반환하는 불변(frozen) 데이터클래스입니다.

### 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `name` | `str` | 패키지 이름 |
| `drv` | `Derivation` | 기반 pix Derivation 객체 |
| `drv_path` | `str` | `.drv` 파일의 스토어 경로 |
| `outputs` | `dict[str, str]` | 출력 이름 → 스토어 경로 매핑 |

### `Package.out`

```python
pkg.out  # "/nix/store/<hash>-hello"
```

`pkg.outputs["out"]`의 단축 — 기본 출력 경로입니다.

### `Package.__str__`

```python
f"echo {pkg} > $out"  # 출력 경로가 삽입됨
```

`pkg.out`을 반환합니다. Nix의 문자열 보간 컨텍스트를 반영합니다 — Nix에서 `${pkg}`를 사용하면 패키지의 기본 출력 경로를 얻습니다.

### `Package.override()`

```python
pkg2 = pkg.override(name="hello-custom", env={"CFLAGS": "-O2"})
```

변경된 인자로 패키지를 재생성합니다. Nix의 `pkg.override`와 같습니다 — 새로운 derivation 해시를 가진 새 Package를 생성합니다.

## `PackageSet`

자동 의존성 주입을 사용하여 상호 의존적인 패키지 세트를 정의하는 기본 클래스입니다.

```python
from pixpkgs import drv, PackageSet, realize
from functools import cached_property

class MyPkgs(PackageSet):
    @cached_property
    def greeting(self):
        return drv(
            name="greeting",
            builder="/bin/sh",
            args=["-c", "echo hello > $out"],
        )

    @cached_property
    def shouter(self):
        return self.call(lambda greeting: drv(
            name="shouter",
            builder="/bin/sh",
            args=["-c", f"read line < {greeting}; echo $line! > $out"],
            deps=[greeting],
        ))

pkgs = MyPkgs()
realize(pkgs.shouter)  # greeting을 먼저 빌드한 다음 shouter 빌드
```

### `PackageSet.call(fn)`

`fn`의 매개변수 이름을 검사하여 `self`의 속성으로 조회합니다. Nix의 `callPackage` 패턴의 Python 등가물입니다 — 의존성이 명시적으로 전달되는 대신 이름으로 주입됩니다.

```python
# 다음 두 표현은 동일합니다:
pkgs.call(lambda greeting: use(greeting))
use(pkgs.greeting)
```

`@cached_property`와 결합하면 지연 평가를 제공합니다 — 패키지는 처음 접근할 때만 생성되고 이후 메모이제이션됩니다.

## `realize()`

```python
from pixpkgs import realize

output_path = realize(pkg)
# "/nix/store/<hash>-hello"
```

### 시그니처

```python
def realize(pkg: Package, conn: DaemonConnection | None = None) -> str
```

Nix 데몬을 통해 패키지를 빌드합니다:

1. 모든 의존성 `.drv` 파일을 `add_text_to_store`를 통해 스토어에 재귀적으로 등록
2. `build_paths`를 호출하여 패키지 빌드
3. 기본 출력 경로를 반환

`conn`이 제공되지 않으면 `DaemonConnection`을 자동으로 열고 닫습니다.
