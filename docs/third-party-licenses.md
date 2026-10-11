# 제3자 라이선스 / Third-party licenses

## 한국어

blender-fx-mcp 자체는 [MIT](../LICENSE) 입니다. 설치하면 아래 패키지가 함께 깔립니다(`uv.lock` 기준, `mcp[cli]` 와 그 아래 전부).
모두 MIT 프로젝트와 함께 쓰고 재배포해도 되는 허용적 라이선스입니다. 카피레프트(GPL·LGPL·AGPL) 패키지는 없습니다.

- 허용 목록: `MIT`·`MIT-0`·`BSD-2-Clause`·`BSD-3-Clause`·`Apache-2.0`·`ISC`·`PSF-2.0`·`MPL-2.0`·`Unlicense`·`0BSD`. `A OR B` 는 하나만 맞으면 된다.
- 점검: `uv run python scripts/license_check.py`. CI 의 lint 작업이 PR 마다 돌린다. 의존성이 바뀌어 표와 다르면 실패하고 고칠 줄을 알려 준다.
- "조건" 칸이 있는 패키지는 그 환경에서만 설치된다. 그 외에는 모든 환경에 설치된다.
- 블렌더(GPL)는 이 패키지에 들어 있지 않습니다. 레시피는 사용자가 설치한 블렌더 안에서 소켓으로 받은 코드로 실행됩니다.

## English

blender-fx-mcp itself is [MIT](../LICENSE). Installing it also installs the packages below (from `uv.lock`: `mcp[cli]` and everything under it).
All are permissive licenses that can be used and redistributed with an MIT project. There are no copyleft (GPL, LGPL, AGPL) packages.

- Allowed list: `MIT`, `MIT-0`, `BSD-2-Clause`, `BSD-3-Clause`, `Apache-2.0`, `ISC`, `PSF-2.0`, `MPL-2.0`, `Unlicense`, `0BSD`. For `A OR B`, one side is enough.
- Check: `uv run python scripts/license_check.py`. The CI lint job runs it on every PR; it fails and names the row to fix when a dependency changes.
- Packages with a "Condition" are only installed in that environment; the rest are installed everywhere.
- Blender (GPL) is not part of this package. Recipes run inside the Blender you installed, as code received over the socket.

## 표 / Table

| 패키지 / Package | 라이선스 / License (SPDX) | 조건 / Condition |
|---|---|---|
| `annotated-doc` | `MIT` | — |
| `annotated-types` | `MIT` | — |
| `anyio` | `MIT` | — |
| `attrs` | `MIT` | — |
| `cffi` | `MIT-0` | — |
| `click` | `BSD-3-Clause` | — |
| `colorama` | `BSD-3-Clause` | Windows |
| `cryptography` | `Apache-2.0 OR BSD-3-Clause` | — |
| `exceptiongroup` | `MIT` | Python < 3.11 |
| `h11` | `MIT` | — |
| `httpcore2` | `BSD-3-Clause` | — |
| `httpx2` | `BSD-3-Clause` | — |
| `httpx2-jsfetch` | `BSD-3-Clause` | Pyodide/Emscripten |
| `idna` | `BSD-3-Clause` | — |
| `jsonschema` | `MIT` | — |
| `jsonschema-specifications` | `MIT` | — |
| `markdown-it-py` | `MIT` | — |
| `mcp` | `MIT` | — |
| `mcp-types` | `MIT` | — |
| `mdurl` | `MIT` | — |
| `opentelemetry-api` | `Apache-2.0` | — |
| `pycparser` | `BSD-3-Clause` | — |
| `pydantic` | `MIT` | — |
| `pydantic-core` | `MIT` | — |
| `pygments` | `BSD-2-Clause` | — |
| `pyjwt` | `MIT` | — |
| `python-dotenv` | `BSD-3-Clause` | — |
| `python-multipart` | `Apache-2.0` | — |
| `pywin32` | `PSF-2.0` | Windows |
| `referencing` | `MIT` | — |
| `rich` | `MIT` | — |
| `rpds-py` | `MIT` | — |
| `shellingham` | `ISC` | — |
| `sse-starlette` | `BSD-3-Clause` | — |
| `starlette` | `BSD-3-Clause` | — |
| `truststore` | `MIT` | — |
| `typer` | `MIT` | — |
| `typing-extensions` | `PSF-2.0` | — |
| `typing-inspection` | `MIT` | — |
| `uvicorn` | `BSD-3-Clause` | — |
