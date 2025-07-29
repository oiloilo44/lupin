// 기본 Excel 위장 기능

// 빠른 숨김 기능
function hideGame() {
    document.getElementById('gameOverlay').classList.add('hidden');
}

function showGame() {
    document.getElementById('gameOverlay').classList.remove('hidden');
}

// 키보드 단축키
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Tab') {
        e.preventDefault();
        hideGame();
    } else if (e.key === 'Escape') {
        showGame();
    }
});

// 엑셀 셀 클릭 효과
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.excel-cell').forEach(cell => {
        cell.addEventListener('click', function() {
            document.querySelectorAll('.excel-cell.selected').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
});