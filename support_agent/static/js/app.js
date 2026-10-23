// Support Agent 智能工单系统 - 前端逻辑
const api = async (path, opts = {}) => {
    const res = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
        body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) throw new Error('请求失败 ' + res.status);
    return res.json();
};

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

const AV_COLORS = ['#0078D4', '#107C10', '#C239B3', '#D13438', '#038387', '#7F5BC8', '#B35A00', '#3B79D0'];
function avatarColor(name) {
    let h = 0;
    for (let i = 0; i < (name || '').length; i++) h = (h * 31 + name.charCodeAt(i)) % 100000;
    return AV_COLORS[h % AV_COLORS.length];
}
function avatar(name, size) {
    const s = size || 28;
    const ch = (name || '?').trim().charAt(0);
    return `<span class="avatar" style="width:${s}px;height:${s}px;font-size:${Math.round(s * 0.42)}px;background:${avatarColor(name)}">${esc(ch)}</span>`;
}

function typeBadge(t) {
    return t === '技术'
        ? '<span class="px-2 py-1 bg-orange-50 text-orange-600 text-xs font-medium rounded">技术</span>'
        : '<span class="px-2 py-1 bg-blue-50 text-ms-blue text-xs font-medium rounded">产品</span>';
}
function priorityBadge(p) {
    const map = {
        P0: 'bg-ms-danger/10 text-ms-danger',
        P1: 'bg-ms-warning/15 text-ms-warning',
        P2: 'bg-gray-100 text-ms-muted',
    };
    return `<span class="px-2 py-0.5 ${map[p] || map.P2} text-xs font-semibold rounded">${esc(p || 'P2')}</span>`;
}
function statusBadge(s) {
    const map = {
        intake: ['bg-gray-100 text-ms-muted', '#A19F9D'],
        classified: ['bg-ms-light text-ms-blue', '#0078D4'],
        processing: ['bg-yellow-50 text-ms-warning', '#FFB900'],
        review: ['bg-orange-50 text-orange-600', '#F7630C'],
        assigned: ['bg-blue-50 text-ms-blue', '#0078D4'],
        replied: ['bg-green-50 text-ms-success', '#107C10'],
        resolved: ['bg-green-50 text-ms-success', '#107C10'],
        rejected: ['bg-red-50 text-ms-danger', '#D13438'],
    };
    const label = {
        intake: '工单接入', classified: '已分类', processing: '处理中', review: '待人工评估',
        assigned: '已分派', replied: '已回复', resolved: '已解决', rejected: '已驳回',
    };
    const [cls, dot] = map[s] || map.intake;
    return `<span class="status-badge ${cls}"><span class="w-1.5 h-1.5 rounded-full" style="background:${dot}"></span>${label[s] || s}</span>`;
}

function toast(msg, isError) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast show' + (isError ? ' error' : '');
    setTimeout(() => { el.className = 'toast'; }, 2600);
}

// ---------------- 导航 ----------------
document.querySelectorAll('.sidebar-item').forEach(item => {
    item.addEventListener('click', e => {
        e.preventDefault();
        document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById('view-' + item.dataset.view).classList.add('active');
        loadView(item.dataset.view);
    });
});

function loadView(name) {
    ({ dashboard: loadDashboard, tickets: loadTickets, agent: loadAgent,
       team: loadTeam, analytics: loadAnalytics, settings: loadSettings }[name] || (() => {}))();
}

// ---------------- 看板 ----------------
async function loadDashboard() {
    const d = await api('/api/dashboard');
    document.getElementById('view-dashboard').innerHTML = dashboardHTML(d);
    bindDashboard(d);
}

function dashboardHTML(d) {
    const k = d.kpi, f = d.flow;
    return `
    <div class="mb-8">
        <h1 class="text-2xl font-semibold text-ms-text mb-1">智能工单看板</h1>
        <p class="text-ms-muted text-sm">实时监控工单流转，智能分派与自动回复</p>
    </div>

    <div class="grid grid-cols-4 gap-5 mb-8">
        ${kpiCard('ms-blue', 'ms-light', '今日工单数', k.today_count, '↑ 12%', 'ms-success', '较昨日 +26', icon1)}
        ${kpiCard('ms-success', 'green-50', '自动解决率', k.auto_rate + '%', '↑ 3.2%', 'ms-success', '本月目标 70%', icon2)}
        ${kpiCard('ms-warning', 'yellow-50', '待分派工单', k.pending, '↑ 5', 'ms-danger', '平均等待 4.2 分钟', icon3)}
        ${kpiCard('purple-500', 'purple-50', '平均响应时间', '2.3<span class="text-lg text-ms-muted font-normal">min</span>', '↓ 0.5', 'ms-success', '行业平均 5.8 min', icon3)}
    </div>

    <div class="ms-card p-6 mb-8">
        <div class="flex items-center justify-between mb-6">
            <h2 class="text-base font-semibold text-ms-text">工单处理流程</h2>
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 bg-ms-success rounded-full pulse-dot"></span>
                <span class="text-xs text-ms-muted">系统运行正常</span>
            </div>
        </div>
        <div class="flex items-center justify-between px-4">
            ${flowNode(f.intake, 'ms-blue', iconChat, '工单接入', '多渠道统一接入', f.intake + ' 个/当前')}
            ${flowNode(f.classified, 'ms-blue', iconBulb, '智能分类', 'NLP 意图识别', '已分类 ' + f.classified)}
            ${flowNode(f.processing, 'ms-blue', iconSwap, '自动处理/分派', 'Agent 回复 / 人工分派', '处理中 ' + f.processing)}
            ${flowNodeLast(f.resolved, 'ms-success', iconCheck, '解决闭环', '满意度回访', '已完成 ' + f.resolved)}
        </div>
    </div>

    <div class="grid grid-cols-2 gap-6 mb-8">
        ${pendingPanel(d.pending)}
        ${agentPanel(d.agent)}
    </div>

    ${recentTable(d.recent)}
    `;
}

