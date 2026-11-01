import { describe, it, expect } from "vitest";
import { evaluationService, GOLDEN_BENCHMARK_QUESTIONS } from "../services/evaluationService";

describe("Evaluation Service & Benchmark Dataset", () => {
  it("provides exactly 20 golden benchmark questions", () => {
    const dataset = evaluationService.getBenchmarkDataset();
    expect(dataset).toHaveLength(20);
    expect(dataset).toEqual(GOLDEN_BENCHMARK_QUESTIONS);
  });

  it("contains negative questions that must abstain", () => {
    const dataset = evaluationService.getBenchmarkDataset();
    const negativeQuestions = dataset.filter((q) => q.expected_to_abstain);
    expect(negativeQuestions.length).toBe(5);
    expect(negativeQuestions.some((q) => q.question.includes("quantum teleportation"))).toBe(true);
  });

  it("calculates factual dataset statistics without fabricated scores", () => {
    const stats = evaluationService.getBenchmarkStats();
    expect(stats.dataset_size).toBe(20);
    expect(stats.grounded_questions).toBe(15);
    expect(stats.abstention_questions).toBe(5);
    expect(stats.backend_endpoint_available).toBe(true);
  });

  it("exposes live evaluation runner and results methods", () => {
    expect(typeof evaluationService.runEvaluation).toBe("function");
    expect(typeof evaluationService.getLatestResults).toBe("function");
  });
});
