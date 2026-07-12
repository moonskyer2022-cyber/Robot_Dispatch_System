const api = {
  session: "/api/auth/session",
  login: "/api/auth/login",
  logout: "/api/auth/logout",
  robots: "/api/robots",
  summary: "/api/summary",
  tasks: "/api/tasks",
  nodes: "/api/map/nodes",
  edges: "/api/map/edges",
  dispatch: "/api/dispatch/run",
  logs: "/api/dispatch/logs",
};

const state = {
  robots: [],
  tasks: [],
  nodes: [],
  edges: [],
  logs: [],
  summary: {
    pending_tasks: 0,
    idle_robots: 0,
    busy_robots: 0,
  },
  taskStatus: "all",
  taskOffset: 0,
  taskLimit: 20,
  hasNextTaskPage: false,
};

let activeLoadController = null;
let loadSequence = 0;

const labels = {
  status: {
    idle: "空闲",
    busy: "执行中",
    charging: "充电中",
    offline: "离线",
    error: "异常",
    pending: "待调度",
    assigned: "已分配",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消",
  },
  type: {
    delivery: "配送任务",
    inspection: "巡检任务",
  },
  capability: {
    delivery: "配送",
    inspection: "巡检",
  },
};

function qs(selector) {
  return document.querySelector(selector);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[character]);
}

function showToast(message, tone = "default") {
  const toast = qs("#toast");
  toast.textContent = message;
  toast.dataset.tone = tone;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}

async function request(url, options = {}) {
  let res;
  try {
    res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      ...options,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("无法连接服务，请检查网络后重试");
  }
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = Array.isArray(error.detail)
      ? error.detail.map((item) => item.msg).join("；")
      : error.detail;
    if (res.status === 401 && url !== api.login) showLogin();
    throw new Error(detail || "请求失败");
  }
  return res.json();
}

function showLogin() {
  qs("#loginOverlay").hidden = false;
  qs("#logoutBtn").hidden = true;
}

function hideLogin(username) {
  qs("#loginOverlay").hidden = true;
  qs("#logoutBtn").hidden = false;
  qs("#logoutBtn").title = `当前用户：${username}`;
  qs("#loginError").textContent = "";
}

function statusBadge(status) {
  const safeStatus = escapeHtml(status);
  return `<span class="status ${safeStatus}">${escapeHtml(labels.status[status] || status)}</span>`;
}

function taskType(type) {
  return labels.type[type] || type;
}

function capabilityText(value) {
  return value.split(",").map((item) => labels.capability[item] || item).join("、");
}

function formatTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function setButtonBusy(button, busy, busyText) {
  if (!button.dataset.label) button.dataset.label = button.textContent;
  button.disabled = busy;
  button.textContent = busy ? busyText : button.dataset.label;
}

function renderMetrics() {
  qs("#pendingCount").textContent = state.summary.pending_tasks;
  qs("#idleCount").textContent = state.summary.idle_robots;
  qs("#busyCount").textContent = state.summary.busy_robots;
  const last = state.logs[0];
  qs("#lastSuggestion").textContent = last ? (last.selected_robot_id || "无可用机器人") : "待运行";
}

function renderRobots() {
  qs("#robotList").innerHTML = state.robots.map((robot) => `
    <article class="robot">
      <div class="robot-top">
        <strong>${escapeHtml(robot.id)} · ${escapeHtml(robot.name)}</strong>
        ${statusBadge(robot.status)}
      </div>
      <div class="robot-meta">
        <span>电量 ${robot.battery}%</span>
        <span>位置 (${robot.x}, ${robot.y})</span>
        <span>能力 ${escapeHtml(capabilityText(robot.capability))}</span>
        <span>任务 ${escapeHtml(robot.current_task_id || "-")}</span>
      </div>
    </article>
  `).join("") || `<div class="empty-state">暂无机器人数据</div>`;
}

function renderTasks() {
  qs("#taskRows").innerHTML = state.tasks.map((task) => `
    <tr>
      <td class="mono">${escapeHtml(task.id)}</td>
      <td>${escapeHtml(taskType(task.type))}</td>
      <td>${task.priority}</td>
      <td>${escapeHtml(task.start_node)} → ${escapeHtml(task.end_node)}</td>
      <td>${escapeHtml(task.assigned_robot_id || "-")}</td>
      <td>${statusBadge(task.status)}</td>
      <td>${task.estimated_duration ? `${task.estimated_duration}s` : "-"}</td>
      <td class="row-actions">
        ${task.status === "assigned" ? `<button data-action="complete" data-task="${escapeHtml(task.id)}">完成</button>` : ""}
        ${["pending", "assigned"].includes(task.status) ? `<button class="danger-button" data-action="cancel" data-task="${escapeHtml(task.id)}">取消</button>` : ""}
      </td>
    </tr>
  `).join("") || `<tr><td colspan="8"><div class="empty-state">当前筛选条件下没有任务</div></td></tr>`;
  const page = Math.floor(state.taskOffset / state.taskLimit) + 1;
  qs("#taskPageLabel").textContent = `第 ${page} 页`;
  qs("#prevTaskPage").disabled = state.taskOffset === 0;
  qs("#nextTaskPage").disabled = !state.hasNextTaskPage;
}

function renderNodeOptions() {
  const startValue = qs("#startNode").value;
  const endValue = qs("#endNode").value;
  const options = state.nodes.map((node) => `<option value="${escapeHtml(node.id)}">${escapeHtml(node.id)} · ${escapeHtml(node.name)}</option>`).join("");
  qs("#startNode").innerHTML = options;
  qs("#endNode").innerHTML = options;
  if (state.nodes.some((node) => node.id === startValue)) qs("#startNode").value = startValue;
  if (state.nodes.some((node) => node.id === endValue)) {
    qs("#endNode").value = endValue;
  } else if (state.nodes.length > 1) {
    qs("#endNode").selectedIndex = 1;
  }
}

