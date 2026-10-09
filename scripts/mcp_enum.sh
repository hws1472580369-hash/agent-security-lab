#!/usr/bin/env bash
#
# 资源枚举：以"攻击者客户端"的身份，逐个尝试读取文件名，观察网关判定
#
# 用途：不依赖 LLM，直接构造 MCP 请求做资源枚举（协议层攻击）
#
# 用法：
#   bash mcp_enum.sh                    用默认钥匙 key_agent_002
#   bash mcp_enum.sh key_admin_001      换一把钥匙
#   bash mcp_enum.sh key_agent_001      普通身份（预期全部 AUTHORIZATION_DENIED）

MCP_URL="${MCP_URL:-http://127.0.0.1:8001/mcp}"
TOKEN="${1:-key_agent_002}"
FILES="public.txt customer_records.txt internal_notes.txt config.txt secret.txt admin.txt system_config.txt"

echo "网关：$MCP_URL"
echo "身份：$TOKEN"
echo

# ---------- 1) 握手，拿会话 ID ----------
HEADERS=$(curl -s -D- -o /dev/null -X POST "$MCP_URL" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"enum","version":"1.0"}}}')

SESSION=$(printf '%s' "$HEADERS" | tr -d '\r' | sed -n 's/^[Mm]cp-[Ss]ession-[Ii]d: *//p')

if [ -z "$SESSION" ]; then
    echo "!! 握手失败：钥匙无效或网关未启动"
    exit 1
fi

echo "会话：$SESSION"
echo

# ---------- 2) 逐个枚举 ----------
for f in $FILES; do
    BODY=$(curl -s -X POST "$MCP_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "mcp-session-id: $SESSION" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d "{\"jsonrpc\":\"2.0\",\"id\":2,\"method\":\"tools/call\",\"params\":{\"name\":\"read_file\",\"arguments\":{\"file_name\":\"$f\"}}}")

    DATA=$(printf '%s' "$BODY" | sed -n 's/^data: //p' | tail -1)

    # 只提取关键字段，输出成一行
    SHORT=$(printf '%s' "$DATA" | python3 -c '
import json, sys, re
s = sys.stdin.read().strip()
try:
    o = json.loads(s)
    # 工具返回被包在 result.content[0].text 里
    t = o.get("result", {}).get("content", [{}])[0].get("text", "")
    inner = json.loads(t) if t.strip().startswith("{") else {}
    print(inner.get("status", "ALLOWED"), "|", inner.get("error_code"), "|", inner.get("reason", ""))
except Exception:
    print(s[:120])
' 2>/dev/null)

    printf '%-24s %s\n' "$f" "$SHORT"
done

echo
echo "（结果以网关审计表为准；本脚本只负责发请求）"
