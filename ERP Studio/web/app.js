'use strict';

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => JSON.parse(JSON.stringify(value));
const stable = value => JSON.stringify(value, (_, v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.keys(v).sort().reduce((o,k)=>(o[k]=v[k],o),{}) : v);
const money = n => new Intl.NumberFormat('zh-CN', {style:'currency',currency:'CNY'}).format((n || 0)/100);
const date = value => value ? new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value)) : '—';
const time = value => value ? new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(value)) : '—';
const statuses = {
  ACTIVE:['已激活','green'],DRAFT:['草稿','yellow'],PENDING_APPROVAL:['待审批','yellow'],APPROVED:['已批准，待激活','blue'],
  RETIRED:['已停用',''],REJECTED:['已拒绝','red'],RUNNING:['运行中','green'],WAITING_HUMAN:['等待人工','yellow'],
  WAITING_INPUT:['等待补证','yellow'],COMPLETED:['已完成','blue'],FAILED:['异常','red'],RECONCILING:['结果待核对','red'],
  HEALTHY:['正常','green'],ATTENTION:['关注','yellow'],DISCONNECTED:['未连接',''],PENDING:['待审批','yellow'],
  SUCCEEDED:['测试通过','green'],READ:['只读','blue'],WRITE:['受控写入','purple'],APPROVE:['已批准','green'],
  SUPERSEDED:['已被新证据替代',''],REQUEST_CHANGES:['等待补证','yellow'],RETURN_FOR_REWORK:['驳回重做','yellow']
};
const badge = state => `<span class="badge ${statuses[state]?.[1] || ''}">${esc(statuses[state]?.[0] || state)}</span>`;
const button = (text, action, opts='') => `<button type="button" class="btn" data-action="${action}" ${opts}>${text}</button>`;
const primary = (text, action, opts='') => `<button type="button" class="btn primary" data-action="${action}" ${opts}>${text}</button>`;
const empty = (title='没有符合条件的记录', description='可以调整筛选条件后再试。', action='') => `<div class="empty"><div class="empty-symbol">✓</div><h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
const field = (label, name, value, type='text', extra='') => `<label class="field">${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const area = (label, name, value, extra='') => `<label class="field">${esc(label)}<textarea name="${name}" ${extra}>${esc(value)}</textarea></label>`;
const option = (value, label, current) => `<option value="${esc(value)}" ${value === current ? 'selected' : ''}>${esc(label)}</option>`;
const selectField = (label,name,values,current,extra='') => `<label class="field">${esc(label)}<select name="${name}" aria-label="${esc(label)}" ${extra}>${values.map(([v,l])=>option(v,l,current)).join('')}</select></label>`;
const pageHeading = (title,english,description,actions='') => `<div class="page-heading"><div><h1>${esc(title)}</h1><div class="english">${esc(english)}</div><p class="page-desc">${esc(description)}</p></div><div class="actions">${actions}</div></div>`;
const stats = (items, five=false) => `<div class="stats ${five?'five':''}">${items.map(([label,value,foot])=>`<div class="stat"><div class="stat-label">${esc(label)}</div><div class="stat-value num">${esc(value)}</div><div class="stat-foot">${esc(foot || '部门实时汇总')}</div></div>`).join('')}</div>`;
const tabs = (items,current,action='tab') => `<div class="tabs" role="tablist">${items.map(([id,label])=>`<button class="tab ${id===current?'active':''}" role="tab" aria-selected="${id===current}" data-action="${action}" data-id="${id}">${label}</button>`).join('')}</div>`;
const NAV = [
  ['业务运行',[['runtime','运行中心','Runtime'],['decisions','人工决策','Human-in-the-loop']]],
  ['数字团队',[['process-agents','流程智能体','Process Agent'],['task-agents','任务智能体','Task Agent'],['department','一人部门','One Person Dept.']]],
  ['能力资产',[['connectors','连接中心','Connector Hub'],['tools','工具中心','MCP Tool Hub'],['skills','业务能力中心','Skill Hub'],['experts','专家中心','Expert Hub'],['knowledge','企业认知基座','Enterprise Cognitive Foundation']]],
  ['设计与治理',[['flow-builder','流程构建器','Flow Builder'],['audit','审计与治理','Audit & Governance']]],
];
let db, pendingCount=3, renderTicket=0, currentInstance=null, overlayStack=[], restoreFocus=null, toastTimer, searchTimer;
let actor = localStorage.getItem('erp-actor') || 'operator';
let mode = localStorage.getItem('erp-mode') || 'replay';
let flow=null, task=null, formDirty=false, flowSaveTimer, graphCleanup=null;
const main = $('#main');
const route = () => ({page:location.pathname.split('/')[1] || 'runtime', params:new URLSearchParams(location.search), process:location.pathname.split('/')[3]});

async function api(path, method='GET', data=null, key=null) {
  const response = await fetch('/api/v1'+path, {
    method, headers:{'Content-Type':'application/json','X-Demo-Actor':actor,'X-Department-ID':'finance',
      ...(method !== 'GET' ? {'Idempotency-Key':key || crypto.randomUUID()} : {})},
    ...(data !== null ? {body:JSON.stringify(data)} : {})
  });
  const value = await response.json();
  if (!response.ok) { const error = new Error(value.message || '请求失败'); Object.assign(error,value,{status:response.status}); throw error; }
  return value;
}
function toast(message) {
  const el=$('#toast'); el.textContent=message; el.classList.add('show'); clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>el.classList.remove('show'),3500);
}
function reportError(error) {
  console.error(error);
  const detail=Array.isArray(error.details) ? error.details.map(e=>`${e.nodeId || e.field || ''} ${e.message}`).join('；') : '';
  const message=error.message+(detail ? '：'+detail : '');
  toast(message);
  const container=$('.drawer-body', $('#overlay-root')) || main;
  $('.form-error',container)?.remove();
  container.insertAdjacentHTML('afterbegin',`<div class="form-error" role="alert">${esc(message)}${error.code?`<div class="tiny">${esc(error.code)} · ${esc(error.traceId || '')}</div>`:''}</div>`);
}
function dirty() { return formDirty || flow?.dirty || task?.dirty; }
function permitNavigation() {
  if (!dirty()) return true;
  if (!confirm('还有未保存的修改，确定离开并放弃这些修改吗？')) return false;
  clearTimeout(flowSaveTimer); formDirty=false; if(flow) flow.dirty=false; if(task) task.dirty=false; return true;
}
function navigate(url, replace=false) {
  if (!permitNavigation()) return;
  overlayStack=[]; $('#overlay-root').innerHTML=''; currentInstance=null;
  history[replace?'replaceState':'pushState']({},'',url); main.scrollTop=0; return render();
}
function updateQuery(values, replace=true) {
  const u=new URL(location.href);
  Object.entries(values).forEach(([k,v])=>v==null || v===''?u.searchParams.delete(k):u.searchParams.set(k,v));
  return navigate(u.pathname+u.search,replace);
}
function shell() {
  const r=route(); let index=0, current;
  $('#sidebar').innerHTML=`<div class="brand"><small>企业智能体工作平台</small><strong>智能体 ERP 操作系统</strong></div><div class="scope-card"><div>当前运行范围</div><strong><i class="dot"></i>财务 · 端到端运营</strong></div><nav class="nav-scroll">${NAV.map(([group,items])=>`<div class="nav-group">${group}</div>${items.map(([id,name,en])=>{
    index++;if(r.page===id)current={name,en,group};return `<a class="nav-link ${r.page===id?'active':''}" href="/${id}" data-nav><span class="nav-index">${String(index).padStart(2,'0')}</span><span class="nav-label">${name}<small>${en}</small></span>${id==='decisions'?`<span id="nav-pending" class="badge yellow" style="margin-left:auto">${pendingCount}</span>`:''}</a>`;
  }).join('')}`).join('')}</nav><div class="role-card"><strong>${{operator:'财务业务运营负责人',reviewer:'独立审批人',designer:'流程设计者',auditor:'只读审计员'}[actor]}</strong><span class="muted tiny">目标、风险边界与最终责任</span></div>`;
  $('#header').innerHTML=`<div style="display:flex;align-items:center"><button class="mobile-menu" data-action="mobile-nav" aria-label="展开导航">☰</button><div><div class="global-title">${current?.name || '运行中心'}</div><div class="tiny muted">财务 / ${current?.group || '业务运行'}</div></div></div><div class="header-controls"><span class="header-mode">DEMO · 模拟执行</span><select id="mode-select" aria-label="演示模式">${option('replay','原型回放',mode)}${option('linked','联动演示',mode)}</select><select id="actor-select" aria-label="演示身份">${[['operator','财务负责人'],['reviewer','独立审批人'],['designer','流程设计者'],['auditor','只读审计员']].map(([v,l])=>option(v,l,actor)).join('')}</select><label class="tiny muted department-select">部门 <select aria-label="部门"><option>财务</option></select></label><button class="btn small square" data-action="reset" title="重置演示数据" aria-label="重置演示数据">↺</button></div>`;
}
async function refreshData() {
  const [bootstrap, decisions]=await Promise.all([api('/bootstrap'),api('/decisions')]);
  db=bootstrap;pendingCount=decisions.total;return decisions;
}
async function render() {
  const ticket=++renderTicket;
  if(graphCleanup){graphCleanup();graphCleanup=null;}
  shell();
  try {
    await refreshData(); if(ticket!==renderTicket)return;
    shell(); const r=route(); let html='';
    switch(r.page) {
      case 'runtime': html=r.process ? await instancesPage(r.process) : await runtimePage();break;
      case 'decisions':html=await decisionsPage();break;
      case 'process-agents':html=processesPage();break;
      case 'task-agents':html=tasksPage();break;
      case 'department':html=await departmentPage();break;
      case 'connectors':html=connectorsPage();break;
      case 'tools':html=await toolsPage();break;
      case 'skills':html=skillsPage();break;
      case 'experts':html=expertsPage();break;
      case 'knowledge':html=await knowledgePage();break;
      case 'flow-builder':html=await flowPage();break;
      case 'audit':html=await auditPage();break;
      default:html=empty('页面不存在','请从左侧导航选择一个模块。');
    }
    if(ticket!==renderTicket)return;
    main.innerHTML=(actor==='auditor'?'<div class="read-only-banner">当前为审计员身份，所有修改操作由后端拒绝。</div>':'')+html;
    if(r.page==='flow-builder' && r.params.get('tab')!=='runs' && r.params.get('tab')!=='versions')setupFlow();
    if(r.page==='knowledge')setupGraph();
    const iid=r.params.get('instance');
    if(iid && !overlayStack.length)await openInstance(iid,false);
  } catch(error) { if(ticket===renderTicket){ main.innerHTML=empty('页面加载失败','请确认 Python 服务仍在运行。',button('重新加载','refresh'));reportError(error); } }
}

