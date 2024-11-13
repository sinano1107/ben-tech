"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Wifi,
  WifiOff,
  Bell,
  BellOff,
  Loader2,
  Home,
  List,
  Clock,
  Link,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  arrayBufferToString,
  arrayBufferToUint32,
  concatArrayBuffers,
  uint8ToArrayBuffer,
} from "@/lib/utils";

class HubController {
  private hubServiceId = "e295c051-7ac4-4d72-b7ea-3e71e47e15a9";
  private controlCharId = "4576af67-ecc6-434e-8ce7-52c6ab1d5f04";
  private responseCharId = "d95426b1-2cb4-4115-bd4b-32ff24232864";
  private streamCharId = "feb2f5aa-ec75-46ef-8da6-2da832175d8e";
  private controlChar: BluetoothRemoteGATTCharacteristic | undefined;
  private responseChar: BluetoothRemoteGATTCharacteristic | undefined;
  private streamChar: BluetoothRemoteGATTCharacteristic | undefined;

  private async requestAndListenStream(command: number) {
    if (this.streamChar === undefined) {
      throw Error("streamCharがありません");
    } else if (this.controlChar === undefined) {
      throw new Error("controlCharがありません");
    }

    let count = 0;
    let length: number | undefined = undefined;
    let joinned_buffer = new ArrayBuffer(0);

    const handleNotifications = (event: Event) => {
      // @ts-expect-error このような実装しか見つからなかった
      const data = event.target.value.buffer;
      if (count === 0) {
        length = arrayBufferToUint32(data);
        console.log(`これから ${length} 個のデータが送られてきます`);
      } else {
        console.log(`${count}個目`, data);
        joinned_buffer = concatArrayBuffers(joinned_buffer, data);
      }
      count += 1;
    };

    this.streamChar.addEventListener(
      "characteristicvaluechanged",
      handleNotifications
    );

    await this.streamChar.startNotifications();
    await this.controlChar.writeValueWithResponse(uint8ToArrayBuffer(command));

    await new Promise((resolve) => {
      const intervalId = setInterval(() => {
        if (length !== undefined && count >= length + 1) {
          clearInterval(intervalId);
          resolve(null);
        }
      }, 100);
    });

    return arrayBufferToString(joinned_buffer);
  }

  private async requestInfo() {
    const response = await this.requestAndListenStream(2);
    console.log("info", JSON.parse(response));
  }

  async connect() {
    // hubをユーザーに選択してもらう
    const hub = await navigator.bluetooth.requestDevice({
      filters: [
        {
          name: "BT-hub",
        },
      ],
      optionalServices: [this.hubServiceId],
    });

    // Hubのサービスを取得
    const connection = await hub.gatt?.connect();
    const service = await connection?.getPrimaryService(this.hubServiceId);

    if (service === undefined) {
      throw Error("serviceの取得に失敗");
    }

    // それぞれのキャラクタリスティックを取得
    [this.controlChar, this.responseChar, this.streamChar] = await Promise.all([
      service.getCharacteristic(this.controlCharId),
      service.getCharacteristic(this.responseCharId),
      service.getCharacteristic(this.streamCharId),
    ]);

    await this.requestInfo();
  }
}
const hubController = new HubController();

