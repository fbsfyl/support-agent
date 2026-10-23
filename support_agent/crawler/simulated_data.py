"""模拟「已经爬取成功」的数据（正式环境：企业内部论坛）。

这里提供一批企业内部 IT 支持论坛 / 帮助中心的帖子样本，
作为知识库向量库的初始来源；爬虫脚本会每日定时增量爬取新数据入库。
"""

SIMULATED_POSTS = [
    {
        "kb_id": "KB-4401", "source": "IT 论坛",
        "title": "Teams 会议录制文件在哪里查看？如何分享给外部嘉宾？",
        "tags": ["Teams", "会议", "录制", "分享"],
        "content": (
            "Teams 会议录制默认保存到发起人的 OneDrive（非频道会议）或 SharePoint（频道会议）。"
            "查看路径：Teams -> 日历 -> 选择会议 -> 录制和转录。"
            "分享给外部嘉宾：在 OneDrive/SharePoint 中找到录制视频，点击分享，"
            "将链接权限改为「任何拥有链接的人」，并设置到期时间与密码。"
        ),
    },
    {
        "kb_id": "KB-4402", "source": "IT 论坛",
        "title": "OneDrive 同步客户端一直显示「正在处理更改」怎么办？",
        "tags": ["OneDrive", "同步", "缓存"],
        "content": (
            "该问题通常由 Office 上传中心缓存或文件锁导致。处理步骤："
            "1) 右键托盘 OneDrive 图标 -> 暂停同步 -> 恢复同步；"
            "2) 关闭所有 Office 程序，清空 %localappdata%\\Microsoft\\Office\\ 上传中心缓存；"
            "3) 若仍无效，重置 OneDrive（onedrive.exe /reset）。"
        ),
    },
    {
        "kb_id": "KB-4403", "source": "帮助中心",
        "title": "SharePoint Online 文档库版本控制如何启用？保留多少个版本合适？",
        "tags": ["SharePoint", "版本控制", "文档库"],
        "content": (
            "在文档库 -> 设置 -> 库设置 -> 版本控制设置中启用。"
            "默认主版本 500 个。建议：普通文档保留 100 个主版本；"
            "合规要求高的库保留 500 个并开启内容审批。"
        ),
    },
    {
        "kb_id": "KB-4404", "source": "IT 论坛",
        "title": "Outlook 邮箱规则不生效，邮件未自动分类怎么办？",
        "tags": ["Outlook", "邮箱规则", "分类"],
        "content": (
            "1) 确认规则是否勾选「仅客户端」；仅客户端规则需 Outlook 在线才生效。"
            "2) 检查规则顺序，多条规则可能冲突。"
            "3) 使用「立即运行规则」手动触发，查看是否有规则阻止后续处理。"
        ),
    },
    {
        "kb_id": "KB-4405", "source": "帮助中心",
        "title": "Microsoft Teams 如何设置会议背景虚化效果？",
        "tags": ["Teams", "背景虚化", "会议"],
        "content": (
            "会议前：加入会议前在设备设置里选择「背景效果」-> 虚化。"
            "会议中：点击「更多操作 ...」->「应用背景效果」-> 选择虚化或自定义背景图片。"
        ),
    },
    {
        "kb_id": "KB-4406", "source": "IT 论坛",
        "title": "Azure Kubernetes Service 集群无法扩展节点，提示配额不足",
        "tags": ["AKS", "Kubernetes", "容器", "配额"],
        "content": (
            "AKS 节点扩展失败多为订阅 vCPU 配额不足或子网 IP 耗尽。"
            "1) 在 Azure 门户检查订阅用量和配额，提交配额增加申请；"
            "2) 检查节点池所在虚拟网络子网剩余 IP 是否足够；"
            "3) 使用多可用区节点池分散压力。"
        ),
    },
    {
        "kb_id": "KB-4407", "source": "IT 论坛",
        "title": "Microsoft 365 Exchange Online 邮件同步失败，影响大量用户",
        "tags": ["M365", "Exchange", "邮件同步"],
        "content": (
            "先到服务健康中心确认是否为服务事件。若不是："
            "1) 检查 DNS（MX/AutoDiscover/CNAME）记录是否正确；"
            "2) 检查 Exchange Online 连接器和传输规则；"
            "3) 对受影响用户运行 Remote Connectivity Analyzer 排查。"
        ),
    },
    {
        "kb_id": "KB-4408", "source": "IT 论坛",
        "title": "Power BI 数据集刷新超时，DirectQuery 连接 SQL Server 失败",
        "tags": ["Power BI", "DirectQuery", "SQL Server"],
        "content": (
            "1) 确认数据网关在线且版本最新；"
            "2) 检查 SQL Server 是否允许网关服务器访问，防火墙放行 1433；"
            "3) DirectQuery 下避免复杂计算列，改用视图或在源端聚合；"
            "4) 在 Power BI 服务中将刷新超时时间调大。"
        ),
    },
    {
        "kb_id": "KB-4409", "source": "帮助中心",
        "title": "Active Directory 域控制器复制失败，错误代码 8606",
        "tags": ["Active Directory", "域控", "复制"],
        "content": (
            "错误 8606 表示复制入站对象时属性值非法。"
            "1) 运行 repadmin /showrepl 确认复制拓扑；"
            "2) 执行 dcdiag /test:replications 定位问题域控；"
            "3) 排查时钟偏差，确保域控时间同步；"
            "4) 必要时执行非权威还原。"
        ),
    },
    {
        "kb_id": "KB-4410", "source": "IT 论坛",
        "title": "SQL Server 2019 数据库备份作业失败，磁盘空间不足",
        "tags": ["SQL Server", "备份", "磁盘"],
        "content": (
            "1) 检查备份目标磁盘剩余空间，清理历史备份文件；"
            "2) 开启备份压缩（WITH COMPRESSION）；"
            "3) 将备份迁移到网络共享或 Azure Blob；"
            "4) 配置备份保留策略自动清理过期文件。"
        ),
    },
    {
        "kb_id": "KB-4411", "source": "帮助中心",
        "title": "Windows Server 2022 远程桌面许可证过期如何续期",
        "tags": ["Windows Server", "远程桌面", "许可证"],
        "content": (
            "1) 打开「远程桌面授权管理器」查看许可证状态；"
            "2) 激活许可证服务器并安装 RDS CAL；"
            "3) 若使用 AD 激活，确认 SID 正确；"
            "4) 在组策略中指定许可证服务器和授权模式。"
        ),
    },
    {
        "kb_id": "KB-4412", "source": "IT 论坛",
        "title": "企业网络访问内部系统缓慢，如何排查 VPN 与防火墙",
        "tags": ["网络", "VPN", "防火墙", "性能"],
        "content": (
            "1) 使用 tracert / ping 定位延迟节点；"
            "2) 检查防火墙会话数和吞吐是否达到上限；"
            "3) 检查 VPN 网关带宽与加密算法（优先 AES-GCM）；"
            "4) 抓包分析是否存在重传或 MTU 问题。"
        ),
    },
    {
        "kb_id": "KB-4413", "source": "帮助中心",
        "title": "Microsoft 365 组和 Teams 团队的区别与选择",
        "tags": ["M365", "Teams", "组"],
        "content": (
            "Microsoft 365 组是底层身份，附带邮箱、日历、OneNote、SharePoint。"
            "Teams 团队基于 Microsoft 365 组，额外提供聊天与会议。"
            "需要协作聊天选 Teams 团队；仅需共享邮箱/文件可用 Microsoft 365 组。"
        ),
    },
    {
        "kb_id": "KB-4414", "source": "IT 论坛",
        "title": "SharePoint Online 站点权限继承如何断开并自定义",
        "tags": ["SharePoint", "权限", "站点"],
        "content": (
            "在站点设置 -> 站点权限 -> 高级权限设置中，"
            "选择「停止继承权限」，然后按组或用户授予不同级别的访问权限。"
        ),
    },
    {
        "kb_id": "KB-4415", "source": "帮助中心",
        "title": "Outlook 无法连接到 Exchange，提示证书错误",
        "tags": ["Outlook", "Exchange", "证书"],
        "content": (
            "证书错误通常是本机根证书未信任或证书已过期。"
            "1) 检查证书有效期与 SAN 是否包含服务器名；"
            "2) 在企业内网将内部 CA 根证书下发到客户端受信任根；"
            "3) 更新 Outlook 客户端到最新版本。"
        ),
    },
    {
        "kb_id": "KB-4416", "source": "IT 论坛",
        "title": "Power BI 报表发布后数据不刷新，网关配置检查清单",
        "tags": ["Power BI", "网关", "刷新"],
        "content": (
            "1) 确认数据源凭据已在网关中正确配置；"
            "2) 检查网关服务账号是否有数据源读取权限；"
            "3) 确认数据集已启用计划刷新且时区正确；"
            "4) 查看刷新历史中的错误详情。"
        ),
    },
]
