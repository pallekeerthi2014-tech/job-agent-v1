const CONFIG = {
  lookbackDays: 30,
  countWindowDays: 7,
  maxThreadsPerCandidate: 50,
  backendBaseUrlProperty: "BACKEND_BASE_URL",
  webhookSecretProperty: "GMAIL_FORWARDING_WEBHOOK_SECRET"
};

function runThinkSuccessForwardingScanner() {
  const backendBaseUrl = getRequiredProperty_(CONFIG.backendBaseUrlProperty).replace(/\/$/, "");
  const webhookSecret = getRequiredProperty_(CONFIG.webhookSecretProperty);
  const targets = fetchTargets_(backendBaseUrl, webhookSecret);
  const events = targets.map((target) => scanCandidate_(target));
  const response = UrlFetchApp.fetch(`${backendBaseUrl}/api/v1/admin/gmail/forwarding-scan`, {
    method: "post",
    contentType: "application/json",
    headers: {
      "X-TSC-Gmail-Webhook-Secret": webhookSecret
    },
    payload: JSON.stringify({ events }),
    muteHttpExceptions: true
  });
  if (response.getResponseCode() >= 300) {
    throw new Error(`Backend update failed: ${response.getResponseCode()} ${response.getContentText()}`);
  }
  return JSON.parse(response.getContentText());
}

function installFifteenMinuteForwardingTrigger() {
  ScriptApp.getProjectTriggers()
    .filter((trigger) => trigger.getHandlerFunction() === "runThinkSuccessForwardingScanner")
    .forEach((trigger) => ScriptApp.deleteTrigger(trigger));
  ScriptApp.newTrigger("runThinkSuccessForwardingScanner").timeBased().everyMinutes(15).create();
}

function setupForwardingScannerProperties() {
  const properties = PropertiesService.getScriptProperties();
  properties.setProperties({
    BACKEND_BASE_URL: "https://job-agent-backend-production-a463.up.railway.app",
    GMAIL_FORWARDING_WEBHOOK_SECRET: "PASTE_THE_SAME_SECRET_SET_IN_RAILWAY"
  }, false);
}

function fetchTargets_(backendBaseUrl, webhookSecret) {
  const response = UrlFetchApp.fetch(`${backendBaseUrl}/api/v1/admin/gmail/forwarding-targets`, {
    method: "get",
    headers: {
      "X-TSC-Gmail-Webhook-Secret": webhookSecret
    },
    muteHttpExceptions: true
  });
  if (response.getResponseCode() >= 300) {
    throw new Error(`Target fetch failed: ${response.getResponseCode()} ${response.getContentText()}`);
  }
  return JSON.parse(response.getContentText());
}

function scanCandidate_(target) {
  const candidateEmail = String(target.candidate_email || "").toLowerCase();
  const query = `newer_than:${CONFIG.lookbackDays}d "${candidateEmail}"`;
  const threads = GmailApp.search(query, 0, CONFIG.maxThreadsPerCandidate);
  const messages = [];

  threads.forEach((thread) => {
    thread.getMessages().forEach((message) => {
      const raw = message.getRawContent();
      const searchable = `${raw}\n${message.getPlainBody() || ""}\n${message.getSubject() || ""}`.toLowerCase();
      if (searchable.includes(candidateEmail)) {
        messages.push(message);
      }
    });
  });

  messages.sort((a, b) => b.getDate().getTime() - a.getDate().getTime());
  const latest = messages[0] || null;
  const countSince = Date.now() - CONFIG.countWindowDays * 24 * 60 * 60 * 1000;
  const emailCount7Days = messages.filter((message) => message.getDate().getTime() >= countSince).length;

  return {
    candidate_email: candidateEmail,
    last_email_received_at: latest ? latest.getDate().toISOString() : null,
    message_id: latest ? latest.getId() : null,
    subject: latest ? latest.getSubject() : null,
    sender: latest ? latest.getFrom() : null,
    email_count_7_days: emailCount7Days
  };
}

function getRequiredProperty_(name) {
  const value = PropertiesService.getScriptProperties().getProperty(name);
  if (!value) throw new Error(`Missing script property: ${name}`);
  return value;
}
