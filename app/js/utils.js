function isVideo(file) {
    return /\.(mp4|avi|mkv|mov)$/i.test(file);
}

function isImage(file) {
    return /\.(jpg|jpeg|png|bmp)$/i.test(file);
}


async function get_models_for_file(filename){
    return  fetch(`/results/${filename}/list`)
            .then(r => r.json())
            .then(models => {
                return models;
            });
}