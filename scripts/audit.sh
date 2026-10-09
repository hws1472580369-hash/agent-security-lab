#!/usr/bin/env bash
#
# 查看网关审计记录
#
# 用法（在虚拟机里执行；vmadmin 身份要加 sudo）：
#   sudo bash audit.sh           显示 id > 125 的记录（真实组正式轮）
#   sudo bash audit.sh 108       显示 id > 108 的记录（含预备轮）
#   sudo bash audit.sh 0         显示全部记录
#
# gateway 身份下不加 sudo 也行。

SINCE="${1:-125}"

docker exec agent-security-gateway python -c "
import sqlite3
since = $SINCE
c = sqlite3.connect('/app/data/security.db')
rows = list(c.execute(
    'select id,agent_id,tool_name,arguments,status,error_code,risk_score '
    'from audit_logs where id > ? order by id', (since,)))
print()
print('新增', len(rows), '条（id >', since, '）')
for r in rows:
    print(r)
"
