import makeWASocket, {
  DisconnectReason,
  jidNormalizedUser,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import QRCode from "qrcode";
import pino from "pino";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

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

function extractText(messageContent) {
  let content = messageContent;

  while (content && typeof content === "object") {
    const text = content.conversation ?? content.extendedTextMessage?.text;
    if (typeof text === "string" && text.trim()) {
      return text.trim();
    }

    content =
      content.ephemeralMessage?.message ??
      content.viewOnceMessage?.message ??
      content.viewOnceMessageV2?.message;
  }

  return null;
}

function getClientId(senderJid) {
  const normalizedJid = jidNormalizedUser(senderJid);
  const separator = normalizedJid.lastIndexOf("@");

  if (separator <= 0) {
    return null;
  }

  const user = normalizedJid.slice(0, separator);
  const server = normalizedJid.slice(separator + 1);
  if (!["s.whatsapp.net", "lid"].includes(server)) {
    return null;
  }

  return `${user}_${server.replace(/\./g, "_")}`;
}

async function handleIncomingMessages(socket, messages) {
  for (const incomingMessage of messages) {
    try {
      if (incomingMessage.key?.fromMe) {
        continue;
      }

      const senderJid = incomingMessage.key?.remoteJid;
      if (typeof senderJid !== "string" || !senderJid) {
        continue;
      }

      const clientId = getClientId(senderJid);
      const message = extractText(incomingMessage.message);
      if (!clientId || !message) {
        continue;
      }

      const agentResponse = await sendToAgent(clientId, message);
      await socket.sendMessage(senderJid, { text: agentResponse });
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