function renderMap() {
  const nodesById = Object.fromEntries(state.nodes.map((node) => [node.id, node]));
  const edges = state.edges.map((edge) => {
    const from = nodesById[edge.from_node];
    const to = nodesById[edge.to_node];
    if (!from || !to) return "";
    return `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" />`;
  }).join("");
  const nodes = state.nodes.map((node) => `
    <div class="node ${node.type}" style="left:${node.x}%; top:${node.y}%">
      ${escapeHtml(node.id)}
    </div>
  `).join("");
  qs("#mapCanvas").innerHTML = `
    <svg class="map-edges" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${edges}</svg>
    ${nodes}
  `;
}

function renderLogs() {
  qs("#logList").innerHTML = state.logs.map((log) => `
    <article class="log-item">
      <div><strong>${escapeHtml(log.task_id)} → ${escapeHtml(log.selected_robot_id || "未分配")}</strong><time>${formatTime(log.created_at)}</time></div>
      <span>${escapeHtml(log.decision_reason)}</span>
    </article>
  `).join("") || `<article class="log-item"><span>暂无调度日志</span></article>`;
}

function render() {
  renderMetrics();
  renderRobots();
  renderTasks();
  renderMap();
  renderLogs();
}

async function loadAll() {
  if (activeLoadController) activeLoadController.abort();
  const controller = new AbortController();
  activeLoadController = controller;
  const sequence = ++loadSequence;
  const statusQuery = state.taskStatus === "all" ? "" : `&status=${encodeURIComponent(state.taskStatus)}`;
  const taskUrl = `${api.tasks}?offset=${state.taskOffset}&limit=${state.taskLimit + 1}${statusQuery}`;
  const requestOptions = { signal: controller.signal };
  try {
    const [robots, tasks, nodes, edges, logs, summary] = await Promise.all([
      request(api.robots, requestOptions),
      request(taskUrl, requestOptions),
      request(api.nodes, requestOptions),
      request(api.edges, requestOptions),
      request(`${api.logs}?limit=50`, requestOptions),
      request(api.summary, requestOptions),
    ]);
    if (sequence !== loadSequence) return;
    state.robots = robots;
    state.hasNextTaskPage = tasks.length > state.taskLimit;
    state.tasks = tasks.slice(0, state.taskLimit);
    state.nodes = nodes;
    state.edges = edges;
    state.logs = logs;
    state.summary = summary;
    renderNodeOptions();
    render();
    qs("#lastUpdated").textContent = `更新于 ${new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}`;
  } finally {
    if (activeLoadController === controller) activeLoadController = null;
  }
}

qs("#taskForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  data.priority = Number(data.priority);
  try {
    setButtonBusy(button, true, "创建中...");
    await request(api.tasks, {
      method: "POST",
      body: JSON.stringify(data),
    });
    showToast("任务已创建", "success");
    await loadAll();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
});

qs("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button[type='submit']");
  const credentials = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    setButtonBusy(button, true, "登录中...");
    const session = await request(api.login, {
      method: "POST",
      body: JSON.stringify(credentials),
    });
    event.currentTarget.reset();
    hideLogin(session.username);
    await loadAll();
  } catch (error) {
    qs("#loginError").textContent = error.message;
  } finally {
    setButtonBusy(button, false);
  }
});

qs("#logoutBtn").addEventListener("click", async () => {
  try {
    await request(api.logout, { method: "POST" });
  } finally {
    showLogin();
  }
});

qs("#runDispatchBtn").addEventListener("click", async () => {
  const button = qs("#runDispatchBtn");
  try {
    setButtonBusy(button, true, "调度中...");
    const result = await request(api.dispatch, { method: "POST" });
    showToast(result.reason, result.assigned ? "success" : "default");
    await loadAll();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
});

qs("#refreshBtn").addEventListener("click", async () => {
  const button = qs("#refreshBtn");
  try {
    setButtonBusy(button, true, "…");
    await loadAll();
    showToast("数据已刷新", "success");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
});

qs("#taskStatusFilter").addEventListener("change", async (event) => {
  state.taskStatus = event.target.value;
  state.taskOffset = 0;
  try {
    await loadAll();
  } catch (error) {
    if (error.name !== "AbortError") showToast(error.message, "error");
  }
});

qs("#prevTaskPage").addEventListener("click", async () => {
  state.taskOffset = Math.max(0, state.taskOffset - state.taskLimit);
  await loadAll().catch((error) => {
    if (error.name !== "AbortError") showToast(error.message, "error");
  });
});

qs("#nextTaskPage").addEventListener("click", async () => {
  if (!state.hasNextTaskPage) return;
  state.taskOffset += state.taskLimit;
  await loadAll().catch((error) => {
    if (error.name !== "AbortError") showToast(error.message, "error");
  });
});

qs("#taskRows").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  try {
    setButtonBusy(button, true, action === "complete" ? "处理中..." : "取消中...");
    await request(`/api/tasks/${encodeURIComponent(button.dataset.task)}/${action}`, { method: "POST" });
    showToast(action === "complete" ? "任务已完成，机器人已释放" : "任务已取消", "success");
    await loadAll();
  } catch (error) {
    showToast(error.message, "error");
    setButtonBusy(button, false);
  }
});

async function bootstrap() {
  const session = await request(api.session);
  if (session.authenticated) {
    hideLogin(session.username);
    await loadAll();
  } else {
    showLogin();
  }
}

bootstrap().catch((error) => {
  showLogin();
  showToast(error.message, "error");
});
setInterval(() => {
  if (!document.hidden && !activeLoadController) loadAll().catch(() => {});
}, 15000);