const icon1 = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>`;
const icon2 = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>`;
const icon3 = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>`;
const iconChat = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>`;
const iconBulb = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>`;
const iconSwap = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>`;
const iconCheck = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>`;
const iconGear = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>`;

function kpiCard(color, iconBg, label, value, delta, deltaColor, sub, icon) {
    return `
    <div class="kpi-card ms-card p-5">
        <div class="absolute top-0 left-0 right-0 h-[3px]" style="background:${color}"></div>
        <div class="flex items-center justify-between mb-3">
            <span class="text-ms-muted text-sm font-medium">${label}</span>
            <div class="w-8 h-8 bg-${iconBg} rounded-lg flex items-center justify-center">
                <svg class="w-4 h-4" style="color:${color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icon}</svg>
            </div>
        </div>
        <div class="flex items-end gap-2">
            <span class="text-3xl font-bold text-ms-text">${value}</span>
            <span class="text-${deltaColor} text-sm font-medium mb-1">${delta}</span>
        </div>
        <span class="text-ms-muted text-xs">${sub}</span>
    </div>`;
}

function flowNode(count, color, icon, title, sub, badge) {
    return `
    <div class="flow-line flex-1 flex flex-col items-center">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg mb-3" style="background:${color}">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icon}</svg>
        </div>
        <span class="text-sm font-semibold text-ms-text mb-1">${title}</span>
        <span class="text-xs text-ms-muted">${sub}</span>
        <div class="mt-2 px-3 py-1 bg-ms-light rounded-full">
            <span class="text-xs font-medium text-ms-blue">${badge}</span>
        </div>
    </div>`;
}
function flowNodeLast(count, color, icon, title, sub, badge) {
    return `
    <div class="flex-1 flex flex-col items-center">
        <div class="w-14 h-14 rounded-2xl flex items-center justify-center shadow-lg mb-3" style="background:${color}">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icon}</svg>
        </div>
        <span class="text-sm font-semibold text-ms-text mb-1">${title}</span>
        <span class="text-xs text-ms-muted">${sub}</span>
        <div class="mt-2 px-3 py-1 bg-green-50 rounded-full">
            <span class="text-xs font-medium text-ms-success">${badge}</span>
        </div>
    </div>`;
}

function pendingPanel(list) {
    const items = (list || []).map(t => {
        const top = t.candidates && t.candidates[0];
        return `
        <div class="border border-ms-border rounded-xl p-4 hover:border-ms-blue transition-colors">
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-2">${priorityBadge(t.priority)}<span class="text-sm font-semibold text-ms-text">${esc(t.ticket_no)}</span></div>
                <span class="text-xs text-ms-muted">${relTime(t.created_at)}</span>
            </div>
            <p class="text-sm text-ms-text mb-3 line-clamp-2">${esc(t.title)}</p>
            <div class="flex items-center gap-2 mb-3">${(t.tags || []).slice(0, 2).map(x => `<span class="px-2 py-0.5 bg-blue-50 text-ms-blue text-xs rounded">${esc(x)}</span>`).join('')}</div>
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    ${avatar(top ? top.name : '--', 28)}
                    <div>
                        <p class="text-xs font-medium text-ms-text">推荐：${top ? esc(top.name) : '暂无'}</p>
                        <p class="text-xs text-ms-muted">匹配度 ${top ? Math.round(top.score * 100) + '%' : '--'}</p>
                    </div>
                </div>
                <button class="px-4 py-1.5 bg-ms-blue text-white text-xs font-medium rounded-lg hover:bg-ms-dark transition-colors" onclick="assignTicket(${t.id})">一键分派</button>
            </div>
        </div>`;
    }).join('');
    return `
    <div class="ms-card">
        <div class="p-5 border-b border-ms-border">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 bg-orange-50 rounded-lg flex items-center justify-center">
                        <svg class="w-4 h-4 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">${iconGear}</svg>
                    </div>
                    <div><h3 class="text-base font-semibold text-ms-text">技术工单自动分派</h3>
                    <p class="text-xs text-ms-muted mt-0.5">基于技能匹配与负载均衡</p></div>
                </div>
                <span class="status-badge bg-orange-50 text-orange-600"><span class="w-1.5 h-1.5 bg-orange-500 rounded-full"></span>${(list || []).length} 待分派</span>
            </div>
        </div>
        <div class="p-4 space-y-3 max-h-[420px] overflow-y-auto scrollbar-thin">${items || '<p class="text-sm text-ms-muted text-center py-8">暂无待分派工单</p>'}</div>
        <div class="p-4 border-t border-ms-border text-center"><button class="text-sm text-ms-blue font-medium hover:underline" onclick="viewPendingAll()">查看全部待分派工单 →</button></div>
    </div>`;
}

function agentPanel(list) {
    const items = (list || []).map(t => agentItem(t)).join('');
    return `
    <div class="ms-card">
        <div class="p-5 border-b border-ms-border">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 bg-ms-light rounded-lg flex items-center justify-center">
                        <svg class="w-4 h-4 text-ms-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icon2}</svg>
                    </div>
                    <div><h3 class="text-base font-semibold text-ms-text">Agent 自动处理中心</h3>
                    <p class="text-xs text-ms-muted mt-0.5">搜索内部论坛与知识库自动回复</p></div>
                </div>
                <span class="status-badge bg-green-50 text-ms-success"><span class="w-1.5 h-1.5 bg-ms-success rounded-full pulse-dot"></span>运行中</span>
            </div>
        </div>
        <div class="p-4 space-y-3 max-h-[420px] overflow-y-auto scrollbar-thin">${items || '<p class="text-sm text-ms-muted text-center py-8">暂无 Agent 处理记录</p>'}</div>
        <div class="p-4 border-t border-ms-border text-center"><button class="text-sm text-ms-blue font-medium hover:underline" onclick="viewAgentAll()">查看全部 Agent 处理记录 →</button></div>
    </div>`;
}

