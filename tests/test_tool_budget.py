# 도구 목록(설명·인자 스키마)은 모든 대화마다 클라이언트 문맥을 차지한다. 군더더기가 다시 붙거나 설명이 끝없이 늘지 않게 상한을 둔다.
# 블렌더 없이 공식 클라이언트(메모리 연결)로 실제로 나가는 목록을 잰다.
import json

import anyio
from mcp import Client

from blender_fx_mcp import server

# 2026-10-12: 33개 도구 25,093자(군더더기를 빼기 전 33,015자). 도구를 더하면 이 수를 올리고 PR 에 이유를 적는다.
TOTAL_BUDGET = 27_000
PER_TOOL_BUDGET = 2_600  # 가장 긴 water·destroy 가 2,400자쯤


async def _tools():
    async with Client(server.mcp) as client:
        return (await client.list_tools()).tools


def _sizes():
    tools = anyio.run(_tools)
    return {t.name: len(json.dumps(t.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False)) for t in tools}, tools


def test_tool_list_fits_budget():
    sizes, _ = _sizes()
    total = sum(sizes.values())
    assert total <= TOTAL_BUDGET, f"도구 목록 {total}자 > {TOTAL_BUDGET}. 설명을 줄이거나 상한을 올린 이유를 PR 에"
    over = {name: n for name, n in sizes.items() if n > PER_TOOL_BUDGET}
    assert not over, f"도구 하나가 {PER_TOOL_BUDGET}자를 넘음: {over}"


def test_tool_list_has_no_filler():
    """pydantic 이 붙이는 인자 title, 문장 도구의 {"result": 문자열} 출력 스키마, 독스트링 들여쓰기를 보내지 않는다."""
    _, tools = _sizes()
    for tool in tools:
        assert "title" not in tool.input_schema, tool.name
        assert all("title" not in prop for prop in tool.input_schema.get("properties", {}).values()), tool.name
        assert tool.output_schema is None, tool.name
        assert "\n    " not in tool.description, tool.name
        assert tool.description == tool.description.strip(), tool.name


def test_drop_titles_keeps_argument_named_title():
    schema = {"title": "fArguments", "type": "object",
              "properties": {"title": {"title": "Title", "type": "string"},
                             "at": {"anyOf": [{"type": "array", "items": {"type": "number", "title": "X"}}, {"type": "null"}],
                                    "title": "At"}}}
    assert server._drop_titles(schema) == {
        "type": "object",
        "properties": {"title": {"type": "string"},
                       "at": {"anyOf": [{"type": "array", "items": {"type": "number"}}, {"type": "null"}]}}}


def test_wrong_argument_type_still_rejected():
    """스키마에서 title 만 뺐고 인자 검사는 그대로다."""
    async def call():
        async with Client(server.mcp) as client:
            return await client.call_tool("clear_snapshots", {"keep": "many"})

    result = anyio.run(call)
    assert result.is_error, result
