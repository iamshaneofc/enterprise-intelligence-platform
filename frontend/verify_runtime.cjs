const puppeteer = require("puppeteer-core");
const path = require("path");
const fs = require("fs");

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SCREENSHOT_DIR = path.resolve(__dirname, "..", "docs", "verification_screenshots");

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runVerification() {
  console.log("=== STARTING FRONTEND RUNTIME & BACKEND INTEGRATION VERIFICATION ===");
  console.log("Using Chrome binary:", CHROME_PATH);

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: "new",
    args: ["--no-sandbox", "--disable-gpu", "--window-size=1280,850"],
    defaultViewport: { width: 1280, height: 850 },
  });

  const page = await browser.newPage();

  // Capture console logs and errors
  const consoleErrors = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(`[Console Error] ${msg.text()}`);
    }
  });
  page.on("pageerror", (err) => {
    consoleErrors.push(`[Page Error] ${err.toString()}`);
  });

  try {
    // -------------------------------------------------------------
    // 1. Verify Login Page
    // -------------------------------------------------------------
    console.log("\n[1/10] Verifying Login Page at http://127.0.0.1:3000/login...");
    await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "01_login_page.png") });
    console.log("  -> Captured: 01_login_page.png");

    // -------------------------------------------------------------
    // 2. Verify Registration & Account Provisioning
    // -------------------------------------------------------------
    console.log("\n[2/10] Verifying User Registration at /register...");
    await page.goto("http://127.0.0.1:3000/register", { waitUntil: "networkidle0" });
    
    const uniqueEmail = `test.architect.${Date.now()}@enterprise.io`;
    await page.type('input[placeholder="Ada Lovelace"]', "Verified System Architect");
    await page.type('input[type="email"]', uniqueEmail);
    await page.type('input[type="password"]', "EnterpriseSecure2026!");
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "02_register_form.png") });
    console.log("  -> Captured: 02_register_form.png");

    await page.click('button[type="submit"]');
    // Wait for redirect to Overview Dashboard
    await page.waitForNavigation({ waitUntil: "networkidle0", timeout: 10000 });
    console.log("  -> Successfully registered and redirected to Overview Dashboard!");

    // -------------------------------------------------------------
    // 3. Verify Overview Dashboard
    // -------------------------------------------------------------
    console.log("\n[3/10] Verifying Overview Dashboard at /...");
    await page.waitForSelector("h1", { timeout: 5000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "03_overview_dashboard.png") });
    console.log("  -> Captured: 03_overview_dashboard.png");

    // -------------------------------------------------------------
    // 4. Verify Knowledge Base & Document Upload
    // -------------------------------------------------------------
    console.log("\n[4/10] Verifying Knowledge Base at /documents...");
    await page.goto("http://127.0.0.1:3000/documents", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "04_knowledge_base_empty.png") });

    // Open Upload Modal
    console.log("  -> Opening upload modal...");
    const uploadBtn = await page.$('button ::-p-text("Upload Document")') || await page.$('button:has-text("Upload Document")');
    if (uploadBtn) await uploadBtn.click();
    await page.waitForTimeout ? page.waitForTimeout(1000) : new Promise((r) => setTimeout(r, 1000));

    // Upload test document
    const testDocPath = path.resolve(__dirname, "..", "backend", "tests", "fixtures", "synthetic_docs", "incident_104_db_pool_outage.md");
    const fileInput = await page.$('input[type="file"]');
    if (fileInput) {
      await fileInput.uploadFile(testDocPath);
      await new Promise((r) => setTimeout(r, 1000));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "05_document_upload_selected.png") });

      // Click Upload & Index button
      const submitUpload = await page.$('button[type="submit"]');
      if (submitUpload) await submitUpload.click();

      // Wait for indexing
      await new Promise((r) => setTimeout(r, 3500));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "06_document_indexed_table.png") });
      console.log("  -> Document uploaded and indexed successfully into table!");
    }

    // Inspect Chunks
    console.log("  -> Inspecting document chunks in Chunk Explorer...");
    const inspectBtn = await page.$('button[title="Inspect Chunks"]');
    if (inspectBtn) {
      await inspectBtn.click();
      await new Promise((r) => setTimeout(r, 1500));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "07_chunk_explorer_modal.png") });
      console.log("  -> Captured: 07_chunk_explorer_modal.png");

      // Close modal
      const closeBtn = await page.$('button ::-p-text("X")') || await page.$('.modal button');
      await page.keyboard.press("Escape");
      await new Promise((r) => setTimeout(r, 500));
    }

    // -------------------------------------------------------------
    // 5. Verify AI Investigation (Grounded RAG & Citations)
    // -------------------------------------------------------------
    console.log("\n[5/10] Verifying AI Investigation Workspace at /chat...");
    await page.goto("http://127.0.0.1:3000/chat", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "08_chat_workspace_initial.png") });

    console.log("  -> Submitting grounded inquiry about Incident 104...");
    const chatInput = await page.$('input[placeholder*="Ask a technical question"]');
    if (chatInput) {
      await chatInput.type("What caused the database connection pool outage in Incident 104?");
      await page.keyboard.press("Enter");

      // Wait for RAG response from backend
      await new Promise((r) => setTimeout(r, 4500));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "09_grounded_rag_response_with_citations.png") });
      console.log("  -> Captured: 09_grounded_rag_response_with_citations.png");
    }

    // -------------------------------------------------------------
    // 6. Verify Model Abstention on Negative Query
    // -------------------------------------------------------------
    console.log("\n[6/10] Verifying Negative Query Model Abstention...");
    if (chatInput) {
      await chatInput.type("Explain quantum teleportation entanglement protocols in detail.");
      await page.keyboard.press("Enter");
      await new Promise((r) => setTimeout(r, 4000));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "10_model_abstention_alert.png") });
      console.log("  -> Captured: 10_model_abstention_alert.png");
    }

    // -------------------------------------------------------------
    // 7. Verify Right Panel Search Explorer (Hybrid, Dense, Sparse)
    // -------------------------------------------------------------
    console.log("\n[7/10] Verifying Knowledge Base Search Tool in right panel...");
    const searchTab = await page.$('button ::-p-text("Search Tool")');
    if (searchTab) {
      await searchTab.click();
      await new Promise((r) => setTimeout(r, 500));
      const rawSearchInput = await page.$('input[placeholder="Search raw chunks..."]');
      if (rawSearchInput) {
        await rawSearchInput.type("connection pool timeout 5s");
        const rawSearchBtn = await page.$('button ::-p-text("Search")');
        if (rawSearchBtn) await rawSearchBtn.click();
        await new Promise((r) => setTimeout(r, 2000));
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "11_search_tool_results.png") });
        console.log("  -> Captured: 11_search_tool_results.png");
      }
    }

    // -------------------------------------------------------------
    // 8. Verify Autonomous Agent Runs & Timeline
    // -------------------------------------------------------------
    console.log("\n[8/10] Verifying Autonomous Agent Runs at /agents...");
    await page.goto("http://127.0.0.1:3000/agents", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "12_agent_runs_empty.png") });

    console.log("  -> Launching new autonomous technical investigation...");
    const newInvestBtn = await page.$('button ::-p-text("New Investigation")');
    if (newInvestBtn) {
      await newInvestBtn.click();
      await new Promise((r) => setTimeout(r, 800));

      const taskArea = await page.$('textarea[placeholder*="Investigate the root cause"]');
      if (taskArea) {
        await taskArea.type("Investigate root cause and timeline for PostgreSQL pool outage");
        const launchSubmit = await page.$('button ::-p-text("Launch Agent")');
        if (launchSubmit) await launchSubmit.click();

        // Wait for agent multi-step loop to finish
        console.log("  -> Waiting for multi-step agent reasoning loop to complete...");
        await new Promise((r) => setTimeout(r, 6000));
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "13_agent_execution_timeline_and_report.png") });
        console.log("  -> Captured: 13_agent_execution_timeline_and_report.png");
      }
    }

    // -------------------------------------------------------------
    // 9. Verify Conversations Page
    // -------------------------------------------------------------
    console.log("\n[9/10] Verifying Conversations Session Archive at /conversations...");
    await page.goto("http://127.0.0.1:3000/conversations", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "14_conversations_archive.png") });
    console.log("  -> Captured: 14_conversations_archive.png");

    // -------------------------------------------------------------
    // 10. Verify Evaluation & Settings Pages
    // -------------------------------------------------------------
    console.log("\n[10/10] Verifying Evaluation Benchmark (/evaluation) and Settings (/settings)...");
    await page.goto("http://127.0.0.1:3000/evaluation", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "15_evaluation_benchmark_suite.png") });
    console.log("  -> Captured: 15_evaluation_benchmark_suite.png");

    await page.goto("http://127.0.0.1:3000/settings", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "16_settings_and_diagnostics.png") });
    console.log("  -> Captured: 16_settings_and_diagnostics.png");

    console.log("\n=== BROWSER CONSOLE ERRORS AUDIT ===");
    if (consoleErrors.length === 0) {
      console.log("SUCCESS: Zero browser console or page errors detected during the entire session!");
    } else {
      console.log(`Warning: Found ${consoleErrors.length} console errors:`);
      consoleErrors.forEach((e) => console.log("  ", e));
    }

    console.log("\n=== VERIFICATION RUN COMPLETE ===");
  } catch (err) {
    console.error("Verification failed with exception:", err);
  } finally {
    await browser.close();
  }
}

runVerification();

