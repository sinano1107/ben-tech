"use client";
import { useEffect, useState } from "react";

export default function Home() {
  return (
    <>
      <BLE />
      <Notification />
    </>
  );
}

const BLE = () => {
  let server: BluetoothRemoteGATTServer | undefined;
  let service: BluetoothRemoteGATTService | undefined;
  let listen_control_char: BluetoothRemoteGATTCharacteristic | undefined;
  let notify_on_button_pressed_char:
    | BluetoothRemoteGATTCharacteristic
    | undefined;

  const connect = async () => {
    try {
      const device = await navigator.bluetooth.requestDevice({
        /*
        filters: [{ services: ["00a8a81d-4125-410e-a5c3-62615319bcbd"] }],
        optionalServices: ["00a8a81d-4125-410e-a5c3-62615319bcbd"],
        */
        acceptAllDevices: true,
      });
      console.log("選択されたデバイス:", device.name);

      server = await device.gatt?.connect();
      service = await server?.getPrimaryService(
        "00a8a81d-4125-410e-a5c3-62615319bcbd"
      );

      notify_on_button_pressed_char = await service?.getCharacteristic(
        "2273b7b4-fbbd-4904-81f5-d9f6ea4dadc7"
      );
      await notify_on_button_pressed_char?.startNotifications();
      notify_on_button_pressed_char?.addEventListener(
        "characteristicvaluechanged",
        handleNotifications
      );
    } catch (error) {
      console.log("デバイスの選択に失敗しました:", error);
    }
  };

  const disconnect = async () => {
    server?.disconnect();
    console.log("接続解除済み");
  };

  const set_led = async (_value: boolean) => {
    if (listen_control_char === undefined) {
      listen_control_char = await service?.getCharacteristic(
        "46898fe4-4b87-47c5-833f-6b9df8ca3b13"
      );
    }
    const value = new Uint8Array(1);
    value[0] = _value ? 1 : 0;
    await listen_control_char?.writeValueWithoutResponse(value);
    console.log("送信完了");
  };

  const handleNotifications = (event: Event) => {
    const value = String.fromCharCode.apply(
      "",
      // @ts-expect-error このような実装しか見つからなかった
      new Uint8Array(event.target.value.buffer)
    );
    console.log("通知を受け取りました", value, event);
  };

  return (
    <div>
      <h1>ben-tech</h1>
      <button onClick={connect}>接続</button>
      <button onClick={disconnect}>接続解除</button>
      <button onClick={() => set_led(true)}>LEDオン</button>
      <button onClick={() => set_led(false)}>LEDオフ</button>
    </div>
  );
};

const Notification = () => {
  const [subscription, setSubscription] = useState<PushSubscription | null>(
    null
  );
  useEffect(() => {
    if ("serviceWorker" in navigator && "PushManager" in window) {
      registerServiceWorker();
    }
  }, []);
  async function registerServiceWorker() {
    const registration = await navigator.serviceWorker.register("/sw.js", {
      //provide the route to the service worker
      scope: "/",
      updateViaCache: "none",
    });
    const sub = await registration.pushManager.getSubscription();
    if (sub) {
      setSubscription(sub); //This would be sent to a server
    } else {
      const pushSubscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY, // Your VAPID public key
      });
      setSubscription(pushSubscription);
    }
  } //Create a function to test the notification
  const handleSendNotification = async () => {
    await fetch("/api/sendNotification", {
      method: "POST",
      body: JSON.stringify({
        message: "Your timer has completed!",
        subscription: subscription, // This ideally, should not be included in the body. It should have already been saved on the server
      }),
      headers: { "Content-Type": "application/json" },
    });
  };
  return (
    <div>
      {" "}
      <h1>My PWA with Push Notifications</h1>{" "}
      <button onClick={handleSendNotification}>Notify Me!</button>{" "}
    </div>
  );
};