function agentItem(t) {
    const conf = t.reply_confidence != null ? t.reply_confidence : 0;
    const pct = Math.round(conf * 100);
    const color = conf >= 0.7 ? 'ms-success' : (conf >= 0.5 ? 'ms-warning' : 'ms-danger');
    if (t.status === 'processing' || !t.auto_reply) {
        return `
        <div class="border border-ms-blue/30 rounded-xl p-4 bg-ms-light/30">
            <div class="flex items-start justify-between mb-3">
                <div class="flex items-center gap-2"><span class="px-2 py-0.5 bg-ms-info/10 text-ms-info text-xs font-semibold rounded">产品</span><span class="text-sm font-semibold text-ms-text">${esc(t.ticket_no)}</span></div>
                <span class="text-xs text-ms-muted">${relTime(t.created_at)}</span>
            </div>
            <p class="text-sm text-ms-text mb-3">${esc(t.title)}</p>
            <div class="agent-processing rounded-lg p-3 mb-3">
                <div class="flex items-center gap-2 mb-2">
                    <svg class="w-4 h-4 text-ms-blue animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>
                    <span class="text-xs font-medium text-ms-blue">Agent 正在搜索内部知识库...</span>
                </div>
                <div class="flex gap-2"><span class="px-2 py-0.5 bg-white/60 text-ms-muted text-xs rounded">内部知识库</span><span class="px-2 py-0.5 bg-white/60 text-ms-muted text-xs rounded">IT 论坛</span></div>
            </div>
            <div class="text-right"><button class="px-3 py-1.5 border border-ms-blue text-ms-blue text-xs font-medium rounded-lg hover:bg-ms-light" onclick="processTicket(${t.id})">立即处理</button></div>
        </div>`;
    }
    const low = conf < 0.5;
    return `
    <div class="border ${low ? 'border-ms-border' : 'border-ms-border'} rounded-xl p-4">
        <div class="flex items-start justify-between mb-3">
            <div class="flex items-center gap-2"><span class="px-2 py-0.5 bg-ms-info/10 text-ms-info text-xs font-semibold rounded">产品</span><span class="text-sm font-semibold text-ms-text">${esc(t.ticket_no)}</span></div>
            <span class="text-xs text-ms-muted">${relTime(t.created_at)}</span>
        </div>
        <p class="text-sm text-ms-text mb-3">${esc(t.title)}</p>
        ${low ? `<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-3"><div class="flex items-center gap-2"><svg class="w-4 h-4 text-ms-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg><span class="text-xs font-medium text-ms-warning">置信度较低，建议人工复核</span></div></div>`
        : `<div class="bg-gray-50 rounded-lg p-3 mb-3"><div class="flex items-center gap-2 mb-2"><svg class="w-4 h-4 text-ms-success" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg><span class="text-xs font-medium text-ms-success">已生成自动回复</span></div><p class="text-xs text-ms-muted line-clamp-2">${esc(t.auto_reply)}</p></div>`}
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-1"><span class="text-xs text-ms-muted">置信度</span><div class="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden"><div class="h-full rounded-full" style="width:${pct}%;background:${color === 'ms-success' ? '#107C10' : color === 'ms-warning' ? '#FFB900' : '#D13438'}"></div></div><span class="text-xs font-medium" style="color:${color === 'ms-success' ? '#107C10' : color === 'ms-warning' ? '#FFB900' : '#D13438'}">${pct}%</span></div>
            <div class="flex gap-2">
                <button class="px-3 py-1.5 border border-gray-300 text-ms-muted text-xs font-medium rounded-lg hover:bg-gray-50" onclick="editReply(${t.id})">编辑</button>
                <button class="px-3 py-1.5 border border-gray-300 text-ms-muted text-xs font-medium rounded-lg hover:bg-gray-50" onclick="rejectTicket(${t.id})">转人工</button>
                <button class="px-3 py-1.5 bg-ms-success text-white text-xs font-medium rounded-lg hover:bg-green-700" onclick="approveTicket(${t.id})">发送</button>
            </div>
        </div>
    </div>`;
}

function recentTable(list) {
    const rows = (list || []).map(t => `
        <tr class="hover:bg-gray-50/50 transition-colors">
            <td class="px-5 py-4"><span class="text-sm font-medium text-ms-blue">${esc(t.ticket_no)}</span></td>
            <td class="px-5 py-4"><p class="text-sm text-ms-text">${esc(t.title)}</p></td>
            <td class="px-5 py-4">${typeBadge(t.ttype)}</td>
            <td class="px-5 py-4">${statusBadge(t.status)}</td>
            <td class="px-5 py-4"><div class="flex items-center gap-2">${t.assignee_name ? avatar(t.assignee_name, 24) + `<span class="text-sm text-ms-text">${esc(t.assignee_name)}</span>` : '<span class="text-sm text-ms-muted">--</span>'}</div></td>
            <td class="px-5 py-4"><span class="text-sm text-ms-muted">${t.status === 'resolved' ? '已闭环' : '处理中'}</span></td>
            <td class="px-5 py-4"><button class="text-ms-blue text-sm hover:underline" onclick="openTicket(${t.id})">查看</button></td>
        </tr>`).join('');
    return `
    <div class="ms-card">
        <div class="p-5 border-b border-ms-border">
            <div class="flex items-center justify-between">
                <div><h3 class="text-base font-semibold text-ms-text">最近工单</h3><p class="text-xs text-ms-muted mt-0.5">过去 24 小时内处理的工单</p></div>
                <button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm hover:bg-ms-dark transition-colors" onclick="showCreateTicket()">+ 新建工单</button>
            </div>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full">
                <thead><tr class="border-b border-ms-border bg-gray-50/50">
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">工单编号</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">问题描述</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">类型</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">状态</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">处理人</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">耗时</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase tracking-wider">操作</th>
                </tr></thead>
                <tbody class="divide-y divide-ms-border">${rows}</tbody>
            </table>
        </div>
    </div>`;
}

