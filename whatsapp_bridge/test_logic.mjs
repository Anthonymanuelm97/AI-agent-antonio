import {
  MAX_MESSAGE_AGE_SECONDS,
  BOT_MARKER,
  MEDIA_TYPES,
  extractClientId,
  identifyClient,
  summarizeMessage,
  hasBotMarker,
  addBotMarker,
  isMessageRecent,
  getMediaType,
  isMediaMessage,
} from "./logic.mjs";

const CONTEXT = {
  jid: "18095550000@s.whatsapp.net",
  displayName: "Test Client",
  timestamp: Math.floor(Date.now() / 1000),
  text: "Hello, I would like to know the price of two coffees.",
};

function createMessage({
  text = CONTEXT.text,
  mediaType = "",
  timestamp = CONTEXT.timestamp,
  senderJid = CONTEXT.jid,
  displayName = "",
  botMarked = false,
} = {}) {
  const messageText = botMarked ? addBotMarker(text) : text;
  const content = mediaType
    ? { [mediaType]: {} }
    : { conversation: messageText };

  return {
    key: { remoteJid: senderJid },
    pushName: displayName,
    messageTimestamp: timestamp,
    message: content,
    text: messageText,
  };
}

const TEST_CASES = [
  {
    name: "Normal text message",
    message: createMessage(),
  },
  {
    name: "Old message",
    message: createMessage({
      timestamp:
        CONTEXT.timestamp - MAX_MESSAGE_AGE_SECONDS - 1,
    }),
  },
  {
    name: "Image message",
    message: createMessage({ mediaType: "imageMessage" }),
  },
  {
    name: "Audio message",
    message: createMessage({ mediaType: "audioMessage" }),
  },
  {
    name: "Document message",
    message: createMessage({ mediaType: "documentMessage" }),
  },
  {
    name: "Bot-marked message",
    message: createMessage({ botMarked: true }),
  },
  {
    name: "JID with separators",
    message: createMessage({
      senderJid: "1809.555-0000:12@s.whatsapp.net",
    }),
  },
  {
    name: "Client with display name",
    message: createMessage({ displayName: CONTEXT.displayName }),
  },
  {
    name: "Client without display name",
    message: createMessage({ displayName: "" }),
  },
  {
    name: "Long text",
    message: createMessage({
      text: "This is a very long test message that should be shortened to fit the preview length.",
    }),
  },
];

let passedTests = 0;
let totalTests = 0;

function runTest(name, assertion) {
  totalTests += 1;
  try {
    if (!assertion()) {
      throw new Error("Assertion returned false.");
    }

    passedTests += 1;
    console.log(`[PASS] ${name}`);
  } catch (error) {
    console.error(`[FAIL] ${name}: ${error.message}`);
  }
}

runTest(
  "Client ID extraction",
  () =>
    extractClientId(TEST_CASES[0].message.key.remoteJid) ===
      "18095550000" &&
    extractClientId(TEST_CASES[6].message.key.remoteJid) ===
      "1809555000012",
);
runTest(
  "Client identification",
  () =>
    identifyClient(
      TEST_CASES[7].message.key.remoteJid,
      TEST_CASES[7].message.pushName,
    ).clientId === "18095550000" &&
    identifyClient(
      TEST_CASES[7].message.key.remoteJid,
      TEST_CASES[7].message.pushName,
    ).displayName === CONTEXT.displayName &&
    identifyClient(TEST_CASES[8].message.key.remoteJid).displayName === "",
);
runTest(
  "Recent message detection",
  () => isMessageRecent(TEST_CASES[0].message.messageTimestamp),
);
runTest(
  "Old message detection",
  () => !isMessageRecent(TEST_CASES[1].message.messageTimestamp),
);
runTest(
  "Image, audio, and document media detection",
  () =>
    MEDIA_TYPES.has("imageMessage") &&
    MEDIA_TYPES.has("audioMessage") &&
    MEDIA_TYPES.has("documentMessage") &&
    getMediaType(TEST_CASES[2].message.message) === "imageMessage" &&
    isMediaMessage(TEST_CASES[3].message.message) &&
    getMediaType(TEST_CASES[4].message.message) === "documentMessage",
);
runTest(
  "Text-only message is not media",
  () => !isMediaMessage(TEST_CASES[0].message.message),
);
runTest(
  "Bot marker detection",
  () =>
    TEST_CASES[5].message.text.startsWith(BOT_MARKER) &&
    hasBotMarker(TEST_CASES[5].message.text) &&
    hasBotMarker(addBotMarker("Test reply")) &&
    !hasBotMarker(TEST_CASES[0].message.text),
);
runTest(
  "Message summary whitespace cleanup",
  () =>
    summarizeMessage("  Hello,\tthere.\n How are you?  ") ===
    "Hello, there. How are you?",
);
runTest(
  "Short message remains unchanged",
  () => summarizeMessage("  Short message.  ", 40) === "Short message.",
);
runTest(
  "Long message is shortened with an ellipsis",
  () => {
    const preview = summarizeMessage(TEST_CASES[9].message.text, 30);
    return preview.endsWith("…") && preview.length <= 30;
  },
);

console.log(`\n${passedTests}/${totalTests} tests passed.`);
if (passedTests !== totalTests) {
  process.exitCode = 1;
}
