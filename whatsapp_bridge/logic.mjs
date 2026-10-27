export const MAX_MESSAGE_AGE_SECONDS = 120;
export const BOT_MARKER = "[AI_AGENT_BOT]";

export const MEDIA_TYPES = new Set([
  "imageMessage",
  "audioMessage",
  "videoMessage",
  "stickerMessage",
  "documentMessage",
  "contactMessage",
  "contactsArrayMessage",
  "locationMessage",
]);

export function extractClientId(jid) {
  if (typeof jid !== "string") {
    return "";
  }

  const identifier = jid.split("@", 1)[0].replace(/\D/g, "");
  return identifier;
}

export function identifyClient(jid, displayName = "") {
  return {
    clientId: extractClientId(jid),
    displayName:
      typeof displayName === "string" ? displayName.trim() : "",
  };
}

export function summarizeMessage(message, maxLength = 120) {
  if (typeof message !== "string") {
    return "";
  }

  const cleanedMessage = message.trim().replace(/\s+/g, " ");
  if (!Number.isFinite(maxLength) || maxLength <= 0) {
    return "";
  }

  const lengthLimit = Math.floor(maxLength);
  if (cleanedMessage.length <= lengthLimit) {
    return cleanedMessage;
  }

  if (lengthLimit <= 1) {
    return "…".slice(0, lengthLimit);
  }

  return `${cleanedMessage.slice(0, lengthLimit - 1).trimEnd()}…`;
}

export function hasBotMarker(message) {
  return typeof message === "string" && message.includes(BOT_MARKER);
}

export function addBotMarker(message) {
  if (typeof message !== "string") {
    return "";
  }

  return `${BOT_MARKER} ${message}`;
}

export function isMessageRecent(timestamp) {
  if (
    (typeof timestamp !== "number" && typeof timestamp !== "string") ||
    (typeof timestamp === "string" && timestamp.trim() === "")
  ) {
    return false;
  }

  const timestampSeconds = Number(timestamp);
  if (!Number.isFinite(timestampSeconds)) {
    return false;
  }

  const ageSeconds = Date.now() / 1000 - timestampSeconds;
  return ageSeconds >= 0 && ageSeconds <= MAX_MESSAGE_AGE_SECONDS;
}

export function getMediaType(message) {
  if (!message || typeof message !== "object" || Array.isArray(message)) {
    return null;
  }

  for (const mediaType of MEDIA_TYPES) {
    if (Object.hasOwn(message, mediaType)) {
      return mediaType;
    }
  }

  return null;
}

export function isMediaMessage(message) {
  return getMediaType(message) !== null;
}
