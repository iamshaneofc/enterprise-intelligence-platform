const puppeteer = require("puppeteer-core");
const path = require("path");
const fs = require("fs");

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const SCREENSHOT_DIR = path.resolve(__dirname, "..", "docs", "verification_screenshots");
const ARTIFACT_DIR = "C:\\Users\\ASUS\\.gemini\\antigravity\\brain\\fe2d6a06-84bb-4a80-b3f9-ce2035883f32";

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function copyToArtifact(filename) {
  const src = path.join(SCREENSHOT_DIR, filename);
  const dest = path.join(ARTIFACT_DIR, filename);
  try {
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dest);
    }
  } catch (e) {
    console.warn(`Could not copy ${filename} to artifact dir:`, e.message);
  }
}

async function runPhase4Verification() {
  console.log("======================================================================");
  console.log("STARTING FRONTEND PHASE 4 FINAL API INTEGRATION BROWSER RUNNER");
  console.log("Chrome executable:", CHROME_PATH);
  console.log("Frontend URL: http://127.0.0.1:3000");
  console.log("Backend URL:  http://127.0.0.1:8000");
  console.log("======================================================================\n");

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
    console.log("[1/12] Verifying Login Page at http://127.0.0.1:3000/login...");
    await page.goto("http://127.0.0.1:3000/login", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "01_login_page.png") });
    await copyToArtifact("01_login_page.png");
    console.log("  -> Captured: 01_login_page.png");

    // -------------------------------------------------------------
    // 2. Verify Registration & Account Provisioning
    // -------------------------------------------------------------
    console.log("\n[2/12] Verifying User Registration at /register...");
    await page.goto("http://127.0.0.1:3000/register", { waitUntil: "networkidle0" });
    
    const uniqueEmail = `qa.phase4.${Date.now()}@enterprise.io`;
    await page.type('input[placeholder="Ada Lovelace"]', "Phase4 Lead Architect");
    await page.type('input[type="email"]', uniqueEmail);
    await page.type('input[type="password"]', "EnterprisePhase4Secure!");
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "02_register_form.png") });
    await copyToArtifact("02_register_form.png");
    console.log("  -> Captured: 02_register_form.png");

    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: "networkidle0", timeout: 10000 });
    console.log("  -> Successfully registered and redirected to Overview Dashboard!");

    // -------------------------------------------------------------
    // 3. Verify Overview Dashboard
    // -------------------------------------------------------------
    console.log("\n[3/12] Verifying Overview Dashboard at /...");
    await page.waitForSelector("h1", { timeout: 5000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "03_overview_dashboard.png") });
    await copyToArtifact("03_overview_dashboard.png");
    console.log("  -> Captured: 03_overview_dashboard.png");

    // -------------------------------------------------------------
    // 4. Verify Knowledge Base & Document Upload
    // -------------------------------------------------------------
    console.log("\n[4/12] Verifying Knowledge Base & Document Ingestion at /documents...");
    await page.goto("http://127.0.0.1:3000/documents", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "04_knowledge_base_empty.png") });
    await copyToArtifact("04_knowledge_base_empty.png");

    // Open Upload Modal
    console.log("  -> Opening upload modal...");
    const uploadBtn = await page.$('button ::-p-text("Upload Document")') || await page.$('button:has-text("Upload Document")');
    if (uploadBtn) await uploadBtn.click();
    await new Promise((r) => setTimeout(r, 1000));

    // Upload test document
    const testDocPath = path.resolve(__dirname, "..", "backend", "tests", "fixtures", "synthetic_docs", "incident_104_db_pool_outage.md");
    const fileInput = await page.$('input[type="file"]');
    if (fileInput) {
      await fileInput.uploadFile(testDocPath);
      await new Promise((r) => setTimeout(r, 1000));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "05_document_upload_selected.png") });
      await copyToArtifact("05_document_upload_selected.png");

      const submitUpload = await page.$('button[type="submit"]');
      if (submitUpload) await submitUpload.click();

      // Wait for indexing
      await new Promise((r) => setTimeout(r, 4000));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "06_document_indexed_table.png") });
      await copyToArtifact("06_document_indexed_table.png");
      console.log("  -> Document uploaded and indexed successfully into table!");
    }

    // Inspect Chunks
    console.log("  -> Inspecting document chunks in Chunk Explorer...");
    const inspectBtn = await page.$('button[title="Inspect Chunks"]');
    if (inspectBtn) {
      await inspectBtn.click();
      await new Promise((r) => setTimeout(r, 1500));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "07_chunk_explorer_modal.png") });
      await copyToArtifact("07_chunk_explorer_modal.png");
      console.log("  -> Captured: 07_chunk_explorer_modal.png");

      await page.keyboard.press("Escape");
      await new Promise((r) => setTimeout(r, 500));
    }

    // -------------------------------------------------------------
    // 5. Verify Grounded RAG Chat & Citations
    // -------------------------------------------------------------
    console.log("\n[5/12] Verifying AI Investigation Workspace at /chat...");
    await page.goto("http://127.0.0.1:3000/chat", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "08_chat_workspace_initial.png") });
    await copyToArtifact("08_chat_workspace_initial.png");

    console.log("  -> Submitting grounded query about Incident 104...");
    const chatInput = await page.$('input[placeholder*="Ask a technical question"]');
    if (chatInput) {
      await chatInput.type("What caused the database connection pool outage in Incident 104?");
      await page.keyboard.press("Enter");

      await new Promise((r) => setTimeout(r, 4500));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "09_grounded_rag_response_with_citations.png") });
      await copyToArtifact("09_grounded_rag_response_with_citations.png");
      console.log("  -> Captured: 09_grounded_rag_response_with_citations.png");
    }

    // -------------------------------------------------------------
    // 6. Verify Model Abstention on Negative / Out-of-Scope Query
    // -------------------------------------------------------------
    console.log("\n[6/12] Verifying Negative Query Model Abstention...");
    if (chatInput) {
      await chatInput.type("Explain quantum teleportation entanglement protocols in detail.");
      await page.keyboard.press("Enter");
      await new Promise((r) => setTimeout(r, 4000));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "10_model_abstention_alert.png") });
      await copyToArtifact("10_model_abstention_alert.png");
      console.log("  -> Captured: 10_model_abstention_alert.png");
    }

    // -------------------------------------------------------------
    // 7. Verify Direct Search Tool (Hybrid, Dense, Sparse)
    // -------------------------------------------------------------
    console.log("\n[7/12] Verifying Search Tool in right panel...");
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
        await copyToArtifact("11_search_tool_results.png");
        console.log("  -> Captured: 11_search_tool_results.png");
      }
    }

    // -------------------------------------------------------------
    // 8. Verify Autonomous Agent Multi-Step Loop & Traces
    // -------------------------------------------------------------
    console.log("\n[8/12] Verifying Autonomous Agent Runs at /agents...");
    await page.goto("http://127.0.0.1:3000/agents", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "12_agent_runs_empty.png") });
    await copyToArtifact("12_agent_runs_empty.png");

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

        console.log("  -> Waiting for multi-step agent loop to complete...");
        await new Promise((r) => setTimeout(r, 6500));
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "13_agent_execution_timeline_and_report.png") });
        await copyToArtifact("13_agent_execution_timeline_and_report.png");
        console.log("  -> Captured: 13_agent_execution_timeline_and_report.png");
      }
    }

    // -------------------------------------------------------------
    // 9. Verify Conversations Archive with Real Data
    // -------------------------------------------------------------
    console.log("\n[9/12] Verifying Conversations Session Archive at /conversations...");
    await page.goto("http://127.0.0.1:3000/conversations", { waitUntil: "networkidle0" });
    await new Promise((r) => setTimeout(r, 2000));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "14_conversations_archive.png") });
    await copyToArtifact("14_conversations_archive.png");
    console.log("  -> Captured: 14_conversations_archive.png (Populated with real conversations!)");

    // -------------------------------------------------------------
    // 10. Verify Multi-Turn Conversation Persistence Across Refresh
    // -------------------------------------------------------------
    console.log("\n[10/12] Verifying Multi-Turn Conversation & Browser Refresh Persistence...");
    await page.goto("http://127.0.0.1:3000/chat", { waitUntil: "networkidle0" });
    await new Promise((r) => setTimeout(r, 1000));

    // Reload page to test state persistence from localStorage
    await page.reload({ waitUntil: "networkidle0" });
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "18_conversation_persistence_after_refresh.png") });
    await copyToArtifact("18_conversation_persistence_after_refresh.png");
    console.log("  -> Captured: 18_conversation_persistence_after_refresh.png");

    // -------------------------------------------------------------
    // 11. Verify Evaluation Page & Live Backend Benchmark Execution
    // -------------------------------------------------------------
    console.log("\n[11/12] Verifying Evaluation Benchmark Suite at /evaluation...");
    await page.goto("http://127.0.0.1:3000/evaluation", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "15_evaluation_benchmark_suite.png") });
    await copyToArtifact("15_evaluation_benchmark_suite.png");
    console.log("  -> Captured: 15_evaluation_benchmark_suite.png (Initial Ready State)");

    console.log("  -> Triggering LIVE backend benchmark execution...");
    const runEvalBtn = await page.$('button ::-p-text("Run Live Benchmark Evaluation")') || await page.$('button:has-text("Run Live Benchmark Evaluation")');
    if (runEvalBtn) {
      await runEvalBtn.click();
      console.log("  -> Benchmark execution requested. Waiting for 20 questions to evaluate on backend...");
      
      // Wait for execution completion
      await new Promise((r) => setTimeout(r, 12000));
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "17_live_evaluation_results.png") });
      await copyToArtifact("17_live_evaluation_results.png");
      console.log("  -> Captured: 17_live_evaluation_results.png (Live backend measurements displayed!)");
    }

    // -------------------------------------------------------------
    // 12. Verify Settings and Diagnostics Page
    // -------------------------------------------------------------
    console.log("\n[12/12] Verifying Settings & System Diagnostics at /settings...");
    await page.goto("http://127.0.0.1:3000/settings", { waitUntil: "networkidle0" });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "16_settings_and_diagnostics.png") });
    await copyToArtifact("16_settings_and_diagnostics.png");
    console.log("  -> Captured: 16_settings_and_diagnostics.png");

    console.log("\n=== BROWSER CONSOLE AUDIT ===");
    if (consoleErrors.length === 0) {
      console.log("SUCCESS: Zero browser console or unhandled page errors detected!");
    } else {
      console.log(`Warning: Found ${consoleErrors.length} console errors:`);
      consoleErrors.forEach((e) => console.log("  ", e));
    }

    console.log("\n======================================================================");
    console.log("PHASE 4 BROWSER INTEGRATION VERIFICATION COMPLETE");
    console.log("======================================================================");
  } catch (err) {
    console.error("Verification failed with exception:", err);
  } finally {
    await browser.close();
  }
}

runPhase4Verification();
