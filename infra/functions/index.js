/**
 * Import function triggers from their respective submodules:
 *
 * const {onCall} = require("firebase-functions/v2/https");
 * const {onDocumentWritten} = require("firebase-functions/v2/firestore");
 *
 * See a full list of supported triggers at https://firebase.google.com/docs/functions
 */

const { onRequest } = require("firebase-functions/v2/https");
const logger = require("firebase-functions/logger");
const { getFirestore, Timestamp } = require("firebase-admin/firestore");
const { initializeApp } = require("firebase-admin/app");
const { setGlobalOptions } = require("firebase-functions");
const axios = require("axios");

setGlobalOptions({
  region: "asia-northeast1",
});
initializeApp();
const db = getFirestore();

// Create and deploy your first functions
// https://firebase.google.com/docs/functions/get-started

// exports.helloWorld = onRequest((request, response) => {
//   logger.info("Hello logs!", {structuredData: true});
//   response.send("Hello from Firebase!");
// });

exports.saveHistory = onRequest(async (request, response) => {
  response.set("Access-Control-Allow-Headers", "*");
  response.set("Access-Control-Allow-Origin", "*");
  response.set("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS, POST");

  const body = request.body;
  const stayingTime = body["stayingTime"];
  const usedRollCount = body["usedRollCount"] || null;
  const subscription = body["subscription"] || null;

  if (stayingTime === undefined) {
    response.status(400).send(
      `何か値が入ってないよ ${JSON.stringify({
        stayingTime,
      })}`
    );
    return;
  }

  logger.info(
    `履歴の保存を要請されました`,
    request.body,
    {
      stayingTime,
      usedRollCount,
      subscription,
    },
    {
      structedData: true,
    }
  );

  const doc = db.doc("/dev/data");
  const data = await doc.get();

  const addHistory = async () => {
    // 選択中のunch_typeを取得
    let unch_type = null;
    if (data.exists) {
      unch_type = data.data()["unch_type"];
    }

    await db.collection("histories").add({
      // 選択中のうんちタイプを適用
      type: unch_type,
      stayingTime,
      usedRollCount,
      createdAt: Timestamp.now(),
    });

    // うんちタイプをリセット
    await doc.update({ unch_type: null });
  };

  const checkPaperRoll = async () => {
    if (usedRollCount === null) return;

    if (!data.exists) return;

    // 現在の合計消費ロール数・閾値を取得
    const currentUsedRollCount = data.data()["usedRollCount"];
    const paperNotificationThreshold =
      data.data()["paperNotificationThreshold"];

    // 合計消費ロールに新たな消費ロール数を加算
    const newUsedRollCount = currentUsedRollCount + usedRollCount;

    // 新たな合計消費ロール数が閾値を上回っていて、subscriptionを渡されていたら通知
    const sendNotification = async () => {
      if (
        newUsedRollCount >= paperNotificationThreshold &&
        subscription !== null
      ) {
        const url = "https://bentech-web-app.vercel.app/api/sendNotification";
        const data = {
          message: "そろそろトイレットペーパーを準備しておきましょう",
          subscription,
        };
        const headers = {
          "Content-Type": "application/json",
        };

        return await axios.post(url, data, { headers });
      }
    };

    // 消費したトイレットペーパーロール数を更新
    const updateUsedRollCount = async () => {
      await doc.update({ usedRollCount: newUsedRollCount });
    };

    // 各タスクを並列で実行
    await Promise.all([sendNotification(), updateUsedRollCount()]);
  };

  try {
    await Promise.all([addHistory(), checkPaperRoll()]);
    response.status(200).send("complete");
  } catch (error) {
    logger.error(`error発生 ${error}`);
    response.status(500).send(`failed ${error}`);
  }
});
