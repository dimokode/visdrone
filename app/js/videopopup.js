let videoElement = null;
let videoFPS = 30;
let videoDetections = null;
let videoRAF = null;


function buildClassFiltersForVideo(frames) {
    const container = modalClassFilters;
    container.innerHTML = "<b>Классы:</b><br>";

    const classes = {};

    for(frame_idx in frames){
        let frame = frames[frame_idx];

        frame.forEach(d => {
            classes[d.class_id] = d.class_name;
            visibleClasses.add(d.class_id);
        });
    }

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

async function openVideoInCanvas(file, modelId) {
    // очищаем старое
    modelSelectPopup.innerHTML = "";
    modalClassFilters.innerHTML = "";

    const models_index = await fetch('/get_models_index', {
                        method: "POST",
                    })
                    .then(r => r.json())
                    .then(data => {
                        return data
                    });
    
    stopVideo();

    videoElement = document.createElement("video");
    videoElement.src = `/uploads/${file}`;
    videoElement.muted = true;
    videoElement.playsInline = true;

    videoElement.onloadedmetadata = async () => {
        popupCanvas.width = videoElement.videoWidth;
        popupCanvas.height = videoElement.videoHeight;

        // загрузка детекций (активная модель)
        const models = await get_models_for_file(file);
        if (models.length == 0){
            modalTitle.textContent+= " / Для данного видео не выполнено ни одной детекции";
            videoDetections = undefined;
            videoElement.play();
            renderVideoFrame();

        }else{

            models.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m;
                opt.textContent = models_index[m];
                if(m==modelId){
                    opt.selected = true;
                }
                modelSelectPopup.appendChild(opt);
            });

            modelSelectPopup.onchange = () => {
                openVideoInCanvas(file, modelSelectPopup.value);
            };
            if (modelId == undefined){
                modelId = models[0];
            }
            const res = await fetch(`/results/${file}/${modelId}`);
            const data = await res.json();


            videoDetections = data.frames;
            videoFPS = data.fps || 25;

            buildClassFiltersForVideo(videoDetections);

            videoElement.play();
            renderVideoFrame();
        }

    };
}


function renderVideoFrame() {
    if (!videoElement) return;

    popupCtx.clearRect(0, 0, popupCanvas.width, popupCanvas.height);

    // рисуем кадр видео
    popupCtx.drawImage(videoElement, 0, 0);

    // текущий frame index
    const frameIdx = Math.floor(videoElement.currentTime * videoFPS);

    // bbox
    drawBBoxes(videoDetections?.[frameIdx] || []);

    videoRAF = requestAnimationFrame(renderVideoFrame);
}


function drawBBoxes(detections) {
    console.log('detections', detections);
    detections.forEach(det => {
        if (!visibleClasses.has(det.class_id)) return;
        
        const [x1, y1, x2, y2] = det.bbox;
        popupCtx.font = "14px Arial";

        const label = `${det.class_name} ${det.confidence.toFixed(2)}`;
        const color = getClassColor(det.class_id);
        popupCtx.fillStyle = color;
        popupCtx.fillRect(x1, y1 - 18, popupCtx.measureText(label).width + 6, 18);

        popupCtx.fillStyle = "white";
        popupCtx.fillText(label, x1 + 3, y1 - 5);

        popupCtx.strokeStyle = color;
        // popupCtx.strokeStyle = 'red';
        popupCtx.lineWidth = 2;

        if (x2 > 1 || y2 > 1) {
            // ничего не делаем
        } else {
            x1 *= popupCanvas.width;
            y1 *= popupCanvas.height;
            x2 *= popupCanvas.width;
            y2 *= popupCanvas.height;
        }

        popupCtx.strokeRect(
            x1,
            y1,
            (x2 - x1),
            (y2 - y1)
        );
    });
}

function stopVideo() {
    if (videoRAF) {
        cancelAnimationFrame(videoRAF);
        videoRAF = null;
    }

    if (videoElement) {
        videoElement.pause();
        videoElement.src = "";
        videoElement = null;
    }

    popupCtx.clearRect(0, 0, popupCanvas.width, popupCanvas.height);
}


document.getElementById("modalClose").onclick = () => {
    stopVideo();
    document.getElementById("modal").style.display = "none";
};
