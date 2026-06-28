"""UDPE 系统变量提供方（system）。

设计文档：plans/udpe-design/design.md §九

V1 提供：
- now: 当前时间
- today: 今天日期
- operator: 当前操作员 {id, name}
- company: 企业信息（写死"数智化管理系统"，M1 简化）
- printTime / printUser: 打印时间 / 打印人
"""
from datetime import datetime

from app.core.print import BindContext, VariableProvider


class SystemVarsProvider:
    """系统变量：时间、用户、企业。

    设计文档：plans/udpe-design/design.md §九
    """

    name = "system"

    async def provide(self, ctx: BindContext) -> dict:
        now = datetime.now()
        return {
            "now": now.isoformat(timespec="seconds"),
            "today": now.strftime("%Y-%m-%d"),
            "year": now.year,
            "operator": {
                "id": ctx.operator_id,
                "name": ctx.operator_name or "",
            },
            "company": {
                "name": "数智化管理系统",
                "shortName": "数智化",
            },
            "printTime": now.strftime("%Y-%m-%d %H:%M"),
            "printUser": ctx.operator_name or "",
        }
