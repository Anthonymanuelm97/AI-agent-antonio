import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
} from "@whiskeysockets/baileys";
import QRCode from "qrcode";
import pino from "pino";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  createState,
  handleMessage,
  readConfig,
} from "./attention.mjs";

const DISCONNECT_REASONS = {
  408: "Internet connection lost or request timed out",
  428: "Connection was closed",
  515: "Normal restart required after device pairing",
};

const bridgeDirectory = dirname(fileURLToPath(import.meta.url));
const authDirectory = resolve(bridgeDirectory, "session");

export async function startBridge(config = readConfig()) {
  const state = createState();
  let reconnectTimer;
  let reconnectAttempts = 0;

  function scheduleReconnect(delay) {
    if (reconnectTimer) {
      return;
    }

    reconnectTimer = setTimeout(() => {
      reconnectTimer = undefined;
      connectWhatsApp().catch((error) => {
        console.error("WhatsApp connection failed:", error);
        scheduleReconnect(
          Math.min(30_000, 2_000 * 2 ** reconnectAttempts++),
        );
      });
    }, delay);
  }

  async function connectWhatsApp() {
    const { state: authState, saveCreds } =
      await useMultiFileAuthState(authDirectory);
    const socket = makeWASocket({
      auth: authState,
      logger: pino({ level: process.env.LOG_BAILEYS ?? "silent" }),
    });

    socket.ev.on("creds.update", () => {
      saveCreds().catch((error) => {
        console.error(
          "Failed to save WhatsApp authentication credentials:",
          error,
        );
      });
    });

    socket.ev.on(
      "connection.update",
      ({ connection, lastDisconnect, qr }) => {
        if (qr) {
          QRCode.toString(qr, { type: "terminal", small: true })
            .then((terminalQr) => {
              console.log("Scan this QR code with WhatsApp:");
              console.log(terminalQr);
            })
            .catch((error) => {
              console.error("Failed to render the WhatsApp QR code:", error);
            });
          QRCode.toFile(resolve(bridgeDirectory, "qr.png"), qr, {
            width: 400,
          })
            .then(() => {
              console.log(
                "If the QR code looks distorted, scan the saved qr.png file instead.",
              );
            })
            .catch((error) => {
              console.error("Failed to save the WhatsApp QR code:", error);
            });
        }

        if (connection === "open") {
          reconnectAttempts = 0;
          console.log(`WhatsApp bridge connected as ${socket.user?.id}.`);
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

          if (statusCode === DisconnectReason.connectionReplaced) {
            console.error(
              "Another WhatsApp bridge instance is connected with this account; reconnect was not attempted.",
            );
            return;
          }

          if (statusCode === DisconnectReason.forbidden) {
            console.error(
              "WhatsApp rejected the connection (403); reconnect was not attempted.",
            );
            return;
          }

          const delay =
            statusCode === DisconnectReason.restartRequired
              ? 0
              : Math.min(30_000, 2_000 * 2 ** reconnectAttempts++);
          console.error(
            `WhatsApp connection closed (status ${statusCode ?? "unknown"}: ${reasonMessage}${disconnectMessage ? `: ${disconnectMessage}` : ""}). Retrying in ${delay / 1000} seconds.`,
          );
          scheduleReconnect(delay);
        }
      },
    );

    socket.ev.on("messages.upsert", ({ messages, type }) => {
      for (const message of messages) {
        void handleMessage(socket, message, type, state, config).catch(
          (error) => {
            console.error(
              "Failed to process an incoming WhatsApp message:",
              error,
            );
          },
        );
      }
    });
  }

  await connectWhatsApp();
}

const isEntryPoint =
  process.argv[1] &&
  pathToFileURL(resolve(process.argv[1])).href === import.meta.url;

if (isEntryPoint) {
  startBridge().catch((error) => {
    console.error("Could not start the WhatsApp bridge:", error.message);
    process.exitCode = 1;
  });
}
