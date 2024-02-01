/*
 * Copyright 2024 Victor Semionov
 */


(() => {
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
})();


(() => {
    const processingElement = document.getElementById('processing');
    const processingStatusElement = document.getElementById('processing-status');
    const resultElement = document.getElementById('result');
    const resultImageElement = document.getElementById('result-image');
    const jobErrorElement = document.getElementById('job-error');
    const updateErrorElement = document.getElementById('update-error');
    const updateErrorReasonElement = document.getElementById('update-error-reason');
    const updateTimeoutElement = document.getElementById('update-timeout');

    const stateDataElement = document.getElementById('state-data')
    const stateData = stateDataElement ? JSON.parse(stateDataElement.textContent) : null;
    const endTime = stateDataElement ? Date.now() + stateData.updateTimeout * 1000 : null;
    if (stateData) {
        setState(stateData.initialStatus, stateData.initialQueuePosition);
    }

    function setState(status, position) {
        if (status === 'finished') {
            processingElement.hidden = true;
            resultElement.hidden = false;
            resultImageElement.src = stateData.imageUrl;
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
            if (Date.now() < endTime) {
                setTimeout(pollState, stateData.updateInterval * 1000);
            } else {
                processingElement.hidden = true;
                updateTimeoutElement.hidden = false;
            }
        }
    }

    function pollState() {
        axios.get(stateData.updateUrl, {timeout: stateData.requestTimeout * 1000})
            .then(response => {
                setState(response.data.status, response.data.position);
            })
            .catch(error => {
                processingElement.hidden = true;
                updateErrorElement.hidden = false;
                updateErrorReasonElement.innerHTML = error.message;
                console.error(error);
            });
    }
})();
