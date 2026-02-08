const modal = document.getElementById("modal");
const modalClose = document.getElementById("modalClose");
const modalTitle = document.getElementById("modalTitle");
const modalClassFilters = document.getElementById('classFilters')

const modelSelectPopup = document.getElementById("modelSelectPopup");

const popupCanvas = document.getElementById("popupCanvas");
const popupCtx = popupCanvas.getContext("2d");

let popupImage = new Image();
let popupDetections = [];


async function openImageInCanvas(imageName) {
    modal.style.display = "block";
    modalTitle.textContent = imageName;

    const models = await get_models_for_file(imageName);
    console.log(models);
    if(models.length == 0){
        modalTitle.textContent+=' / Для данного изображения не было выполнено ни одной детекции'
    }

    modelSelectPopup.innerHTML = "";

    models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        modelSelectPopup.appendChild(opt);
    });

    if (models.length > 0) {
        loadPopupResult(imageName, models[0]);
    }else{
        console.log('==0', imageName);
        loadPopupResult(imageName);
    }

    modelSelectPopup.onchange = () => {
        loadPopupResult(imageName, modelSelectPopup.value);
    };
}


function loadPopupResult(imageName, modelId) {
    if(modelId != undefined){
        fetch(`/results/${imageName}/${modelId}`)
            .then(r => r.json())
            .then(data => {
                console.log('data', data)
                popupDetections = data.detections;

                popupImage.onload = () => {
                    popupCanvas.width = popupImage.width;
                    popupCanvas.height = popupImage.height;
                    buildClassFilters(popupDetections);

                    renderPopup();

                };

                popupImage.src = `/uploads/${imageName}?t=` + Date.now();
            });
    }else{
        console.log('22', popupCanvas.width, popupCanvas.height)
        popupImage.onload = () => {
            popupCanvas.width = popupImage.width;
            popupCanvas.height = popupImage.height;
            popupCtx.clearRect(0, 0, popupCanvas.width, popupCanvas.height);
            popupCtx.drawImage(popupImage, 0, 0);
        };

        popupImage.src = `/uploads/${imageName}?t=` + Date.now();

    }

}


function renderPopup() {
  popupCtx.clearRect(0, 0, popupCanvas.width, popupCanvas.height);
  popupCtx.drawImage(popupImage, 0, 0);


  popupDetections.forEach(det => {

    const class_id = det.class_id;

    if (!visibleClasses.has(class_id)) return;

    const color = getClassColor(class_id);

    const [x1, y1, x2, y2] = det.bbox;
    const w = x2 - x1;
    const h = y2 - y1;

    popupCtx.strokeStyle = color;
    popupCtx.lineWidth = 2;
    popupCtx.strokeRect(x1, y1, w, h);

    const label = `${det.class_name} ${det.confidence.toFixed(2)}`;
    popupCtx.font = "14px Arial";

    popupCtx.fillStyle = color;
    popupCtx.fillRect(x1, y1 - 18, popupCtx.measureText(label).width + 6, 18);

    popupCtx.fillStyle = "white";
    popupCtx.fillText(label, x1 + 3, y1 - 5);
  });
}




function buildClassFilters(detections) {
    const container = modalClassFilters;
    container.innerHTML = "<b>Классы:</b><br>";

    const classes = {};
    detections.forEach(d => {
        classes[d.class_id] = d.class_name;
        visibleClasses.add(d.class_id);
    });

    console.log('classes', classes)
    console.log('visibleClasses', visibleClasses)

    Object.entries(classes).forEach(([id, name]) => {
        const color = getClassColor(id);

        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = true;
        cb.onchange = () => {
            cb.checked ? visibleClasses.add(+id) : visibleClasses.delete(+id);
            console.log('visibleClasses', visibleClasses)

            renderPopup();
        };

        const label = document.createElement("label");
        label.style.color = color;
        label.append(cb, " ", name);

        container.appendChild(label);
        container.appendChild(document.createElement("br"));
    });
}


function modal_close() {
    modal.style.display = "none";
    classFilters.innerHTML = "";
}

modalClose.onclick = () => modal_close();

window.onclick = e => {
  if (e.target === modal) modal_close();
};


