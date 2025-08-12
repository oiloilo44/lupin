// 기본 Excel 위장 기능

// 빠른 숨김 기능
function hideGame() {
    document.getElementById('gameOverlay').classList.add('hidden');
}

function showGame() {
    document.getElementById('gameOverlay').classList.remove('hidden');
}

// 업무모드 토글 기능
function toggleWorkMode() {
    const overlay = document.getElementById('gameOverlay');
    const button = document.querySelector('.quick-hide');
    
    if (overlay.classList.contains('hidden')) {
        overlay.classList.remove('hidden');
        button.textContent = '업무모드';
    } else {
        overlay.classList.add('hidden');
        button.textContent = '게임모드';
    }
}

// 투명도 조절 기능
function initOpacityControl() {
    const slider = document.getElementById('opacitySlider');
    const valueDisplay = document.getElementById('opacityValue');
    const overlay = document.getElementById('gameOverlay');
    
    if (!slider || !valueDisplay || !overlay) return;
    
    // 저장된 투명도 설정 로드 (우선순위)
    const savedOpacity = localStorage.getItem('gameOpacity');
    const initialOpacity = savedOpacity ? parseInt(savedOpacity) : 70; // 저장된 값이 없으면 70 사용
    
    // 초기 투명도 설정
    slider.value = initialOpacity;
    setOverlayOpacity(initialOpacity);
    
    // 슬라이더 이벤트 리스너
    slider.addEventListener('input', function() {
        const opacity = parseInt(this.value);
        setOverlayOpacity(opacity);
    });
}

// 오버레이 투명도 설정
function setOverlayOpacity(opacity) {
    const overlay = document.getElementById('gameOverlay');
    const valueDisplay = document.getElementById('opacityValue');
    
    if (overlay && valueDisplay) {
        overlay.style.opacity = opacity / 100;
        valueDisplay.textContent = opacity + '%';
        
        // 토스트 투명도도 함께 업데이트
        updateToastsWithOverlayOpacity();
        
        // 로컬 스토리지에 저장
        localStorage.setItem('gameOpacity', opacity);
    }
}

// 전역 토스트 시스템 (기존 스타일 적용)
function showGlobalToast(title, message, type = 'info', duration = 3000) {
    const container = document.getElementById('globalToastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const toastContent = `
        <div class="toast-title">${escapeHtml(title)}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
    `;
    
    toast.innerHTML = toastContent;
    container.appendChild(toast);
    
    // 게임 오버레이 투명도 적용
    updateToastOpacity(toast);
    
    // 애니메이션 시작
    setTimeout(() => toast.classList.add('show'), 100);
    
    // 자동 제거
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// 토스트 투명도 업데이트
function updateToastOpacity(toast = null) {
    const overlay = document.getElementById('gameOverlay');
    const toasts = toast ? [toast] : document.querySelectorAll('#globalToastContainer .toast');
    
    if (overlay && toasts.length > 0) {
        const overlayOpacity = parseFloat(overlay.style.opacity) || 0.7;
        
        toasts.forEach(t => {
            t.style.opacity = overlayOpacity;
        });
    }
}

// 투명도 변경 시 토스트도 함께 업데이트
function updateToastsWithOverlayOpacity() {
    updateToastOpacity();
}

// HTML 이스케이프 함수
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 키보드 단축키
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        toggleWorkMode();
    }
});

// DOMContentLoaded 이벤트 리스너
document.addEventListener('DOMContentLoaded', function() {
    // 엑셀 셀 클릭 효과
    document.querySelectorAll('.excel-cell').forEach(cell => {
        cell.addEventListener('click', function() {
            document.querySelectorAll('.excel-cell.selected').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
    
    // 투명도 컨트롤 초기화
    initOpacityControl();
});