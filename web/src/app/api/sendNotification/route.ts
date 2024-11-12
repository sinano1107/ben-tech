import {
    NextResponse
} from "next/server";
import webpush from "web-push";
webpush.setVapidDetails(
    "mailto:tftf161107@icloud.com", // Your email 
    process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY!,
    process.env.VAPID_PRIVATE_KEY!
);
export async function POST(req: Request) {
    const {
        message,
        subscription
    } = await req.json();
    if (!subscription) {
        return NextResponse.json({
            error: "No subscription available"
        }, {
            status: 400
        });
    }
  try {
      await new Promise(resolve => setTimeout(resolve, 3000))
        await webpush.sendNotification(subscription, JSON.stringify({
            title: "Notification",
            body: message
        }));
        return NextResponse.json({
            success: true
        });
    } catch (error) {
        console.error("Error sending notification:", error);
        return NextResponse.json({
            error: "Failed to send notification"
        }, {
            status: 500
        });
    }
}