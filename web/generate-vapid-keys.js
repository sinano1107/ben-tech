const webpush = require("web-push");
const vapidKeys = webpush.generateVAPIDKeys();

console.log("Paste the following keys in your .env file:");
console.log("-------------------");
console.log("NEXT_PUBLIC_VAPID_PUBLIC_KEY:");
console.log(vapidKeys.publicKey);
console.log("VAPID_PRIVATE_KEY:");
console.log("vapidKeys.privateKey");
