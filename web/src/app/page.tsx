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
  Pencil,
  Link,
  RefreshCw,
  AlertCircle,
  Settings,
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
import { db } from "@/repository/frontend/firebase";
import {
  collection,
  doc,
  onSnapshot,
  orderBy,
  query,
  Timestamp,
  updateDoc,
} from "firebase/firestore";
import Image, { StaticImageData } from "next/image";
import BananaUnch from "../../public/banana.png";
import KataiUnch from "../../public/katai.png";
import BishaUnch from "../../public/bisha.png";
import KorokoroUnch from "../../public/korokoro.png";

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
    const info = JSON.parse(response);
    console.log("info", info);
    return info;
  }

  private async sendTextByStream(command: number, text: string) {
    if (this.controlChar === undefined) {
      throw Error("controlCharがありません");
    } else if (this.streamChar === undefined) {
      throw Error("streamCharがありません");
    }

    const utf8Encoder = new TextEncoder();
    const msgArray = utf8Encoder.encode(text);

    await this.controlChar.writeValueWithResponse(uint8ToArrayBuffer(command));

    const length = Number(msgArray.length / 20) + 1;
    await this.streamChar.writeValueWithResponse(uint8ToArrayBuffer(length));

    for (let i = 0; i < length; i++) {
      const start = i * 20;
      const end = i == length - 1 ? -1 : start + 20;
      const data = msgArray.slice(start, end);
      await this.streamChar.writeValueWithResponse(data);
    }
  }

  async sendWifiData(ssid: string, password: string) {
    if (this.responseChar === undefined) {
      throw Error("responseCharがありません");
    }

    let success: boolean | null = null;

    const handle = async (event: Event) => {
      // @ts-expect-error
      const value = arrayBufferToUint32(event.target.value.buffer);
      success = value === 1;

      await this.responseChar?.stopNotifications();
      this.responseChar!.removeEventListener(
        "characteristicvaluechanged",
        handle
      );
    };

    await this.responseChar.startNotifications();
    this.responseChar.addEventListener("characteristicvaluechanged", handle);

    const data = {
      ssid,
      password,
    };
    await this.sendTextByStream(1, JSON.stringify(data));

    while (success === null) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // localStorageへの書き込み
    if (success) {
      localStorage.setItem("WIFI_SSID", ssid);
      localStorage.setItem("WIFI_PASSWORD", password);
    }

    return success;
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

    const info = await this.requestInfo();
    return {
      wifiConnected: info["WIFI_CONNECTED"],
      subscription: info["SUBSCRIPTION"],
      connectedDevices: info["CONNECTED_DEVICES"],
    };
  }

  async disconnectWifi() {
    if (this.controlChar === undefined) {
      throw new Error("controlCharがありません");
    }

    await this.controlChar.writeValueWithResponse(uint8ToArrayBuffer(3));
  }

  async sendSubscription() {
    console.log("subscriptionを送信します");
    await this.sendTextByStream(
      4,
      JSON.stringify(notificationManager.getSubscription())
    );
    console.log("subscription送信完了");
  }

  async reScan() {
    const response = await this.requestAndListenStream(5);
    const devices = JSON.parse(response);
    console.log("接続済みのデバイス", devices);
    return devices;
  }
}

class NotificationManager {
  private subscription: PushSubscription | null = null;

  async registerServiceWorker() {
    if (!("serviceWorker" in navigator && "PushManager" in window)) {
      alert("このブラウザは通知に対応していないようです");
      return;
    }

    const registration = await navigator.serviceWorker.register("/sw.js", {
      scope: "/",
      updateViaCache: "none",
    });

    // 既存のsubscription
    this.subscription = await registration.pushManager.getSubscription();
    if (this.subscription === null) {
      this.subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
      });
    }
  }

  getSubscription() {
    return this.subscription;
  }
}

type BenTechDeviceType =
  | "lid-controller"
  | "paper-observer"
  | "auto-flusher"
  | "deodorant";

interface BenTechDevice {
  type: BenTechDeviceType;
  displayName: string;
  description: string;
}

const BenTechDeviceList: BenTechDevice[] = [
  {
    type: "lid-controller",
    displayName: "Lid controller",
    description: "蓋を開け閉めします",
  },
  {
    type: "paper-observer",
    displayName: "Paper observer",
    description: "トイレットペーパーの消費量を観測します",
  },
  {
    type: "auto-flusher",
    displayName: "Auto flusher",
    description: "水を流します",
  },
  {
    type: "deodorant",
    displayName: "Deodorant",
    description: "消臭します",
  },
];

type UnchType = "banana" | "bisha" | "katai" | "korokoro";

interface Unch {
  type: UnchType;
  image: StaticImageData;
  name: String;
}