function relTime(s) {
    if (!s) return '--';
    const d = new Date(s.replace(' ', 'T'));
    const diff = (Date.now() - d.getTime()) / 60000;
    if (diff < 1) return '刚刚';
    if (diff < 60) return Math.floor(diff) + ' 分钟前';
    if (diff < 1440) return Math.floor(diff / 60) + ' 小时前';
    return Math.floor(diff / 1440) + ' 天前';
}

function bindDashboard(d) {}

// ---------------- 全部工单 ----------------
let ticketFilter = { status: '', ttype: '', search: '', page: 1 };
async function loadTickets() {
    const q = new URLSearchParams(ticketFilter).toString();
    const d = await api('/api/tickets?' + q);
    document.getElementById('view-tickets').innerHTML = ticketsHTML(d);
    bindTickets();
}
function ticketsHTML(d) {
    const rows = d.items.map(t => `
        <tr class="hover:bg-gray-50/50 transition-colors">
            <td class="px-5 py-4"><span class="text-sm font-medium text-ms-blue">${esc(t.ticket_no)}</span></td>
            <td class="px-5 py-4"><p class="text-sm text-ms-text">${esc(t.title)}</p></td>
            <td class="px-5 py-4">${typeBadge(t.ttype)}</td>
            <td class="px-5 py-4">${statusBadge(t.status)}</td>
            <td class="px-5 py-4">${t.assignee_name ? esc(t.assignee_name) : '--'}</td>
            <td class="px-5 py-4"><button class="text-ms-blue text-sm hover:underline" onclick="openTicket(${t.id})">查看</button></td>
        </tr>`).join('');
    return `
    <div class="mb-8"><h1 class="text-2xl font-semibold mb-1">全部工单</h1><p class="text-ms-muted text-sm">查看与管理所有工单</p></div>
    <div class="ms-card">
        <div class="p-5 border-b border-ms-border flex items-center justify-between gap-3 flex-wrap">
            <div class="flex items-center gap-2">
                <input id="tkSearch" placeholder="搜索工单..." class="pl-3 pr-4 py-2 border border-ms-border rounded-lg text-sm focus:outline-none focus:border-ms-blue w-56" value="${esc(ticketFilter.search)}">
                <select id="tkStatus" class="border border-ms-border rounded-lg text-sm py-2 px-2">
                    <option value="">全部状态</option>
                    <option value="intake">工单接入</option><option value="classified">已分类</option><option value="processing">处理中</option><option value="review">待人工评估</option><option value="assigned">已分派</option><option value="replied">已回复</option><option value="resolved">已解决</option><option value="rejected">已驳回</option>
                </select>
                <select id="tkType" class="border border-ms-border rounded-lg text-sm py-2 px-2">
                    <option value="">全部类型</option><option value="技术">技术</option><option value="产品">产品</option>
                </select>
                <button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm hover:bg-ms-dark" onclick="applyTicketFilter()">查询</button>
                <button class="px-4 py-2 border border-ms-border rounded-lg text-sm hover:bg-gray-50" onclick="showCreateTicket()">+ 新建工单</button>
            </div>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full">
                <thead><tr class="border-b border-ms-border bg-gray-50/50">
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">工单编号</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">问题描述</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">类型</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">状态</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">处理人</th>
                    <th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">操作</th>
                </tr></thead>
                <tbody class="divide-y divide-ms-border">${rows || '<tr><td colspan="6" class="px-5 py-8 text-center text-ms-muted">暂无工单</td></tr>'}</tbody>
            </table>
        </div>
        <div class="p-4 border-t border-ms-border text-sm text-ms-muted">共 ${d.total} 条</div>
    </div>`;
}
function bindTickets() {
    const s = document.getElementById('tkStatus'), t = document.getElementById('tkType');
    if (s) s.value = ticketFilter.status;
    if (t) t.value = ticketFilter.ttype;
}
function applyTicketFilter() {
    ticketFilter.search = document.getElementById('tkSearch').value;
    ticketFilter.status = document.getElementById('tkStatus').value;
    ticketFilter.ttype = document.getElementById('tkType').value;
    ticketFilter.page = 1;
    loadTickets();
}

