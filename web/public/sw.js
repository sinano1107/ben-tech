self.addEventListener("push", function (event) {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: data.icon || "/icon.png",
      badge: "/next.svg",
      vibrate: [100, 50, 100],
      data: { dateOfArrival: Date.now(), primaryKey: "5" },
    };
    event.waitUntil(self.registration.showNotification(data.title, options));
  }
});
self.addEventListener("notificationclick", function (event) {
  console.log("Notification click received.");
  event.notification.close();
  event.waitUntil(clients.openWindow("https://bentech-web-app.vercel.app/")); //This should be the url to your website
});
