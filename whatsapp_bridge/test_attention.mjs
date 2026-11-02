import assert from "node:assert/strict";
import {
  createState,
  handleMessage,
  readConfig,
} from "./attention.mjs";
import { BOT_MARKER, MAX_MESSAGE_AGE_SECONDS } from "./logic.mjs";

const originalApiBaseUrl = process.env.API_BASE_URL;
const originalBridgeToken = process.env.BRIDGE_TOKEN;
const originalFetch = globalThis.fetch;
const testConfig = {
  apiBaseUrl: "https://example.test",
  bridgeToken: "test-bridge-token",
};
const requestCalls = [];
const sentMessages = [];
let fetchResponse;
let nextOutgoingMessageId = 0;
let passedTests = 0;

function restoreEnvironmentValue(name, value) {
  if (value === undefined) {
    delete process.env[name];
  } else {
    process.env[name] = value;
  }
}

function createMessage({
  id = "incoming-message",
  senderJid = "18095550000@s.whatsapp.net",
  timestamp = Math.floor(Date.now() / 1000),
  text = "Hello",
  fromMe = false,
  message,
} = {}) {
  return {
    key: { remoteJid: senderJid, id, fromMe },
    messageTimestamp: timestamp,
    pushName: "Test Customer",
    message: message ?? { conversation: text },
  };
}

function createMockSocket() {
  return {
    async sendMessage(jid, content) {
      sentMessages.push({ jid, text: content.text });
      nextOutgoingMessageId += 1;
      return { key: { id: `outgoing-message-${nextOutgoingMessageId}` } };
    },
  };
}

function createFetchResponse({
  ok = true,
  status = 200,
  json = async () => ({ client_id: "test-client", response: "Test agent response" }),
} = {}) {
  return { ok, status, json };
}

async function runTest(name, assertion) {
  await assertion();
  passedTests += 1;
  console.log(`[PASS] ${name}`);
}

const mockFetch = async (url, options) => {
  requestCalls.push({
    url,
    method: options.method,
    headers: options.headers,
    body: options.body,
  });
  return fetchResponse;
};
globalThis.fetch = mockFetch;

