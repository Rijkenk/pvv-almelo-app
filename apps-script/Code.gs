// Ontvangt agendapunten en documenten uit de fractie-app en zet ze in de inzendmap.
// Draait onder het Google-account van Kenneth; insturen vraagt de fractiecode.
const FOLDER_ID = "15jQYsGtz-z2puJSPVKFfXOG3qsJklSdx";
const FRACTIECODE = "VUL-HIER-EEN-CODE-IN";

function doPost(e) {
  try {
    const d = JSON.parse(e.postData.contents);
    if (d.code !== FRACTIECODE) return reply({ok: false, error: "code"});
    const folder = DriveApp.getFolderById(FOLDER_ID);
    const stamp = Utilities.formatDate(new Date(), "Europe/Amsterdam", "yyyy-MM-dd HH.mm");
    const from = String(d.from || "onbekend").slice(0, 40);
    if (d.kind === "agenda") {
      const name = `Agendapunt ${stamp} - ${String(d.title || "").slice(0, 80)} (${from})`;
      folder.createFile(name, String(d.text || "").slice(0, 5000), MimeType.PLAIN_TEXT);
    } else if (d.kind === "document") {
      const bytes = Utilities.base64Decode(d.data);
      const name = `${stamp} - ${from} - ${String(d.filename || "document").slice(0, 120)}`;
      const file = folder.createFile(Utilities.newBlob(bytes, d.mime || "application/octet-stream", name));
      if (d.note) file.setDescription(`Van ${from}: ${String(d.note).slice(0, 500)}`);
    } else {
      return reply({ok: false, error: "soort"});
    }
    return reply({ok: true});
  } catch (err) {
    return reply({ok: false, error: "fout"});
  }
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
