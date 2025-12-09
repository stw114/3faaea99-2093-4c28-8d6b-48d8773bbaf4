const scanBtn = document.getElementById('scan-btn');
const statusText = document.getElementById('status-text');
const progressFill = document.getElementById('progress-fill');
const resultsTableBody = document.querySelector('#results-table tbody');
const bullCount = document.getElementById('bull-count');
const bearCount = document.getElementById('bear-count');
const neutralCount = document.getElementById('neutral-count');

let isScanning = false;

// Initial load
fetchResults();
setInterval(fetchStatus, 1000);

scanBtn.addEventListener('click', async () => {
    try {
        const response = await fetch('/api/scan', { method: 'POST' });
        const data = await response.json();
        console.log(data);
        fetchStatus();
    } catch (error) {
        console.error('Error starting scan:', error);
    }
});

async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        statusText.textContent = data.status;
        progressFill.style.width = `${data.progress}%`;
        
        if (data.is_scanning) {
            isScanning = true;
            scanBtn.disabled = true;
            scanBtn.textContent = 'Scanning...';
        } else {
            if (isScanning) {
                // Just finished scanning
                isScanning = false;
                scanBtn.disabled = false;
                scanBtn.textContent = 'Scan Now';
                fetchResults(); // Refresh results
            }
        }
    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

async function fetchResults() {
    try {
        const response = await fetch('/api/results');
        const data = await response.json();
        renderTable(data.results);
        updateStats(data.results);
    } catch (error) {
        console.error('Error fetching results:', error);
    }
}

function renderTable(results) {
    resultsTableBody.innerHTML = '';
    
    if (results.length === 0) {
        resultsTableBody.innerHTML = '<tr><td colspan="6" style="text-align:center">No results yet. Click "Scan Now".</td></tr>';
        return;
    }
    
    results.forEach(row => {
        const tr = document.createElement('tr');
        const signalClass = `signal-${row.signal.toLowerCase()}`;
        
        tr.innerHTML = `
            <td>${row.code}</td>
            <td>${row.name}</td>
            <td>${row.price}</td>
            <td style="color: ${row.change_percent >= 0 ? 'var(--bull)' : 'var(--bear)'}">${row.change_percent}%</td>
            <td><span class="signal-badge ${signalClass}">${row.signal}</span></td>
            <td>${row.confidence}%</td>
        `;
        resultsTableBody.appendChild(tr);
    });
}

function updateStats(results) {
    let bull = 0, bear = 0, neutral = 0;
    
    results.forEach(row => {
        if (row.signal === 'Bull') bull++;
        else if (row.signal === 'Bear') bear++;
        else neutral++;
    });
    
    bullCount.textContent = bull;
    bearCount.textContent = bear;
    neutralCount.textContent = neutral;
}
