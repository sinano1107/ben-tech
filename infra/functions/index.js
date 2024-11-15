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
  const type = body["type"];
  const stayingTime = body["stayingTime"];
  const usedRollCount = body["usedRollCount"];
  const subscription = body["subscription"];

  if (
    type === undefined ||
    stayingTime === undefined ||
    usedRollCount === undefined ||
    subscription === undefined
  ) {
    response.status(400).send(
      `何か値が入ってないよ ${JSON.stringify({
        type,
        stayingTime,
        usedRollCount,
        subscription,
      })}`
    );
    return;
  }

  logger.info(`履歴の保存を要請されました`, request.body, {
    structedData: true,
  });

  const sendNotification = async () => {
    if (subscription === null) {
      logger.info("subscriptionがnullなのでブレイクします");
      return;
    }

    // POSTリクエストのための設定
    const url = "https://bentech-web-app.vercel.app/api/sendNotification";
    const data = {
      message: "cloud functions からの通知",
      subscription,
    }; // POSTするデータ
    const headers = {
      "Content-Type": "application/json",
    };

    return await axios.post(url, data, { headers });
  };

  const addHistory = async () => {
    await db.collection("histories").add({
      type,
      stayingTime,
      usedRollCount,
      createdAT: Timestamp.now(),
    });
  };

  try {
    const [sendNotificationResponse, _] = await Promise.all([
      sendNotification(),
      addHistory(),
    ]);
    response.status(200).send("complete");
  } catch (error) {
    logger.error(`error発生 ${error}`);
    response.status(500).send(`failed ${error}`);
  }
});
