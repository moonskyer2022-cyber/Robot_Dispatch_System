const api = {
  robots: "/api/robots",
  tasks: "/api/tasks",
  nodes: "/api/map/nodes",
  dispatch: "/api/dispatch/run",
  logs: "/api/dispatch/logs",
};

const state = {
  robots: [],
  tasks: [],
  nodes: [],
  logs: [],
};

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

function showToast(message) {
  const toast = qs("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}

async function request(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "请求失败");
  }
  return res.json();
}

function statusBadge(status) {
  return `<span class="status ${status}">${labels.status[status] || status}</span>`;
}

function taskType(type) {
  return labels.type[type] || type;
}

function capabilityText(value) {
  return value.split(",").map((item) => labels.capability[item] || item).join("、");
}

function renderMetrics() {
  qs("#pendingCount").textContent = state.tasks.filter((task) => task.status === "pending").length;
  qs("#idleCount").textContent = state.robots.filter((robot) => robot.status === "idle").length;
  qs("#busyCount").textContent = state.robots.filter((robot) => robot.status === "busy").length;
  const last = state.logs[0];
  qs("#lastSuggestion").textContent = last ? (last.selected_robot_id || "无可用机器人") : "待运行";
}

function renderRobots() {
  qs("#robotList").innerHTML = state.robots.map((robot) => `
    <article class="robot">
      <div class="robot-top">
        <strong>${robot.id} · ${robot.name}</strong>
        ${statusBadge(robot.status)}
      </div>
      <div class="robot-meta">
        <span>电量 ${robot.battery}%</span>
        <span>位置 (${robot.x}, ${robot.y})</span>
        <span>能力 ${capabilityText(robot.capability)}</span>
        <span>任务 ${robot.current_task_id || "-"}</span>
      </div>
    </article>
  `).join("");
}

function renderTasks() {
  qs("#taskRows").innerHTML = state.tasks.map((task) => `
    <tr>
      <td>${task.id}</td>
      <td>${taskType(task.type)}</td>
      <td>${task.priority}</td>
      <td>${task.start_node} → ${task.end_node}</td>
      <td>${task.assigned_robot_id || "-"}</td>
      <td>${statusBadge(task.status)}</td>
      <td>${task.estimated_duration ? `${task.estimated_duration}s` : "-"}</td>
      <td>
        ${task.status === "assigned" ? `<button data-complete="${task.id}">完成</button>` : ""}
      </td>
    </tr>
  `).join("");

  document.querySelectorAll("[data-complete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await request(`/api/tasks/${btn.dataset.complete}/complete`, { method: "POST" });
      showToast("任务已完成，机器人已释放");
      await loadAll();
    });
  });
}

function renderNodeOptions() {
  const options = state.nodes.map((node) => `<option value="${node.id}">${node.id} · ${node.name}</option>`).join("");
  qs("#startNode").innerHTML = options;
  qs("#endNode").innerHTML = options;
  if (state.nodes.length > 1) {
    qs("#endNode").selectedIndex = 1;
  }
}

function renderMap() {
  qs("#mapCanvas").innerHTML = state.nodes.map((node) => `
    <div class="node ${node.type}" style="left:${node.x}%; top:${node.y}%">
      ${node.id}
    </div>
  `).join("");
}

function renderLogs() {
  qs("#logList").innerHTML = state.logs.map((log) => `
    <article class="log-item">
      <strong>${log.task_id} → ${log.selected_robot_id || "未分配"}</strong>
      <span>${log.decision_reason}</span>
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
  const [robots, tasks, nodes, logs] = await Promise.all([
    request(api.robots),
    request(api.tasks),
    request(api.nodes),
    request(api.logs),
  ]);
  state.robots = robots;
  state.tasks = tasks;
  state.nodes = nodes;
  state.logs = logs;
  renderNodeOptions();
  render();
}

qs("#taskForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  data.priority = Number(data.priority);
  await request(api.tasks, {
    method: "POST",
    body: JSON.stringify(data),
  });
  showToast("任务已创建");
  await loadAll();
});

qs("#runDispatchBtn").addEventListener("click", async () => {
  const result = await request(api.dispatch, { method: "POST" });
  showToast(result.reason);
  await loadAll();
});

loadAll().catch((error) => showToast(error.message));
