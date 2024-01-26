/*
 * Copyright 2024 Victor Semionov
 */


const initialImgSrc = document.querySelector('.ps-upload + label > img')?.src;
document.querySelectorAll('.ps-upload').forEach(input => {
    input.onchange = evt => {
        const label = input.labels[0];
        const img = label.querySelector('img');
        const span = label.querySelector('span');
        const [file] = input.files;
        if (file) {
            span.hidden = true;
            img.src = URL.createObjectURL(file);
        } else {
            span.hidden = false;
            img.src = initialImgSrc;
        }
    };
});


const processingElement = document.getElementById('processing');
const processingStatusElement = document.getElementById('processing-status');
const resultElement = document.getElementById('result');
const resultImageElement = document.getElementById('result-image');
const jobErrorElement = document.getElementById('job-error');
const ajaxErrorElement = document.getElementById('ajax-error');
const ajaxErrorReasonElement = document.getElementById('ajax-error-reason');

const stateDataElement = document.getElementById('state-data')
const stateData = stateDataElement ? JSON.parse(stateDataElement.textContent) : null;
if (stateData) {
    setState(stateData.initialStatus, stateData.initialQueuePosition);
}

function setState(status, position) {
    if (status === 'finished') {
        processingElement.hidden = true;
        resultElement.hidden = false;
        resultImageElement.src = stateData.resultUrl;
    } else if (status === 'failed' || status === 'stopped' || status === 'canceled') {
        processingElement.hidden = true;
        jobErrorElement.hidden = false;
    } else {
        processingElement.hidden = false;
        if (position != null) {
            processingStatusElement.classList.remove('invisible');
            processingStatusElement.innerHTML = 'Position in the queue: ' + (position + 1);
        } else {
            processingStatusElement.classList.add('invisible');
            processingStatusElement.innerHTML = '&nbsp;';
        }
        setTimeout(pollState, stateData.pollInterval * 1000);
    }
}

function pollState() {
    axios.get(stateData.statusUrl, {timeout: stateData.requestTimeout * 1000})
        .then(response => {
            setState(response.data.status, response.data.position);
        })
        .catch(error => {
            processingElement.hidden = true;
            ajaxErrorElement.hidden = false;
            ajaxErrorReasonElement.innerHTML = error.message;
            console.error(error);
        });
}
