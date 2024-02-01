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

    const stateDataElement = document.getElementById('state-data')
    const stateData = stateDataElement ? JSON.parse(stateDataElement.textContent) : null;
    const endTime = stateData ? Date.now() + stateData.updateTimeout * 1000 : null;

    let listenSocket = null;
    if (stateData) {
        setState(stateData.initialStatus, stateData.initialQueuePosition);
    }


    function setState(status, position) {
        if (status === 'finished') {
            processingElement.hidden = true;
            document.getElementById('result').hidden = false;
            document.getElementById('result-image').src = stateData.imageUrl;
        } else if (status === 'failed' || status === 'stopped' || status === 'canceled') {
            processingElement.hidden = true;
            document.getElementById('job-error').hidden = false;
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
                if (stateData.listenUrl) {
                    if (listenSocket == null) {
                        listenState();
                    }
                } else {
                    setTimeout(pollState, stateData.updateInterval * 1000);
                }
            } else {
                processingElement.hidden = true;
                document.getElementById('update-timeout').hidden = false;
            }
        }
    }

    function listenState() {
        listenSocket = new WebSocket(stateData.listenUrl);
        // TODO: timeout
        listenSocket.onmessage = evt => {
            const data = JSON.parse(evt.data);
            setState(data.status, data.position);
        };
        listenSocket.onclose = evt => {
            console.warn('WebSocket closed: "' + evt.reason + '". Falling back to polling.');
            stateData.listenUrl = null;
            setTimeout(pollState, stateData.updateInterval * 1000);
        };
    }

    function pollState() {
        axios.get(stateData.pollUrl, {timeout: stateData.requestTimeout * 1000})
            .then(response => {
                setState(response.data.status, response.data.position);
            })
            .catch(error => {
                console.error(error);
                processingElement.hidden = true;
                document.getElementById('update-error').hidden = false;
                document.getElementById('update-error-reason').innerHTML = error.message;
            });
    }
})();
