// OneSquare PWA Common JavaScript Functions

// API Testing Functions
async function testAPI(endpoint) {
    try {
        const button = event.target;
        const originalText = button.textContent;
        
        // Show loading state
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> 테스트 중...';
        button.disabled = true;
        
        const response = await fetch(endpoint);
        const data = await response.json();
        
        // Show result
        showToast(data.message || '테스트 완료', response.ok ? 'success' : 'error');
        
        // Restore button
        button.textContent = originalText;
        button.disabled = false;
        
    } catch (error) {
        console.error('API Test Error:', error);
        showToast('API 테스트 중 오류 발생: ' + error.message, 'error');
        
        // Restore button
        event.target.textContent = '테스트';
        event.target.disabled = false;
    }
}

// Notion API Test
async function testNotionAPI() {
    try {
        const button = event.target;
        const resultDiv = document.getElementById('notion-result');
        
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Notion API 테스트 중...';
        button.disabled = true;
        
        const response = await fetch('/api/notion/test/');
        const data = await response.json();
        
        resultDiv.innerHTML = `
            <div class="alert alert-${response.ok ? 'success' : 'danger'}" role="alert">
                <h6>${response.ok ? '✅ 성공' : '❌ 오류'}</h6>
                <p><strong>메시지:</strong> ${data.message}</p>
                ${data.details ? `<p><strong>세부사항:</strong> ${JSON.stringify(data.details, null, 2)}</p>` : ''}
                <small class="text-muted">타임스탬프: ${data.timestamp || new Date().toISOString()}</small>
            </div>
        `;
        
        button.textContent = 'Notion API 테스트';
        button.disabled = false;
        
    } catch (error) {
        console.error('Notion API Test Error:', error);
        document.getElementById('notion-result').innerHTML = `
            <div class="alert alert-danger" role="alert">
                <h6>❌ 오류</h6>
                <p>Notion API 테스트 중 오류 발생: ${error.message}</p>
            </div>
        `;
        
        event.target.textContent = 'Notion API 테스트';
        event.target.disabled = false;
    }
}

// Toast Notification System
function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast-notification');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
    toast.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 1050;
        min-width: 300px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    `;
    
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, duration);
}

// PWA Installation
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Store the event so it can be triggered later
    deferredPrompt = e;
    
    // Show custom install prompt
    showInstallPrompt();
});

function showInstallPrompt() {
    const installPrompt = document.createElement('div');
    installPrompt.className = 'install-prompt';
    installPrompt.innerHTML = `
        <span>📱 OneSquare를 홈 화면에 추가하시겠습니까?</span>
        <button class="btn btn-light btn-sm ms-2" onclick="installApp()">설치</button>
        <button class="btn btn-outline-light btn-sm ms-1" onclick="this.parentElement.remove()">닫기</button>
    `;
    
    document.body.appendChild(installPrompt);
    installPrompt.style.display = 'block';
}

async function installApp() {
    if (deferredPrompt) {
        // Show the install prompt
        deferredPrompt.prompt();
        
        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            showToast('OneSquare가 성공적으로 설치되었습니다!', 'success');
        } else {
            showToast('설치가 취소되었습니다.', 'info');
        }
        
        // Clear the saved prompt since it can only be used once
        deferredPrompt = null;
        
        // Remove install prompt
        const installPrompt = document.querySelector('.install-prompt');
        if (installPrompt) {
            installPrompt.remove();
        }
    }
}

// Network Status Monitoring
function updateNetworkStatus() {
    const offlineIndicator = document.querySelector('.offline-indicator');
    
    if (!navigator.onLine) {
        if (!offlineIndicator) {
            const indicator = document.createElement('div');
            indicator.className = 'offline-indicator';
            indicator.textContent = '📵 오프라인 모드 - 일부 기능이 제한될 수 있습니다.';
            document.body.insertBefore(indicator, document.body.firstChild);
            indicator.style.display = 'block';
        }
    } else {
        if (offlineIndicator) {
            offlineIndicator.remove();
        }
    }
}

// Event Listeners
window.addEventListener('online', updateNetworkStatus);
window.addEventListener('offline', updateNetworkStatus);

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    updateNetworkStatus();
    
    // Check if app is running in standalone mode (PWA)
    if (window.matchMedia('(display-mode: standalone)').matches) {
        console.log('Running as PWA');
        document.body.classList.add('pwa-mode');
    }
});

// Service Worker Update Handling
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('controllerchange', () => {
        showToast('앱이 업데이트되었습니다. 새로고침해주세요.', 'info', 5000);
    });
}