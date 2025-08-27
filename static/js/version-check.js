/**
 * 클라이언트 사이드 버전 체크 및 자동 새로고침
 */

class VersionChecker {
    constructor(currentVersion, checkInterval = 60000) {
        this.currentVersion = currentVersion;
        this.checkInterval = checkInterval;
        this.isCheckingVersion = false;
        this.updateNotificationShown = false;
        this.lastCheckTime = 0;
        this.minFocusCheckInterval = 600000; // 포커스 시 체크는 10분 간격 최소
    }

    /**
     * 버전 체크 시작
     */
    start() {
        // 주기적으로 버전 체크
        setInterval(() => {
            this.checkForUpdates();
        }, this.checkInterval);

        // 페이지 포커스시에도 체크 (10분 간격 제한)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkForUpdatesOnFocus();
            }
        });
    }

    /**
     * 포커스 시 버전 체크 (간격 제한 적용)
     */
    checkForUpdatesOnFocus() {
        const now = Date.now();
        if (now - this.lastCheckTime >= this.minFocusCheckInterval) {
            this.checkForUpdates();
        }
    }

    /**
     * 서버 버전 체크
     */
    async checkForUpdates() {
        if (this.isCheckingVersion) return;

        this.isCheckingVersion = true;
        this.lastCheckTime = Date.now();

        try {
            const response = await fetch('/api/version', {
                method: 'GET',
                cache: 'no-cache'
            });

            if (response.ok) {
                const data = await response.json();
                const serverVersion = data.version;

                if (serverVersion !== this.currentVersion && !this.updateNotificationShown) {
                    this.showUpdateNotification();
                    this.updateNotificationShown = true;
                }
            }
        } catch (error) {
            console.log('버전 체크 실패:', error);
        } finally {
            this.isCheckingVersion = false;
        }
    }

    /**
     * 업데이트 알림 표시
     */
    showUpdateNotification() {
        const notification = document.createElement('div');
        notification.className = 'version-update-notification';
        notification.innerHTML = `
            <div class="update-content">
                <strong>새 버전이 있습니다</strong>
                <p>페이지를 새로고침하여 최신 기능을 이용하세요.</p>
                <div class="update-buttons">
                    <button class="btn-reload">새로고침</button>
                    <button class="btn-dismiss">나중에</button>
                </div>
            </div>
        `;

        // 스타일 추가
        if (!document.getElementById('version-update-styles')) {
            const style = document.createElement('style');
            style.id = 'version-update-styles';
            style.textContent = `
                .version-update-notification {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 10000;
                    max-width: 300px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                }

                .update-content strong {
                    color: #2563eb;
                    display: block;
                    margin-bottom: 8px;
                }

                .update-content p {
                    margin: 0 0 12px 0;
                    color: #6b7280;
                    font-size: 14px;
                }

                .update-buttons {
                    display: flex;
                    gap: 8px;
                }

                .update-buttons button {
                    padding: 6px 12px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 13px;
                }

                .btn-reload {
                    background: #2563eb;
                    color: white;
                }

                .btn-dismiss {
                    background: #f3f4f6;
                    color: #6b7280;
                }

                .btn-reload:hover {
                    background: #1d4ed8;
                }

                .btn-dismiss:hover {
                    background: #e5e7eb;
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(notification);

        // 30초 후 자동 새로고침 카운트다운 (사용자에게 충분한 시간 제공)
        let countdown = 30;
        const countdownInterval = setInterval(() => {
            countdown--;
            if (countdown <= 0) {
                location.reload();
            }
        }, 1000);

        // 버튼 이벤트 리스너 추가
        notification.querySelector('.btn-reload').addEventListener('click', () => {
            location.reload();
        });

        notification.querySelector('.btn-dismiss').addEventListener('click', () => {
            clearInterval(countdownInterval);
            notification.remove();
            // 다시 표시되지 않도록 플래그 유지
        });
    }
}

// 전역으로 노출
window.VersionChecker = VersionChecker;
