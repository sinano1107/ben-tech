"use client";

export default function Home() {
  const handleClick = async () => {
    try {
      const device = await navigator.bluetooth.requestDevice({
        filters: [{ services: ["00a8a81d-4125-410e-a5c3-62615319bcbd"] }],
        optionalServices: ["00a8a81d-4125-410e-a5c3-62615319bcbd"],
      });
      console.log("選択されたデバイス:", device.name);

      const server = await device.gatt?.connect();

      const service = await server?.getPrimaryService(
        "00a8a81d-4125-410e-a5c3-62615319bcbd"
      );
      const char = await service?.getCharacteristic(
        "46898fe4-4b87-47c5-833f-6b9df8ca3b13"
      );
      const value = new Uint8Array(1);
      value[0] = 1;
      console.log(value);

      await char?.writeValueWithoutResponse(value);
      console.log("送信完了");

      server?.disconnect();
      console.log("接続解除済み");
    } catch (error) {
      console.log("デバイスの選択に失敗しました:", error);
    }
  };

  return (
    <div>
      <h1>ben-tech</h1>
      <button onClick={handleClick}>ボタン</button>
    </div>
  );
}