const unchList: Unch[] = [
  {
    type: "banana",
    image: BananaUnch,
    name: "バナナ",
  },
  {
    type: "katai",
    image: KataiUnch,
    name: "カタイ",
  },
  {
    type: "korokoro",
    image: KorokoroUnch,
    name: "コロコロ",
  },
  {
    type: "bisha",
    image: BishaUnch,
    name: "ビシャビシャ",
  },
];

interface History {
  id: string;
  type: UnchType | null;
  createdAt: Timestamp;
  usedRollCount: number;
  stayingTime: number;
}

function getUnchImage(type: UnchType) {
  switch (type) {
    case "banana":
      return BananaUnch;
    case "bisha":
      return BishaUnch;
    case "katai":
      return KataiUnch;
    case "korokoro":
      return KorokoroUnch;
  }
}

type Data = {
  usedRollCount: number;
  paperNotificationThreshold: number;
};

const hubController = new HubController();
const notificationManager = new NotificationManager();

export default function Component() {
  const [isNotificationDataInitialized, setIsNotificationDataInitialized] =
    useState(false);
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
  const [connectedDevices, setConnectedDevices] = useState<BenTechDeviceType[]>(
    []
  );
  const [history, setHistory] = useState<History[]>([]);
  const [editTargetHistory, setEditTargetHistory] = useState<History | null>(
    null
  );
  const [data, setData] = useState<Data>({
    usedRollCount: 0,
    paperNotificationThreshold: 100,
  });
  const [isSetting, setIsSetting] = useState(false);
  const [paperNotificationThreshold, setPaperNotificationThreshold] =
    useState(5);

  const handleHubConnect = useCallback(async () => {
    setIsHubConnecting(true);

    try {
      const info = await hubController.connect();
      setIsWifiConnected(info.wifiConnected);
      setIsHubConnected(true);
      setIsNotificationEnabled(
        JSON.stringify(notificationManager.getSubscription()) ===
          info.subscription
      );
      setConnectedDevices(info.connectedDevices);
    } catch (error) {
      console.log("Hubとの接続に失敗しました:", error);
    } finally {
      setIsHubConnecting(false);
    }
  }, []);

  const handleWifiConnect = useCallback(async () => {
    if (!ssid || !password) {
      console.log("ssidもしくはpasswordが空です");
      return;
    }
    setIsWifiLoading(true);

    try {
      const success = await hubController.sendWifiData(ssid, password);
      if (!success) throw Error("success = false");
      setIsWifiConnected(true);
      setIsWifiDialogOpen(false);
    } catch (error) {
      console.error("WiFiとの接続に失敗しました:", error);
    } finally {
      setIsWifiLoading(false);
    }
  }, [ssid, password]);

  const handleWifiDisconnect = useCallback(async () => {
    await hubController.disconnectWifi();
    setIsWifiConnected(false);
  }, []);

  const handleNotificationOn = useCallback(async () => {
    setIsNotificationLoading(true);

    try {
      await hubController.sendSubscription();
      setIsNotificationEnabled(true);
    } catch (error) {
      console.log("subscriptionの送信に失敗しました", error);
    } finally {
      setIsNotificationLoading(false);
    }
  }, []);

  const handleScanDevices = useCallback(async () => {
    setIsScanning(true);
    try {
      const connectedDevices = await hubController.reScan();
      setConnectedDevices(connectedDevices);
    } catch (error) {
      console.log("リスキャンに失敗しました", error);
    } finally {
      setIsScanning(false);
    }
  }, []);

  const handleEditHistory = useCallback(async () => {
    if (editTargetHistory === null) return;
    const docRef = doc(db, "histories", editTargetHistory.id);
    await updateDoc(docRef, {
      type: editTargetHistory.type,
      updatedAt: Timestamp.now(),
    });
    setEditTargetHistory(null);
  }, [editTargetHistory]);

  const handlePaperReset = useCallback(async () => {
    const docRef = doc(db, "dev", "data");
    await updateDoc(docRef, {
      usedRollCount: 0,
    });
  }, []);

  const handleSetting = useCallback(async () => {
    const docRef = doc(db, "dev", "data");
    await updateDoc(docRef, {
      paperNotificationThreshold,
    });
    setIsSetting(false);
  }, [paperNotificationThreshold]);

  useEffect(() => {
    const registerServiceWorker = async () => {
      await notificationManager.registerServiceWorker();
      setIsNotificationDataInitialized(true);
    };
    registerServiceWorker();
  }, []);

  useEffect(() => {
    setSsid(localStorage.getItem("WIFI_SSID") || "");
    setPassword(localStorage.getItem("WIFI_PASSWORD") || "");
  }, []);

  // 履歴をリッスン
  useEffect(() => {
    const q = query(collection(db, "histories"), orderBy("createdAt", "desc"));
    const unsub = onSnapshot(q, (querySnapshot) => {
      let history: History[] = [];
      querySnapshot.forEach((doc) => {
        const data = doc.data();
        console.log(data);
        history.push({
          id: doc.id,
          type: data.type,
          createdAt: data.createdAt,
          usedRollCount: data.usedRollCount,
          stayingTime: data.stayingTime,
        });
      });
      setHistory(history);
    });

    return unsub;
  }, []);

  // dev/dataをリッスン
  useEffect(() => {
    const docRef = doc(db, "dev", "data");
    const unsub = onSnapshot(docRef, (doc) => {
      const data = doc.data() as Data;
      setData(data);
      setPaperNotificationThreshold(data.paperNotificationThreshold);
    });

    return unsub;
  }, []);

  const renderScreen = () => {
    switch (currentScreen) {
      case "home":
        return (
          <div className="space-y-4">
            {/* ペーパーを用意しておくよう警告 */}
            {data.usedRollCount >= data.paperNotificationThreshold && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>
                  そろそろトイレットペーパーを準備しておきましょう
                </AlertTitle>
                <AlertDescription>
                  トイレットペーパーを交換したらこちらから
                  <span> </span>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handlePaperReset}
                  >
                    リセット！
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {history.map((h) => {
              const unchImage = h.type === null ? null : getUnchImage(h.type);
              const stayingTime = new Date(h.stayingTime * 1000);

              return (
                <Card
                  key={h.createdAt.seconds}
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                >
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <h2 className="text-lg font-semibold">
                        滞在時間: {stayingTime.getMinutes()}分
                        {stayingTime.getSeconds()}秒
                      </h2>
                      <p className="text-sm text-gray-500">
                        ペーパー消費量:{" "}
                        {h.usedRollCount === null
                          ? "不明"
                          : h.usedRollCount + "ロール"}
                      </p>
                      <p className="text-sm text-gray-500">
                        {new Date(h.createdAt.seconds * 1000).toLocaleString()}
                      </p>
                    </div>
                    {unchImage && (
                      <Image
                        src={unchImage}
                        alt=""
                        className="w-24 object-contain"
                      />
                    )}

                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setEditTargetHistory(h)}
                    >
                      <Pencil className="h-5 w-5" />
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
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
            {connectedDevices.map((connectedDeviceType) => {
              const info = BenTechDeviceList.find(
                (device) => device.type === connectedDeviceType
              );

              return (
                <Card
                  key={info?.type}
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                >
                  <CardContent className="flex items-center justify-between p-4">
                    <div>
                      <h3 className="text-lg font-semibold">
                        {info?.displayName}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {info?.description}
                      </p>
                    </div>
                    <Link className="h-5 w-5 text-gray-400" />
                  </CardContent>
                </Card>
              );
            })}
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
              disabled={!isNotificationDataInitialized || isHubConnecting}
            >
              {!isNotificationDataInitialized || isHubConnecting ? (
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
                onClick={
                  isWifiConnected
                    ? handleWifiDisconnect
                    : () => setIsWifiDialogOpen(true)
                }
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
                onClick={handleNotificationOn}
                disabled={isNotificationLoading || isNotificationEnabled}
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
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSetting(true)}
          >
            <Settings className="h-5 w-5" />
          </Button>
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

      <Dialog open={isSetting} onOpenChange={setIsSetting}>
        <DialogContent className="sm:max-w-[425px] rounded-lg">
          <DialogHeader>
            <DialogTitle>Settings</DialogTitle>
          </DialogHeader>
          <Label htmlFor="paperNotificationThreshold">
            トイレットペーパーの通知を行うロール数
          </Label>
          <form>
            <Input
              id="paperNotificationThreshold"
              type="number"
              min={5}
              max={100}
              value={paperNotificationThreshold}
              onChange={(e) =>
                setPaperNotificationThreshold(Number(e.target.value))
              }
            />
            <div className="flex justify-center mt-4">
              <Button
                type="submit"
                onClick={(e) => {
                  e.preventDefault();
                  handleSetting();
                }}
              >
                編集
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* 履歴編集ダイアログ */}
      <Dialog
        open={editTargetHistory !== null}
        onOpenChange={(enable) => {
          if (!enable) {
            setEditTargetHistory(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-[425px] rounded-xl">
          <DialogHeader>
            <DialogTitle>便のタイプを編集</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-4 place-items-center">
            {unchList.map((unch) => (
              <div key={unch.type} className="w-[100px]">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setEditTargetHistory((prev) => {
                      if (prev === null) return null;
                      let newHistory = structuredClone(prev);
                      newHistory.type = unch.type;
                      return newHistory;
                    });
                  }}
                  className={`p-0 h-auto w-auto ${
                    editTargetHistory?.type === unch.type
                      ? "ring-2 ring-primary ring-offset-2"
                      : ""
                  }`}
                >
                  <Image src={unch.image} alt="" className="rounded-md" />
                </Button>
                <span className="mt-2 text-sm text-center block">
                  {unch.name}
                </span>
              </div>
            ))}
          </div>

          <div className="flex justify-center mt-4">
            <Button onClick={handleEditHistory}>編集</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
