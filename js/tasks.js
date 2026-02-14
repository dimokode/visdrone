let activeTasks = {}; 
// key = `${file}__${model}`
// value = { taskId, status, progress }

// let taskEventSources = {};
// window.taskEventSources = {};

async function clear_queue() {
    fetch('/clear_queue', {
        method: "POST"
    })
    .then(r => r.json())
    .then(r => console.log(r))
}



async function set_r_to_q() {
    fetch('/set_r_to_q')
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

    initModelProgress(files, models)
    updateGlobalProgress();

    for (const file of files) {
        for (const model of models) {
            await createTask(file, model);
        }
    }
}


function addModelProgressToFile(container, models_index, file, model) {
            const row = document.createElement("div");
            row.className = "model-progress";

            const name = document.createElement("span");
            name.className = "model-name";
            name.textContent = models_index[model];
            
            
            // <button onclick="stopTask('FILE','MODEL')">Stop</button>

            const btnStoptask = document.createElement("button")
            btnStoptask.className = "progress-button"
            btnStoptask.textContent = "X"
            btnStoptask.onclick = () => stopTask(file, model)

            const bar = document.createElement("div");
            bar.className = "progress-bar";

            const fill = document.createElement("div");
            fill.className = "progress-fill";
            fill.id = `pb-${file}-${model}`;

            bar.appendChild(fill);
            row.appendChild(btnStoptask);
            row.appendChild(name);
            row.appendChild(bar);

            container.appendChild(row);
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
            addModelProgressToFile(container, models_index, file, model)
        });
    });
}

// async function createTask(file, model) {
//     console.log('createTask', file, model);
//     const res = await fetch("/enqueue_task", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ file, model })
//     });
//     data = await res.json();
//     console.log('res', data);
    
//     task_id = data['task_id'];
    
//     console.log('task_id', task_id);


//     const key = `${file}__${model}`;

//     activeTasks[key] = {
//         taskId: task_id,
//         file,
//         model,
//         progress: 0,
//         status: "queued"
//     };

//     // startTaskSSE(task_id, file, model);
// }

async function createTask(file, model) {
    const res = await fetch("/enqueue_task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file, model })
    });

    const data = await res.json();

    const key = `${file}__${model}`;

    activeTasks[key] = {
        taskId: data.task_id,
        file,
        model,
        progress: 0,
        status: "queued"
    };
}



// function startTaskSSE(taskId, file, model) {

//     const key = `${file}__${model}`;
//     console.log("Opening SSE for", key);


//     window.taskEventSources = window.taskEventSources || {};

//     if (window.taskEventSources[key]) {
//         console.log(`Task Event with key ${key} found`);
//         try{
//             window.taskEventSources[key].close();
//             delete window.taskEventSources[key];
//             console.log(`Connection with key ${key} is successfully closed`);
//         }catch(err){
//             console.error(err.message);
//         }
//     }

//     try{
//         const es = new EventSource(`/run_inference_sse?task=${taskId}`);
//         window.taskEventSources[key] = es;
//         console.log(`New connection ${key} created`);
//         console.log(es);
//     }catch(err){
//         console.error(err.message);
//     }


//     // es.onmessage = (e) => {
//     window.taskEventSources[key].onmessage = (e) => {
//         const data = JSON.parse(e.data);
//         // console.log('startTaskSSE', data);

//         if (data.type === "done") {
//             window.taskEventSources[key].close();
//             delete window.taskEventSources[key];
            
//             activeTasks[key].progress = 1.0;
//             activeTasks[key].status = "done";

//             updateFileModelProgress(file, model, 1.0);
//             updateGlobalProgress();
//             return;
//         }
        
//         // защита от откатов
//         // if (data.progress < activeTasks[key].progress) return;
        
//         activeTasks[key].progress = data.progress;
//         activeTasks[key].status = data.status;

//         updateFileModelProgress(file, model, data.progress);
//         updateGlobalProgress();
//     };
// }


// function startGlobalSSE() {
//     const es = new EventSource("/tasks_stream");

//     es.onmessage = (e) => {
//         const data = JSON.parse(e.data);

//         const key = `${data.file}__${data.model}`;

//         if (!activeTasks[key]) {
//             activeTasks[key] = {
//                 taskId: data.id,
//                 file: data.file,
//                 model: data.model,
//                 progress: 0,
//                 status: data.status
//             };
//         }

//         // защита от откатов
//         if (data.progress <= activeTasks[key].progress && data.status !== "done") return;


//         activeTasks[key].progress = data.progress;
//         activeTasks[key].status = data.status;

//         updateFileModelProgress(
//             data.file,
//             data.model,
//             data.progress
//         );

//         updateGlobalProgress();
//     };
// }


function startGlobalSSE() {
    const es = new EventSource("/tasks_stream");

    es.onmessage = (e) => {
        const data = JSON.parse(e.data);

        const key = `${data.file}__${data.model}`;

        // если задачи ещё нет в памяти — создаём
        if (!activeTasks[key]) {
            activeTasks[key] = {
                taskId: data.id,
                file: data.file,
                model: data.model,
                progress: 0,
                status: data.status
            };
        }

        const current = activeTasks[key].progress || 0;
        const incoming = data.progress || 0;

        if (data.status === "done") {
            activeTasks[key].progress = 1;
            activeTasks[key].status = "done";

            updateFileModelProgress(data.file, data.model, 1);
            updateGlobalProgress();
            return;
        }

        // допускаем маленькую погрешность float
        if (incoming + 0.0001 < current) {
            return;
        }

        activeTasks[key].progress = incoming;
        activeTasks[key].status = data.status;

        updateFileModelProgress(data.file, data.model, incoming);
        updateGlobalProgress();
    };

    es.onerror = () => {
        console.log("SSE disconnected, reconnecting...");
    };
}



function updateFileModelProgress(file, model, progress) {
    const bar = document.getElementById(`pb-${file}-${model}`);
    if (!bar) {
        console.log("BAR NOT FOUND", file, model);
        return;
    }

    console.log('updateFileModelProgress', file, model, progress);

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

    console.log('updateGlobalProgress', `sum=${sum}, total=${total}, global=${global}`)

    const bar = document.getElementById("globalProgress");
    bar.style.width = pct + "%";
    bar.textContent = pct + "%";
}


async function stopTask(file, model) {
    const key = `${file}__${model}`;
    const task = activeTasks[key];
    if (!task) return;

    await fetch(`/stop_task/${task.taskId}`, {
        method: "POST"
    });

    task.status = "stopped";

    if (taskEventSources[key]) {
        taskEventSources[key].close();
    }
}


async function restoreTasks() {
    
    // console.log('taskEventSources', window.taskEventSources);

    const models_index = await fetch('/get_models_index', {
                method: "POST",
            })
            .then(r => r.json())
            .then(data => {
                return data
            });

    const res = await fetch("/tasks");
    const tasks = await res.json();
    console.log('restoreTasks', 'tasks', tasks);


    for (const task of tasks) {
        const { id, file, model, progress, status } = task;
        console.log('restore' , id, file, model, progress, status);

        const key = `${file}__${model}`;

        activeTasks[key] = {
            taskId: id,
            file,
            model,
            progress,
            status
        };

        const container = document.getElementById(`models-${file}`);

        addModelProgressToFile(container, models_index, file, model)

        updateFileModelProgress(file, model, progress);

        // if (status === "running" || status === "queued") {
        //     startTaskSSE(id, file, model);
        // }
    }

    updateGlobalProgress();
}