// ---------------- 自动处理中心 ----------------
async function loadAgent() {
    const d = await api('/api/tickets?ttype=产品');
    const review = d.items.filter(t => t.status === 'review' || t.status === 'processing');
    document.getElementById('view-agent').innerHTML = `
    <div class="mb-8"><h1 class="text-2xl font-semibold mb-1">自动处理中心</h1><p class="text-ms-muted text-sm">Agent 基于内部知识库向量检索自动回复，人工评估后发送</p></div>
    <div class="grid grid-cols-2 gap-6">${review.map(t => `<div class="ms-card"><div class="p-4">${agentItem(t)}</div></div>`).join('') || '<div class="ms-card p-8 text-center text-ms-muted">暂无待处理的产品工单</div>'}</div>
    <div class="mt-8 ms-card">
        <div class="p-5 border-b border-ms-border"><h3 class="text-base font-semibold">已回复工单</h3></div>
        <div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b bg-gray-50/50"><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">工单编号</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">问题描述</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">状态</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">操作</th></tr></thead>
        <tbody class="divide-y">${d.items.filter(t => t.status === 'replied' || t.status === 'resolved').map(t => `<tr class="hover:bg-gray-50/50"><td class="px-5 py-4"><span class="text-sm font-medium text-ms-blue">${esc(t.ticket_no)}</span></td><td class="px-5 py-4"><p class="text-sm">${esc(t.title)}</p></td><td class="px-5 py-4">${statusBadge(t.status)}</td><td class="px-5 py-4"><button class="text-ms-blue text-sm hover:underline" onclick="openTicket(${t.id})">查看</button></td></tr>`).join('')}</tbody></table></div>
    </div>`;
}

// ---------------- 团队管理 ----------------
async function loadTeam() {
    const d = await api('/api/technicians');
    const rows = d.items.map(t => `
        <tr class="hover:bg-gray-50/50">
            <td class="px-5 py-4"><div class="flex items-center gap-2">${avatar(t.name, 32)}<span class="text-sm font-medium">${esc(t.name)}</span></div></td>
            <td class="px-5 py-4 text-sm text-ms-muted">${esc(t.title || '--')}</td>
            <td class="px-5 py-4 text-sm text-ms-text">${esc(t.expertise)}</td>
            <td class="px-5 py-4">${(t.skill_tags || '').split(',').filter(Boolean).map(x => `<span class="px-2 py-0.5 bg-blue-50 text-ms-blue text-xs rounded mr-1">${esc(x)}</span>`).join('')}</td>
            <td class="px-5 py-4 text-sm text-ms-muted">${t.load_count}</td>
            <td class="px-5 py-4"><button class="text-ms-blue text-sm hover:underline mr-3" onclick="editTechnician(${t.id})">编辑</button><button class="text-ms-danger text-sm hover:underline" onclick="delTechnician(${t.id})">删除</button></td>
        </tr>`).join('');
    document.getElementById('view-team').innerHTML = `
    <div class="mb-8 flex items-center justify-between"><div><h1 class="text-2xl font-semibold mb-1">团队管理</h1><p class="text-ms-muted text-sm">技术人员擅长领域将写入向量库，用于工单自动分派</p></div><button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm hover:bg-ms-dark" onclick="showTechForm()">+ 新增技术人</button></div>
    <div class="ms-card"><div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b bg-gray-50/50"><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">姓名</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">职位</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">擅长领域</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">技能标签</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">在办</th><th class="px-5 py-3 text-left text-xs font-semibold text-ms-muted uppercase">操作</th></tr></thead><tbody class="divide-y">${rows}</tbody></table></div></div>`;
}
function showTechForm(id) {
    const t = id ? currentTechs.find(x => x.id === id) : null;
    const html = `
    <div class="ms-card p-5 mb-6"><h3 class="text-base font-semibold mb-4">${t ? '编辑' : '新增'}技术人员</h3>
    <div class="grid grid-cols-2 gap-4">
        <input id="f_name" placeholder="姓名" value="${t ? esc(t.name) : ''}" class="border border-ms-border rounded-lg px-3 py-2 text-sm">
        <input id="f_title" placeholder="职位" value="${t ? esc(t.title || '') : ''}" class="border border-ms-border rounded-lg px-3 py-2 text-sm">
        <input id="f_expertise" placeholder="擅长领域描述（进入向量库）" value="${t ? esc(t.expertise) : ''}" class="border border-ms-border rounded-lg px-3 py-2 text-sm col-span-2">
        <input id="f_tags" placeholder="技能标签（逗号分隔）" value="${t ? esc(t.skill_tags || '') : ''}" class="border border-ms-border rounded-lg px-3 py-2 text-sm col-span-2">
    </div>
    <div class="mt-4 flex gap-2"><button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm" onclick="saveTechnician(${id || 0})">保存</button></div></div>`;
    const view = document.getElementById('view-team');
    view.innerHTML = html + view.innerHTML;
}
let currentTechs = [];
async function saveTechnician(id) {
    const body = {
        name: document.getElementById('f_name').value,
        title: document.getElementById('f_title').value,
        expertise: document.getElementById('f_expertise').value,
        skill_tags: document.getElementById('f_tags').value,
    };
    if (id) await api('/api/technicians/' + id, { method: 'PUT', body });
    else await api('/api/technicians', { method: 'POST', body });
    toast('已保存'); loadTeam();
}
async function editTechnician(id) {
    const d = await api('/api/technicians'); currentTechs = d.items;
    showTechForm(id);
}
async function delTechnician(id) {
    if (!confirm('确认删除该技术人员？')) return;
    await api('/api/technicians/' + id, { method: 'DELETE' });
    toast('已删除'); loadTeam();
}

// ---------------- 数据分析 ----------------
async function loadAnalytics() {
    const d = await api('/api/analytics');
    document.getElementById('view-analytics').innerHTML = `
    <div class="mb-8"><h1 class="text-2xl font-semibold mb-1">数据分析</h1><p class="text-ms-muted text-sm">工单类型、状态与处理人分布</p></div>
    <div class="grid grid-cols-2 gap-6">
        ${barCard('按类型分布', d.by_type, 'ttype')}
        ${barCard('按状态分布', d.by_status, 'label')}
        ${barCard('处理人工单量', d.by_tech, 'assignee_name')}
    </div>`;
}
function barCard(title, data, key) {
    const max = Math.max(1, ...data.map(x => x.c));
    const bars = data.map(x => `
        <div class="flex items-center gap-3 mb-3">
            <span class="text-sm text-ms-muted w-24 truncate">${esc(x[key] || '未分类')}</span>
            <div class="flex-1 h-5 bg-gray-100 rounded overflow-hidden"><div class="h-full bg-ms-blue rounded" style="width:${Math.round(x.c / max * 100)}%"></div></div>
            <span class="text-sm font-medium w-8 text-right">${x.c}</span>
        </div>`).join('');
    return `<div class="ms-card p-5"><h3 class="text-base font-semibold mb-4">${title}</h3>${bars || '<p class="text-ms-muted text-sm">暂无数据</p>'}</div>`;
}

