document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const themeToggle = document.getElementById('theme-toggle');
    const moonIcon = document.getElementById('moon-icon');
    const sunIcon = document.getElementById('sun-icon');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const logContainer = document.getElementById('log-container');
    const refreshLogsBtn = document.getElementById('refresh-logs');
    const triggerSyncBtn = document.getElementById('trigger-sync');
    const toast = document.getElementById('toast');

    // Forms & Inputs
    const configForm = document.getElementById('config-form');
    const settingsForm = document.getElementById('settings-form');
    const exportBtn = document.getElementById('export-btn');
    const importBtn = document.getElementById('import-btn');
    const importFile = document.getElementById('import-file');

    // --- Theme Management ---
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });

    function updateThemeIcon(theme) {
        if (theme === 'dark') {
            moonIcon.style.display = 'none';
            sunIcon.style.display = 'block';
        } else {
            moonIcon.style.display = 'block';
            sunIcon.style.display = 'none';
        }
    }

    // --- Tab Navigation ---
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            
            // Update active states
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // --- Toast Notification ---
    function showToast(message, isError = false) {
        toast.textContent = message;
        toast.style.backgroundColor = isError ? '#ef4444' : 'var(--primary-color)';
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }

    // --- API Interactions ---

    // Load Logs
    function fetchLogs() {
        fetch('/api/logs')
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    logContainer.textContent = 'Error loading logs: ' + data.error;
                } else {
                    logContainer.textContent = data.logs || 'No logs found yet.';
                }
            })
            .catch(err => {
                logContainer.textContent = 'Failed to fetch logs.';
                console.error(err);
            });
    }

    refreshLogsBtn.addEventListener('click', fetchLogs);

    const flushLogsBtn = document.getElementById('flush-logs');
    if (flushLogsBtn) {
        flushLogsBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to flush all logs?')) {
                fetch('/api/logs/flush', { method: 'POST' })
                    .then(res => res.json())
                    .then(data => {
                        showToast(data.message);
                        fetchLogs();
                    })
                    .catch(console.error);
            }
        });
    }

    // Initial log load
    fetchLogs();
    setInterval(fetchLogs, 5000); // Poll every 5s

    // Status polling
    function fetchStatus() {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                const indicator = document.getElementById('sync-indicator');
                const btn = document.getElementById('trigger-sync');
                if (data.is_syncing) {
                    indicator.style.display = 'inline-block';
                    btn.disabled = true;
                    btn.textContent = 'Sync in Progress...';
                } else {
                    indicator.style.display = 'none';
                    btn.disabled = false;
                    btn.textContent = 'Manual Sync';
                }
            })
            .catch(console.error);
    }
    
    fetchStatus();
    setInterval(fetchStatus, 3000);

    // Manual Sync Trigger
    triggerSyncBtn.addEventListener('click', () => {
        fetch('/api/trigger', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                showToast(data.message);
                setTimeout(fetchLogs, 1000); // Refresh logs shortly after starting
            });
    });

    // Load Configurations
    function loadConfigurations() {
        fetch('/api/config')
            .then(res => res.json())
            .then(data => {
                const fields = ['username', 'password', 'region', 'brand', 'db_host', 'db_name', 'db_user', 'db_password', 'db_port'];
                fields.forEach(field => {
                    const el = document.getElementById(`cfg-${field}`);
                    if (el && data[field] !== undefined) {
                        el.value = data[field];
                    }
                });
            });

        fetch('/api/settings')
            .then(res => res.json())
            .then(data => {
                if (data.interval_hours !== undefined) {
                    document.getElementById('set-interval').value = data.interval_hours;
                }
                if (data.sync_time !== undefined) {
                    document.getElementById('set-sync-time').value = data.sync_time;
                }
            });
    }

    loadConfigurations();

    // Save Configuration
    configForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const payload = {};
        const fields = ['username', 'password', 'region', 'brand', 'db_host', 'db_name', 'db_user', 'db_password', 'db_port'];
        fields.forEach(field => {
            const el = document.getElementById(`cfg-${field}`);
            if (el) {
                payload[field] = el.type === 'number' ? Number(el.value) : el.value;
            }
        });

        fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') showToast('Configuration saved successfully');
            else showToast('Error saving configuration', true);
        });
    });

    // Save Settings
    settingsForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const payload = {
            interval_hours: Number(document.getElementById('set-interval').value),
            sync_time: document.getElementById('set-sync-time').value || null
        };

        fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') showToast('Settings saved successfully');
            else showToast('Error saving settings', true);
        });
    });

    // --- Import / Export ---
    exportBtn.addEventListener('click', () => {
        fetch('/api/export')
            .then(res => res.json())
            .then(data => {
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'data_logger_backup.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            });
    });

    importBtn.addEventListener('click', () => {
        importFile.click();
    });

    importFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const jsonData = JSON.parse(event.target.result);
                fetch('/api/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(jsonData)
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        showToast('Settings imported successfully');
                        loadConfigurations(); // Reload form fields
                    } else {
                        showToast(data.message, true);
                    }
                });
            } catch (err) {
                showToast('Invalid JSON file', true);
            }
            // Reset input
            importFile.value = '';
        };
        reader.readAsText(file);
    });
});