async function runtimePage() {
  const result=await api('/runtime/summary?mode='+mode);
  const cards=result.cards;
  return pageHeading('运行中心','Runtime Center','只看财务流程智能体总体运行状态；进入流程后再查看业务实例。',
    button('刷新状态','refresh')+button('启动联动场景','start-scenario')+primary('设计流程','goto-flow'))+
    stats([['运行中流程实例',cards.running,mode==='replay'?'原型演示快照':'实时实例聚合'],[mode==='replay'?'今日完成':'已完成实例',cards.completed,mode==='replay'?'原型演示快照':'当前演示数据累计'],['等待人工',cards.waiting,mode==='replay'?'原型演示快照':'实时实例聚合'],['当前异常',cards.error,mode==='replay'?'原型演示快照':'实时实例聚合']])+
    `<section class="panel"><div class="panel-title"><h2>流程智能体总体运行状态</h2><span class="panel-subtitle">点击流程智能体进入业务实例工作列表</span></div><div class="table-wrap"><table><thead><tr><th>流程智能体</th><th>运行中</th><th>已完成</th><th>异常</th><th>等待人工</th><th>SLA</th><th>入口</th></tr></thead><tbody>${result.rows.map(p=>`<tr><td><button class="link-button" data-action="instances" data-id="${p.id}"><strong>${esc(p.name)}</strong><small>${p.tasks} 个任务智能体 · ${p.humans} 个人工点</small></button></td><td>${p.running}</td><td>${p.completed}</td><td>${p.error}</td><td>${p.waiting}</td><td><span class="badge ${p.sla==='正常'?'green':'yellow'}">${p.sla}</span></td><td>${button('查看实例','instances',`data-id="${p.id}"`)}</td></tr>`).join('')}</tbody></table></div></section><p class="snapshot-note">${esc(result.source)} · SAP / OCR / Expert 均为本地模拟 · 真实 ERP 写入关闭</p>`;
}
async function instancesPage(pid) {
  const process=db.processes.find(p=>p.id===pid);
  if(!process)return empty('流程不存在');
  const filter=route().params.get('status') || '';
  const result=await api(`/processes/${encodeURIComponent(pid)}/instances?mode=${mode}&status=${encodeURIComponent(filter)}`);
  const c=result.counts;
  return `<a href="/runtime" class="back-link" data-nav>← 返回流程总览</a>`+
    pageHeading(`${process.name} · 业务实例工作列表`,'Process Instances',`当前处理 ${Object.values(c).reduce((a,b)=>a+b,0)} 个业务实例，查看任务轨迹、业务证据和人工介入原因。`,
      button('刷新状态','refresh')+primary('启动联动场景','start-scenario'))+
    stats([['处理中',c.running],['等待人工',c.waiting],['异常',c.error],['已完成',c.completed]])+
    (c.other?`<div class="banner warning">另有 ${c.other} 条等待补证、已拒绝或已取消的实例，状态互斥计数。</div>`:'')+
    `<section class="panel"><div class="panel-title"><h2>业务实例</h2><select id="instance-filter" aria-label="筛选实例状态">${[['','全部状态'],['RUNNING','运行中'],['WAITING_HUMAN','等待人工'],['WAITING_INPUT','等待补证'],['FAILED','异常'],['RECONCILING','结果待核对'],['COMPLETED','已完成'],['REJECTED','已拒绝']].map(([v,l])=>option(v,l,filter)).join('')}</select></div>${result.total?instanceTable(result.items):empty('当前没有业务实例','可启动发票联动场景体验完整审批与模拟写入。',button('清空筛选','clear-instance-filter'))}</section><p class="snapshot-note">金额以整数分存储。原型快照、人工决策示例与新增联动场景分别保留业务 ID。</p>`;
}
function instanceTable(rows) {
  return `<div class="table-wrap"><table><thead><tr><th>业务实例编号</th><th>供应商 / 业务对象</th><th>金额</th><th>当前节点 / 任务智能体</th><th>状态</th><th>开始时间</th><th>耗时</th><th>人工负责人</th></tr></thead><tbody>${rows.map(r=>`<tr><td><button class="link-button" data-action="instance" data-id="${r.id}"><strong style="color:var(--primary)">${esc(r.id)}</strong></button>${r.scenario==='linked'?'<small>新增联动场景</small>':''}</td><td>${esc(r.supplier)}</td><td class="num">${money(r.amountMinor)}</td><td>${esc(r.node)}<small>${esc(r.task)}</small></td><td>${badge(r.status)}</td><td>${date(r.startedAt)}</td><td>${r.elapsedMinutes} 分钟</td><td>${esc(r.owner)}</td></tr>`).join('')}</tbody></table></div>`;
}
async function decisionsPage() {
  const result=await api('/decisions');
  return pageHeading('人工决策','Human-in-the-loop','统一处理正常审批、异常确认、驳回重做与补证重提；人工负责最终判断。',button('批量委派','delegate'))+
    `<div class="grid split"><section class="panel"><div class="panel-title"><h2>待决队列</h2><span class="badge yellow">共 ${result.total} 项待处理</span></div>${result.total?result.items.map(d=>`<article class="decision-card"><div class="decision-header"><h3>${esc(db.processes.find(p=>p.id===d.processId)?.name)}需要责任人确认</h3><span class="badge ${d.sourceKind==='NORMAL_APPROVAL'?'blue':'yellow'}">${{NORMAL_APPROVAL:'正常审批',EXCEPTION_REVIEW:'异常复核',RESUBMISSION:'补证重提'}[d.sourceKind]}</span></div><p class="muted small" style="margin-top:7px">${esc(d.title)}</p><span class="tag neutral">${esc(d.rule)} · ${esc(d.ruleVersion)}</span><span class="tag neutral">负责人：${esc(d.assignee==='operator'?'财务负责人':'独立审批人')}</span><div class="decision-bottom"><span class="tiny muted">证据快照 ${d.evidenceSnapshotHash.slice(0,12)}</span><div class="actions">${button('查看证据','instance',`data-id="${d.instanceId}"`)}${primary('批准','quick-approve',`data-id="${d.id}"`)}</div></div></article>`).join(''):empty('当前没有待处理决策','所有人工待办已处理。你可以回到运行中心继续模拟执行。',button('前往运行中心','goto-runtime'))}</section><section class="panel" style="height:max-content"><div class="panel-title"><h2>决策原则</h2></div>${[
      ['证据完整可追溯','证据、规则版本与建议动作同时可见。证据变化后，旧批准自动失效。'],
      ['决策纳入统一审计','批准、拒绝、补证和委派均记录身份、证据指纹、规则版本与结果。'],
      ['职责分离','责任人与执行智能体分离。Expert 只给建议，不拥有工具或写入权限。'],
      ['批准后重新校验','人工批准恢复流程至写入前复核，模拟 ERP 调用是后续的独立步骤。'],
    ].map(([h,p],i)=>`<div class="principle"><span class="count">${i+1}</span><div><h3>${h}</h3><p>${p}</p></div></div>`).join('')}<div class="banner" style="margin:16px 0 0">本地演示：右上角可切换审批身份，状态会持久化到 SQLite。</div></section></div>`;
}
function processesPage() {
  return pageHeading('流程智能体','Process Agent','协调业务对象、任务智能体与人工控制点的端到端流程。',button('导入模板','import-flow')+primary('新建流程','new-process'))+
    `<div class="grid three">${db.processes.map(p=>`<article class="asset-card"><div class="asset-top"><span class="asset-icon">${esc(p.id.slice(0,3))}</span><h3>${esc(p.name)}</h3></div><p class="description">协调业务对象、任务智能体与人工控制点的端到端流程</p><div class="asset-meta"><span>${p.tasks} 个任务智能体</span><span>${p.humans} 个人工介入点</span></div><div class="asset-meta"><span>${esc(p.version)}</span><span>部门同步运行</span></div><div class="asset-footer">${badge(p.status)}<div class="actions">${button('设计','design-process',`data-id="${p.id}"`)}${button('查看业务实例','instances',`data-id="${p.id}"`)}</div></div></article>`).join('')}</div>`;
}
function tasksPage() {
  const tab=route().params.get('tab') || 'catalog';
  return pageHeading('任务智能体','Task Agent','可复用的数字岗位；将 Skill、Expert、Knowledge、Connector 与 MCP Tool 组合为边界清晰的内部资产依赖。')+
    tabs([['catalog','任务目录'],['designer','任务设计器']],tab)+
    (tab==='designer'?taskDesigner():`<div class="grid three">${db.assets.filter(a=>a.kind==='TASK').map(a=>`<article class="asset-card"><div class="asset-top"><span class="asset-icon">${a.id}</span><h3>${esc(a.name)}</h3></div><p class="description">${esc(a.spec.processes.join(' / '))}</p><div class="asset-meta"><span>超时 ${a.spec.timeout} 秒</span><span>重试 ${a.spec.retries} 次</span><span>可信度 ${a.spec.confidence}</span></div><p class="tiny muted">人工条件：${esc(a.spec.humanCondition)}<br>负责人：${esc(a.spec.owner)}</p><div class="asset-footer"><span class="badge blue">可配置</span>${button('打开设计器','design-task',`data-id="${a.id}"`)}</div></article>`).join('')}</div>`);
}
function assetById(id) { return db.assets.find(a=>a.id===id); }
function currentSpec(asset) { return clone(asset.draftSpec || asset.spec); }
function taskDesigner() {
  const aid=route().params.get('asset') || 'T1', asset=assetById(aid) || assetById('T1');
  if(!task || task.id!==asset.id || !task.dirty)task={id:asset.id,spec:currentSpec(asset),dirty:false,category:task?.category || 'SKILL'};
  const s=task.spec;
  let library=[];
  if(['SKILL','EXPERT','TOOL'].includes(task.category))library=db.assets.filter(a=>a.kind===task.category).map(a=>({name:a.name,id:a.id,kind:a.kind}));
  if(task.category==='KNOWLEDGE')library=['采购订单知识域','发票证据关系','供应商主数据','企业制度规则'].map(name=>({name,kind:'KNOWLEDGE'}));
  if(task.category==='CONNECTOR')library=['SAP 系统群','邮件连接器','文件内容连接器','消息通知连接器'].map(name=>({name,kind:'CONNECTOR'}));
  return `<div class="builder-overflow"><div class="task-layout"><aside class="builder-library"><h3>资产库</h3><p class="tiny muted">点击 + 加入内部步骤或依赖</p>${tabs([['SKILL','Skill'],['EXPERT','Expert'],['KNOWLEDGE','Knowledge'],['CONNECTOR','Connector'],['TOOL','MCP Tool']],task.category,'task-category')}${library.map((a,i)=>`<button class="library-item" data-action="task-add" data-name="${esc(a.name)}" data-kind="${a.kind}" data-id="${a.id || ''}"><strong>＋ ${esc(a.name)}</strong><small>${a.kind==='KNOWLEDGE'?'加载有权限的业务上下文':a.kind==='CONNECTOR'?'解析连接配置与路由':'执行并记录结构化结果'}</small></button>`).join('')}</aside><section class="panel" style="margin:0"><div class="panel-title"><h2>有序执行步骤</h2><span class="tiny muted">已选 ${s.steps.length} 项资产 · ${s.steps.length} 个步骤</span></div>${s.steps.map((step,i)=>`<div class="step"><span class="step-index">${i+1}</span><div class="step-info"><strong>${esc(step.name)}</strong><small>${step.kind==='KNOWLEDGE'?'加载授权知识上下文':step.kind==='CONNECTOR'?'解析路由与身份配置':'执行并记录完整轨迹'}</small><span class="tag">${esc(step.kind)}</span><span class="tag neutral">已关联</span></div><div class="step-actions"><button data-action="task-move" data-index="${i}" data-dir="-1" aria-label="上移步骤">↑</button><button data-action="task-move" data-index="${i}" data-dir="1" aria-label="下移步骤">↓</button><button data-action="task-remove" data-index="${i}" aria-label="移除步骤">×</button></div></div>`).join('')}</section><aside class="properties"><h3>任务治理</h3><form id="task-form">${field('任务名称','name',s.name)}${field('所属部门','department','财务','text','readonly')}${field('每次执行超时 / 秒','timeout',s.timeout,'number','min="1" max="3600"')}${field('自动重试次数','retries',s.retries,'number','min="0" max="5"')}${field('可信度阈值','confidence',s.confidence,'number','min="0" max="1" step="0.01"')}${field('人工介入条件','humanCondition',s.humanCondition)}${field('负责人','owner',s.owner)}</form><div class="actions">${primary('保存草稿','task-save')}${button('固定测试','task-test')}${button('提交审批','task-submit')}</div><p class="snapshot-note">${badge(asset.state)} · ${esc(asset.activeVersion || '尚未激活')}<br>知识与连接器分别编译为上下文加载和路由解析；Expert 不获得工具执行权限。</p>${testResult(asset.testRun)}</aside></div></div>`;
}