// ---------------- 系统设置 ----------------
const CRON_PRESETS = [
    { label: '每天 02:00（默认）', value: '0 2 * * *' },
    { label: '每天 08:00', value: '0 8 * * *' },
    { label: '每小时', value: '0 * * * *' },
    { label: '每 30 分钟', value: '*/30 * * * *' },
    { label: '每 5 分钟', value: '*/5 * * * *' },
    { label: '每分钟（测试用）', value: '* * * * *' },
    { label: '自定义 cron', value: '__custom__' },
];
let currentSettings = {};
async function loadSettings() {
    currentSettings = await api('/api/settings');
    const s = currentSettings;
    const jobs = await api('/api/crawl/jobs');
    const kb = await api('/api/knowledge');
    document.getElementById('view-settings').innerHTML = settingsHTML(s, jobs, kb);
    bindSettings();
}
function settingsHTML(s, jobs, kb) {
    const curCron = s.crawl_schedule || '';
    const presetVal = CRON_PRESETS.some(p => p.value === curCron) ? curCron : '__custom__';
    const cronOptions = CRON_PRESETS.map(p => `<option value="${p.value}" ${presetVal === p.value ? 'selected' : ''}>${p.label}</option>`).join('');
    const cronWrapHidden = presetVal === '__custom__' ? '' : 'hidden';
    const crawlOn = String(s.crawl_enabled) === 'true';
    return `
    <div class="mb-8"><h1 class="text-2xl font-semibold mb-1">系统设置</h1><p class="text-ms-muted text-sm">大模型、向量库、爬虫与知识库管理</p></div>
    <div class="grid grid-cols-2 gap-6">
        <div class="ms-card p-6">
            <h3 class="text-base font-semibold mb-4">大模型配置</h3>
            <div class="space-y-3">
                <div><label class="text-xs text-ms-muted">Provider</label>
                <select id="s_provider" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"><option value="mock" ${s.llm_provider === 'mock' ? 'selected' : ''}>内置规则（无需密钥）</option><option value="deepseek" ${s.llm_provider === 'deepseek' ? 'selected' : ''}>DeepSeek</option><option value="openai" ${s.llm_provider === 'openai' ? 'selected' : ''}>OpenAI 兼容</option></select></div>
                <div><label class="text-xs text-ms-muted">API Base URL</label><input id="s_base_url" value="${esc(s.llm_base_url)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
                <div><label class="text-xs text-ms-muted">API Key</label><input id="s_api_key" type="password" value="${esc(s.llm_api_key)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
                <div><label class="text-xs text-ms-muted">Model</label><input id="s_model" value="${esc(s.llm_model)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
                <div><label class="text-xs text-ms-muted">Temperature</label><input id="s_temperature" value="${esc(s.llm_temperature)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
            </div>
            <h3 class="text-base font-semibold mb-3 mt-6">向量库配置</h3>
            <div class="space-y-3">
                <div><label class="text-xs text-ms-muted">Embedding Provider</label><select id="s_emb_provider" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"><option value="local" ${s.embedding_provider === 'local' ? 'selected' : ''}>本地哈希向量（轻量）</option><option value="openai" ${s.embedding_provider === 'openai' ? 'selected' : ''}>OpenAI Embedding</option></select></div>
                <div><label class="text-xs text-ms-muted">Embedding Model</label><input id="s_emb_model" value="${esc(s.embedding_model)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
            </div>
            <h3 class="text-base font-semibold mb-3 mt-6">自动处理中心</h3>
            <div class="grid grid-cols-2 gap-3">
                <div><label class="text-xs text-ms-muted">回复置信度阈值</label><input id="s_confidence" value="${esc(s.auto_reply_confidence_threshold)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
                <div><label class="text-xs text-ms-muted">推荐技术人数</label><input id="s_topk" value="${esc(s.assign_top_k)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
            </div>
            <button class="mt-6 px-5 py-2 bg-ms-blue text-white rounded-lg text-sm hover:bg-ms-dark" onclick="saveSettings()">保存配置</button>
        </div>
        <div class="space-y-6">
            <div class="ms-card p-6">
                <h3 class="text-base font-semibold mb-4">爬虫与知识库入库</h3>
                <div class="space-y-3">
                    <label class="flex items-center gap-2 text-sm text-ms-text cursor-pointer"><input type="checkbox" id="s_crawl_enabled" ${crawlOn ? 'checked' : ''} class="w-4 h-4"> 启用定时增量爬取</label>
                    <div><label class="text-xs text-ms-muted">调度频率</label><select id="s_schedule_preset" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1">${cronOptions}</select></div>
                    <div id="s_cron_wrap" class="${cronWrapHidden}"><label class="text-xs text-ms-muted">自定义 cron（分 时 日 月 周）</label><input id="s_schedule" value="${esc(s.crawl_schedule)}" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
                    <div><label class="text-xs text-ms-muted">企业论坛地址</label><input id="s_forum_url" value="${esc(s.crawl_forum_url)}" placeholder="正式环境：内部论坛 URL" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mt-1"></div>
                    <div class="flex gap-2"><button class="px-4 py-2 bg-ms-success text-white rounded-lg text-sm" onclick="runCrawl()">立即增量爬取</button><button class="px-4 py-2 border border-ms-border rounded-lg text-sm" onclick="saveSettings()">保存</button></div>
                </div>
                <div class="mt-4"><h4 class="text-sm font-semibold mb-2">最近爬取任务</h4>
                ${jobs.items.map(j => `<div class="text-xs text-ms-muted py-1 border-b border-ms-border flex justify-between"><span>${esc(j.source)} · ${esc(j.status)}</span><span>新增${j.new_count}/更新${j.updated_count} · ${esc(j.started_at || '')}</span></div>`).join('') || '<p class="text-xs text-ms-muted">暂无任务</p>'}</div>
            </div>
            <div class="ms-card p-6">
                <h3 class="text-base font-semibold mb-4">知识库文章（${kb.items.length}）</h3>
                <div class="space-y-2 max-h-[300px] overflow-y-auto scrollbar-thin">
                ${kb.items.map(k => `<div class="border border-ms-border rounded-lg p-3"><p class="text-sm font-medium">${esc(k.kb_id)} · ${esc(k.title)}</p><p class="text-xs text-ms-muted mt-1">${esc(k.source)} · ${esc(k.tags)}</p></div>`).join('')}
                </div>
            </div>
        </div>
    </div>`;
}
function bindSettings() {
    const sel = document.getElementById('s_schedule_preset');
    if (sel) sel.addEventListener('change', () => {
        document.getElementById('s_cron_wrap').classList.toggle('hidden', sel.value !== '__custom__');
    });
}
async function saveSettings() {
    const preset = document.getElementById('s_schedule_preset').value;
    const crawl_schedule = preset === '__custom__'
        ? document.getElementById('s_schedule').value
        : preset;
    const body = {
        llm_provider: document.getElementById('s_provider').value,
        llm_base_url: document.getElementById('s_base_url').value,
        llm_api_key: document.getElementById('s_api_key').value,
        llm_model: document.getElementById('s_model').value,
        llm_temperature: document.getElementById('s_temperature').value,
        embedding_provider: document.getElementById('s_emb_provider').value,
        embedding_model: document.getElementById('s_emb_model').value,
        auto_reply_confidence_threshold: document.getElementById('s_confidence').value,
        assign_top_k: document.getElementById('s_topk').value,
        crawl_enabled: document.getElementById('s_crawl_enabled').checked ? 'true' : 'false',
        crawl_forum_url: document.getElementById('s_forum_url').value,
        crawl_schedule: crawl_schedule,
    };
    await api('/api/settings', { method: 'PUT', body });
    toast('配置已保存');
    loadSettings();
}
async function runCrawl() {
    toast('爬取中...');
    const r = await api('/api/crawl/run', { method: 'POST' });
    toast(r.message || '爬取完成');
    loadSettings();
}

