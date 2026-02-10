function HTBLabXBlock(runtime, element, context) {
    const panel = element.querySelector('.htblab-panel');
    const statusNode = panel.querySelector('.htblab-status');
    const vmsNode = panel.querySelector('.htblab-vms');
    const metaNode = panel.querySelector('.htblab-meta');
    panel.querySelector('.htblab-title').textContent = context.display_name;
    panel.querySelector('.htblab-hint').textContent = context.hint || '';

    const teamQuery = context.team_group_id ? `?team_id=${encodeURIComponent(context.team_group_id)}` : '';
    const base = `/api/htblab/${encodeURIComponent(context.course_id)}/${encodeURIComponent(context.block_id)}`;

    async function call(action) {
        const url = action === 'status' ? `${base}/status${teamQuery}` : `${base}/${action}${teamQuery}`;
        const response = await fetch(url, {
            method: action === 'status' ? 'GET' : 'POST',
            headers: {'Content-Type': 'application/json'},
            body: action === 'status' ? null : JSON.stringify({
                team_id: context.team_group_id || null,
                xblock_config: context.xblock_config || {},
            }),
            credentials: 'same-origin',
        });
        const data = await response.json();
        render(data);
        return data;
    }

    function render(data) {
        statusNode.textContent = `Status: ${data.state || 'unknown'} | Expires: ${data.expires_at || 'n/a'}`;
        metaNode.textContent = data.message || '';
        const vms = data.vms || [];
        vmsNode.innerHTML = '';
        vms.forEach(vm => {
            const card = document.createElement('div');
            card.className = 'htblab-vm-card';
            const ips = (vm.ips || []).join(', ') || 'IP pending';
            const creds = vm.creds_visible ? `${vm.username || ''} / ${vm.password || ''}` : 'No credentials provided (target VM)';
            card.innerHTML = `<strong>${vm.role}</strong><div>State: ${vm.state}</div><div>IPs: ${ips}</div><div>${creds}</div>`;
            vmsNode.appendChild(card);
        });
    }

    element.querySelectorAll('button[data-action]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const action = btn.dataset.action;
            if (action === 'refresh') {
                await call('status');
                return;
            }
            if (action === 'extend' && !context.allow_extend) {
                metaNode.textContent = 'Extend is disabled for this lab.';
                return;
            }
            await call(action);
            setTimeout(() => call('status'), 1500);
        });
    });

    call('status');
    setInterval(() => call('status'), 10000);
}
