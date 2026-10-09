#!/usr/bin/env bash
#
# MCP 网关探针：一次跑完"认证门禁 + 九步流水线"的观察点
#
# 用法：
#   bash mcp_probe.sh              跑 7 个基础检查
#   bash mcp_probe.sh --delete     额外跑一次 delete_file（会真的删掉容器数据卷里的 public.txt）
#
# 可覆盖的变量：
#   MCP_URL=http://127.0.0.1:8001/mcp
#   MCP_TOKEN=key_agent_002
#   WRONG_TOKEN=key_wrong_999

MCP_URL="${MCP_URL:-http://127.0.0.1:8001/mcp}"
MCP_TOKEN="${MCP_TOKEN:-key_agent_002}"
WRONG_TOKEN="${WRONG_TOKEN:-key_wrong_999}"
PROTOCOL="2025-06-18"

DO_DELETE=0
if [ "${1:-}" = "--delete" ]; then
    DO_DELETE=1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

title() { printf '\n\033[36m== %s ==\033[0m\n' "$1"; }
pass()  { printf '\033[32m  [通过] %s\033[0m\n' "$1"; }
fail()  { printf '\033[31m  [意外] %s\033[0m\n' "$1"; }

# 把 JSON 排版得好看一点；没有 python3 就原样输出
pretty() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import sys, json
s = sys.stdin.read()
try:
    print(json.dumps(json.loads(s), ensure_ascii=False, indent=2))
except Exception:
    print(s)'
    else
        cat
    fi
}

# 从 SSE 响应里取出 data 行（MCP 的流式 HTTP 用 SSE 格式回包）
sse_data() {
    sed -n 's/^data: //p' "$1" | tail -n 1
}

echo "网关地址：$MCP_URL"
echo "使用身份：$MCP_TOKEN"

# ---------------------------------------------------------------- 1
title "1. 不带钥匙访问（期望 401）"
CODE=$(curl -s -o /dev/null -w '%{http_code}' "$MCP_URL")
echo "  HTTP $CODE"
if [ "$CODE" = "401" ]; then
    pass "没刷证，门不开"
else
    fail "期望 401，实际 $CODE"
fi

# ---------------------------------------------------------------- 2
INIT_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1.0"}}}'

title "2. 用错误的钥匙握手（期望 401）"
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$MCP_URL" \
    -H "Authorization: Bearer $WRONG_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$INIT_PAYLOAD")
echo "  HTTP $CODE"
if [ "$CODE" = "401" ]; then
    pass "假钥匙被数据库挡住了"
else
    fail "期望 401，实际 $CODE"
fi

# ---------------------------------------------------------------- 3
title "3. 用正确钥匙握手（期望 200 + 会话 ID）"
CODE=$(curl -s -D "$WORK/h3" -o "$WORK/b3" -w '%{http_code}' -X POST "$MCP_URL" \
    -H "Authorization: Bearer $MCP_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d "$INIT_PAYLOAD")
SESSION=$(tr -d '\r' < "$WORK/h3" | sed -n 's/^[Mm]cp-[Ss]ession-[Ii]d: *//p')
echo "  HTTP $CODE"
echo "  会话 ID：${SESSION:-（没拿到）}"
if [ "$CODE" = "200" ] && [ -n "$SESSION" ]; then
    pass "钥匙对了，服务端开了个会话"
else
    fail "握手没成功，后面的检查会跳过"
fi

# 会话 ID 是后续请求的通行证
AUTH=(-H "Authorization: Bearer $MCP_TOKEN")
SESS=(-H "mcp-session-id: $SESSION")
PROTO=(-H "MCP-Protocol-Version: $PROTOCOL")
JSON=(-H "Content-Type: application/json")
SSE=(-H "Accept: application/json, text/event-stream")

if [ -n "$SESSION" ]; then

    # ------------------------------------------------------------ 4
    title "4. 告诉服务端“我初始化好了”（通知，无返回）"
    CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$MCP_URL" \
        "${AUTH[@]}" "${SESS[@]}" "${PROTO[@]}" "${JSON[@]}" "${SSE[@]}" \
        -d '{"jsonrpc":"2.0","method":"notifications/initialized"}')
    echo "  HTTP $CODE"

    # ------------------------------------------------------------ 5
    title "5. 列出网关暴露的工具（tools/list）"
    curl -s -o "$WORK/b5" -X POST "$MCP_URL" \
        "${AUTH[@]}" "${SESS[@]}" "${PROTO[@]}" "${JSON[@]}" "${SSE[@]}" \
        -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
    sse_data "$WORK/b5" | pretty

    # ------------------------------------------------------------ 6
    title "6. 读 public.txt（PUBLIC 资源，期望放行并返回内容）"
    curl -s -o "$WORK/b6" -X POST "$MCP_URL" \
        "${AUTH[@]}" "${SESS[@]}" "${PROTO[@]}" "${JSON[@]}" "${SSE[@]}" \
        -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"read_file","arguments":{"file_name":"public.txt"}}}'
    sse_data "$WORK/b6" | pretty

    # ------------------------------------------------------------ 7
    title "7. 读 internal_notes.txt（SECRET 资源，期望被资源策略拒绝）"
    curl -s -o "$WORK/b7" -X POST "$MCP_URL" \
        "${AUTH[@]}" "${SESS[@]}" "${PROTO[@]}" "${JSON[@]}" "${SSE[@]}" \
        -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"read_file","arguments":{"file_name":"internal_notes.txt"}}}'
    sse_data "$WORK/b7" | pretty

    # ------------------------------------------------------------ 8
    if [ "$DO_DELETE" = "1" ]; then
        title "8. 删 public.txt（高风险操作，会真的删掉容器数据卷里的文件）"
        curl -s -o "$WORK/b8" -X POST "$MCP_URL" \
            "${AUTH[@]}" "${SESS[@]}" "${PROTO[@]}" "${JSON[@]}" "${SSE[@]}" \
            -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"delete_file","arguments":{"file_name":"public.txt"}}}'
        sse_data "$WORK/b8" | pretty
        echo "  提示：想恢复，在 gateway 身份下执行 docker compose down -v && docker compose up -d"
    else
        title "8. 跳过 delete_file（加 --delete 参数才会跑）"
    fi
fi

title "看审计记录（需要 docker 权限，gateway 身份或 sudo）"
cat <<'EOF'
  docker exec agent-security-gateway python -c "
import sqlite3
c = sqlite3.connect('/app/data/security.db')
for r in c.execute('select id, agent_id, tool_name, allowed, status, error_code, reason from audit_logs order by id desc limit 10'):
    print(r)
"
EOF
