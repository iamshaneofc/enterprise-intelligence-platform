import { describe, it, expect } from "vitest";

describe("Markdown Formatting & Citation Markers", () => {
  it("detects and extracts citation markers [c_0], [c_1] from text", () => {
    const text = "Incident 104 postmortem [c_0] states connections exhausted [c_1].";
    const matches = text.match(/\[c_\d+\]/g);
    expect(matches).toEqual(["[c_0]", "[c_1]"]);
  });

  it("handles code block extraction cleanly", () => {
    const text = "Here is Python code:\n```python\nprint('hello')\n```\nDone.";
    const blocks = text.split(/(```[\s\S]*?```)/g);
    expect(blocks.length).toBe(3);
    expect(blocks[1]).toContain("print('hello')");
  });

  it("identifies model abstention directive correctly", () => {
    const response = "ABSTAIN: insufficient_evidence. No documentation exists.";
    expect(response.startsWith("ABSTAIN: insufficient_evidence")).toBe(true);
  });
});

