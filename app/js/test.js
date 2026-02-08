function test(filename = '0000271_00601_d_0000377.jpg'){
    // updateGlobalProgress(0.1);
    // 0000271_00601_d_0000377.jpg
    console.log(fileList);
    const targetDiv = document.getElementById(`file-${filename}`);
    const checkbox = targetDiv.querySelector('input.file-checkbox')
    checkbox.click();
    // const checkbox = document.querySelector('div.#0000271_00601_d_0000377.jpg > input.file-checkbox');
    // if (checkbox) {
    //     checkbox.click();
    //     console.log('Checkbox кликнут');
    // }
}