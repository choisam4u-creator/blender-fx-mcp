# 공식 MCP 레지스트리 등록 절차

공식 레지스트리(<https://registry.modelcontextprotocol.io>)에 올릴 때 쓰는 메모. **등록은 샘님 Mac에서 직접** 한다
(클라우드 회차는 등록·PyPI 배포를 하지 않는다).

## 파일

- `server.json.example` — 등록용 `server.json` 의 원본. 등록할 때 `server.json` 으로 복사해 쓴다.
- 스키마: `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json` (2026-10-04 기준 최신)
- `tests/test_registry.py` — 네트워크 없이 도는 점검(필수 칸, camelCase, 버전 일치, README 의 `mcp-name`, 환경변수 사용 여부)

## 2026-10-04 점검 결과

| 항목 | 이전 | 지금 |
|---|---|---|
| 스키마 버전 | 2025-07-09 | 2025-12-11 |
| 키 이름 | `registry_type`, `runtime_hint`, `environment_variables`, `is_required` (snake_case — 새 스키마에서 **필수 칸 누락**으로 거부됨) | `registryType`, `runtimeHint`, `environmentVariables`, `isRequired` |
| 버전 | 0.6.0 (pyproject 는 0.6.3) | pyproject 와 같게, 시험으로 강제 |
| PyPI 소유 확인 | README 에 `mcp-name` 없음 | README 2번째 줄에 `<!-- mcp-name: io.github.choisam4u-creator/blender-fx-mcp -->` |
| 설명 길이 | 48자 (상한 100자) | 그대로 |
| 환경변수 형식 | 없음 | `BLENDER_FX_PORT` number, `BLENDER_FX_LANG` choices ko/en, `BLENDER_FX_OUT` filepath |

스키마 전체 검증(네트워크 필요):

```bash
curl -s https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json -o /tmp/server.schema.json
uv run --with jsonschema python -c "import json,jsonschema; jsonschema.validate(json.load(open('server.json.example')), json.load(open('/tmp/server.schema.json'))); print('OK')"
```

## 등록 순서 (샘님 Mac)

1. 버전을 올린다: `pyproject.toml` 과 `server.json.example` 의 `version` 두 곳(`tests/test_registry.py` 가 어긋나면 실패).
2. PyPI 에 그 버전을 올린다(`uv build` → `uv publish`). README 의 `mcp-name` 줄이 패키지 설명에 들어가야 레지스트리가 소유를 확인한다.
3. 게시 도구 설치: `brew install mcp-publisher`
4. `cp server.json.example server.json`
5. `mcp-publisher login github` — 이름이 `io.github.choisam4u-creator/…` 이므로 GitHub 로그인으로 확인된다.
6. `mcp-publisher publish`
7. 확인: `curl "https://registry.modelcontextprotocol.io/v0/servers?search=blender-fx-mcp"`

## 주의

- 같은 버전은 다시 올릴 수 없다. 고칠 게 있으면 버전을 올린다.
- `server.json` 은 등록할 때만 만들고 커밋하지 않는다(원본은 `.example`).
- 토큰·비밀 값은 `server.json` 에 넣지 않는다. 이 서버는 비밀 값이 필요 없다.