// ---------------- 工单操作 ----------------
async function processTicket(id) {
    await api('/api/tickets/' + id + '/process', { method: 'POST' });
    toast('已自动处理，等待人工评估');
    loadDashboard();
}
async function approveTicket(id) {
    await api('/api/tickets/' + id + '/approve', { method: 'POST' });
    toast('已通过评估并提交下一环节');
    loadDashboard();
}
async function rejectTicket(id) {
    const reason = prompt('请输入驳回原因（将重新走流程分派）：', '人工评估不通过');
    if (reason === null) return;
    await api('/api/tickets/' + id + '/reject', { method: 'POST', body: { reason } });
    toast('已驳回，重新分派中');
    loadDashboard();
}
async function assignTicket(id) {
    await api('/api/tickets/' + id + '/approve', { method: 'POST' });
    toast('已分派给推荐技术人员');
    loadDashboard();
}
async function openTicket(id) {
    const d = await api('/api/tickets/' + id);
    const t = d.ticket;
    const logs = d.logs.map(l => `<div class="flex items-start gap-2 py-2 border-b border-ms-border"><span class="px-2 py-0.5 bg-ms-light text-ms-blue text-xs rounded whitespace-nowrap">${esc(l.node)}</span><div><p class="text-xs text-ms-text">${esc(l.detail)}</p><p class="text-xs text-ms-muted mt-0.5">${esc(l.operator)} · ${esc(l.created_at)}</p></div></div>`).join('');
    const cands = (t.candidates || []).map(c => `<div class="flex items-center justify-between border border-ms-border rounded-lg p-3 mb-2"><div class="flex items-center gap-2">${avatar(c.name, 28)}<div><p class="text-sm font-medium">${esc(c.name)}</p><p class="text-xs text-ms-muted">${esc(c.expertise)}</p></div></div><div class="text-right"><span class="text-xs text-ms-muted">匹配度</span><span class="text-sm font-semibold text-ms-blue ml-1">${Math.round(c.score * 100)}%</span></div></div>`).join('');
    const srcs = (t.reply_sources || []).map(s => `<div class="flex items-center justify-between py-1.5 border-b border-ms-border/60 last:border-0"><span class="text-xs text-ms-text">${esc(s.kb_id)} · ${esc(s.title)}</span><span class="text-xs text-ms-muted ml-3 whitespace-nowrap">相似度 ${Math.round(s.score * 100)}%</span></div>`).join('');
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6';
    modal.innerHTML = `
    <div class="bg-white rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6">
        <div class="flex items-start justify-between mb-4"><div><h3 class="text-lg font-semibold">${esc(t.ticket_no)}</h3><p class="text-sm text-ms-muted mt-1">${esc(t.title)}</p></div><button class="text-ms-muted hover:text-ms-text" onclick="this.closest('.fixed').remove()">✕</button></div>
        <div class="flex items-center gap-2 mb-4">${typeBadge(t.ttype)}${priorityBadge(t.priority)}${statusBadge(t.status)}</div>
        <p class="text-sm text-ms-text mb-4">${esc(t.description || '')}</p>
        ${t.auto_reply ? `<div class="bg-gray-50 rounded-lg p-3 mb-4"><p class="text-xs font-medium text-ms-success mb-1">Agent 自动回复（置信度 ${Math.round((t.reply_confidence || 0) * 100)}%）</p><p class="text-sm">${esc(t.auto_reply)}</p></div>` : ''}
        ${t.reply_sources && t.reply_sources.length ? `<div class="mb-4"><p class="text-sm font-semibold mb-2">命中知识库来源</p><div class="border border-ms-border rounded-lg px-3 py-1">${srcs}</div></div>` : ''}
        ${cands ? `<div class="mb-4"><p class="text-sm font-semibold mb-2">推荐技术人员</p>${cands}</div>` : ''}
        <p class="text-sm font-semibold mb-2">流程日志</p><div class="mb-4">${logs}</div>
        <div class="flex gap-2 flex-wrap">
            ${t.status === 'review' ? `<button class="px-4 py-2 bg-ms-success text-white rounded-lg text-sm" onclick="approveTicket(${t.id});this.closest('.fixed').remove()">通过评估</button><button class="px-4 py-2 border border-ms-danger text-ms-danger rounded-lg text-sm" onclick="rejectTicket(${t.id});this.closest('.fixed').remove()">驳回重走</button>` : ''}
            ${(t.status === 'assigned' || t.status === 'replied') ? `<button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm" onclick="resolveTicket(${t.id});this.closest('.fixed').remove()">标记解决闭环</button><button class="px-4 py-2 border border-ms-danger text-ms-danger rounded-lg text-sm" onclick="escalateTicket(${t.id})">转人工</button>` : ''}
            <button class="px-4 py-2 border border-ms-border rounded-lg text-sm" onclick="this.closest('.fixed').remove()">关闭</button>
        </div>
    </div>`;
    document.body.appendChild(modal);
}
async function resolveTicket(id) {
    await api('/api/tickets/' + id + '/resolve', { method: 'POST' });
    toast('已进入解决闭环');
    loadDashboard();
}
async function escalateTicket(id) {
    const reason = prompt('请输入转人工原因：', '用户要求人工介入');
    if (reason === null) return;
    await api('/api/tickets/' + id + '/escalate', { method: 'POST', body: { reason } });
    document.querySelectorAll('.fixed.inset-0').forEach(m => m.remove());
    toast('已转人工，重新进入人工评估');
    loadDashboard();
}

// 编辑 Agent 自动回复
async function editReply(id) {
    const d = await api('/api/tickets/' + id);
    const t = d.ticket;
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6';
    modal.innerHTML = `
    <div class="bg-white rounded-xl max-w-xl w-full p-6">
        <h3 class="text-lg font-semibold mb-4">编辑自动回复</h3>
        <textarea id="r_text" rows="8" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mb-4">${esc(t.auto_reply || '')}</textarea>
        <div class="flex gap-2"><button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm" onclick="saveReply(${id})">保存</button><button class="px-4 py-2 border border-ms-border rounded-lg text-sm" onclick="this.closest('.fixed').remove()">取消</button></div>
    </div>`;
    document.body.appendChild(modal);
}
async function saveReply(id) {
    const auto_reply = document.getElementById('r_text').value;
    await api('/api/tickets/' + id + '/reply', { method: 'PUT', body: { auto_reply } });
    document.querySelectorAll('.fixed.inset-0').forEach(m => m.remove());
    toast('回复已保存');
    loadDashboard();
}

// 跳转辅助
function goView(name) {
    const el = document.querySelector(`[data-view="${name}"]`);
    if (el) el.click();
}
function viewPendingAll() {
    ticketFilter.status = 'review';
    ticketFilter.ttype = '技术';
    ticketFilter.search = '';
    ticketFilter.page = 1;
    goView('tickets');
}
function viewAgentAll() {
    goView('agent');
}

// ---------------- 新建工单 ----------------
function showCreateTicket() {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/40 z-[100] flex items-center justify-center p-6';
    modal.innerHTML = `
    <div class="bg-white rounded-xl max-w-xl w-full p-6">
        <h3 class="text-lg font-semibold mb-4">新建工单</h3>
        <input id="c_title" placeholder="问题标题" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mb-3">
        <textarea id="c_desc" placeholder="问题描述" rows="4" class="w-full border border-ms-border rounded-lg px-3 py-2 text-sm mb-4"></textarea>
        <div class="flex gap-2"><button class="px-4 py-2 bg-ms-blue text-white rounded-lg text-sm" onclick="createTicket()">提交并自动流转</button><button class="px-4 py-2 border border-ms-border rounded-lg text-sm" onclick="this.closest('.fixed').remove()">取消</button></div>
    </div>`;
    document.body.appendChild(modal);
}
async function createTicket() {
    const title = document.getElementById('c_title').value;
    const description = document.getElementById('c_desc').value;
    if (!title) { toast('请输入标题', true); return; }
    const r = await api('/api/tickets', { method: 'POST', body: { title, description, source: 'web' } });
    document.querySelectorAll('.fixed.inset-0').forEach(m => m.remove());
    toast('工单已接入，开始自动流转');
    await api('/api/tickets/' + r.ticket.id + '/process', { method: 'POST' });
    loadDashboard();
}

// 全局搜索
document.getElementById('globalSearch').addEventListener('keydown', e => {
    if (e.key === 'Enter') {
        ticketFilter.search = e.target.value;
        document.querySelector('[data-view="tickets"]').click();
    }
});

// 初始加载
loadDashboard();
