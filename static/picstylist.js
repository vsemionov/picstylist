/*
 * Copyright 2024 Victor Semionov
 */


(() => {
    const initialImgSrc = document.querySelector('.ps-upload + label > img')?.src;
    document.querySelectorAll('.ps-upload').forEach(input => {
        input.onchange = () => {
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
    const updateInterval = stateData ? stateData.updateInterval * 1000 : null;
    const requestTimeout = stateData ? stateData.requestTimeout * 1000 : null;
    const endTime = stateData ? Date.now() + stateData.updateTimeout * 1000 : null;

    let terminalStatus = false;
    let listenSocket = null;
    let listenTimeout = null;

    if (stateData) {
        setState(stateData.initialStatus, stateData.initialQueuePosition);
    }


    function setState(status, position) {
        if (status === 'finished') {
            processingElement.hidden = true;
            document.getElementById('result').hidden = false;
            document.getElementById('result-image').src = stateData.imageUrl;
            terminalStatus = true;
        } else if (status === 'failed' || status === 'stopped' || status === 'canceled') {
            processingElement.hidden = true;
            document.getElementById('job-error').hidden = false;
            terminalStatus = true;
        } else if (status == null) {
            processingElement.hidden = true;
            document.getElementById('job-expired').hidden = false;
            terminalStatus = true;
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
                    setTimeout(pollState, updateInterval);
                }
            } else {
                processingElement.hidden = true;
                document.getElementById('update-timeout').hidden = false;
                if (listenSocket != null) {
                    listenSocket.close();
                }
            }
        }
    }

    function listenState() {
        const onListenTimeout = () => {
            console.warn('WebSocket timeout.');
            stateData.listenUrl = null;
            listenSocket.close();
        }
        listenSocket = new WebSocket(stateData.listenUrl);
        listenTimeout = setTimeout(onListenTimeout, requestTimeout);
        listenSocket.onmessage = evt => {
            clearTimeout(listenTimeout);
            const data = JSON.parse(evt.data);
            setState(data.status, data.position);
            if (terminalStatus) {
                listenSocket.close();
            } else {
                listenTimeout = setTimeout(onListenTimeout, requestTimeout);
            }
        };
        listenSocket.onclose = evt => {
            if (!terminalStatus) {
                console.warn('WebSocket closed: "' + evt.reason + '". Falling back to polling.');
                stateData.listenUrl = null;
                setTimeout(pollState, updateInterval);
            }
        };
    }

    function pollState() {
        axios.get(stateData.pollUrl, {timeout: requestTimeout})
            .then(response => {
                setState(response.data.status, response.data.position);
            })
            .catch(error => {
                const status = error.response?.status;
                if (status === 404 || status === 410) {
                    setState(null);
                } else {
                    processingElement.hidden = true;
                    document.getElementById('update-error').hidden = false;
                    document.getElementById('update-error-details').innerHTML = error.message;
                }
            });
    }
})();