export default function Component() {
  const [isWifiConnected, setIsWifiConnected] = useState(false);
  const [isWifiDialogOpen, setIsWifiDialogOpen] = useState(false);
  const [isNotificationEnabled, setIsNotificationEnabled] = useState(false);
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [isWifiLoading, setIsWifiLoading] = useState(false);
  const [isNotificationLoading, setIsNotificationLoading] = useState(false);
  const [currentScreen, setCurrentScreen] = useState("home");
  const [isHubConnected, setIsHubConnected] = useState(false);
  const [isHubConnecting, setIsHubConnecting] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [bleDevices, setBleDevices] = useState([
    { name: "デバイス1", status: "接続中" },
    { name: "デバイス2", status: "未接続" },
    { name: "デバイス3", status: "ペアリング済み" },
  ]);

  const handleWifiConnect = useCallback(() => {
    setIsWifiLoading(true);
    setTimeout(() => {
      setIsWifiConnected(true);
      setIsWifiDialogOpen(false);
      setIsWifiLoading(false);
    }, 2000);
  }, []);

  const handleHubConnect = useCallback(async () => {
    setIsHubConnecting(true);

    try {
      await hubController.connect();
      setIsHubConnected(true);
    } catch (error) {
      console.error("Hubとの接続に失敗しました:", error);
    } finally {
      setIsHubConnecting(false);
    }
  }, []);

  const handleScanDevices = useCallback(() => {
    setIsScanning(true);
    setTimeout(() => {
      setBleDevices([
        ...bleDevices,
        { name: `新しいデバイス${bleDevices.length + 1}`, status: "未接続" },
      ]);
      setIsScanning(false);
    }, 2000);
  }, [bleDevices]);

  const renderScreen = () => {
    switch (currentScreen) {
      case "home":
        return (
          <div className="space-y-4">
            {[
              { title: "最後の接続", time: "2時間前" },
              { title: "データ同期", time: "昨日" },
              { title: "設定変更", time: "先週" },
              { title: "初回接続", time: "先月" },
              { title: "アプリインストール", time: "2ヶ月前" },
            ].map((item, index) => (
              <Card
                key={index}
                className="cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <h2 className="text-lg font-semibold">{item.title}</h2>
                    <p className="text-sm text-gray-500">{item.time}</p>
                  </div>
                  <Clock className="h-5 w-5 text-gray-400" />
                </CardContent>
              </Card>
            ))}
          </div>
        );
      case "devices":
        return (
          <div className="space-y-4">
            {!isHubConnected && (
              <Alert variant="default">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Hubとの接続が必要です</AlertTitle>
                <AlertDescription>
                  デバイスを表示するには、まずHubとの接続を完了してください。
                  画面右上のボタンからHubに接続できます。
                </AlertDescription>
              </Alert>
            )}
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">BLEデバイス接続状況</h2>
              <Button
                variant="outline"
                size="sm"
                onClick={handleScanDevices}
                disabled={isScanning || !isHubConnected}
              >
                {isScanning ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                {isScanning ? "スキャン中..." : "再スキャン"}
              </Button>
            </div>
            {bleDevices.map((device, index) => (
              <Card
                key={index}
                className="cursor-pointer hover:bg-gray-50 transition-colors"
              >
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <h3 className="text-lg font-semibold">{device.name}</h3>
                    <p className="text-sm text-gray-500">{device.status}</p>
                  </div>
                  <Link className="h-5 w-5 text-gray-400" />
                </CardContent>
              </Card>
            ))}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm p-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">BenTech</h1>
        <div className="flex space-x-2">
          {!isHubConnected ? (
            <Button
              variant="ghost"
              size="icon"
              aria-label="Hubデバイスに接続"
              onClick={handleHubConnect}
              disabled={isHubConnecting}
            >
              {isHubConnecting ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Link className="h-5 w-5" />
              )}
            </Button>
          ) : (
            <>
              <Button
                variant="ghost"
                size="icon"
                aria-label="WiFi接続状況"
                onClick={() => setIsWifiDialogOpen(true)}
                disabled={isWifiLoading}
              >
                {isWifiLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : isWifiConnected ? (
                  <Wifi className="h-5 w-5" />
                ) : (
                  <WifiOff className="h-5 w-5" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                aria-label="通知設定"
                onClick={() => {
                  setIsNotificationLoading(true);
                  setTimeout(() => {
                    setIsNotificationEnabled(!isNotificationEnabled);
                    setIsNotificationLoading(false);
                  }, 1000);
                }}
                disabled={isNotificationLoading}
              >
                {isNotificationLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : isNotificationEnabled ? (
                  <Bell className="h-5 w-5" />
                ) : (
                  <BellOff className="h-5 w-5" />
                )}
              </Button>
            </>
          )}
        </div>
      </header>

      {/* Body - Content */}
      <main className="flex-1 overflow-auto p-4">{renderScreen()}</main>

      {/* Navigation */}
      <nav className="bg-white shadow-sm p-4 flex justify-around">
        <Button
          variant="ghost"
          size="icon"
          aria-label="ホーム"
          onClick={() => setCurrentScreen("home")}
        >
          <Home
            className={`h-6 w-6 ${
              currentScreen === "home" ? "text-primary" : "text-gray-500"
            }`}
          />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          aria-label="デバイス"
          onClick={() => setCurrentScreen("devices")}
        >
          <List
            className={`h-6 w-6 ${
              currentScreen === "devices" ? "text-primary" : "text-gray-500"
            }`}
          />
        </Button>
      </nav>

      {/* WiFi Connection Dialog */}
      <Dialog open={isWifiDialogOpen} onOpenChange={setIsWifiDialogOpen}>
        <DialogContent className="sm:max-w-[425px] rounded-lg">
          <DialogHeader>
            <DialogTitle className="text-center">WiFi接続</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4 px-6">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="ssid" className="text-right">
                SSID
              </Label>
              <Input
                id="ssid"
                value={ssid}
                onChange={(e) => setSsid(e.target.value)}
                className="col-span-3 rounded-md"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="password" className="text-right">
                パスワード
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="col-span-3 rounded-md"
              />
            </div>
          </div>
          <DialogFooter className="px-6 pb-6">
            <Button
              onClick={handleWifiConnect}
              disabled={isWifiLoading}
              className="w-full rounded-md"
            >
              {isWifiLoading ? (
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
              ) : null}
              {isWifiLoading ? "接続中..." : "接続"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