async function departmentPage() {
  const data=await api('/department/dashboard');
  const staffing=db.configs.find(c=>c.id==='staffing');
  const pid=route().params.get('process') || 'P1';
  const config=db.configs.find(c=>c.id==='rules-'+pid), rule=config.spec;
  return pageHeading('财务一人部门看板','One Person Department','一名负责人治理 KPI、人员分配、阈值和异常；配置变化必须经过独立审批。')+
    stats([['KPI 达成',data.kpis[0],'原型演示指标'],['自动处理',data.kpis[1],'原型演示指标'],['人工介入率',data.kpis[2],'演示，单位为 %'],['异常按时关闭',data.kpis[3],'原型演示指标'],['积压',data.kpis[4],'原型演示指标']],true)+
    `<div class="charts-grid"><section class="chart-card"><h3>目标进度</h3><div class="chart-inner"><div class="ring"><div class="ring-text"><strong>96%</strong><span>目标达成</span></div></div><div class="chart-legend"><div><i></i>关账准时率</div><strong style="font-size:19px;color:#253f78">96.2%</strong><div>本月目标 98% · 演示</div></div></div></section><section class="chart-card"><h3>7 天处理量与积压</h3><div class="chart-inner" style="padding-bottom:15px"><div class="bars">${data.volume.map((n,i)=>`<div class="bar-column"><i style="height:${n/2}%" title="处理量 ${n}"></i><b style="height:${data.backlog[i]/2}%" title="积压 ${data.backlog[i]}"></b><span>${['周一','周二','周三','周四','周五','周六','周日'][i]}</span></div>`).join('')}</div></div></section><section class="chart-card"><h3>数字团队健康与负载</h3>${['发票识别','三单匹配','重复发票检查','会计科目建议'].map((n,i)=>`<div class="load-row"><span>${n}</span><div class="progress"><i style="width:${[62,78,89,55][i]}%"></i></div><span>${[62,78,89,55][i]}%</span></div>`).join('')}</section><section class="chart-card"><h3>异常来源占比</h3><div class="chart-inner"><div class="ring" style="background:conic-gradient(#5e83d6 0 144deg,#b69ad6 144deg 252deg,#dbb765 252deg 324deg,#78b9a5 324deg)"><div class="ring-text"><strong>4</strong><span>来源分类</span></div></div><div class="chart-legend">${['金额差异','证据不全','超时待核对','其他异常'].map((n,i)=>`<div><i style="background:${['#5e83d6','#b69ad6','#dbb765','#78b9a5'][i]}"></i>${n} ${[40,30,20,10][i]}%</div>`).join('')}</div></div></section></div>`+
    `<section class="panel"><div class="panel-title"><h2>人工介入点与人员分配</h2>${button('＋ 新增介入点','staff-add')}</div><form id="staff-form"><div class="table-wrap"><table><thead><tr><th>人工介入点</th><th>主负责人</th><th>备选负责人</th><th>响应时限 / 分钟</th></tr></thead><tbody id="staff-rows">${staffing.spec.map(staffRow).join('')}</tbody></table></div></form><div class="actions" style="margin-top:14px">${primary('保存人员分配待审批版本','staff-save')}<span class="tiny muted">当前生效 ${staffing.version} · 审批并激活后才改变默认配置</span></div></section>`+
    `<section class="panel"><div class="panel-title"><h2>流程业务规则</h2><select id="rule-process" aria-label="规则流程">${option('P1','供应商发票审核流程',pid)}${option('P2','月结关账流程',pid)}</select></div><div class="banner">${esc(pid==='P1'?'公司代码 1000 · 应付账款':'集团报表 · 月末关账')}　配置 ${esc(config.version)}　审批责任人 ${esc(rule.owner)}</div><form id="rules-form"><div class="form-grid">${pid==='P1'?
      field('采购订单与发票金额差异率 / %','thresholdPercent',rule.thresholdPercent,'number','min="0" max="100" step="0.01"')+field('收货与开票数量差 / 件','quantityTolerance',rule.quantityTolerance,'number','min="0"')+field('税率异常容忍度 / 百分点','taxTolerancePoints',rule.taxTolerancePoints,'number','min="0" step="0.01"')+field('重复发票识别窗口 / 天','duplicateWindowDays',rule.duplicateWindowDays,'number','min="1"'):
      field('GR/IR 未清项账龄上限 / 天','maxAgeDays',rule.maxAgeDays,'number','min="1"')+field('待处理会计凭证截止时间','deadline',rule.deadline,'time')+field('科目余额环比异常幅度 / %','balanceChangePercent',rule.balanceChangePercent,'number','min="0"')+field('关账任务延期容忍时间 / 小时','delayHours',rule.delayHours,'number','min="0"')
    }</div><label class="check-row"><input type="checkbox" name="strict" ${pid==='P1'?(rule.blockDuplicates?'checked':''):(rule.mandatoryHuman?'checked':'')}>${pid==='P1'?'拦截重复发票、无采购订单发票及供应商银行账户突变':'关账日历关键节点不得绕过人工确认'}</label></form><div class="actions" style="margin-top:14px">${primary('保存规则待审批版本','rules-save')}<span class="tiny muted">活动实例保留绑定的规则版本，草稿不直接影响运行</span></div></section><p class="snapshot-note">${data.source}。图表数据为补充演示数据。</p>`;
}
function staffRow(row) {
  return `<tr><td><input name="point" aria-label="人工介入点" value="${esc(row.point)}"></td><td><input name="owner" aria-label="主负责人" value="${esc(row.owner)}"></td><td><input name="backup" aria-label="备选负责人" value="${esc(row.backup)}"></td><td><input name="minutes" aria-label="响应时限" type="number" min="1" max="1440" value="${row.minutes}" style="width:100px"></td></tr>`;
}
function connectorsPage() {
  const tab=route().params.get('tab') || 'sap';
  const rows=db.connectors.filter(c=>c.tab===tab);
  return pageHeading('连接中心','Connector Hub','独立管理系统实例、身份与凭据、连接状态及业务路由；受治理业务动作由工具中心独立管理。')+
    `<div class="banner">只负责连接到哪里、以谁的身份、通过哪条路由；业务动作、输入输出契约、权限与底层 API 映射在工具中心配置。</div>`+
    tabs([['sap','SAP 系统群'],['messages','协作消息'],['files','文件内容'],['data','数据外围']],tab)+
    (tab==='sap'?stats([['系统实例',8,'演示系统目录'],['生产环境',7,'模拟连接'],['健康正常',6,'模拟健康状态'],['需要关注',2,'模拟健康状态'],['业务路由',12,'原型路由快照']],true)+
      `<section class="panel"><div class="panel-title"><h2>SAP 系统实例</h2><span class="tiny muted">不存储真实凭据</span></div><div class="table-wrap"><table><thead><tr><th>系统别名</th><th>事业部</th><th>区域</th><th>环境</th><th>业务范围</th><th>健康状态</th><th></th></tr></thead><tbody>${rows.map(c=>`<tr><td><strong>${c.name}</strong></td><td>${c.division}</td><td>${c.region}</td><td>${c.environment}</td><td>${c.domain}</td><td>${badge(c.health)}</td><td>${button('查看 / 测试','connector',`data-id="${c.id}"`)}</td></tr>`).join('')}</tbody></table></div></section><section class="panel"><h2>业务路由策略</h2><div class="route-card"><div><strong>SAP 集团核心路由</strong><p class="muted tiny">routeKey: finance.ap · companyCode: 1000</p></div><div><span class="badge green">唯一解析 · 演示</span><p class="muted tiny">S4-集团核心 · v1 · 最小权限身份</p></div></div></section>`:
      `<div class="grid three">${rows.map(c=>`<article class="asset-card"><div class="asset-top"><span class="asset-icon">${tab==='messages'?'↗':tab==='files'?'▤':'⌘'}</span><h3>${c.name}</h3></div><p class="description">${tab==='messages'?'消息接收、发送、通知与证据归档':tab==='files'?'文件提取、内容访问与证据归档':'连接状态：已纳管 · 最小权限 · 调用审计开启'}</p><div class="asset-footer">${badge(c.health)}${button('查看 / 测试','connector',`data-id="${c.id}"`)}</div></article>`).join('')}</div>`);
}
async function toolsPage() {
  const q=route().params, search=q.get('search') || '', access=q.get('access') || '', state=q.get('state') || '';
  const rows=await api('/assets?kind=TOOL&search='+encodeURIComponent(search)+'&access='+access+'&state='+state);
  const all=db.assets.filter(a=>a.kind==='TOOL');
  return pageHeading('工具中心','MCP Tool Hub','独立治理面向 Agent 的业务动作、契约、权限、底层 API 映射、版本、测试、发布与审计。',primary('＋ 新建 MCP Tool','new-tool'))+
    stats([['工具总数',all.length,'本地资产目录'],['只读',all.filter(a=>a.spec.access==='READ').length,'最小权限'],['受控写入',all.filter(a=>a.spec.access==='WRITE').length,'仅模拟适配器'],['待审批',all.filter(a=>a.state==='PENDING_APPROVAL').length,'版本状态'],['调用成功率','99.24%','原型演示指标']],true)+
    `<section class="panel"><div class="toolbar"><input id="tool-search" aria-label="搜索工具" placeholder="搜索业务动作 / API 映射 / 路由" value="${esc(search)}"><select id="tool-access" aria-label="工具权限">${[['','全部权限'],['READ','只读'],['WRITE','受控写入']].map(([v,l])=>option(v,l,access)).join('')}</select><select id="tool-state" aria-label="工具状态">${[['','全部状态'],['ACTIVE','已激活'],['DRAFT','草稿'],['PENDING_APPROVAL','待审批']].map(([v,l])=>option(v,l,state)).join('')}</select>${button('重置','tool-reset')}</div><div class="panel-title"><h2>受治理业务动作</h2><span class="tiny muted">共 ${rows.total} 条</span></div>${rows.total?`<div class="table-wrap"><table><thead><tr><th>业务动作 / 底层映射</th><th>连接路由</th><th>权限</th><th>版本</th><th>测试</th><th>状态</th><th></th></tr></thead><tbody>${rows.items.map(a=>`<tr><td><strong>${esc(a.name)}</strong><small>${esc(a.spec.protocol)} · ${esc(a.spec.mapping)}</small></td><td>${esc(a.spec.route)}</td><td>${badge(a.spec.access)}</td><td>${esc(a.activeVersion || a.version)}</td><td>${a.testRun?`${a.testRun.passed}/${a.testRun.sampleCount}`:`${a.spec.testCount || 0}/${a.spec.testCount || 0}`}<small>演示测试</small></td><td>${badge(a.state)}</td><td>${button('配置','edit-tool',`data-id="${a.id}"`)}</td></tr>`).join('')}</tbody></table></div>`:empty('没有匹配的工具','名称、映射、路由与权限条件采用 AND 筛选。',button('清空筛选','tool-reset'))}</section>`;
}

const SKILL_CATEGORIES=['全部','SAP 业务','文档内容','Excel 数据处理','多表清洗','报告生成','图片','音视频','消息通知','治理安全'];
function skillsPage() {
  const tab=route().params.get('tab') || 'catalog', category=route().params.get('category') || '全部';
  const rows=db.assets.filter(a=>a.kind==='SKILL' && (category==='全部' || a.category===category));
  return pageHeading('业务能力中心','Skill Hub','Skill 组合多个 MCP Tool 完成业务能力；连接路由与工具依赖保持独立治理。')+
    tabs([['catalog','Skill 目录'],['builder','Skill Builder']],tab)+
    (tab==='builder'?skillBuilder():`<div class="pills" style="margin-bottom:16px">${SKILL_CATEGORIES.map(c=>`<button class="pill ${category===c?'active':''}" data-action="skill-category" data-id="${c}">${c}</button>`).join('')}</div><div class="grid three">${rows.map((a,i)=>`<article class="asset-card"><div class="asset-top"><span class="asset-icon">S</span><h3>${esc(a.name)}</h3></div><p class="description">输入文件或业务消息，输出结构化结果与证据引用。</p><div class="asset-meta"><span>${esc(a.category)}</span><span>${esc(a.version)}</span></div><p class="tiny muted">依赖：内容、消息与 SAP 模拟路由<br>权限受控 · 被引用 ${12+i} 次（演示）</p><div class="asset-footer">${badge(a.state)}${button('打开 Builder','design-skill',`data-id="${a.id}"`)}</div></article>`).join('')}</div>`);
}
function testResult(run) {
  if(!run)return '';
  return `<div class="test-result"><strong>确定性沙箱测试 · ${run.passed}/${run.sampleCount}</strong><p class="tiny muted">${esc(run.message)}</p>${run.cases.map(c=>`<div class="test-case"><span>${esc(c.name)}</span><span class="badge green">${c.ruleResult.passed?'规则通过':c.expertResult.recommendation==='ABSTAIN'?'缺证拒答':'转人工'}</span></div>`).join('')}<p class="tiny mono muted" style="margin-top:8px">${run.id}</p></div>`;
}
function skillBuilder() {
  const a=assetById(route().params.get('asset') || 'S1') || assetById('S1'),s=currentSpec(a);
  return `<div class="grid split"><section class="panel"><div class="panel-title"><h2>自然语言定义能力</h2>${badge(a.state)}</div><form id="skill-form" data-asset="${a.id}">${area('业务描述','description',s.description)}${button('填充 / 刷新结构化配置','fill-skill')}<div class="form-grid" style="margin-top:16px">${field('Skill 名称','name',s.name)}${field('草稿版本','version',a.draftVersion || a.version,'text','readonly')}${field('执行模型','model','确定性模拟器','text','readonly')}${field('执行模式','mode','确定性编排','text','readonly')}</div><h3>依赖资产</h3><div class="grid two" style="margin:8px 0 15px"><div><p class="tiny muted">Connector 路由</p>${['SAP 集团核心','文件内容','协作消息'].map(n=>`<label class="check-row"><input type="checkbox" name="routes" value="${n}" ${(s.routes || []).includes(n)?'checked':''}>${n}</label>`).join('')}</div><div><p class="tiny muted">MCP Tool</p>${db.assets.filter(x=>x.kind==='TOOL').slice(0,6).map(x=>`<label class="check-row"><input type="checkbox" name="tools" value="${esc(x.name)}" ${(s.tools || []).includes(x.name)?'checked':''}>${esc(x.name)}</label>`).join('')}</div></div><div class="form-grid">${area('输入 JSON Schema','inputSchema',JSON.stringify(s.inputSchema,null,2),'class="code-editor" spellcheck="false"')}${area('输出 JSON Schema','outputSchema',JSON.stringify(s.outputSchema,null,2),'class="code-editor" spellcheck="false"')}</div></form><div class="actions">${button('保存草稿','skill-save')}${primary('提交发布审批','skill-submit')}</div></section><aside><section class="panel"><h2>固定测试样例</h2><div class="detail-box" style="margin-top:12px">发票 INV-2026-0182<br>公司代码 1000 · PO 4500123<br>金额差异 1.2% · 证据完整<br><span class="muted tiny">与缺证、未授权、阈值边界共 4 个演示用例</span></div>${primary('运行固定测试','skill-test')}${testResult(a.testRun)}</section><section class="panel"><h3>执行与发布边界</h3><p class="muted small" style="margin-top:9px">自然语言仅填充可编辑草稿。测试使用本地模拟适配器，不调用真实模型。提交审批不会替换已发布版本。</p><div class="banner" style="margin-top:13px;margin-bottom:0">当前活动版：${esc(a.activeVersion || '无')}<br>模型准确率、成本及延迟尚未实测。</div></section></aside></div>`;
}
function expertsPage() {
  const a=assetById('E1'),s=currentSpec(a);
  return pageHeading('专家中心','Expert Hub','独立判断资产：读取知识与可信 Skill 结果，不绑定 Connector / MCP Tool，也不执行任何系统动作。')+
    `<div class="grid split"><section class="panel"><div class="panel-title"><h2>判断目标与配置</h2>${badge(a.state)}</div><form id="expert-form" data-asset="E1">${area('自然语言判断目标','description',s.description)}${button('填充判断配置','fill-expert')}<div class="form-grid" style="margin-top:16px">${field('Expert 名称','name',s.name)}${field('模型','model','确定性模拟器','text','readonly')}</div><h3>知识 / 证据输入</h3>${['应付与供应商域','企业制度财务与内控','历史批准案例'].map(n=>`<label class="check-row"><input type="checkbox" name="knowledge" value="${n}" ${(s.knowledge || []).includes(n)?'checked':''}>${n}</label>`).join('')}<label class="check-row"><input type="checkbox" name="skillResult" ${(s.skillResults || []).length?'checked':''}>可选 Skill 结果：三单匹配</label><div class="form-grid" style="margin-top:15px">${field('至少可追溯证据引用数','minEvidence',s.minEvidence,'number','min="2"')}${field('负责人','owner',s.owner)}</div><label class="check-row"><input type="checkbox" name="abstainWithoutEvidence" ${s.abstainWithoutEvidence?'checked':''}>启用引用校验 / 无证据拒答</label></form><div class="actions" style="margin-top:16px">${button('保存草稿','expert-save')}${primary('提交审批','expert-submit')}</div></section><aside><section class="panel"><h2>职责边界</h2><div class="banner warning" style="margin-top:12px">Expert 仅生成建议、简短依据和证据引用。它没有连接器、工具注册表或系统写入权限。</div><dl class="kv"><dt>允许输出</dt><dd>ALLOW_REVIEW / BLOCK / ABSTAIN</dd><dt>必须包含</dt><dd>confidence、evidenceRefs、requiresHuman</dd><dt>证据不足 / 冲突</dt><dd>拒答并转人工</dd><dt>人工条件</dt><dd>规则强制人工时，建议不得覆盖</dd></dl></section><section class="panel"><h2>评测与拒答治理</h2><p class="muted small" style="margin:9px 0 12px">检查阈值边界、缺证拒答与未授权服务场景；仅为固定沙箱用例。</p>${primary('运行评测集','expert-test')}${testResult(a.testRun)}</section><section class="panel"><h3>责任与审批</h3><p class="small muted" style="margin-top:8px">${esc(s.owner)}<br>${esc(s.approvalChain)}</p><p class="tiny muted" style="margin-top:8px">当前活动版本 ${esc(a.activeVersion || '无')} · 知识、Prompt 与规则的变更均需要新版本审批。</p></section></aside></div>`;
}

