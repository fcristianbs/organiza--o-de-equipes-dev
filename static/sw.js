// Service Worker para Web Push Notifications (Plataforma/Navegador Fechado)

self.addEventListener('push', function(event) {
    let data = { title: "📌 Nova Tarefa Criada!", body: "Uma nova tarefa foi adicionada ao projeto.", url: "/" };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: '/static/img/icon.png',
        badge: '/static/img/badge.png',
        data: { url: data.url || '/' },
        tag: 'task-notification-' + Date.now(),
        renotify: true,
        requireInteraction: true
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const targetUrl = event.notification.data ? event.notification.data.url : '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (let i = 0; i < clientList.length; i++) {
                let client = clientList[i];
                if ('focus' in client) {
                    client.navigate(targetUrl);
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
