let activeTasks = {}; 
// key = `${file}__${model}`
// value = { taskId, status, progress }

let taskEventSources = {};

async function clear_queue() {
    fetch('/clear_queue', {
        method: "POST"
    })
    .then(r => r.json())
    .then(r => console.log(r))
}

async function startProcessing() {
    console.log('startProcessing');
    const files = Array.from(selectedFiles);
    const models = Array.from(selectedModels);

    if (!files.length || !models.length) {
        alert("Выбери файлы и модели");
        return;
    }

    for (const file of files) {
        for (const model of models) {
            await createTask(file, model);
        }
    }
    initModelProgress(files, models)
    updateGlobalProgress();
}


async function initModelProgress(files, models) {
    const models_index = await fetch('/get_models_index', {
                    method: "POST",
                })
                .then(r => r.json())
                .then(data => {
                    return data
                });

    files.forEach(file => {
        const container = document.getElementById(`models-${file}`);
        container.innerHTML = "";

        models.forEach(model => {
            const row = document.createElement("div");
            row.className = "model-progress";

            const name = document.createElement("span");
            name.className = "model-name";
            name.textContent = models_index[model];

            const bar = document.createElement("div");
            bar.className = "progress-bar";

            const fill = document.createElement("div");
            fill.className = "progress-fill";
            fill.id = `pb-${file}-${model}`;

            bar.appendChild(fill);
            row.appendChild(name);
            row.appendChild(bar);

            container.appendChild(row);
        });
    });
}

async function createTask(file, model) {
    console.log(file, model);
    const res = await fetch("/enqueue_task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file, model })
    });
    data = await res.json();
    console.log('res', data);
    
    task_id = data['task_id'];
    
    console.log('task_id', task_id);


    const key = `${file}__${model}`;

    activeTasks[key] = {
        taskId: task_id,
        file,
        model,
        progress: 0,
        status: "queued"
    };

    startTaskSSE(task_id, file, model);
}


function startTaskSSE(taskId, file, model) {
    const es = new EventSource(`/run_inference_sse?task=${taskId}`);

    const key = `${file}__${model}`;
    taskEventSources[key] = es;

    es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        console.log(data);

        if (data.type === "done") {
            es.close();
            return;
        }

        activeTasks[key].progress = data.progress;
        activeTasks[key].status = data.status;

        updateFileModelProgress(file, model, data.progress);
        updateGlobalProgress();
    };
}


function updateFileModelProgress(file, model, progress) {
    const bar = document.getElementById(`pb-${file}-${model}`);
    if (!bar) return;

    const pct = Math.round(progress * 100);

    bar.style.width = pct + "%";
    bar.textContent = pct + "%";

    if (progress >= 1) {
        bar.classList.add("done");
        bar.textContent = "done";
    }
}


function updateGlobalProgress() {
    const total = Object.keys(activeTasks).length;
    if (!total) return;

    let sum = 0;

    for (const key in activeTasks) {
        sum += activeTasks[key].progress;
    }

    const global = sum / total;
    const pct = Math.round(global * 100);

    const bar = document.getElementById("globalProgress");
    bar.style.width = pct + "%";
    bar.textContent = pct + "%";
}