async function flowPage() {
  const r=route(), aid=r.params.get('flow') || 'P1', a=assetById(aid) || assetById('P1');
  if(!flow || flow.id!==a.id || (!flow.dirty && !flow.saving))flow={id:a.id,spec:currentSpec(a),dirty:false,selected:flow?.id===a.id?flow.selected:'match',category:flow?.category || 'TASK',undo:flow?.id===a.id?flow.undo:[],redo:flow?.id===a.id?flow.redo:[]};
  const tab=r.params.get('tab') || 'design';
  let content='';
  if(tab==='runs') {
    const rows=await api('/processes/'+a.id+'/instances?mode=linked');
    content=`<section class="panel"><div class="panel-title"><h2>该流程的运行记录</h2><span class="tiny muted">实例保留启动时的流程版本</span></div>${rows.total?instanceTable(rows.items):empty('暂无运行记录','启动联动场景后，这里显示真实保存的演示实例。')}</section>`;
  } else if(tab==='versions') {
    content=`<section class="panel"><h2>版本与草稿</h2><div class="banner" style="margin-top:12px">活动版本 ${esc(a.activeVersion || '无')} · ${badge(a.state)} · 草稿 ${esc(a.draftVersion || '尚未创建')}。提交与审批均不会立即切换活动版。</div>${a.versions.map(v=>`<div class="approval-card"><div class="panel-title" style="margin-bottom:5px"><strong>${esc(v.version)}</strong>${badge(v.state)}</div><p class="tiny muted">${v.spec.nodes?.length || 0} 个业务节点 · ${v.spec.edges?.length || 0} 条连线 · 创建者 ${esc(v.createdBy)}</p></div>`).join('')}<div class="detail-box"><strong>草稿与活动版差异</strong><p class="tiny muted">${flow.spec.nodes.length} 个草稿节点 / ${a.activeSpec?.nodes?.length || 0} 个活动节点；${stable(flow.spec)===stable(a.activeSpec)?'配置相同':'配置或画布位置存在差异'}</p></div>${button('前往资产审批','goto-approvals')}</section>`;
  } else {
    const items=flowLibrary();
    const selected=flow.spec.nodes.find(n=>n.id===flow.selected);
    content=`<div class="builder-overflow"><div class="flow-layout"><aside class="builder-library"><h3>节点库</h3><p class="tiny muted">点击节点插入到当前选中节点之后</p>${tabs([['TASK','任务智能体'],['EXPERT','Expert'],['RULE','业务规则'],['HUMAN','人工介入'],['ERP_WRITE','SAP 与审计']],flow.category,'flow-category')}<input id="flow-search" aria-label="搜索节点或业务资产" placeholder="搜索节点或业务资产" style="width:100%;font-size:10px;margin:4px 0 2px">${items.map(n=>`<button class="library-item" data-action="flow-insert" data-kind="${n.type}" data-name="${esc(n.name)}"><strong>＋ ${esc(n.name)}</strong><small>${esc(n.description)}</small></button>`).join('')}</aside><div class="flow-canvas" id="flow-canvas" tabindex="0" aria-label="流程画布，可拖动节点，滚轮缩放"><div class="flow-tools">${button('−','flow-zoom','data-dir="-1"')}<span id="flow-zoom-label" class="tiny muted" style="min-width:34px;text-align:center">60%</span>${button('＋','flow-zoom','data-dir="1"')}${button('适应画布','flow-fit')}<span class="tiny muted" style="padding:0 4px">Skill / Tool 在任务内部调用</span></div><div class="flow-stage" id="flow-stage"></div><div class="canvas-note">拖动节点或空白区域 · 滚轮缩放 · 点击连线端口添加连接</div></div><aside class="properties" id="flow-properties">${flowProperties(selected)}</aside></div></div>`;
  }
  return pageHeading('流程构建器','Flow Builder','编排业务骨架：任务智能体执行并调用 Skill，Expert 独立判断，规则、人工、SAP 写入与审计均为可治理节点。')+
    `<section class="panel builder-bar"><div class="actions"><strong>${esc(a.name)} · ${esc(a.draftVersion || a.version)}</strong>${badge(a.draftSpec?'DRAFT':a.state)}${tabs([['design','设计'],['runs','运行记录'],['versions','版本']],tab)}<span class="save-state" id="flow-save-state">${flow.dirty?'未保存':'草稿已载入'}</span></div><div class="actions">${button('↶','flow-undo','aria-label="撤销"')}${button('↷','flow-redo','aria-label="重做"')}${button('自动布局','flow-layout')}${button('保存草稿','flow-save')}${button('测试运行','flow-test')}${primary('提交审批','flow-submit')}</div></section>${content}`;
}
function flowLibrary() {
  const type=flow.category;
  if(type==='TASK')return db.assets.filter(a=>a.kind==='TASK').map(a=>({type,name:a.name+'任务智能体',description:'执行业务核验并输出结构化结果，内部调用 Skill'}));
  if(type==='EXPERT')return [{type,name:'应付账款复核专家',description:'仅根据证据生成建议，不执行任何系统动作'}];
  if(type==='RULE')return ['采购订单与发票金额差异率','收货数量与开票数量差异','GR/IR 未清项账龄上限','待处理会计凭证截止时间'].map(name=>({type,name,description:'确定性阈值判断与条件分支'}));
  if(type==='HUMAN')return [{type,name:'三单差异复核',description:'正常审批或异常复核；记录身份、证据与决定'}];
  return [{type:'ERP_WRITE',name:'受控会计凭证预制',description:'验证审批、版本与证据后调用模拟适配器'},{type:'AUDIT',name:'审计归档',description:'追加审计与对象结果，归档执行轨迹'}];
}
function flowProperties(n) {
  if(!n)return empty('选择一个节点','点击画布节点查看属性。');
  return `<h3>节点属性</h3><p class="tiny muted">业务语义、能力引用与治理边界</p><div class="detail-box" style="margin-top:9px"><strong>${esc(n.type)}</strong><br>${esc(n.name)}</div><form id="node-form">${field('节点名称','name',n.name)}${area('执行职责','responsibility',n.responsibility || '')}${n.type==='HUMAN'?field('主负责人','owner',n.owner)+field('备选负责人','backup',n.backup):''}${n.type==='TASK'?field('引用 Skill（任务内部）','skill',n.skill || ''):''}${field('输出契约','outputContract',n.outputContract || '结构化业务结果 + 证据引用')}</form><div class="detail-box"><strong>依赖 / 边界</strong><p class="tiny muted">${n.type==='EXPERT'?'只接收知识与可信结果；无工具权限':n.type==='ERP_WRITE'?'批准快照一致、最小权限、幂等写入':'依赖锁定发布版本；失败转人工'}</p></div>${button('删除节点','flow-delete',`data-id="${n.id}"`)}<p class="snapshot-note mono">${esc(n.id)}</p>`;
}
function flowSnapshot() { flow.undo.push(clone(flow.spec)); if(flow.undo.length>30)flow.undo.shift();flow.redo=[]; }
function changedFlow(autosave=true) {
  flow.dirty=true;$('#flow-save-state') && ($('#flow-save-state').textContent='未保存');
  if(autosave && actor!=='auditor'){clearTimeout(flowSaveTimer);flowSaveTimer=setTimeout(()=>saveFlow(true).catch(reportError),800);}
}
function drawFlow() {
  const stage=$('#flow-stage');if(!stage)return;
  const s=flow.spec,byId=Object.fromEntries(s.nodes.map(n=>[n.id,n]));
  const viewport=s.viewport || {x:10,y:0,zoom:.6};
  stage.style.transform=`translate(${viewport.x}px,${viewport.y}px) scale(${viewport.zoom})`;
  $('#flow-zoom-label').textContent=Math.round(viewport.zoom*100)+'%';
  stage.innerHTML=`<svg class="flow-svg" aria-hidden="true"><defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#a7b3c5"/></marker></defs>${s.edges.map(e=>{
    const a=byId[e.source],b=byId[e.target];if(!a || !b)return '';
    const x1=a.x+180,y1=a.y+52,x2=b.x,y2=b.y+52,mid=(x1+x2)/2;
    return `<path d="M${x1} ${y1} C${mid} ${y1} ${mid} ${y2} ${x2-2} ${y2}" fill="none" stroke="${e.source===flow.selected?'#6d8dcc':'#b8c3d2'}" stroke-width="1.7" marker-end="url(#arrow)"/>${e.condition?`<text x="${mid}" y="${(y1+y2)/2-8}" fill="#8b98ad" font-size="10" text-anchor="middle">${esc(e.condition)}</text>`:''}`;
  }).join('')}</svg>${s.nodes.map(n=>`<div class="flow-node ${n.type} ${n.id===flow.selected?'selected':''}" data-node="${n.id}" style="left:${n.x}px;top:${n.y}px" role="button" tabindex="0" aria-label="${esc(n.name)}"><span class="node-port in" data-port="in" data-node-id="${n.id}"></span><small>${{EVENT:'事件',TASK:'任务智能体',RULE:'业务规则',EXPERT:'独立专家',HUMAN:'人工介入',ERP_WRITE:'受控 SAP 写入',AUDIT:'统一审计',END:'结束'}[n.type]}</small><strong>${esc(n.name)}</strong><div class="node-desc">${n.type==='EVENT'?'邮件 / 文件事件':n.type==='TASK'?'执行：结构化核验':n.type==='RULE'?'确定性阈值判断':'证据留痕 · 边界清晰'}</div>${n.type==='TASK'?`<span class="tag">Skill · ${esc(n.skill || '三单匹配')}</span>`:''}<span class="node-port out" data-port="out" data-node-id="${n.id}"></span></div>`).join('')}`;
}
function setupFlow() {
  const canvas=$('#flow-canvas');if(!canvas)return;drawFlow();
  let dragging=null;
  canvas.addEventListener('pointerdown',e=>{
    if(e.target.closest('button'))return;
    const port=e.target.closest('[data-port]');
    if(port){
      if(port.dataset.port==='out'){flow.connecting=port.dataset.nodeId;toast('选择目标节点左侧连接口');}
      else if(flow.connecting){
        const source=flow.connecting,target=port.dataset.nodeId;flow.connecting=null;
        if(source===target || flow.spec.edges.some(x=>x.source===source&&x.target===target)){toast('连接无效或已经存在');return;}
        flowSnapshot();flow.spec.edges.push({source,target,condition:''});drawFlow();changedFlow();
      }
      return;
    }
    const el=e.target.closest('[data-node]');
    if(el){
      flow.selected=el.dataset.node;const node=flow.spec.nodes.find(n=>n.id===flow.selected);
      $('#flow-properties').innerHTML=flowProperties(node);
      dragging={type:'node',node,startX:e.clientX,startY:e.clientY,x:node.x,y:node.y,before:clone(flow.spec),moved:false};
    }else dragging={type:'pan',startX:e.clientX,startY:e.clientY,x:flow.spec.viewport.x,y:flow.spec.viewport.y,before:clone(flow.spec),moved:false};
    canvas.setPointerCapture(e.pointerId);drawFlow();
  });
  canvas.addEventListener('pointermove',e=>{
    if(!dragging)return;
    const dx=e.clientX-dragging.startX,dy=e.clientY-dragging.startY;
    if(Math.abs(dx)+Math.abs(dy)>3)dragging.moved=true;
    if(dragging.type==='node'){
      dragging.node.x=Math.max(0,Math.round(dragging.x+dx/flow.spec.viewport.zoom));
      dragging.node.y=Math.max(0,Math.round(dragging.y+dy/flow.spec.viewport.zoom));
    }else{flow.spec.viewport.x=dragging.x+dx;flow.spec.viewport.y=dragging.y+dy;}
    drawFlow();
  });
  function finish(){if(dragging?.moved){flow.undo.push(dragging.before);flow.redo=[];changedFlow();}dragging=null;}
  canvas.addEventListener('pointerup',finish);canvas.addEventListener('pointercancel',finish);
  canvas.addEventListener('wheel',e=>{e.preventDefault();flow.spec.viewport.zoom=Math.max(.25,Math.min(1.5,flow.spec.viewport.zoom*(e.deltaY>0?.9:1.1)));drawFlow();changedFlow();},{passive:false});
  canvas.addEventListener('keydown',e=>{const n=e.target.closest('[data-node]');if(n && (e.key==='Enter'||e.key===' ')){e.preventDefault();flow.selected=n.dataset.node;$('#flow-properties').innerHTML=flowProperties(flow.spec.nodes.find(x=>x.id===flow.selected));drawFlow();}});
}
async function saveFlow(silent=false) {
  clearTimeout(flowSaveTimer);
  const targetFlow=flow;
  if(targetFlow.saving)await targetFlow.saving;
  const a=assetById(targetFlow.id), hash=stable(targetFlow.spec), value=clone(targetFlow.spec);
  if(!targetFlow.dirty && a.state==='DRAFT'){if(!silent)toast('草稿已保存');return a;}
  $('#flow-save-state') && ($('#flow-save-state').textContent='保存中…');
  const operation=api('/assets/'+a.id+'/draft','PUT',{spec:value,expectedRevision:a.revision});
  targetFlow.saving=operation;
  try{
    const saved=await operation;Object.assign(a,saved);targetFlow.dirty=stable(targetFlow.spec)!==hash;
    if(flow===targetFlow && $('#flow-save-state'))$('#flow-save-state').textContent=targetFlow.dirty?'有新的未保存修改':'草稿已保存';
    if(!silent)toast('流程草稿已保存，活动版本保持不变');
    if(flow===targetFlow && targetFlow.dirty)changedFlow();return a;
  }finally{targetFlow.saving=null;}
}

