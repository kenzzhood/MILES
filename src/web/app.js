const chatForm = document.getElementById("chat-form");
const promptInput = document.getElementById("prompt-input");
const messagesEl = document.getElementById("messages");
const planListEl = document.getElementById("plan-list");
const tasksListEl = document.getElementById("tasks-list");

const messageTemplate = document.getElementById("message-template");
const taskTemplate = document.getElementById("task-template");

const activeStreams = new Map();

function addMessage(sender, text, isError = false) {
  const node = messageTemplate.content.firstElementChild.cloneNode(true);
  node.querySelector(".sender").textContent = sender;
  node.querySelector(".timestamp").textContent = new Date().toLocaleTimeString();
  const body = node.querySelector(".body");
  // Render markdown if available, otherwise text
  if (window.marked) {
    body.innerHTML = marked.parse(text);
  } else {
    body.textContent = text;
  }

  // Check for 3D model link and render viewer
  if (text.includes("/models/") && text.includes(".glb")) {
    const match = text.match(/\/models\/[\w\-.%]+\.glb/);
    if (match) {
      const modelUrl = match[0];
      const viewer = document.createElement("model-viewer");
      viewer.src = modelUrl;
      viewer.setAttribute("camera-controls", "");
      viewer.setAttribute("auto-rotate", "");
      viewer.setAttribute("ar", "");
      viewer.setAttribute("shadow-intensity", "1");
      viewer.setAttribute("environment-image", "neutral");
      viewer.setAttribute("exposure", "1");
      viewer.style.width = "100%";
      viewer.style.height = "400px";
      viewer.style.backgroundColor = "#f0f0f0";
      viewer.style.borderRadius = "8px";
      viewer.style.marginTop = "10px";
      body.appendChild(viewer);
    }
  }

  if (isError) {
    body.style.color = "#f87171";
  }
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderPlan(tasks) {
  planListEl.innerHTML = "";
  tasks.forEach((task, index) => {
    const li = document.createElement("li");
    li.innerHTML = `<strong>Step ${index + 1} · ${task.worker_name}</strong><br/><span>${task.prompt}</span>`;
    planListEl.appendChild(li);
  });
}

function ensureTaskEntry(taskId, workerName, prompt) {
  let entry = tasksListEl.querySelector(`[data-task-id="${taskId}"]`);
  if (entry) {
    return entry;
  }

  entry = taskTemplate.content.firstElementChild.cloneNode(true);
  entry.dataset.taskId = taskId;
  entry.querySelector(".task-worker").textContent = workerName;
  entry.querySelector(".task-prompt").textContent = prompt;
  tasksListEl.appendChild(entry);
  return entry;
}

function updateTaskStatus(taskId, status, resultText) {
  const entry = tasksListEl.querySelector(`[data-task-id="${taskId}"]`);
  if (!entry) {
    return;
  }
  const statusEl = entry.querySelector(".task-status");
  statusEl.dataset.status = status;
  statusEl.textContent = status;

  if (status === "SUCCESS" && resultText) {
    const result = document.createElement("div");
    result.className = "task-result";

    // Debugging: Log the result text
    console.log("Task Success Result:", resultText);

    // Check if result contains a model link (simple heuristic)
    if (resultText.includes("/models/") && resultText.includes(".glb")) {
      console.log("Result contains GLB link, attempting extraction...");
      // Extract URL - more permissive regex to catch /models/filename.glb
      const match = resultText.match(/\/models\/[\w\-.%]+\.glb/);
      if (match) {
        console.log("Found Model URL:", match[0]);
        const modelUrl = match[0];
        const viewer = document.createElement("model-viewer");
        viewer.src = modelUrl;
        viewer.setAttribute("camera-controls", "");
        viewer.setAttribute("auto-rotate", "");
        viewer.setAttribute("ar", "");
        viewer.setAttribute("shadow-intensity", "1");
        viewer.setAttribute("environment-image", "neutral");
        viewer.setAttribute("exposure", "1");
        viewer.style.width = "100%";
        viewer.style.height = "400px";
        viewer.style.backgroundColor = "#f0f0f0";
        viewer.style.borderRadius = "8px";
        viewer.style.marginTop = "10px";

        result.appendChild(viewer);
      } else {
        console.warn("Model URL regex match failed.");
      }
    }

    // Render markdown for text part
    if (window.marked) {
      const textDiv = document.createElement("div");
      textDiv.innerHTML = marked.parse(resultText);
      result.insertBefore(textDiv, result.firstChild);
    } else {
      result.textContent = resultText;
    }
    entry.appendChild(result);
  }
}

function subscribeToTask(taskId, workerName, prompt) {
  ensureTaskEntry(taskId, workerName, prompt);
  updateTaskStatus(taskId, "PENDING");

  const stream = new EventSource(`/api/v1/stream/${taskId}`);
  activeStreams.set(taskId, stream);

  stream.onmessage = (event) => {
    try {
      const payload = JSON.parse(event.data);
      updateTaskStatus(taskId, payload.status, payload.result);
      if (payload.status === "SUCCESS" || payload.status === "FAILURE") {
        stream.close();
        activeStreams.delete(taskId);
        addMessage(
          workerName,
          payload.result || `Task ${taskId} finished with status ${payload.status}`
        );
      }
    } catch (err) {
      console.error("Failed to parse task stream payload", err);
    }
  };

  stream.onerror = () => {
    stream.close();
    activeStreams.delete(taskId);
    updateTaskStatus(taskId, "FAILURE");
  };
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) {
    return;
  }

  addMessage("You", prompt);
  promptInput.value = "";

  try {
    const response = await fetch("/api/v1/interact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || "Unknown error calling API");
    }

    const data = await response.json();
    const tasks = data.plan?.tasks || [];
    renderPlan(tasks);

    if (data.direct_response) {
      addMessage("Orchestrator", data.direct_response);
    }

    if (tasks.length) {
      addMessage(
        "Orchestrator",
        `Plan generated with ${tasks.length} step${tasks.length > 1 ? "s" : ""}.`
      );
      tasks.forEach((task, index) => {
        const taskId = data.task_ids[index];
        subscribeToTask(taskId, task.worker_name, task.prompt);
      });
    } else if (!data.direct_response) {
      addMessage(
        "Orchestrator",
        "No specialists were dispatched for this prompt."
      );
    }
  } catch (error) {
    console.error(error);
    addMessage("System", error.message, true);
  }
});

window.addEventListener("beforeunload", () => {
  activeStreams.forEach((source) => source.close());
  activeStreams.clear();
});

