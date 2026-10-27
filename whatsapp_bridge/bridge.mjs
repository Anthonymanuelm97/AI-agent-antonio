import makeWASocket, {
  DisconnectReason,
  jidNormalizedUser,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import QRCode from "qrcode";
import pino from "pino";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  getMediaType,
  hasBotMarker,
  identifyClient,
  isMediaMessage,
  isMessageRecent,
  summarizeMessage,
} from "./logic.mjs";

const DISCONNECT_REASONS = {
  408: "Internet connection lost or request timed out",
  428: "Connection was closed",
  515: "Normal restart required after device pairing",
};

const bridgeDirectory = dirname(fileURLToPath(import.meta.url));
const authDirectory = resolve(bridgeDirectory, "session");
const apiBaseUrl = process.env.API_BASE_URL?.trim().replace(/\/+$/, "");
let reconnectTimer;

if (!apiBaseUrl) {
  throw new Error("API_BASE_URL must be set before starting the WhatsApp bridge.");
}

const parsedApiUrl = new URL(apiBaseUrl);
if (parsedApiUrl.protocol !== "http:" && parsedApiUrl.protocol !== "https:") {
  throw new Error("API_BASE_URL must use HTTP or HTTPS.");
}

async function sendToAgent(clientId, message) {
  const response = await fetch(`${apiBaseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, message }),
  });

  if (!response.ok) {
    throw new Error(`FastAPI returned HTTP ${response.status}.`);
  }

  const result = await response.json();
  if (typeof result.response !== "string" || !result.response.trim()) {
    throw new Error("FastAPI returned an invalid chat response.");
  }

  return result.response;
}

function unwrapMessageContent(messageContent) {
  let content = messageContent;

  while (content && typeof content === "object") {
    const wrappedContent =
      content.ephemeralMessage?.message ??
      content.viewOnceMessage?.message ??
      content.viewOnceMessageV2?.message;
    if (!wrappedContent) {
      break;
    }

    content = wrappedContent;
  }

  return content;
}

function extractText(messageContent) {
  const content = unwrapMessageContent(messageContent);
  const text = content?.conversation ?? content?.extendedTextMessage?.text;

  return typeof text === "string" && text.trim() ? text.trim() : null;
}

async function handleIncomingMessages(socket, messages) {
  for (const incomingMessage of messages) {
    try {
      const senderJid = incomingMessage.key?.remoteJid;
      const messageId = incomingMessage.key?.id;
      const normalizedSenderJid =
        typeof senderJid === "string" ? jidNormalizedUser(senderJid) : "";
      const senderServer = normalizedSenderJid.split("@").at(-1);
      const client = identifyClient(
        normalizedSenderJid,
        incomingMessage.pushName,
      );
      const timestampValue =
        incomingMessage.messageTimestamp?.toString?.() ??
        incomingMessage.messageTimestamp;
      const parsedTimestamp = Number(timestampValue);
      const timestamp = Number.isFinite(parsedTimestamp)
        ? parsedTimestamp
        : null;
      const messageContent = unwrapMessageContent(incomingMessage.message);
      const text = extractText(messageContent);
      const context = {
        senderJid,
        clientId: client.clientId,
        displayName: client.displayName,
        timestamp,
        text,
        summary: summarizeMessage(text),
        mediaType: getMediaType(messageContent),
        isMedia: isMediaMessage(messageContent),
        isRecent: isMessageRecent(timestamp),
        hasBotMarker: hasBotMarker(text),
        fromMe: incomingMessage.key?.fromMe === true,
      };

      if (
        context.fromMe ||
        typeof messageId !== "string" ||
        !messageId ||
        sentMessages.has(messageId) ||
        allowedMessages.has(messageId) ||
        typeof senderJid !== "string" ||
        !senderJid ||
        senderJid === "status@broadcast" ||
        senderServer === "g.us" ||
        !["s.whatsapp.net", "lid"].includes(senderServer) ||
        !context.clientId ||
        !context.text ||
        context.isMedia ||
        !context.isRecent ||
        context.hasBotMarker
      ) {
        continue;
      }

      allowedMessages.add(messageId);

      const agentResponse = await sendToAgent(context.clientId, context.text);
      const sentMessage = await socket.sendMessage(context.senderJid, {
        text: agentResponse,
      });
      const sentMessageId = sentMessage?.key?.id;
      if (typeof sentMessageId === "string" && sentMessageId) {
        sentMessages.add(sentMessageId);
      }
    } catch (error) {
      console.error("Failed to process an incoming WhatsApp message:", error);
    }
  }
}

function scheduleReconnect() {
  if (reconnectTimer) {
    return;
  }

  reconnectTimer = setTimeout(() => {
    reconnectTimer = undefined;
    connectWhatsApp().catch((error) => {
      console.error("WhatsApp connection failed:", error);
      scheduleReconnect();
    });
  }, 3000);
}

const sentMessages = new Set();
const allowedMessages = new Set();

async function connectWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(authDirectory);
  const socket = makeWASocket({
    auth: state,
    logger: pino({ level: "warn" }),
  });

  socket.ev.on("creds.update", () => {
    saveCreds().catch((error) => {
      console.error("Failed to save WhatsApp authentication credentials:", error);
    });
  });

  socket.ev.on("connection.update", ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      QRCode.toString(qr, { type: "terminal", small: true })
        .then((terminalQr) => {
          console.log("Scan this QR code with WhatsApp:");
          console.log(terminalQr);
        })
        .catch((error) => {
          console.error("Failed to render the WhatsApp QR code:", error);
        });
    }

    if (connection === "open") {
      console.log("WhatsApp bridge connected.");
    }

    if (connection === "close") {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const disconnectMessage = lastDisconnect?.error?.message;
      const reasonMessage =
        DISCONNECT_REASONS[statusCode] ?? "Unknown disconnect reason";
      if (statusCode === DisconnectReason.loggedOut) {
        console.error(
          `WhatsApp logged out this session (${reasonMessage}${disconnectMessage ? `: ${disconnectMessage}` : ""}); reconnect was not attempted.`,
        );
        return;
      }

      console.error(
        `WhatsApp connection closed (status ${statusCode ?? "unknown"}: ${reasonMessage}${disconnectMessage ? `: ${disconnectMessage}` : ""}); reconnecting.`,
      );
      scheduleReconnect();
    }
  });

  socket.ev.on("messages.upsert", ({ messages }) => {
    void handleIncomingMessages(socket, messages);
  });
}

connectWhatsApp().catch((error) => {
  console.error("WhatsApp connection failed:", error);
  scheduleReconnect();
});
