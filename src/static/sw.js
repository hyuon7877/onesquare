// OneSquare Service Worker v1.0
// PWA 오프라인 지원 및 캐싱 전략

const CACHE_NAME = 'onesquare-v1';
const urlsToCache = [
  '/',
  '/static/css/common.css',
  '/static/js/common.js',
  '/static/js/modal.js',
  '/offline/',
  '/dashboard/',
  '/field-reports/',
];

// Service Worker 설치
self.addEventListener('install', event => {
  console.log('[ServiceWorker] 설치 시작');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[ServiceWorker] 캐시 열기 성공');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('[ServiceWorker] 모든 리소스 캐싱 완료');
        return self.skipWaiting(); // 즉시 활성화
      })
  );
});

// Service Worker 활성화
self.addEventListener('activate', event => {
  console.log('[ServiceWorker] 활성화');
  
  const cacheWhitelist = [CACHE_NAME];
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('[ServiceWorker] 오래된 캐시 삭제:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim(); // 즉시 제어권 획득
    })
  );
});

// Fetch 이벤트 처리 (캐싱 전략)
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // API 요청 처리
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/field-reports/sync/')) {
    event.respondWith(
      networkFirstStrategy(request)
    );
    return;
  }
  
  // 정적 리소스 처리
  if (request.destination === 'image' || 
      url.pathname.startsWith('/static/') || 
      url.pathname.startsWith('/media/')) {
    event.respondWith(
      cacheFirstStrategy(request)
    );
    return;
  }
  
  // HTML 페이지 처리
  if (request.mode === 'navigate') {
    event.respondWith(
      networkFirstWithOfflineFallback(request)
    );
    return;
  }
  
  // 기본 처리
  event.respondWith(
    staleWhileRevalidate(request)
  );
});

// 캐시 우선 전략 (정적 리소스)
async function cacheFirstStrategy(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    console.log('[ServiceWorker] 캐시에서 제공:', request.url);
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[ServiceWorker] 네트워크 요청 실패:', error);
    return new Response('오프라인 상태입니다', { status: 503 });
  }
}

// 네트워크 우선 전략 (API)
async function networkFirstStrategy(request) {
  const cache = await caches.open(CACHE_NAME);
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[ServiceWorker] 네트워크 실패, 캐시 확인:', request.url);
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // 오프라인 시 빈 응답 반환
    return new Response(JSON.stringify({
      error: '오프라인 상태입니다',
      cached: false
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// 네트워크 우선 + 오프라인 폴백 (HTML)
async function networkFirstWithOfflineFallback(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
      return networkResponse;
    }
  } catch (error) {
    console.log('[ServiceWorker] 오프라인 모드 활성화');
  }
  
  // 캐시된 페이지 확인
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // 오프라인 페이지 반환
  return caches.match('/offline/');
}

// Stale While Revalidate 전략
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);
  
  const fetchPromise = fetch(request).then(networkResponse => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(() => {
    return cachedResponse || new Response('오프라인 상태입니다', { status: 503 });
  });
  
  return cachedResponse || fetchPromise;
}

// 백그라운드 동기화
self.addEventListener('sync', event => {
  console.log('[ServiceWorker] 백그라운드 동기화 시작');
  
  if (event.tag === 'sync-reports') {
    event.waitUntil(syncOfflineReports());
  }
});

// 오프라인 리포트 동기화
async function syncOfflineReports() {
  try {
    const response = await fetch('/field-reports/sync/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('[ServiceWorker] 동기화 완료:', data);
      
      // 동기화 성공 알림
      self.registration.showNotification('OneSquare', {
        body: `${data.synced_count}개의 리포트가 동기화되었습니다`,
        icon: '/static/images/icon-192.png',
        badge: '/static/images/badge-72.png'
      });
    }
  } catch (error) {
    console.error('[ServiceWorker] 동기화 실패:', error);
  }
}

// 푸시 알림 수신
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : '새로운 알림이 있습니다',
    icon: '/static/images/icon-192.png',
    badge: '/static/images/badge-72.png',
    vibrate: [200, 100, 200],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    }
  };
  
  event.waitUntil(
    self.registration.showNotification('OneSquare', options)
  );
});

// 알림 클릭 처리
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow('/')
  );
});

// 메시지 수신 (캐시 업데이트 등)
self.addEventListener('message', event => {
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
  
  if (event.data.action === 'clearCache') {
    caches.delete(CACHE_NAME).then(() => {
      console.log('[ServiceWorker] 캐시 삭제 완료');
    });
  }
});

console.log('[ServiceWorker] 로드 완료');