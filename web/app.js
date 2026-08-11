import {
  PatcherError,
  buildCandidate,
  inspectSource,
  outputFileName,
  validateManifest,
} from "./patcher-core.mjs";

const ui = {
  fileInput: document.querySelector("#firmware-file"),
  dropZone: document.querySelector("#drop-zone"),
  fileIdle: document.querySelector("#file-idle"),
  fileInfo: document.querySelector("#file-info"),
  fileName: document.querySelector("#file-name"),
  fileSize: document.querySelector("#file-size"),
  sourceHash: document.querySelector("#source-hash"),
  agreement: document.querySelector("#agreement"),
  buildButton: document.querySelector("#build-button"),
  status: document.querySelector("#status"),
  statusIcon: document.querySelector("#status-icon"),
  statusTitle: document.querySelector("#status-title"),
  statusDetail: document.querySelector("#status-detail"),
  result: document.querySelector("#result"),
  resultProfile: document.querySelector("#result-profile"),
  resultHash: document.querySelector("#result-hash"),
  resultOffsets: document.querySelector("#result-offsets"),
  download: document.querySelector("#download-link"),
  copyHash: document.querySelector("#copy-hash"),
};

const profileLabels = {
  fan40C_off37C: "40℃開始 / 37℃停止",
  fan35C_off32C: "35℃開始 / 32℃停止",
};

const errorMessages = {
  SOURCE_SIZE: ["このBINは対象サイズではありません", "475,136バイトのV8.16.9原本だけに対応しています。"],
  SOURCE_HASH: ["対象の原本と一致しません", "ファイル名ではなく内容を照合しました。別バージョンやパッチ済みBINには適用できません。"],
  SOURCE_TRAILER: ["ファームウェア末尾が一致しません", "破損または別形式の可能性があります。生成は中止しました。"],
  SOURCE_BYTES: ["変更対象の命令が一致しません", "既知のV8.16.9原本ではありません。生成は中止しました。"],
  CHANGED_OFFSETS: ["想定外の差分を検出しました", "安全のため候補BINを生成しませんでした。"],
  OUTPUT_HASH: ["生成結果の検証に失敗しました", "ダウンロードは無効化されました。"],
  BROWSER: ["このブラウザでは利用できません", "最新版のChrome、Edge、Safari、Firefoxで開き直してください。"],
  MANIFEST: ["パッチ定義を読み込めません", "ページを再読み込みしてください。"],
  PROFILE: ["冷却設定を確認できません", "設定を選び直してください。"],
};

let manifest;
let sourceBytes;
let sourceFile;
let sourceValid = false;
let downloadUrl;

function selectedProfile() {
  return document.querySelector('input[name="profile"]:checked')?.value;
}

function formatBytes(value) {
  return `${value.toLocaleString("ja-JP")} bytes`;
}

function setStatus(kind, title, detail) {
  ui.status.dataset.kind = kind;
  ui.statusIcon.textContent = kind === "working" ? "…" : kind === "success" ? "✓" : kind === "error" ? "!" : "i";
  ui.statusTitle.textContent = title;
  ui.statusDetail.textContent = detail;
}

function resetResult() {
  ui.result.hidden = true;
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = undefined;
  ui.download.removeAttribute("href");
}

function updateButton() {
  ui.buildButton.disabled = !(manifest && sourceValid && ui.agreement.checked && selectedProfile());
}

function showError(error) {
  const [title, detail] = errorMessages[error instanceof PatcherError ? error.code : ""] ?? [
    "処理を完了できませんでした",
    error?.message || "ページを再読み込みして、もう一度お試しください。",
  ];
  setStatus("error", title, detail);
}

async function loadFile(file) {
  resetResult();
  sourceValid = false;
  sourceBytes = undefined;
  sourceFile = file;
  updateButton();

  if (!file) {
    ui.fileIdle.hidden = false;
    ui.fileInfo.hidden = true;
    setStatus("idle", "原本BINを選択してください", "ファイルはこの端末内だけで処理されます。");
    return;
  }

  ui.fileIdle.hidden = true;
  ui.fileInfo.hidden = false;
  ui.fileName.textContent = file.name;
  ui.fileSize.textContent = formatBytes(file.size);
  ui.sourceHash.textContent = "計算中…";
  setStatus("working", "原本を照合しています", "SHA-256、サイズ、末尾マーカーを確認中です。");

  try {
    sourceBytes = new Uint8Array(await file.arrayBuffer());
    const result = await inspectSource(sourceBytes, manifest);
    ui.sourceHash.textContent = result.sha256;
    sourceValid = true;
    setStatus("success", "V8.16.9原本を確認しました", "すべての原本チェックに合格しました。冷却設定を確認してください。");
  } catch (error) {
    ui.sourceHash.textContent = "不一致";
    showError(error);
  }
  updateButton();
}

async function build() {
  if (!sourceValid || !sourceBytes) return;
  resetResult();
  ui.buildButton.disabled = true;
  setStatus("working", "候補BINを生成しています", "変更前バイトと生成後SHA-256を照合しています。");

  try {
    const profile = selectedProfile();
    const result = await buildCandidate(sourceBytes, manifest, profile);
    const name = outputFileName(profile);
    downloadUrl = URL.createObjectURL(new Blob([result.bytes], { type: "application/octet-stream" }));
    ui.download.href = downloadUrl;
    ui.download.download = name;
    ui.resultProfile.textContent = profileLabels[profile];
    ui.resultHash.textContent = result.sha256;
    ui.resultOffsets.textContent = result.changedOffsets.map((value) => `0x${value.toString(16).toUpperCase()}`).join(", ");
    ui.result.hidden = false;
    setStatus("success", "候補BINの検証が完了しました", "元ファイルは変更されていません。下のボタンから候補BINを保存できます。");
    ui.result.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    showError(error);
  }
  updateButton();
}

ui.fileInput.addEventListener("change", () => loadFile(ui.fileInput.files?.[0]));
ui.agreement.addEventListener("change", updateButton);
document.querySelectorAll('input[name="profile"]').forEach((input) => {
  input.addEventListener("change", () => {
    resetResult();
    updateButton();
  });
});
ui.buildButton.addEventListener("click", build);
ui.copyHash.addEventListener("click", async () => {
  await navigator.clipboard.writeText(ui.resultHash.textContent);
  ui.copyHash.textContent = "コピー済み";
  setTimeout(() => { ui.copyHash.textContent = "SHA-256をコピー"; }, 1600);
});

for (const eventName of ["dragenter", "dragover"]) {
  ui.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    ui.dropZone.dataset.dragging = "true";
  });
}
for (const eventName of ["dragleave", "drop"]) {
  ui.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    delete ui.dropZone.dataset.dragging;
  });
}
ui.dropZone.addEventListener("drop", (event) => loadFile(event.dataTransfer?.files?.[0]));

try {
  const response = await fetch("./profiles.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  manifest = validateManifest(await response.json());
  updateButton();
} catch (error) {
  showError(new PatcherError("MANIFEST", error.message));
}
