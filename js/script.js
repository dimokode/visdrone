const CLASS_COLORS = {};
const PALETTE = [
  "#e6194b", "#3cb44b", "#ffe119", "#4363d8",
  "#f58231", "#911eb4", "#46f0f0", "#f032e6"
];

let visibleClasses = new Set();

function getClassColor(classId) {
    if (!CLASS_COLORS[classId]) {
        CLASS_COLORS[classId] = PALETTE[
            Object.keys(CLASS_COLORS).length % PALETTE.length
        ];
    }
    return CLASS_COLORS[classId];
}


let selectedDetection = null;

function hitTest(x, y) {
    for (const det of detections) {
        if (!visibleClasses.has(det.class_id)) continue;
        const [x1, y1, x2, y2] = det.bbox;
        if (x >= x1 && x <= x2 && y >= y1 && y <= y2) {
            return det;
        }
    }
    return null;
}


const fileList = document.getElementById("fileList");

const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const resultDiv = document.getElementById("result");
const modelSelect = document.getElementById("modelSelect");

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const files = e.dataTransfer.files
    if (files.length > 0){
        uploadFiles(files);
    } 
});

fileInput.addEventListener("change", () => {
    console.log(fileInput)
    console.log(fileInput.files)
    console.log('change');
    uploadFiles(fileInput.files);
});


function uploadFiles(files) {
    const formData = new FormData();
    for (const f of files) formData.append("images", f);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload");

    xhr.upload.onprogress = e => {
        uploadProgress.value = (e.loaded / e.total) * 100;
    };

    xhr.onload = () => {
        const data = JSON.parse(xhr.responseText);
        showFileList(data.files);
        for(f of files){
            check_checkbox_by_filename(f.name);
        }
    };

    xhr.send(formData);

}


function delete_files_with_results() {
    const files = Array.from(selectedFiles);
    console.log(files);

    fetch("/delete_files_with_results", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ files })
    })
    .then(res => res.json())
    .then(res => {
        if (res.success){
            for(let filename of files){
                const file_element = document.getElementById("file-" + filename)
                if(file_element){
                    file_element.remove();
                }
            }
        }else{
            console.log("Error", res.err_msg);
        }
    });
}

// FileList +++++++++++++++++++++++++++++++++++++++++++++++++++++

const selectedFiles = new Set();

function showFiles(){
    fetch("/get_files", {
        method: "POST",
    })
    .then(res => res.json())
    .then(response => {
        console.log(response);
        showFileList(response.files);
    })
}

function openPopup(file) {
    document.getElementById("modalTitle").textContent = file;
    document.getElementById("modal").style.display = "block";

    if (isVideo(file)) {
        openVideoInCanvas(file);
    } else {
        openImageInCanvas(file);
    }
}


function showFileList(files) {

    files.forEach(file => {
        // console.log('file', file)
        const row = document.createElement("div");
        row.className = "file-row";
        row.id = `file-${file}`;

        // header
        const header = document.createElement("div");
        header.className = "file-header";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "file-checkbox";
        checkbox.checked = selectedFiles.has(file);
        checkbox.onchange = () => {
            checkbox.checked
                ? selectedFiles.add(file)
                : selectedFiles.delete(file);
        };

        const name = document.createElement("span");
        name.className = "file-name";
        name.textContent = file;
        name.onclick = () => {
            openPopup(file);
        }

        header.appendChild(checkbox);
        header.appendChild(name);
        row.appendChild(header);

        // models progress container
        const modelsDiv = document.createElement("div");
        modelsDiv.className = "models-progress";
        modelsDiv.id = `models-${file}`;

        row.appendChild(modelsDiv);
        fileList.appendChild(row);
    });
}

function check_checkbox_by_filename(filename){
    const targetDiv = document.getElementById(`file-${filename}`);
    const checkbox = targetDiv.querySelector('input.file-checkbox')
    if (checkbox){
        checkbox.click();
    }
}



document.getElementById("selectAllFiles").onchange = e => {
    const checked = e.target.checked;
    document.querySelectorAll(".file-checkbox").forEach(cb => {
        cb.checked = checked;
        cb.onchange();
    });
};

// Models +++++++++++++++++++++++++++++++++++++++
const selectedModels = new Set();

function showModels(){
    fetch("/get_models", {
        method: "POST",
    })
    .then(res => res.json())
    .then(response => {
        console.log(response);
        showModelList(response.models);
    })
}

function showModelList(models) {
    const container = document.getElementById("modelList");
    container.innerHTML = "";

    models.forEach(model => {
        const row = document.createElement("div");
        row.className = "model-row";

        // checkbox
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "model-checkbox";
        checkbox.value = model['id'];

        checkbox.onchange = () => {
            if (checkbox.checked) {
                selectedModels.add(model['id']);
            } else {
                selectedModels.delete(model['id']);
            }
        };

        // filename (кликабельный)
        const name = document.createElement("span");
        name.className = "model-name";
        name.textContent = model['name'];


        row.appendChild(checkbox);
        row.appendChild(name);
        container.appendChild(row);

        checkbox.checked = selectedModels.has(model['id']);

    });
}

document.getElementById("selectAllModels").onchange = e => {
    const checked = e.target.checked;
    document.querySelectorAll(".model-checkbox").forEach(cb => {
        cb.checked = checked;
        cb.onchange();
    });
};


function updateFileModelProgress(file, model, progress) {
    const bar = document.getElementById(`pb-${file}-${model}`);
    if (!bar) return;

    const percent = Math.round(progress * 100);

    bar.style.width = percent + "%";
    bar.textContent = percent + "%";

    if (progress >= 1) {
        bar.classList.add("done");
        bar.textContent = "done";
    }
}
