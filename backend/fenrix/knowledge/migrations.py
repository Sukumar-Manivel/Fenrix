"""Hand-written migration recipes. Used when no local LLM is available, and as
few-shot examples when one is. Keys are (from_key, to_key); "native" means the
recommendation is to drop the dependency and use the platform instead."""
from __future__ import annotations

MIGRATIONS: dict[tuple[str, str], dict] = {
    ("npm:moment", "npm:dayjs"): {
        "language": "javascript",
        "summary": "Day.js keeps Moment's API, so most calls change only at the import.",
        "before": """import moment from "moment";

const due = moment(invoice.createdAt).add(30, "days");
console.log(due.format("DD MMM YYYY"));
console.log(moment().isAfter(due) ? "overdue" : "on time");""",
        "after": """import dayjs from "dayjs";

const due = dayjs(invoice.createdAt).add(30, "day");
console.log(due.format("DD MMM YYYY"));
console.log(dayjs().isAfter(due) ? "overdue" : "on time");""",
        "steps": ["npm uninstall moment && npm install dayjs",
                  "Replace imports; unit names become singular (\"days\" → \"day\")",
                  "Load plugins such as utc or relativeTime where you used those features"],
    },
    ("npm:moment", "npm:date-fns"): {
        "language": "javascript",
        "summary": "date-fns uses plain functions on native Date objects.",
        "before": """import moment from "moment";
const label = moment(date).add(7, "days").format("YYYY-MM-DD");""",
        "after": """import { addDays, format } from "date-fns";
const label = format(addDays(date, 7), "yyyy-MM-dd");""",
        "steps": ["npm uninstall moment && npm install date-fns",
                  "Note the format tokens differ: YYYY → yyyy, DD → dd"],
    },
    ("npm:request", "npm:axios"): {
        "language": "javascript",
        "summary": "Replace callback-style request with promise-based axios.",
        "before": """const request = require("request");

request.post({ url: API + "/payments", json: payload }, (err, res, body) => {
  if (err) return done(err);
  done(null, body.id);
});""",
        "after": """const axios = require("axios");

async function createPayment(payload) {
  const { data } = await axios.post(`${API}/payments`, payload, { timeout: 5000 });
  return data.id;
}""",
        "steps": ["npm uninstall request && npm install axios",
                  "Convert callbacks to async/await",
                  "Set an explicit timeout — request had none by default"],
    },
    ("npm:request", "npm:undici"): {
        "language": "javascript",
        "summary": "Node 18+ ships fetch (built on undici); no dependency needed for simple calls.",
        "before": """request({ url, json: true }, (err, res, body) => cb(err, body));""",
        "after": """const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
if (!res.ok) throw new Error(`HTTP ${res.status}`);
const body = await res.json();""",
        "steps": ["Remove request", "Use global fetch (Node 18+) or import { request } from \"undici\""],
    },
    ("npm:left-pad", "native"): {
        "language": "javascript",
        "summary": "String.prototype.padStart has been built into JavaScript since ES2017.",
        "before": """const leftPad = require("left-pad");
const account = leftPad(id, 10, "0");""",
        "after": """const account = String(id).padStart(10, "0");""",
        "steps": ["npm uninstall left-pad", "Replace calls with padStart — no dependency needed"],
    },
    ("npm:ua-parser-js", "npm:bowser"): {
        "language": "javascript",
        "summary": "Bowser is MIT-licensed and covers browser, OS and platform detection.",
        "before": """import { UAParser } from "ua-parser-js";
const { browser, os } = new UAParser(req.headers["user-agent"]).getResult();
audit.log({ browser: browser.name, os: os.name });""",
        "after": """import Bowser from "bowser";
const ua = Bowser.parse(req.headers["user-agent"] ?? "");
audit.log({ browser: ua.browser.name, os: ua.os.name });""",
        "steps": ["npm uninstall ua-parser-js && npm install bowser",
                  "Alternatively pin ua-parser-js to 1.x, which is still MIT-licensed"],
    },
    ("npm:highcharts", "npm:chart.js"): {
        "language": "javascript",
        "summary": "Chart.js is MIT-licensed and covers line, bar, pie and mixed charts.",
        "before": """import Highcharts from "highcharts";
Highcharts.chart("revenue", {
  title: { text: "Revenue" },
  xAxis: { categories: months },
  series: [{ type: "line", name: "Revenue", data: revenue }],
});""",
        "after": """import Chart from "chart.js/auto";
new Chart(document.getElementById("revenue"), {
  type: "line",
  data: { labels: months, datasets: [{ label: "Revenue", data: revenue }] },
  options: { plugins: { title: { display: true, text: "Revenue" } } },
});""",
        "steps": ["npm uninstall highcharts && npm install chart.js",
                  "Change the container from a <div> to a <canvas>"],
    },
    ("npm:event-stream", "native"): {
        "language": "javascript",
        "summary": "Node's built-in stream.pipeline and Transform cover what event-stream was used for.",
        "before": """const es = require("event-stream");
fs.createReadStream(file).pipe(es.split()).pipe(es.map((line, cb) => cb(null, line.toUpperCase() + "\\n"))).pipe(out);""",
        "after": """const { pipeline, Transform } = require("node:stream");
const readline = require("node:readline");

const upper = new Transform({ objectMode: true, transform(line, _enc, cb) { cb(null, line.toUpperCase() + "\\n"); } });
pipeline(readline.createInterface({ input: fs.createReadStream(file) }), upper, out, (err) => err && console.error(err));""",
        "steps": ["npm uninstall event-stream", "Use node:stream — zero third-party code"],
    },
    ("npm:colors", "npm:picocolors"): {
        "language": "javascript",
        "summary": "picocolors has no dependencies and does not patch String.prototype.",
        "before": """require("colors");
console.log("Deploy finished".green);""",
        "after": """const pc = require("picocolors");
console.log(pc.green("Deploy finished"));""",
        "steps": ["npm uninstall colors && npm install picocolors"],
    },
    ("npm:faker", "npm:@faker-js/faker"): {
        "language": "javascript",
        "summary": "@faker-js/faker is the community-maintained continuation of faker.",
        "before": """const faker = require("faker");
const name = faker.name.findName();""",
        "after": """const { faker } = require("@faker-js/faker");
const name = faker.person.fullName();""",
        "steps": ["npm uninstall faker && npm install --save-dev @faker-js/faker"],
    },
    ("npm:node-ipc", "native"): {
        "language": "javascript",
        "summary": "No equivalent library is trustworthy enough, so Fenrix suggests a small in-house IPC helper on node:net.",
        "before": """const ipc = require("node-ipc");
ipc.serve(() => ipc.server.on("job", (data, socket) => ipc.server.emit(socket, "ack", data.id)));
ipc.server.start();""",
        "after": """// ipc.js — minimal newline-delimited JSON IPC over a Unix socket
const net = require("node:net");

function serve(path, handlers) {
  const server = net.createServer((socket) => {
    let buffer = "";
    socket.on("data", (chunk) => {
      buffer += chunk;
      let i;
      while ((i = buffer.indexOf("\\n")) >= 0) {
        const { type, data } = JSON.parse(buffer.slice(0, i));
        buffer = buffer.slice(i + 1);
        const reply = handlers[type]?.(data);
        if (reply !== undefined) socket.write(JSON.stringify(reply) + "\\n");
      }
    });
  });
  return server.listen(path);
}

module.exports = { serve };

// usage
serve("/tmp/jobs.sock", { job: (data) => ({ type: "ack", data: data.id }) });""",
        "steps": ["npm uninstall node-ipc", "Add ipc.js to the codebase and cover it with tests",
                  "Restrict the socket file's permissions to the service user"],
    },
    ("pypi:pymupdf", "pypi:pypdf"): {
        "language": "python",
        "summary": "pypdf is BSD-licensed and handles text extraction, splitting and merging.",
        "before": """import fitz  # PyMuPDF

doc = fitz.open("statement.pdf")
text = "".join(page.get_text() for page in doc)""",
        "after": """from pypdf import PdfReader

reader = PdfReader("statement.pdf")
text = "".join(page.extract_text() or "" for page in reader.pages)""",
        "steps": ["pip uninstall pymupdf && pip install pypdf",
                  "For tables, consider pdfplumber (MIT)"],
    },
    ("pypi:mysqlclient", "pypi:pymysql"): {
        "language": "python",
        "summary": "PyMySQL is MIT-licensed and can stand in for MySQLdb without code changes.",
        "before": """import MySQLdb

conn = MySQLdb.connect(host=HOST, user=USER, passwd=PASSWORD, db="ledger")""",
        "after": """import pymysql
pymysql.install_as_MySQLdb()   # existing `import MySQLdb` code keeps working

conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, database="ledger")""",
        "steps": ["pip uninstall mysqlclient && pip install pymysql",
                  "For Django, call install_as_MySQLdb() in settings or __init__.py"],
    },
    ("pypi:pyqt5", "pypi:pyside6"): {
        "language": "python",
        "summary": "PySide6 is the official LGPL Qt binding; the API is nearly identical.",
        "before": """from PyQt5.QtWidgets import QApplication, QPushButton
from PyQt5.QtCore import pyqtSignal""",
        "after": """from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Signal   # pyqtSignal → Signal""",
        "steps": ["pip uninstall pyqt5 && pip install pyside6",
                  "Rename pyqtSignal/pyqtSlot to Signal/Slot",
                  "Replace app.exec_() with app.exec()"],
    },
    ("maven:com.itextpdf:itextpdf", "maven:org.apache.pdfbox:pdfbox"): {
        "language": "java",
        "summary": "Apache PDFBox is Apache-2.0 licensed and safe for client-facing products.",
        "before": """Document doc = new Document();
PdfWriter.getInstance(doc, new FileOutputStream("statement.pdf"));
doc.open();
doc.add(new Paragraph("Account statement"));
doc.close();""",
        "after": """try (PDDocument doc = new PDDocument()) {
    PDPage page = new PDPage();
    doc.addPage(page);
    try (PDPageContentStream text = new PDPageContentStream(doc, page)) {
        text.beginText();
        text.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 14);
        text.newLineAtOffset(50, 750);
        text.showText("Account statement");
        text.endText();
    }
    doc.save("statement.pdf");
}""",
        "steps": ["Replace com.itextpdf:itextpdf with org.apache.pdfbox:pdfbox 3.x in pom.xml",
                  "For heavy table layouts, consider OpenPDF (LGPL/MPL), which keeps the iText 4 API"],
    },
    ("maven:com.itextpdf:itextpdf", "maven:com.github.librepdf:openpdf"): {
        "language": "java",
        "summary": "OpenPDF is a fork of iText 4 — mostly a package rename.",
        "before": """import com.itextpdf.text.Document;
import com.itextpdf.text.pdf.PdfWriter;""",
        "after": """import com.lowagie.text.Document;
import com.lowagie.text.pdf.PdfWriter;""",
        "steps": ["Swap the Maven dependency for com.github.librepdf:openpdf",
                  "Update imports from com.itextpdf.text to com.lowagie.text"],
    },
    ("maven:mysql:mysql-connector-java", "maven:org.mariadb.jdbc:mariadb-java-client"): {
        "language": "xml",
        "summary": "The MariaDB driver is LGPL and speaks the MySQL protocol.",
        "before": """<dependency>
  <groupId>mysql</groupId>
  <artifactId>mysql-connector-java</artifactId>
  <version>8.0.33</version>
</dependency>
<!-- spring.datasource.url=jdbc:mysql://db:3306/ledger -->""",
        "after": """<dependency>
  <groupId>org.mariadb.jdbc</groupId>
  <artifactId>mariadb-java-client</artifactId>
  <version>3.5.1</version>
</dependency>
<!-- spring.datasource.url=jdbc:mariadb://db:3306/ledger -->""",
        "steps": ["Swap the dependency", "Change the JDBC URL prefix to jdbc:mariadb://"],
    },
    ("go:github.com/hashicorp/terraform", "go:github.com/opentofu/opentofu"): {
        "language": "bash",
        "summary": "OpenTofu is a drop-in, MPL-2.0 replacement for Terraform 1.5.x.",
        "before": """terraform init && terraform plan -out plan.tfplan""",
        "after": """tofu init && tofu plan -out plan.tfplan""",
        "steps": ["Install OpenTofu", "Run tofu init in each workspace; state files are compatible"],
    },
}


def upgrade_snippet(ecosystem: str, name: str, version: str) -> dict:
    if ecosystem == "maven":
        group, artifact = name.split(":", 1) if ":" in name else (name, name)
        return {"language": "xml", "code": f"""<dependency>
  <groupId>{group}</groupId>
  <artifactId>{artifact}</artifactId>
  <version>{version}</version>
</dependency>""", "command": f"mvn versions:use-dep-version -Dincludes={group}:{artifact} -DdepVersion={version}"}
    if ecosystem == "npm":
        return {"language": "bash", "code": f"npm install {name}@{version} --save-exact\nnpm ls {name}   # confirm no older copy remains",
                "command": f"npm install {name}@{version}"}
    if ecosystem == "pypi":
        return {"language": "bash", "code": f"pip install \"{name}=={version}\"\n# requirements.txt\n{name}=={version}",
                "command": f"pip install {name}=={version}"}
    if ecosystem == "deb":
        return {"language": "bash", "code": f"apt-get update && apt-get install --only-upgrade {name}\n# rebuild images from a patched base image",
                "command": f"apt-get install --only-upgrade {name}"}
    return {"language": "bash", "code": f"go get {name}@v{version}", "command": f"go get {name}@v{version}"}
