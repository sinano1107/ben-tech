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
const { getFirestore } = require("firebase-admin/firestore");
const { initializeApp } = require("firebase-admin/app");
const { setGlobalOptions } = require("firebase-functions");

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

  logger.info(`履歴の保存を要請されました ${request.body}`, {
    structedData: true,
  });
  await db.collection("histories").add({
    msg: "Hello!",
  });
  response.send("complete");
});
