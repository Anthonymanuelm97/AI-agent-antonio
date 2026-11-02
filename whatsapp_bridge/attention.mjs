import { jidNormalizedUser } from "@whiskeysockets/baileys";
import {
  getMediaType,
  hasBotMarker,
  identifyClient,
  isMediaMessage,
  isMessageRecent,
} from "./logic.mjs";

export function readConfig() {
  const apiBaseUrl = process.env.API_BASE_URL?.trim().replace(/\/+$/, "");
  const bridgeToken = process.env.BRIDGE_TOKEN?.trim();

  if (!apiBaseUrl) {
    throw new Error(
      "API_BASE_URL must be set before starting the WhatsApp bridge.",
    );
  }
  if (!bridgeToken) {
    throw new Error("BRIDGE_TOKEN is not configured.");
  }

  const parsedApiUrl = new URL(apiBaseUrl);
  if (!["http:", "https:"].includes(parsedApiUrl.protocol)) {
    throw new Error("API_BASE_URL must use HTTP or HTTPS.");
  }

  return { apiBaseUrl, bridgeToken };
}

export function createState() {
  return {
    sentMessages: new Set(),
    allowedMessages: new Set(),
  };
}

async function sendToAgent(clientId, message, config) {
  const response = await fetch(`${config.apiBaseUrl}/whatsapp/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Bridge-Token": config.bridgeToken,
    },
    body: JSON.stringify({ client_id: clientId, message }),
  });

  if (!response.ok) {
    throw new Error(
      `FastAPI rejected the WhatsApp request with HTTP ${response.status}.`,
    );
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

export async function handleMessage(socket, message, type, state, config) {
  const senderJid = message.key?.remoteJid;
  const messageId = message.key?.id;
  const normalizedSenderJid =
    typeof senderJid === "string" ? jidNormalizedUser(senderJid) : "";
  const senderServer = normalizedSenderJid.split("@").at(-1);
  const client = identifyClient(normalizedSenderJid, message.pushName);
  const timestampValue =
    message.messageTimestamp?.toString?.() ?? message.messageTimestamp;
  const parsedTimestamp = Number(timestampValue);
  const timestamp = Number.isFinite(parsedTimestamp) ? parsedTimestamp : null;
  const messageContent = unwrapMessageContent(message.message);
  const text = extractText(messageContent);
  const context = {
    senderJid,
    clientId: client.clientId,
    timestamp,
    text,
    mediaType: getMediaType(messageContent),
    isMedia: isMediaMessage(messageContent),
    isRecent: isMessageRecent(timestamp),
    hasBotMarker: hasBotMarker(text),
    fromMe: message.key?.fromMe === true,
  };

  if (
    context.fromMe ||
    typeof messageId !== "string" ||
    !messageId ||
    state.sentMessages.has(messageId) ||
    state.allowedMessages.has(messageId) ||
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
    return;
  }

  state.allowedMessages.add(messageId);

  const agentResponse = await sendToAgent(
    context.clientId,
    context.text,
    config,
  );
  const sentMessage = await socket.sendMessage(context.senderJid, {
    text: agentResponse,
  });
  const sentMessageId = sentMessage?.key?.id;
  if (typeof sentMessageId === "string" && sentMessageId) {
    state.sentMessages.add(sentMessageId);
  }
}
