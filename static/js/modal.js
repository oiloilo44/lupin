// 모달 시스템

function showModal(title, body, buttons = []) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = body;
    
    const footer = document.getElementById('modalFooter');
    footer.innerHTML = '';
    
    buttons.forEach(button => {
        const btn = document.createElement('button');
        btn.className = `modal-button ${button.class || 'secondary'}`;
        btn.textContent = button.text;
        btn.onclick = button.onclick;
        footer.appendChild(btn);
    });
    
    document.getElementById('modalOverlay').classList.add('show');
}

function hideModal() {
    document.getElementById('modalOverlay').classList.remove('show');
}

function showConfirmModal(title, message, onConfirm, onCancel) {
    showModal(title, message, [
        {
            text: '취소',
            class: 'secondary',
            onclick: () => {
                hideModal();
                if (onCancel) onCancel();
            }
        },
        {
            text: '확인',
            class: 'primary',
            onclick: () => {
                hideModal();
                if (onConfirm) onConfirm();
            }
        }
    ]);
}