const graphTypes=[['ALL','全部'],['SAP','SAP 对象'],['CONTEXT','外部上下文'],['PERSON','人员角色'],['EVENT','业务事件'],['RULE','可执行规则']];
const graphColors={SAP:'#4e8bd8',CONTEXT:'#a06bd3',PERSON:'#4aa88b',EVENT:'#c8984e',RULE:'#c9658b'};
let graphData=null, graphSelected='price', graphCamera=JSON.parse(localStorage.getItem('erp-graph-camera') || '{"yaw":0.12,"pitch":0.08,"zoom":1}');
async function knowledgePage() {
  const params=route().params,type=params.get('type') || 'ALL',search=params.get('search') || '';
  graphData=await api('/knowledge/graph?type='+type+'&search='+encodeURIComponent(search));
  if(!graphData.nodes.some(n=>n.id===graphSelected))graphSelected=graphData.nodes[0]?.id || null;
  return pageHeading('企业认知基座','Enterprise Cognitive Foundation','统一关联外部上下文、SAP 业务对象、人员、事件与企业规则，构成可追溯的企业知识关系。')+
    `<div class="toolbar"><input id="graph-search" placeholder="搜索对象、关系或规则，例如采购订单、价格变更" aria-label="搜索知识图谱" value="${esc(search)}"><div class="pills">${graphTypes.map(([id,label])=>`<button class="pill ${id===type?'active':''}" data-action="graph-filter" data-id="${id}">${label}</button>`).join('')}</div></div><div class="graph-layout"><div class="graph-canvas" id="graph-canvas"><canvas id="graph" aria-label="可拖动旋转、滚轮缩放和点击节点的三维知识图谱"></canvas><div class="graph-legend">${graphTypes.slice(1).map(([id,label])=>`<div><i style="background:${graphColors[id]}"></i>${label}</div>`).join('')}</div><div class="canvas-note">拖动旋转 · 滚轮缩放 · 点击节点查看关系</div>${!graphData.nodes.length?'<div style="position:absolute;inset:100px 0 0;pointer-events:none">'+empty('没有匹配的知识实体','请调整关键词或清空筛选。')+'</div>':''}</div><aside class="graph-detail" id="graph-detail"></aside></div><p class="snapshot-note">12 个固定三维实体及演示关系。知识反馈需要审核，不会自动修改生产规则或模型。</p>`;
}
function setupGraph() {
  const canvas=$('#graph');if(!canvas)return;
  const container=$('#graph-canvas'),ctx=canvas.getContext('2d');let width=0,height=0,projected=[],pointer=null;
  async function showDetails(id) {
    if(!id){$('#graph-detail').innerHTML=empty('未选中实体');return;}
    try{
      const node=await api('/knowledge/entities/'+id);if(graphSelected!==id || !$('#graph-detail'))return;
      const visibleIds=new Set(graphData.nodes.map(n=>n.id));
      $('#graph-detail').innerHTML=`<span class="tiny muted">${esc(graphTypes.find(t=>t[0]===node.type)?.[1])}</span><h2>${esc(node.name)}</h2><p class="tiny muted">${esc(node.english)}</p><p class="small muted" style="margin-top:9px">${esc(node.description)}</p><span class="tag neutral">${esc(node.businessKey)}</span>${node.neighbors.filter(n=>visibleIds.has(n.id)).map(n=>`<button class="relation" data-action="graph-select" data-id="${n.id}"><small>${esc(graphTypes.find(t=>t[0]===n.type)?.[1])}</small><strong>${esc(n.name)}</strong><small>${esc(n.english)}</small><p class="tiny muted" style="margin-top:5px">${esc(n.description)}</p></button>`).join('')}<p class="snapshot-note">来源：演示知识快照 · 证据与业务类型独立标识</p>`;
    }catch(e){reportError(e);}
  }
  function project(node) {
    let [x,y,z]=node.position;const cy=Math.cos(graphCamera.yaw),sy=Math.sin(graphCamera.yaw),cp=Math.cos(graphCamera.pitch),sp=Math.sin(graphCamera.pitch);
    const xx=x*cy+z*sy,zz=-x*sy+z*cy,yy=y*cp-zz*sp,depth=y*sp+zz*cp;
    const perspective=6/(6-depth),scale=Math.min(width/5.6,height/4.9)*graphCamera.zoom;
    return {node,x:width/2+xx*scale*perspective,y:height/2-yy*scale*perspective,z:depth,r:(node.id===graphSelected?9:5)*perspective};
  }
  function draw() {
    ctx.clearRect(0,0,width,height);projected=graphData.nodes.map(project).sort((a,b)=>a.z-b.z);
    const map=Object.fromEntries(projected.map(n=>[n.node.id,n]));
    for(const edge of graphData.edges){const a=map[edge.source],b=map[edge.target];if(!a||!b)continue;const active=edge.source===graphSelected||edge.target===graphSelected;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.lineWidth=active?1.3:.7;ctx.strokeStyle=active?'#6a8fa6bb':'#8a9cbf25';ctx.stroke();}
    for(const p of projected){const color=graphColors[p.node.type];const glow=ctx.createRadialGradient(p.x,p.y,1,p.x,p.y,p.r*3);glow.addColorStop(0,color+'77');glow.addColorStop(1,color+'00');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(p.x,p.y,p.r*3,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.stroke();if(p.node.id===graphSelected){ctx.beginPath();ctx.arc(p.x,p.y,p.r+5,0,Math.PI*2);ctx.lineWidth=2;ctx.strokeStyle=color+'66';ctx.stroke();}ctx.textAlign='center';ctx.font=`${p.node.id===graphSelected?'600 ':''}10px Arial,"Microsoft YaHei",sans-serif`;ctx.fillStyle='#324256';ctx.fillText(p.node.name,p.x,p.y+p.r+16);ctx.font='8px Arial,sans-serif';ctx.fillStyle='#8795aa';ctx.fillText(p.node.english,p.x,p.y+p.r+29);}
  }
  function resize(){const rect=container.getBoundingClientRect();width=rect.width;height=rect.height;const dpr=window.devicePixelRatio || 1;canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);draw();}
  const observer=new ResizeObserver(resize);observer.observe(container);
  canvas.addEventListener('pointerdown',e=>{pointer={x:e.clientX,y:e.clientY,yaw:graphCamera.yaw,pitch:graphCamera.pitch,moved:false};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{if(!pointer)return;const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;if(Math.abs(dx)+Math.abs(dy)>4)pointer.moved=true;if(pointer.moved){graphCamera.yaw=pointer.yaw+dx*.007;graphCamera.pitch=Math.max(-1.15,Math.min(1.15,pointer.pitch+dy*.007));draw();}});
  canvas.addEventListener('pointerup',e=>{if(pointer&&!pointer.moved){const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;const hit=[...projected].reverse().find(p=>Math.hypot(p.x-x,p.y-y)<19);if(hit){graphSelected=hit.node.id;draw();showDetails(graphSelected);}}pointer=null;localStorage.setItem('erp-graph-camera',JSON.stringify(graphCamera));});
  canvas.addEventListener('wheel',e=>{e.preventDefault();graphCamera.zoom=Math.max(.6,Math.min(2.5,graphCamera.zoom*(e.deltaY>0?.92:1.08)));draw();localStorage.setItem('erp-graph-camera',JSON.stringify(graphCamera));},{passive:false});
  canvas.selectNode=id=>{graphSelected=id;draw();showDetails(id);};
  showDetails(graphSelected);graphCleanup=()=>observer.disconnect();
}

const GOVERNANCE=[['Connector','最小权限与凭据到期检查'],['MCP Tool','Schema、权限、映射与版本锁定'],['Skill','输入输出契约与版本锁定'],['Task Agent','超时、重试与可信度阈值'],['Process Agent','审批后激活与受控写入'],['Expert','证据校验、无证据拒答与输出边界'],['人工决定','职责分离与证据完整性']];
async function auditPage() {
  const tab=route().params.get('tab') || 'trace', search=route().params.get('search') || '', iid=route().params.get('trace') || '';
  const header=pageHeading('审计与治理','Audit & Governance','Connector、MCP Tool、Skill、Task Agent、Process Agent、Expert 与人工决定形成职责分离的统一审计链。')+tabs([['trace','统一审计链'],['approvals','资产发布审批']],tab);
  if(tab==='approvals')return header+approvalsPage();
  const result=await api('/audit/events?search='+encodeURIComponent(search)+'&instanceId='+encodeURIComponent(iid));
  return header+`<div class="toolbar"><input id="audit-search" placeholder="搜索实例、trace、主体或操作" aria-label="搜索审计" value="${esc(search)}">${button('清空筛选','audit-reset')}${iid?`<span class="tag">${esc(iid)}</span>`:''}<span class="tiny muted">${result.total} 条记录</span></div><div class="grid split"><section class="panel"><div class="panel-title"><h2>${iid?'实例审计链':'统一审计链'}</h2><span class="tiny muted">追加记录 · 时间为 Asia/Shanghai</span></div>${result.items.length?result.items.slice().reverse().map(e=>`<div class="audit-entry"><div class="audit-time">${time(e.occurredAt)}<small style="display:block">#${e.sequence}</small></div><div><div class="audit-actor">${esc(e.actorType)} · ${esc(e.actorId)}</div><div class="audit-title">${esc(e.action)}</div><p class="audit-detail">${esc(e.detail)}</p><div style="margin-top:5px"><button class="link-button tiny muted" data-action="audit-event" data-id="${e.sequence}">${esc(e.instanceId || e.refs?.[0] || e.traceId)} ↗</button>${e.outcome!=='SUCCESS'?` <span class="badge red">${esc(e.outcome)}</span>`:''}</div></div></div>`).join(''):empty('暂无审计记录','调整搜索条件，或执行一项演示操作。')}</section><section class="panel" style="height:max-content"><h2>治理控制</h2>${GOVERNANCE.map(([h,p])=>`<div class="governance-row"><span class="check-icon">✓</span><div><strong>${h}</strong><p class="tiny muted">${p}</p></div><span class="badge green">开启</span></div>`).join('')}<p class="snapshot-note">本地 SQLite 通过触发器禁止应用更新或删除审计记录；演示重置会明确清空演示数据。未实现外部防篡改归档。</p></section></div>`;
}
function approvalsPage() {
  const approvals=[...db.approvals].reverse();
  return `<div class="banner">业务审批与资产发布审批分开存储。提交人不能批准自己的版本；请使用右上角“独立审批人”处理发布审批。</div><section class="panel"><div class="panel-title"><h2>发布与配置审批</h2><span class="tiny muted">${approvals.filter(a=>a.state==='PENDING').length} 项待处理</span></div>${approvals.length?approvals.map(a=>{
    const asset=assetById(a.assetId);
    const stateBadge=a.state==='APPROVED'?(asset.activeVersion===a.version?badge('ACTIVE'):'<span class="badge blue">已批准</span>'):badge(a.state);
    return `<article class="approval-card"><div class="panel-title" style="margin-bottom:4px"><h3>${esc(a.name)} · ${esc(a.version)}</h3>${stateBadge}</div><p class="tiny muted">${esc(a.kind)} · 提交人 ${esc(a.submittedBy)} · ${date(a.createdAt)} · 快照 ${a.specHash.slice(0,12)}</p><p class="small muted">${esc(a.comment || '')}</p><div class="actions">${a.state==='PENDING'?primary('批准版本','approval-approve',`data-id="${a.id}"`)+button('拒绝','approval-reject',`data-id="${a.id}"`):a.state==='APPROVED' && asset.state==='APPROVED'?primary('激活已批准版本','asset-activate',`data-id="${a.assetId}"`):a.state==='APPROVED'?'<span class="tiny muted">版本已激活或已被后续版本替代</span>':''}${button('查看配置快照','approval-detail',`data-id="${a.id}"`)}</div></article>`;
  }).join(''):empty('暂无发布审批','保存配置或资产草稿、测试后可提交审批。')}</section>`;
}

function layer(title,subtitle,body,footer='',wide=false) {
  return `<div class="overlay modal-overlay" data-backdrop><section class="modal ${wide?'wide':''}" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div class="drawer-head"><div><h2 id="dialog-title">${esc(title)}</h2><p class="tiny muted">${esc(subtitle)}</p></div><button class="close" data-action="close-overlay" aria-label="关闭">×</button></div><div class="drawer-body">${body}</div><div class="drawer-foot">${footer || button('关闭','close-overlay')}</div></section></div>`;
}
function paintLayer() {
  $('#overlay-root').innerHTML=overlayStack.at(-1)?.html || '';
  if(overlayStack.length) {
    const focus=$('[autofocus],input:not([readonly]):not([type=checkbox]),textarea,button', $('#overlay-root'));
    focus?.focus({preventScroll:true});
  }else restoreFocus?.focus?.({preventScroll:true});
}
function openLayer(html) {
  if(!overlayStack.length)restoreFocus=document.activeElement;
  overlayStack.push({html,dirty:false});paintLayer();
}
function closeLayer(force=false) {
  if(overlayStack.at(-1)?.dirty && !force && !confirm('表单尚未保存，确定放弃修改吗？'))return;
  overlayStack.pop();paintLayer();
  if(!overlayStack.length){currentInstance=null;const u=new URL(location.href);u.searchParams.delete('instance');history.replaceState({},'',u.pathname+u.search);}
}
function clearLayers() { overlayStack=[];paintLayer(); }
async function openInstance(iid,updateUrl=true) {
  const row=await api('/instances/'+encodeURIComponent(iid));currentInstance=row;
  if(updateUrl){const u=new URL(location.href);u.searchParams.set('instance',iid);history.replaceState({},'',u.pathname+u.search);}
  const pending=row.decisions.find(d=>d.state==='PENDING');
  const rule=row.ruleResult,expert=row.expertResult;
  const footer=(pending?primary('批准继续','decision-resolve','data-kind="APPROVE"')+button('补充材料','decision-resolve','data-kind="REQUEST_CHANGES"')+button('驳回重做','decision-resolve','data-kind="RETURN_FOR_REWORK"')+`<button class="btn danger" data-action="decision-resolve" data-kind="REJECT">拒绝</button>`:'')+
    (['WAITING_HUMAN','WAITING_INPUT'].includes(row.status)?button('补充授权及订单证据','add-evidence'):'')+
    (row.status==='RUNNING' && row.approvedHash?primary('继续复核并模拟执行','instance-advance'):'')+
    (row.status==='RECONCILING'?primary('核对模拟远端结果','instance-reconcile'):'')+
    (row.status==='COMPLETED'||row.status==='REJECTED'?button('添加反馈','add-feedback'):'')+
    button('查看审计','instance-audit');
  const html=`<div class="overlay" data-backdrop><section class="drawer" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div class="drawer-head"><div><h2 id="dialog-title">业务实例详情</h2><p class="tiny muted mono">${esc(row.id)}</p></div><button class="close" data-action="close-overlay" aria-label="关闭实例详情">×</button></div><div class="drawer-body"><section class="drawer-section"><div class="panel-title"><h2>${esc(row.supplier)}</h2>${badge(row.status)}</div><dl class="kv"><dt>金额</dt><dd><strong style="font-size:21px">${money(row.amountMinor)}</strong></dd><dt>当前节点</dt><dd>${esc(row.node)}</dd><dt>任务智能体</dt><dd>${esc(row.task)}</dd><dt>负责人</dt><dd>${esc(row.owner)}</dd><dt>流程 / 规则版本</dt><dd>${esc(row.processVersion)} / ${esc(row.ruleVersion)}</dd><dt>场景</dt><dd>${row.scenario==='linked'?'新建联动演示':row.scenario==='queue'?'独立人工决策示例':'原型业务列表快照'}</dd></dl></section>
    ${row.id==='INV-2026-0179'&&!row.emailAdjusted?`<div class="banner warning" style="display:block">原型初始金额为 ¥126,800。点击下方按钮显式模拟邮件调整事件；读取详情不会修改金额。<div style="margin-top:8px">${primary('模拟邮件金额调整 → ¥16,500','email-event')}</div></div>`:''}
    <section class="drawer-section"><h3>任务链与能力资产</h3><div class="detail-box">发票识别 → 三单匹配 → 金额阈值判断 → 三单匹配 → 人工决策 → 审计归档<br><span class="tag">Task Agent · 三单匹配</span><span class="tag">Skill · 发票 OCR 提取</span><span class="tag">Expert · 应付账款复核专家</span></div></section>
    <section class="drawer-section"><h3>外部上下文</h3><div class="detail-box"><strong>供应商邮件与发票附件（演示）</strong><p>设备维护服务金额调整为 ${money(row.amountMinor)}，附发票与服务完成说明。外部内容仅作为业务证据。</p><p class="tiny muted">供应商：${esc(row.supplier)} · 公司代码 1000</p></div></section>
    <section class="drawer-section"><h3>SAP 结构化事实</h3><dl class="kv"><dt>采购订单</dt><dd>PO-4500123 · ${money(row.poAmountMinor)}</dd><dt>收货凭证</dt><dd>${row.evidence.some(e=>e.type==='GOODS_RECEIPT')?'GR-50007621 · 已有收货证据':'缺少收货记录'}</dd><dt>新增服务授权</dt><dd>${row.serviceAuthorized?'已补充授权证据':'待核实授权与修订订单'}</dd></dl></section>
    <section class="drawer-section"><h3>三单差异与专家建议</h3>${rule?`<div class="detail-box"><strong>金额差异 ${money(rule.differenceMinor)} · ${esc(rule.variancePercent)}%</strong><p class="tiny muted">差异率分母为采购订单金额；阈值 ${esc(rule.thresholdPercent)}%</p>${rule.mandatoryHuman?'<span class="badge yellow">规则要求人工复核</span>':'<span class="badge green">金额规则校验通过</span>'}</div>`:''}<div class="banner ${expert?.recommendation==='ABSTAIN'?'warning':''}" style="display:block">${esc(expert?.rationaleSummary || '这是原型列表记录。新增联动场景将生成规则结果与结构化专家建议。')}<p class="tiny" style="margin-top:6px">${expert?`模拟 Expert · ${esc(expert.recommendation)} · 置信度 ${expert.confidence}`:'所有外部系统均使用模拟器'}</p></div></section>
    <section class="drawer-section"><h3>业务证据 <span class="tiny muted">${row.evidence.length} 项</span></h3>${row.evidence.map(e=>`<div class="evidence-item"><div><strong>${esc(e.name)}</strong><small>${esc(e.source)} · ${esc(e.hash.slice(0,14))}</small></div>${button('查看','evidence-detail',`data-id="${e.id}"`)}</div>`).join('')}<p class="tiny muted mono">快照 ${row.evidenceSnapshotHash}</p></section>
    ${pending?`<section class="drawer-section"><h3>人工决定</h3><div class="detail-box">责任人：${pending.assignee==='operator'?'财务负责人':'独立审批人'} · 备选：${pending.backup==='operator'?'财务负责人':'独立审批人'}<br>规则：${esc(pending.rule)} · ${esc(pending.ruleVersion)}<br>批准后恢复至写入前复核，不能直接视为 ERP 写入成功。</div><label class="field">意见 / 补证或拒绝原因<textarea id="decision-reason" placeholder="批准可选；补证、驳回或拒绝必须填写原因"></textarea></label></section>`:''}
    <section class="drawer-section"><h3>ERP 读取 / 受控写入对象</h3><div class="detail-box">允许读取：供应商主数据、采购订单、收货记录<br>受控写入：模拟会计凭证 / 付款建议<br><strong>真实 ERP 写入：关闭</strong>${row.externalObject?`<br>模拟对象号：<span class="mono">${esc(row.externalObject)}</span>`:''}</div>${row.invocations.map(v=>`<p class="tiny muted">调用 ${v.state} · 模拟调用次数 ${v.calls} · ${esc(v.externalObject || '未生成对象')}</p>`).join('')}</section>
    <section class="drawer-section"><h3>时间线与审计记录</h3><div class="timeline">${row.timeline.length?row.timeline.map(e=>`<div class="timeline-item"><span class="tiny muted">${time(e.occurredAt)} · ${esc(e.actorType)}</span><div><strong>${esc(e.action)}</strong></div><p>${esc(e.detail)}</p></div>`).join(''):'<p class="tiny muted">当前为初始快照，尚未发生本地操作。</p>'}</div><p class="snapshot-note mono">${esc(row.traceId)}</p></section>
    ${row.feedback.length?`<section class="drawer-section"><h3>待审核反馈</h3>${row.feedback.map(x=>`<div class="detail-box">${esc(x.reason)}<p class="tiny muted">待审核；未修改活动规则</p></div>`).join('')}</section>`:''}
    </div><div class="drawer-foot">${footer}</div></section></div>`;
  if(overlayStack.length && $('.drawer', $('#overlay-root'))){overlayStack[overlayStack.length-1]={html,dirty:false};paintLayer();}
  else openLayer(html);
}
async function updateInstance() {
  const iid=currentInstance.id;clearLayers();await refreshData();await render();
  if(!overlayStack.length)await openInstance(iid,false);
}
function toMinor(text) {
  const value=String(text).trim();
  if(!/^\d+(\.\d{1,2})?$/.test(value))throw new Error('金额必须为正数，最多两位小数');
  const [whole,frac='']=value.split('.');const amount=Number(whole)*100+Number(frac.padEnd(2,'0'));
  if(!Number.isSafeInteger(amount)||amount<=0)throw new Error('金额超出有效范围');return amount;
}
function showEvidenceForm() {
  const row=currentInstance;
  openLayer(layer('补充业务证据','本地模拟证据；提交后旧待办与旧批准失效，重新进入人工复核。',
    `<form id="evidence-form">${area('新增服务授权与修订订单说明','note','已由采购负责人核实服务授权，采购订单修订为发票金额，并完成服务验收。')}${field('修订采购订单金额 / 元','poAmount',String(row.amountMinor/100),'number','min="0.01" step="0.01"')}<label class="check-row"><input name="includeReceipt" type="checkbox" checked>同时补充服务收货记录（模拟）</label></form>`,button('取消','close-overlay')+primary('存证并重新提交','evidence-submit')));
}
function showStartScenario() {
  openLayer(layer('启动发票联动场景','运行后将自动切换到实时聚合的联动演示。',
    `<div class="banner" style="display:block">供应商邮件与发票 → 模拟 OCR → 三单匹配 → 规则 R-21 → 专家建议 → 人工复核 → 受控模拟写入 → 审计归档</div><form id="scenario-form">${selectField('故障注入','fault',[['none','标准差异复核场景'],['missing_receipt','缺少收货证据：专家拒答'],['write_timeout','写入超时：模拟远端已成功，需核对'],['write_failure','写入明确失败：保留异常记录']],'none')}</form><p class="muted small">发票 ¥16,500，采购订单 ¥18,500，差异 10.8%。需补充授权与修订订单，再批准继续。不会访问真实 SAP、模型或邮件系统。</p>`,button('取消','close-overlay')+primary('启动场景','scenario-launch')));
}
function showDelegate() {
  api('/decisions').then(result=>{
    if(!result.total){toast('当前没有可委派的待办');return;}
    openLayer(layer('批量委派','只改变责任人，不改变批准状态。',`<form id="delegate-form">${result.items.map(d=>`<label class="check-row"><input type="checkbox" name="tasks" value="${d.id}" data-revision="${d.revision}" checked>${esc(d.title)}</label>`).join('')}<div class="form-grid" style="margin-top:15px">${selectField('目标审批人','assignee',[['reviewer','独立审批人'],['operator','财务负责人']],'reviewer')}${selectField('备选审批人','backup',[['operator','财务负责人'],['reviewer','独立审批人']],'operator')}</div>${area('委派原因','reason','')}</form>`,button('取消','close-overlay')+primary('提交委派','delegate-submit')));
  }).catch(reportError);
}
function toolForm(asset=null) {
  const s=asset?currentSpec(asset):{name:'',protocol:'OData',mapping:'',route:'SAP 集团核心路由',access:'READ',inputSchema:{type:'object',properties:{companyCode:{type:'string'}},required:['companyCode']},outputSchema:{type:'object',properties:{result:{type:'object'},evidenceRefs:{type:'array',items:{type:'string'}}}},writeConditions:'业务审批有效、证据快照一致、最小权限'};
  const locked=asset&&['PENDING_APPROVAL','APPROVED'].includes(asset.state);
  return `<form id="tool-form" data-asset="${asset?.id || ''}"><section class="drawer-section"><h3>1 基本信息</h3>${field('业务动作名称','name',s.name)}<div class="form-grid">${field('领域','domain',s.domain || '财务 · 应付账款')}${field('负责人','owner',s.owner || asset?.owner || '财务业务运营负责人')}</div></section><section class="drawer-section"><h3>2 接口映射</h3><div class="form-grid">${selectField('协议','protocol',[['OData','OData'],['BAPI','BAPI'],['RFC','RFC'],['Business API','Business API'],['Mock API','Mock API']],s.protocol)}${field('底层业务 API / Operation','mapping',s.mapping)}</div><p class="tiny muted">映射文本仅作演示；生产预制与过账契约需独立确认。</p></section><section class="drawer-section"><h3>3 Schema / 输入输出</h3>${area('输入 JSON Schema','inputSchema',JSON.stringify(s.inputSchema,null,2),'class="code-editor" spellcheck="false"')}${area('输出 JSON Schema','outputSchema',JSON.stringify(s.outputSchema,null,2),'class="code-editor" spellcheck="false"')}</section><section class="drawer-section"><h3>4 身份权限</h3>${field('Connector 路由','route',s.route)}${selectField('访问模式','access',[['READ','只读'],['WRITE','受控写入']],s.access)}${area('写入前置条件','writeConditions',s.writeConditions)}</section><section class="drawer-section"><h3>5 测试用例</h3><div class="detail-box">固定沙箱检查：正常差异、缺收货、未授权服务、阈值边界。所有测试使用本地模拟适配器。</div>${asset?testResult(asset.testRun):''}</section><section class="drawer-section"><h3>6 审批发布</h3><p class="tiny muted">保存为草稿 → 固定测试 → 独立审批 → 激活版本。</p>${asset?`<div style="margin-top:7px">${badge(asset.state)} <span class="tiny muted">活动版 ${esc(asset.activeVersion || '无')}</span></div>`:''}${locked?'<div class="banner warning" style="margin-top:10px">该版本已锁定，请在资产审批中完成审批或驳回。</div>':''}</section></form>`;
}
function showTool(id=null,replace=false) {
  const a=id?assetById(id):null, locked=a&&['PENDING_APPROVAL','APPROVED'].includes(a.state);
  const html=`<div class="overlay" data-backdrop><section class="drawer" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div class="drawer-head"><div><h2 id="dialog-title">${a?'配置业务动作':'创建受治理业务动作'}</h2><p class="tiny muted">MCP Tool · 业务契约与治理资产</p></div><button class="close" data-action="close-overlay" aria-label="关闭工具配置">×</button></div><div class="drawer-body">${toolForm(a)}</div><div class="drawer-foot">${!locked?primary(a?'保存草稿':'创建草稿','tool-save')+(a?button('固定测试','tool-test')+button('提交发布审批','tool-submit'):''):button('前往资产审批','goto-approvals')}</div></section></div>`;
  if(replace){overlayStack[overlayStack.length-1]={html,dirty:false};paintLayer();}else openLayer(html);
}
function parseSchema(value,label) {
  try{return JSON.parse(value);}catch{throw new Error(label+'不是合法 JSON，请检查逗号、引号及括号');}
}
function readToolForm() {
  const form=$('#tool-form'),fd=new FormData(form);
  return {name:fd.get('name').trim(),protocol:fd.get('protocol'),mapping:fd.get('mapping').trim(),
    route:fd.get('route').trim(),access:fd.get('access'),inputSchema:parseSchema(fd.get('inputSchema'),'输入 Schema'),
    outputSchema:parseSchema(fd.get('outputSchema'),'输出 Schema'),writeConditions:fd.get('writeConditions'),domain:fd.get('domain'),owner:fd.get('owner'),testCount:0};
}
function replaceAsset(a) {const index=db.assets.findIndex(x=>x.id===a.id);if(index<0)db.assets.push(a);else db.assets[index]=a;return a;}
async function ensureDraft(a,spec) {
  const current=currentSpec(a);
  if(stable(current)===stable(spec) && a.state==='DRAFT')return a;
  const result=await api('/assets/'+a.id+'/draft','PUT',{spec,expectedRevision:a.revision});replaceAsset(result);return result;
}
async function saveTool() {
  const form=$('#tool-form'),id=form.dataset.asset,spec=readToolForm(),fd=new FormData(form);
  if(!spec.name)throw new Error('请填写业务动作名称');
  const saved=id?await ensureDraft(assetById(id),{...currentSpec(assetById(id)),...spec}):await api('/assets','POST',{kind:'TOOL',name:spec.name,owner:fd.get('owner'),spec});
  replaceAsset(saved);if(overlayStack.at(-1))overlayStack.at(-1).dirty=false;return saved;
}
function showNewProcess() {
  openLayer(layer('新建流程智能体','基于发票示例骨架创建独立草稿，创建后进入流程构建器。',`<form id="new-process-form">${field('流程名称','name','')}${field('所属部门','department','财务','text','readonly')}${field('业务对象','businessObject','供应商发票')}${field('负责人','owner','财务业务运营负责人')}</form>`,button('取消','close-overlay')+primary('创建并进入构建器','create-process')));
}
function showImportFlow() {
  const template=clone(assetById('P1').activeSpec);
  openLayer(layer('导入流程模板','只接受 FlowDefinition JSON，不执行导入文件中的任何代码。',`<form id="import-form">${field('流程名称','name','导入的发票审核流程')}<label class="field">选择本地 JSON 文件<input id="import-file" type="file" accept=".json,application/json"></label>${area('FlowDefinition JSON','definition',JSON.stringify(template,null,2),'class="code-editor" style="min-height:260px" spellcheck="false"')}</form>`,button('导出示例模板','download-flow')+primary('校验并导入草稿','import-submit'),true));
}
function readAssetForm(kind) {
  const form=$('#'+kind+'-form');if(!form)throw new Error('请先打开设计器');
  const id=form.dataset.asset || task?.id,a=assetById(id),s=currentSpec(a),fd=new FormData(form);
  if(kind==='skill')Object.assign(s,{description:fd.get('description'),name:fd.get('name'),routes:fd.getAll('routes'),tools:fd.getAll('tools'),inputSchema:parseSchema(fd.get('inputSchema'),'输入 Schema'),outputSchema:parseSchema(fd.get('outputSchema'),'输出 Schema')});
  if(kind==='expert')Object.assign(s,{description:fd.get('description'),name:fd.get('name'),knowledge:fd.getAll('knowledge'),skillResults:fd.has('skillResult')?['三单匹配']:[],minEvidence:Number(fd.get('minEvidence')),owner:fd.get('owner'),abstainWithoutEvidence:fd.has('abstainWithoutEvidence')});
  if(kind==='task')Object.assign(s,task.spec,{name:fd.get('name'),timeout:Number(fd.get('timeout')),retries:Number(fd.get('retries')),confidence:fd.get('confidence'),owner:fd.get('owner'),humanCondition:fd.get('humanCondition')});
  return {asset:a,spec:s};
}
async function saveAssetForm(kind) {
  const {asset,spec}=readAssetForm(kind),a=await ensureDraft(asset,spec);
  formDirty=false;if(kind==='task')task.dirty=false;return a;
}
let pendingFill=null;
function showFill(kind) {
  const {asset,spec}=readAssetForm(kind);pendingFill={kind,spec:clone(spec)};
  if(kind==='skill'){pendingFill.spec.name='供应商发票三单匹配';pendingFill.spec.routes=['SAP 集团核心','文件内容'];pendingFill.spec.tools=['读取采购订单','读取收货记录','校验供应商发票'];}
  else{pendingFill.spec.minEvidence=2;pendingFill.spec.abstainWithoutEvidence=true;pendingFill.spec.knowledge=['应付与供应商域','企业制度财务与内控','历史批准案例'];}
  openLayer(layer('预览结构化配置','确定性演示填充，仅应用到当前表单，不自动运行或发布。',`<div class="grid two"><div><h3>当前配置</h3><pre class="detail-box mono" style="white-space:pre-wrap">${esc(JSON.stringify(spec,null,2))}</pre></div><div><h3>建议草稿</h3><pre class="detail-box mono" style="white-space:pre-wrap">${esc(JSON.stringify(pendingFill.spec,null,2))}</pre></div></div>`,button('取消','close-overlay')+primary('应用到可编辑草稿','apply-fill'),true));
}
function applyFill() {
  const {kind,spec}=pendingFill;closeLayer(true);
  const form=$('#'+kind+'-form');
  for(const name of ['name','minEvidence'])if(form.elements[name] && spec[name]!=null)form.elements[name].value=spec[name];
  for(const name of ['routes','tools','knowledge'])$$(`input[name="${name}"]`,form).forEach(el=>el.checked=(spec[name] || []).includes(el.value));
  if(kind==='expert')form.elements.abstainWithoutEvidence.checked=true;
  formDirty=true;pendingFill=null;toast('结构化草稿已应用，保存后才持久化');
}

async function runAssetOperation(kind,operation) {
  let a;
  if(kind==='flow')a=await saveFlow(true);
  else if(kind==='tool')a=await saveTool();
  else a=await saveAssetForm(kind);
  if(operation==='save') {
    toast('草稿已保存，活动版本保持不变');
    if(kind==='tool')showTool(a.id,true);else if(kind!=='flow')await render();
    return;
  }
  if(operation==='test') {
    const result=await api('/assets/'+a.id+'/test-runs','POST',{expectedRevision:a.revision});replaceAsset(result.asset);
    if(kind==='tool')showTool(a.id,true);
    else if(kind==='flow')openLayer(layer('流程固定测试结果',result.run.message,testResult(result.run),button('关闭','close-overlay'),true));
    else await render();
    toast('4 个固定沙箱用例通过，非真实模型评测');return;
  }
  const result=await api('/assets/'+a.id+'/submit','POST',{expectedRevision:a.revision,comment:'本地演示版本提交'});replaceAsset(result.asset);
  formDirty=false;if(flow)flow.dirty=false;if(task)task.dirty=false;
  clearLayers();await refreshData();await render();
  openLayer(layer('已提交发布审批','活动版本保持不变。',`<div class="banner success">${esc(a.name)}已进入独立审批队列。</div><p class="muted small">在右上角切换为“独立审批人”，前往审计与治理批准版本，再执行激活。</p>`,button('留在当前页','close-overlay')+primary('前往资产审批','goto-approvals')));
}

async function insertFlowNode(kind,name,chosenEdge=null) {
  const selected=flow.spec.nodes.find(n=>n.id===flow.selected) || flow.spec.nodes.find(n=>n.type==='AUDIT');
  if(selected.type==='END'){toast('请选择结束节点之前的一个节点');return;}
  const outgoing=flow.spec.edges.filter(e=>e.source===selected.id);
  if(outgoing.length>1 && !chosenEdge) {
    openLayer(layer('选择插入分支','当前节点有多个出边，请选择需要拆分的连线。',`<form id="insert-branch-form"><input type="hidden" name="kind" value="${kind}"><input type="hidden" name="name" value="${esc(name)}">${selectField('目标分支','target',outgoing.map(e=>[e.target,`${e.condition || '无条件'} → ${flow.spec.nodes.find(n=>n.id===e.target)?.name}`]),outgoing[0].target)}</form>`,primary('插入节点','flow-insert-branch')));return;
  }
  flowSnapshot();const edge=chosenEdge?outgoing.find(e=>e.target===chosenEdge):outgoing[0];
  const node={id:'node-'+crypto.randomUUID().slice(0,8),type:kind,name,x:selected.x+220,y:selected.y+120,owner:'应付账款负责人',backup:'财务运营负责人',responsibility:'执行业务核验并记录结构化结果',skill:'三单匹配',outputContract:'结构化结果 + evidenceRefs'};
  flow.spec.nodes.push(node);
  if(edge) {
    flow.spec.edges=flow.spec.edges.filter(e=>e!==edge);
    flow.spec.edges.push({source:selected.id,target:node.id,condition:edge.condition});
    if(kind==='RULE'){flow.spec.edges.push({source:node.id,target:edge.target,condition:'PASS'},{source:node.id,target:edge.target,condition:'REVIEW'});}
    else flow.spec.edges.push({source:node.id,target:edge.target,condition:''});
  }else flow.spec.edges.push({source:selected.id,target:node.id,condition:''});
  flow.selected=node.id;changedFlow();drawFlow();$('#flow-properties').innerHTML=flowProperties(node);toast('节点已插入，提交前将校验完整流程');
}

async function handleAction(action,el) {
  const id=el?.dataset.id;
  if(['flow','skill','expert','task','tool'].some(k=>action.startsWith(k+'-')&&['save','test','submit'].includes(action.split('-')[1]))) {
    const [kind,op]=action.split('-');return runAssetOperation(kind,op);
  }
  switch(action) {
    case 'mobile-nav':$('#sidebar').classList.toggle('open');return;
    case 'refresh':if(permitNavigation())await render();toast('已读取最新持久化状态');return;
    case 'goto-runtime':navigate('/runtime');return;
    case 'goto-flow':navigate('/flow-builder?flow=P1');return;
    case 'goto-approvals':if(overlayStack.at(-1))overlayStack.at(-1).dirty=false;clearLayers();navigate('/audit?tab=approvals');return;
    case 'instances':navigate('/runtime/processes/'+id);return;
    case 'design-process':navigate('/flow-builder?flow='+id);return;
    case 'design-task':task=null;navigate('/task-agents?tab=designer&asset='+id);return;
    case 'design-skill':navigate('/skills?tab=builder&asset='+id);return;
    case 'tab':updateQuery({tab:id});return;
    case 'instance':await openInstance(id);return;
    case 'close-overlay':closeLayer();return;
    case 'clear-instance-filter':updateQuery({status:null});return;
    case 'start-scenario':showStartScenario();return;
    case 'scenario-launch':{
      const data=await api('/scenarios/linked','POST',{fault:new FormData($('#scenario-form')).get('fault')});
      mode='linked';localStorage.setItem('erp-mode',mode);clearLayers();navigate('/runtime/processes/P1?instance='+data.id);toast('邮件、OCR、匹配与专家建议已模拟完成，等待人工复核');return;
    }
    case 'email-event':await api('/instances/'+currentInstance.id+'/events','POST',{type:'email_adjustment_0179',expectedRevision:currentInstance.revision});await updateInstance();toast('显式邮件调整事件已提交，金额与待办已联动');return;
    case 'quick-approve':{
      const result=await api('/decisions'),d=result.items.find(x=>x.id===id);if(!d)throw new Error('待办已更新，请刷新');
      try{await api('/decisions/'+id+'/resolve','POST',{action:'APPROVE',reason:'已核验证据，批准继续',expectedRevision:d.revision,evidenceSnapshotHash:d.evidenceSnapshotHash});await render();toast('已批准，实例恢复至写入前复核');}
      catch(error){await openInstance(d.instanceId);throw error;}return;
    }
    case 'decision-resolve':{
      const d=currentInstance.decisions.find(d=>d.state==='PENDING'),kind=el.dataset.kind;
      const result=await api('/decisions/'+d.id+'/resolve','POST',{action:kind,reason:$('#decision-reason')?.value || '',returnNodeId:'match',expectedRevision:d.revision,evidenceSnapshotHash:d.evidenceSnapshotHash});
      if(overlayStack.at(-1))overlayStack.at(-1).dirty=false;await updateInstance();toast(kind==='APPROVE'?'已批准，等待写入前复核':'人工决定已保存到审计链');return result;
    }
    case 'add-evidence':showEvidenceForm();return;
    case 'evidence-submit':{
      const fd=new FormData($('#evidence-form'));
      await api('/instances/'+currentInstance.id+'/evidence','POST',{expectedRevision:currentInstance.revision,note:fd.get('note'),poAmountMinor:toMinor(fd.get('poAmount')),includeReceipt:fd.has('includeReceipt')});
      await updateInstance();toast('新证据已存档，原待办已失效，请重新审批');return;
    }
    case 'evidence-detail':{
      const e=currentInstance.evidence.find(e=>e.id===id);
      openLayer(layer(e.name,e.source,`<div class="banner">模拟证据内容预览；未接入真实文档服务。</div><p style="white-space:pre-wrap">${esc(e.content)}</p><dl class="kv" style="margin-top:20px"><dt>证据 ID</dt><dd class="mono">${esc(e.id)}</dd><dt>内容指纹</dt><dd class="mono">${esc(e.hash)}</dd><dt>证据类型</dt><dd>${esc(e.type)}</dd></dl>`));return;
    }
    case 'instance-advance':case 'instance-reconcile':{
      await api('/instances/'+currentInstance.id+'/'+(action==='instance-advance'?'advance':'reconcile'),'POST',{expectedRevision:currentInstance.revision});await updateInstance();toast(currentInstance.status==='COMPLETED'?'模拟凭证已归档，审计链已更新':'模拟执行状态已更新');return;
    }
    case 'instance-audit':{const iid=currentInstance.id;clearLayers();navigate('/audit?trace='+encodeURIComponent(iid));return;}
    case 'add-feedback':openLayer(layer('添加业务反馈','反馈进入待审核案例池，不直接修改规则或模型。',`<form id="feedback-form">${area('纠错理由或处理结果反馈','reason','')}</form>`,primary('提交待审核反馈','feedback-submit')));return;
    case 'feedback-submit':await api('/instances/'+currentInstance.id+'/feedback','POST',{reason:new FormData($('#feedback-form')).get('reason')});await updateInstance();toast('反馈已进入待审核案例池');return;
    case 'delegate':showDelegate();return;
    case 'delegate-submit':{
      const form=$('#delegate-form'),fd=new FormData(form),revisions={};$$('input[name=tasks]:checked',form).forEach(e=>revisions[e.value]=Number(e.dataset.revision));
      await api('/decisions/delegate','POST',{taskIds:fd.getAll('tasks'),assigneeId:fd.get('assignee'),backupId:fd.get('backup'),reason:fd.get('reason'),revisions});clearLayers();await render();toast('责任人已委派，审批状态保持待处理');return;
    }
    case 'new-process':showNewProcess();return;
    case 'create-process':{
      const fd=new FormData($('#new-process-form')),spec=clone(assetById('P1').activeSpec);spec.name=fd.get('name');spec.businessObject=fd.get('businessObject');
      const a=await api('/assets','POST',{kind:'PROCESS',name:fd.get('name'),owner:fd.get('owner'),spec});clearLayers();flow=null;navigate('/flow-builder?flow='+a.id);toast('独立流程草稿已创建');return;
    }
    case 'import-flow':showImportFlow();return;
    case 'download-flow':{
      const content=new Blob([JSON.stringify(assetById('P1').activeSpec,null,2)],{type:'application/json'}),url=URL.createObjectURL(content),link=document.createElement('a');link.href=url;link.download='erp-flow-template.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;
    }
    case 'import-submit':{
      const fd=new FormData($('#import-form')),spec=parseSchema(fd.get('definition'),'流程模板');
      const a=await api('/assets','POST',{kind:'PROCESS',name:fd.get('name'),spec});clearLayers();flow=null;navigate('/flow-builder?flow='+a.id);toast('模板校验通过，已导入独立草稿');return;
    }
    case 'flow-category':flow.category=id;await render();return;
    case 'flow-insert':await insertFlowNode(el.dataset.kind,el.dataset.name);return;
    case 'flow-insert-branch':{const fd=new FormData($('#insert-branch-form'));closeLayer(true);await insertFlowNode(fd.get('kind'),fd.get('name'),fd.get('target'));return;}
    case 'flow-layout':{
      flowSnapshot();const order=[],seen=new Set(),queue=flow.spec.nodes.filter(n=>n.type==='EVENT');while(queue.length){const n=queue.shift();if(seen.has(n.id))continue;seen.add(n.id);order.push(n);queue.push(...flow.spec.edges.filter(e=>e.source===n.id).map(e=>flow.spec.nodes.find(n=>n.id===e.target)).filter(Boolean));}
      order.push(...flow.spec.nodes.filter(n=>!seen.has(n.id)));order.forEach((n,i)=>{n.x=35+i*220;n.y=['EXPERT','HUMAN'].includes(n.type)?355:180;});drawFlow();changedFlow();toast('节点位置已自动排列，条件与依赖保持不变');return;
    }
    case 'flow-zoom':flow.spec.viewport.zoom=Math.max(.25,Math.min(1.5,flow.spec.viewport.zoom+Number(el.dataset.dir)*.1));drawFlow();changedFlow();return;
    case 'flow-fit':{
      const c=$('#flow-canvas'),maxX=Math.max(...flow.spec.nodes.map(n=>n.x+190)),maxY=Math.max(...flow.spec.nodes.map(n=>n.y+120));
      flow.spec.viewport={zoom:Math.max(.25,Math.min(1,(c.clientWidth-30)/maxX,(c.clientHeight-60)/maxY)),x:10,y:30};drawFlow();changedFlow();return;
    }
    case 'flow-undo':case 'flow-redo':{
      const source=action==='flow-undo'?flow.undo:flow.redo,target=action==='flow-undo'?flow.redo:flow.undo;if(!source.length){toast('没有可恢复的操作');return;}target.push(clone(flow.spec));flow.spec=source.pop();drawFlow();$('#flow-properties').innerHTML=flowProperties(flow.spec.nodes.find(n=>n.id===flow.selected));changedFlow();return;
    }
    case 'flow-delete':{
      const node=flow.spec.nodes.find(n=>n.id===id);if(['EVENT','END','AUDIT'].includes(node.type)){toast('入口、终点和必要审计节点不可删除');return;}
      const related=flow.spec.edges.filter(e=>e.source===id||e.target===id);
      openLayer(layer('删除流程节点','删除将同时移除相邻连接，需要重新连接后通过流程校验。',`<p>删除“${esc(node.name)}”，影响 ${related.length} 条连接。</p><input id="delete-node-id" type="hidden" value="${id}">`,button('取消','close-overlay')+primary('删除节点与相关连接','flow-delete-confirm')));return;
    }
    case 'flow-delete-confirm':{const nid=$('#delete-node-id').value;closeLayer(true);flowSnapshot();flow.spec.nodes=flow.spec.nodes.filter(n=>n.id!==nid);flow.spec.edges=flow.spec.edges.filter(e=>e.source!==nid&&e.target!==nid);flow.selected='match';drawFlow();$('#flow-properties').innerHTML=flowProperties(flow.spec.nodes.find(n=>n.id===flow.selected));changedFlow();return;}
    case 'task-category':task.category=id;await render();return;
    case 'task-add':{
      if(task.spec.steps.some(s=>s.kind===el.dataset.kind&&s.name===el.dataset.name)){toast('该资产已关联，请选择其他资产');return;}
      task.spec.steps.push({id:'step-'+crypto.randomUUID().slice(0,8),name:el.dataset.name,kind:el.dataset.kind,assetId:id || null});task.dirty=true;await render();toast('已加入执行步骤：'+el.dataset.name);return;
    }
    case 'task-remove':task.spec.steps.splice(Number(el.dataset.index),1);task.dirty=true;await render();return;
    case 'task-move':{
      const i=Number(el.dataset.index),j=i+Number(el.dataset.dir);if(j<0||j>=task.spec.steps.length)return;[task.spec.steps[i],task.spec.steps[j]]=[task.spec.steps[j],task.spec.steps[i]];task.dirty=true;await render();return;
    }
    case 'staff-add':$('#staff-rows').insertAdjacentHTML('beforeend',staffRow({point:'新介入点',owner:'财务运营负责人',backup:'应付账款负责人',minutes:30}));formDirty=true;return;
    case 'staff-save':case 'rules-save':{
      const isStaff=action==='staff-save',cid=isStaff?'staffing':'rules-'+(route().params.get('process')||'P1'),config=db.configs.find(c=>c.id===cid);let spec;
      if(isStaff)spec=$$('#staff-rows tr').map(row=>({point:$('[name=point]',row).value,owner:$('[name=owner]',row).value,backup:$('[name=backup]',row).value,minutes:Number($('[name=minutes]',row).value)}));
      else{spec=clone(config.spec);const fd=new FormData($('#rules-form'));for(const [k,v] of fd){if(k!=='strict')spec[k]=['quantityTolerance','duplicateWindowDays','maxAgeDays'].includes(k)?Number(v):v;}spec[cid==='rules-P1'?'blockDuplicates':'mandatoryHuman']=fd.has('strict');}
      await api('/config-drafts','POST',{configId:cid,spec,expectedRevision:config.revision});formDirty=false;await render();openLayer(layer('配置已保存为待审批版本','当前生效配置保持不变。',`<div class="banner success">${isStaff?'人员分配':'业务规则'}已提交独立审批，测试记录与配置快照一并保存。</div>`,button('继续查看','close-overlay')+primary('前往资产审批','goto-approvals')));return;
    }
    case 'connector':{
      const c=db.connectors.find(c=>c.id===id);openLayer(layer(c.name,'连接与路由详情 · 不返回真实凭据',`<dl class="kv"><dt>健康状态</dt><dd>${badge(c.health)}</dd><dt>连接路由版本</dt><dd>${esc(c.routeVersion)}</dd><dt>凭据引用</dt><dd class="mono">demo://no-credentials</dd><dt>权限</dt><dd>最小权限 · 真实系统调用关闭</dd></dl>${c.lastTest?`<div class="banner ${c.lastTest.success?'success':'warning'}" style="margin-top:16px">${esc(c.lastTest.message)} · ${date(c.lastTest.at)}</div>`:''}`,primary('运行模拟连接测试','connector-test',`data-id="${id}"`)));return;
    }
    case 'connector-test':{const c=await api('/connectors/'+id+'/test','POST',{});db.connectors[db.connectors.findIndex(x=>x.id===id)]=c;closeLayer(true);await handleAction('connector',{dataset:{id}});toast(c.lastTest.message);return;}
    case 'new-tool':showTool();return;
    case 'edit-tool':showTool(id);return;
    case 'tool-reset':updateQuery({search:null,access:null,state:null});return;
    case 'skill-category':updateQuery({category:id});return;
    case 'fill-skill':showFill('skill');return;
    case 'fill-expert':showFill('expert');return;
    case 'apply-fill':applyFill();return;
    case 'graph-filter':updateQuery({type:id});return;
    case 'graph-select':$('#graph')?.selectNode(id);return;
    case 'audit-reset':updateQuery({search:null,trace:null});return;
    case 'audit-event':{
      const result=await api('/audit/events'),e=result.items.find(e=>e.sequence===Number(id));
      openLayer(layer('审计事件 #'+id,e.action,`<dl class="kv">${[['追踪 ID',e.traceId],['业务实例',e.instanceId || '—'],['执行身份',e.actorType+' / '+e.actorId],['规则版本',e.ruleVersion || '—'],['证据快照',e.evidenceSnapshotHash || '—'],['证据引用',(e.evidenceRefs || []).join(', ') || '—'],['资产引用',(e.refs || []).join(', ') || '—'],['执行结果',e.outcome],['详细说明',e.detail]].map(([k,v])=>`<dt>${esc(k)}</dt><dd class="mono">${esc(v)}</dd>`).join('')}</dl>`));return;
    }
    case 'approval-detail':{const a=db.approvals.find(x=>x.id===id);openLayer(layer(a.name+' · '+a.version,'审批绑定不可编辑的配置快照',`<pre class="detail-box mono" style="white-space:pre-wrap">${esc(JSON.stringify(a.spec,null,2))}</pre>`,button('关闭','close-overlay'),true));return;}
    case 'approval-approve':{
      const a=db.approvals.find(x=>x.id===id);await api('/approvals/'+id+'/resolve','POST',{action:'APPROVE',expectedRevision:a.revision});await render();toast('版本已批准，激活后才生效');return;
    }
    case 'approval-reject':openLayer(layer('拒绝版本发布','拒绝后可重新编辑草稿。',`<form id="reject-approval-form" data-id="${id}">${area('拒绝原因','reason','')}</form>`,primary('保存拒绝决定','approval-reject-submit')));return;
    case 'approval-reject-submit':{
      const form=$('#reject-approval-form'),a=db.approvals.find(x=>x.id===form.dataset.id);await api('/approvals/'+a.id+'/resolve','POST',{action:'REJECT',expectedRevision:a.revision,reason:new FormData(form).get('reason')});clearLayers();await render();toast('版本已驳回，当前活动版保持不变');return;
    }
    case 'asset-activate':{const a=assetById(id);await api('/assets/'+id+'/activate','POST',{expectedRevision:a.revision});await render();toast('已批准版本已激活，存量实例仍保留原版本');return;}
    case 'reset':openLayer(layer('重置本地演示','这会清空本 Demo 创建的数据、草稿、决定与审计，并恢复初始示例。',`<p class="muted small">仅影响当前项目 data/erp_demo.sqlite3 中的演示数据。此操作无法撤销。</p>`,button('取消','close-overlay')+primary('确认重置演示数据','reset-confirm')));return;
    case 'reset-confirm':{
      await api('/demo/reset','POST',{confirm:'RESET_DEMO'});clearLayers();formDirty=false;flow=null;task=null;clearTimeout(flowSaveTimer);actor='operator';mode='replay';localStorage.removeItem('erp-graph-camera');localStorage.setItem('erp-mode',mode);localStorage.setItem('erp-actor',actor);graphCamera={yaw:.12,pitch:.08,zoom:1};navigate('/runtime');toast('初始演示数据已恢复');return;
    }
  }
}

document.addEventListener('click',async event=>{
  const nav=event.target.closest('a[data-nav]');
  if(nav){event.preventDefault();$('#sidebar').classList.remove('open');navigate(nav.getAttribute('href'));return;}
  const el=event.target.closest('[data-action]');
  if(el){
    event.preventDefault();if(el.disabled)return;
    const action=el.dataset.action;el.disabled=true;
    try{await handleAction(action,el);}catch(error){reportError(error);}finally{if(el.isConnected)el.disabled=false;}
  } else if(event.target.matches('[data-backdrop]'))closeLayer();
});
document.addEventListener('input',event=>{
  const el=event.target;
  if(el.id==='flow-search'){$$('.library-item',main).forEach(item=>item.hidden=!item.textContent.includes(el.value));return;}
  const searchIds={'tool-search':'search','graph-search':'search','audit-search':'search'};
  if(searchIds[el.id]){clearTimeout(searchTimer);const pos=el.selectionStart,value=el.value,id=el.id;searchTimer=setTimeout(async()=>{await updateQuery({[searchIds[id]]:value});const next=$('#'+id);next?.focus();next?.setSelectionRange(pos,pos);},300);return;}
  if(el.closest('#node-form')){
    const node=flow.spec.nodes.find(n=>n.id===flow.selected);node[el.name]=el.value;drawFlow();changedFlow();return;
  }
  if(el.closest('#overlay-root')){if(overlayStack.at(-1))overlayStack.at(-1).dirty=true;return;}
  if(el.closest('#task-form')){task.spec[el.name]=['timeout','retries'].includes(el.name)?Number(el.value):el.value;task.dirty=true;return;}
  if(el.closest('form'))formDirty=true;
});
document.addEventListener('change',async event=>{
  const el=event.target;
  try{
    if(el.id==='mode-select'){
      if(!permitNavigation()){el.value=mode;return;}mode=el.value;localStorage.setItem('erp-mode',mode);await render();
    }else if(el.id==='actor-select'){
      if(!permitNavigation()){el.value=actor;return;}actor=el.value;localStorage.setItem('erp-actor',actor);clearLayers();await render();
    }else if(el.id==='instance-filter')updateQuery({status:el.value});
    else if(el.id==='rule-process')updateQuery({process:el.value});
    else if(el.id==='tool-access'||el.id==='tool-state')updateQuery({access:$('#tool-access').value,state:$('#tool-state').value});
    else if(el.id==='import-file'){
      const file=el.files[0];if(!file)return;if(file.size>1024*1024)throw new Error('模板文件最多 1 MB');$('#import-form [name=definition]').value=await file.text();overlayStack.at(-1).dirty=true;
    }
  }catch(error){reportError(error);}
});
document.addEventListener('submit',event=>event.preventDefault());
document.addEventListener('keydown',event=>{
  if(!overlayStack.length)return;
  if(event.key==='Escape'){event.preventDefault();closeLayer();}
  if(event.key==='Tab'){
    const focusable=$$('button:not(:disabled),input:not(:disabled):not([type=hidden]),select:not(:disabled),textarea:not(:disabled),a[href]',$('#overlay-root'));
    const first=focusable[0],last=focusable.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  }
});
window.addEventListener('popstate',()=>{clearLayers();formDirty=false;if(flow)flow.dirty=false;if(task)task.dirty=false;render();});
window.addEventListener('beforeunload',event=>{if(dirty() || overlayStack.some(x=>x.dirty)){event.preventDefault();event.returnValue='';}});
setInterval(async()=>{try{const d=await api('/decisions');pendingCount=d.total;const el=$('#nav-pending');if(el)el.textContent=d.total;}catch{}},15000);
if(location.pathname==='/')history.replaceState({},'','/runtime');
render();
