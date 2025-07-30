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
        
        // 로컬 스토리지에 저장
        localStorage.setItem('gameOpacity', opacity);
    }
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