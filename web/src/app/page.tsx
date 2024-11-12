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
  let control_char: BluetoothRemoteGATTCharacteristic | undefined;
  let response_char: BluetoothRemoteGATTCharacteristic | undefined;
  let socker_char: BluetoothRemoteGATTCharacteristic | undefined;

  const connect = async () => {
    try {
      const device = await navigator.bluetooth.requestDevice({
        filters: [
          {
            name: "BT-hub",
          },
        ],
        optionalServices: ["e295c051-7ac4-4d72-b7ea-3e71e47e15a9"],
      });
      console.log("選択されたデバイス:", device.name);

      server = await device.gatt?.connect();
      service = await server?.getPrimaryService(
        "e295c051-7ac4-4d72-b7ea-3e71e47e15a9"
      );

      [control_char, socker_char] = await Promise.all([
        service?.getCharacteristic("4576af67-ecc6-434e-8ce7-52c6ab1d5f04"),
        service?.getCharacteristic("feb2f5aa-ec75-46ef-8da6-2da832175d8e"),
      ]);

      response_char = await service?.getCharacteristic(
        "d95426b1-2cb4-4115-bd4b-32ff24232864"
      );
      await response_char?.startNotifications();
      response_char?.addEventListener(
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

  function uint8ToArrayBuffer(n: number, length = 1) {
    const view = new DataView(new ArrayBuffer(length));
    view.setUint8(0, n);
    return view.buffer;
  }

  const sendTextByStream = async (_value: string) => {
    const utf8Encoder = new TextEncoder();
    const msgArray = utf8Encoder.encode(_value);

    await control_char?.writeValueWithResponse(uint8ToArrayBuffer(1));

    const length = Number(msgArray.length / 20) + 1;
    await socker_char?.writeValueWithResponse(uint8ToArrayBuffer(length));

    for (let i = 0; i < length; i++) {
      const start = i * 20;
      const end = i == length - 1 ? -1 : start + 20;
      const data = msgArray.slice(start, end);
      await socker_char?.writeValueWithResponse(data);
    }
  };

  const sendWiFiData = async () => {
    const data = {
      ssid: localStorage.getItem("WIFI_SSID"),
      password: localStorage.getItem("WIFI_PASSWORD"),
    };
    await sendTextByStream(JSON.stringify(data));
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
      <button onClick={sendWiFiData}>ソケットで送信</button>
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