try {
  await runTest("readConfig valid configuration", () => {
    const printedOutput = [];
    const originalConsoleMethods = {
      log: console.log,
      info: console.info,
      warn: console.warn,
      error: console.error,
    };

    process.env.API_BASE_URL = `${testConfig.apiBaseUrl}///`;
    process.env.BRIDGE_TOKEN = testConfig.bridgeToken;
    for (const method of Object.keys(originalConsoleMethods)) {
      console[method] = (...values) => printedOutput.push(values.join(" "));
    }

    try {
      assert.deepEqual(readConfig(), testConfig);
      assert.equal(printedOutput.join(" ").includes(testConfig.bridgeToken), false);
    } finally {
      Object.assign(console, originalConsoleMethods);
    }
  });

  await runTest("readConfig missing API_BASE_URL", () => {
    delete process.env.API_BASE_URL;
    process.env.BRIDGE_TOKEN = testConfig.bridgeToken;
    assert.throws(() => readConfig(), /API_BASE_URL must be set/);
  });

  await runTest("readConfig missing BRIDGE_TOKEN", () => {
    process.env.API_BASE_URL = testConfig.apiBaseUrl;
    delete process.env.BRIDGE_TOKEN;
    assert.throws(() => readConfig(), /BRIDGE_TOKEN is not configured/);
  });

  await runTest("readConfig rejects invalid URL protocols", () => {
    process.env.API_BASE_URL = "file:///tmp/api";
    process.env.BRIDGE_TOKEN = testConfig.bridgeToken;
    assert.throws(() => readConfig(), /must use HTTP or HTTPS/);
  });

  await runTest("createState", () => {
    const state = createState();
    assert.ok(state.sentMessages instanceof Set);
    assert.ok(state.allowedMessages instanceof Set);
    assert.equal(state.sentMessages.size, 0);
    assert.equal(state.allowedMessages.size, 0);
  });

  await runTest("valid customer message", async () => {
    requestCalls.length = 0;
    sentMessages.length = 0;
    fetchResponse = createFetchResponse();
    const state = createState();
    const message = createMessage();
    const socket = createMockSocket();

    await handleMessage(socket, message, "notify", state, testConfig);

    assert.ok(state.allowedMessages.has(message.key.id));
    assert.equal(requestCalls.length, 1);
    assert.equal(
      requestCalls[0].url,
      `${testConfig.apiBaseUrl}/whatsapp/chat`,
    );
    assert.equal(requestCalls[0].method, "POST");
    assert.equal(requestCalls[0].headers["X-Bridge-Token"], testConfig.bridgeToken);
    assert.equal(requestCalls[0].headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(requestCalls[0].body), {
      client_id: "18095550000",
      message: "Hello",
    });
    assert.deepEqual(sentMessages, [
      { jid: message.key.remoteJid, text: "Test agent response" },
    ]);
    assert.ok(state.sentMessages.has("outgoing-message-1"));
  });

  await runTest("duplicate incoming message", async () => {
    requestCalls.length = 0;
    sentMessages.length = 0;
    fetchResponse = createFetchResponse();
    const state = createState();
    const message = createMessage({ id: "duplicate-message" });
    const socket = createMockSocket();

    await handleMessage(socket, message, "notify", state, testConfig);
    await handleMessage(socket, message, "notify", state, testConfig);

    assert.equal(requestCalls.length, 1);
    assert.equal(sentMessages.length, 1);
  });

  await runTest("sent-message protection", async () => {
    requestCalls.length = 0;
    sentMessages.length = 0;
    const state = createState();
    state.sentMessages.add("already-sent");

    await handleMessage(
      createMockSocket(),
      createMessage({ id: "already-sent" }),
      "notify",
      state,
      testConfig,
    );

    assert.equal(requestCalls.length, 0);
    assert.equal(sentMessages.length, 0);
  });

  const ignoredMessageCases = [
    ["fromMe filter", { fromMe: true }],
    ["group filter", { senderJid: "120363000000000000@g.us" }],
    ["status filter", { senderJid: "status@broadcast" }],
    ["unsupported sender JID filter", { senderJid: "18095550000@example.net" }],
    [
      "old-message filter",
      {
        timestamp:
          Math.floor(Date.now() / 1000) - MAX_MESSAGE_AGE_SECONDS - 1,
      },
    ],
    [
      "media filter",
      { message: { imageMessage: { caption: "Image caption" } } },
    ],
    [
      "bot-marker filter",
      { text: `Automated response ${BOT_MARKER}` },
    ],
    ["missing-text filter", { message: { extendedTextMessage: {} } }],
  ];

  for (const [name, messageOptions] of ignoredMessageCases) {
    await runTest(name, async () => {
      requestCalls.length = 0;
      sentMessages.length = 0;
      const state = createState();

      await handleMessage(
        createMockSocket(),
        createMessage(messageOptions),
        "notify",
        state,
        testConfig,
      );

      assert.equal(requestCalls.length, 0);
      assert.equal(sentMessages.length, 0);
    });
  }

  await runTest("wrapped WhatsApp text", async () => {
    requestCalls.length = 0;
    sentMessages.length = 0;
    fetchResponse = createFetchResponse();
    const wrappedMessage = createMessage({
      message: {
        ephemeralMessage: {
          message: { extendedTextMessage: { text: "Wrapped hello" } },
        },
      },
    });

    await handleMessage(
      createMockSocket(),
      wrappedMessage,
      "notify",
      createState(),
      testConfig,
    );

    assert.equal(requestCalls.length, 1);
    assert.deepEqual(JSON.parse(requestCalls[0].body), {
      client_id: "18095550000",
      message: "Wrapped hello",
    });
    assert.equal(sentMessages[0].text, "Test agent response");
  });

  await runTest("HTTP failure", async () => {
    requestCalls.length = 0;
    sentMessages.length = 0;
    fetchResponse = createFetchResponse({ ok: false, status: 503 });

    await assert.rejects(
      handleMessage(
        createMockSocket(),
        createMessage({ id: "http-failure" }),
        "notify",
        createState(),
        testConfig,
      ),
      /HTTP 503/,
    );
    assert.equal(requestCalls.length, 1);
    assert.equal(sentMessages.length, 0);
  });

  await runTest("invalid FastAPI response", async () => {
    requestCalls.length = 0;
    sentMessages.length = 0;
    fetchResponse = createFetchResponse({
      json: async () => ({ response: "  " }),
    });

    await assert.rejects(
      handleMessage(
        createMockSocket(),
        createMessage({ id: "invalid-response" }),
        "notify",
        createState(),
        testConfig,
      ),
      /invalid chat response/,
    );
    assert.equal(requestCalls.length, 1);
    assert.equal(sentMessages.length, 0);
  });

  assert.equal(globalThis.fetch, mockFetch);
  console.log("\nNo real network requests were made; FastAPI fetch calls were mocked.");
  console.log("No WhatsApp connection or Baileys socket was created.");
  console.log(`\n${passedTests} tests passed.`);
} finally {
  restoreEnvironmentValue("API_BASE_URL", originalApiBaseUrl);
  restoreEnvironmentValue("BRIDGE_TOKEN", originalBridgeToken);
  if (originalFetch === undefined) {
    delete globalThis.fetch;
  } else {
    globalThis.fetch = originalFetch;
  }
}
