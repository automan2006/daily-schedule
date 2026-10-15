# 连接与字段

依赖 Google Calendar 与 Todoist: To Do List & Calendar 两个已有应用，账号凭据由宿主管理。工具前缀可随平台变化，以当次工具定义为准；不把本机工具名、用户 ID 或旧时区固化为运行条件。

## Todoist

- user_info：校验当前时区与账户能力。find_tasks/find_tasks_by_date/search：查找候选并处理分页。fetch_object(type="task", id, includeChildren=true)：修改前读取详情、删除前识别子任务。
- add_tasks：每批最多 25 条；projectId 默认 "inbox"。priority 使用字符串 p1/p2/p3/p4，不能传整数。deadlineDate 只支持 YYYY-MM-DD；dueString 可表达执行日期、时间或重复规则。不将 IANA 时区名拼到 dueString 后面。
- update_tasks：仅发送变化字段；deadlineDate="remove" 清截止，dueString="remove" 清执行日期。labels 替换整个数组，要保留未改标签；projectId/sectionId/parentId 仅移动时发送。
- reschedule_tasks：重复任务单次改期优先此工具；date 支持 YYYY-MM-DD 或 YYYY-MM-DDTHH:MM:SS，日期形式可能保留原时刻，操作后读回。
- complete_tasks / uncomplete_tasks：完成与恢复；必须检查重复规则推进和返回结果。
- delete_object：任务删除仅使用 type="task" 和已核实且属于用户指令范围的 ID；不是删除项目的入口。
- add_reminders：按实际 schema 和账户支持设置。若用户需要账户不支持的硬截止或提醒，只降级该字段，报告限制；其他合法任务仍可记录。
- 计划日期与硬截止不应相互覆盖。描述可使用“最晚截止（北京时间）：YYYY-MM-DD HH:mm”和“关联日历：calendar_id / event_id / 已返回链接”保留无法完整表达的信息。修改时保留其他文字。

## Google Calendar

- list_calendars：默认 primary，可用返回 ID 选择其他可写日历。search_events 使用显式 time_min/time_max 与 timezone_str="Asia/Shanghai"；工具缺省时区可能不同，不依赖它。按窗口翻页，不把第一页当作完整列表。
- get_availability 或搜索并读回重叠日程：检查目标时间段，必要时读取实际参与占用的日历。read_event/batch_read_event：获取真实字段与关联。
- create_event：定时日程使用带 +08:00 或已正确换算的 RFC3339 start_time/end_time，并传 timezone_str。纯个人安排 attendees=[]，除非用户明确要求邀请人；不主动建 Meet 或发送邀请。
- 全天日程只使用 start_date/end_date，结束日期为不包含当日的边界：单日 10 月 16 日事件结束值为 10 月 17 日。跨天任务显示 10 月 15—18 日时，start_date=2026-10-15、end_date=2026-10-19，并设置 transparency="transparent"、attendees=[]。精确截止时刻写入描述，不混入定时边界。
- update_event：只改要求字段；切换全天/定时需同时提供起止边界。保留参与人和重复规则。支持 update_scope=this_instance/entire_series/this_and_following，以实际实例/系列详情确定目标。
- this_and_following 不是原子操作，失败后停止重复写入，读取原系列与可能新建的后续系列，报告可验证的影响。
- delete_event：只有 event_id/calendar_id，没有单独删除范围参数。查明与指令范围对应的实例 ID 或主系列 ID 后直接使用；无法表达“本次及以后”等请求时不要猜测操作。
- 周期条目用描述标记 Daily Schedule 类型=period、Todoist task ID、原始周期开始日期、截止与优先级；定时执行块标记类型=execution。不要从标题相似推定类型。修改截止只更新 period 边界，不覆盖 execution。
- reminders 根据用户明确要求和工具 schema 设置。日历没有通用 Todoist 优先级字段；若用户要求日程优先级，可写入描述，不伪装为原生任务优先级。

工具返回 successCount/failureCount、failures 或 isError 时逐项检查；通用“Action completed”不是关键日期或写入正确的充分证据，要检查结构化结果并读回。
