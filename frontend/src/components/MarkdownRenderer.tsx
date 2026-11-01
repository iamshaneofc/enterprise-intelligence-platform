import React, { useState } from "react";
import { Check, Copy } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (marker: string) => void;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  onCitationClick,
  className = "",
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopyCode = (codeText: string, index: number) => {
    navigator.clipboard.writeText(codeText);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Helper to render text with clickable citation markers like [c_0], [c_1]
  const renderFormattedText = (text: string) => {
    // Regex matching [c_0], [c_1], etc.
    const parts = text.split(/(\[c_\d+\])/g);

    return parts.map((part, i) => {
      if (/^\[c_\d+\]$/.test(part)) {
        return (
          <button
            key={i}
            onClick={() => onCitationClick && onCitationClick(part)}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 text-[11px] font-mono font-semibold rounded bg-blue-100 text-blue-700 hover:bg-blue-200 border border-blue-200 transition-colors cursor-pointer select-none align-baseline"
            title={`View evidence source ${part}`}
          >
            {part}
          </button>
        );
      }

      // Inline code `code`
      const inlineCodeParts = part.split(/(`[^`]+`)/g);
      return inlineCodeParts.map((subPart, j) => {
        if (subPart.startsWith("`") && subPart.endsWith("`") && subPart.length > 2) {
          return (
            <code
              key={`${i}-${j}`}
              className="px-1.5 py-0.5 rounded bg-slate-100 font-mono text-xs text-rose-600 border border-slate-200"
            >
              {subPart.slice(1, -1)}
            </code>
          );
        }

        // Bold **text**
        const boldParts = subPart.split(/(\*\*[^*]+\*\*)/g);
        return boldParts.map((bPart, k) => {
          if (bPart.startsWith("**") && bPart.endsWith("**") && bPart.length > 4) {
            return (
              <strong key={`${i}-${j}-${k}`} className="font-semibold text-slate-900">
                {bPart.slice(2, -2)}
              </strong>
            );
          }
          return bPart;
        });
      });
    });
  };

  // Split into paragraphs or code blocks
  const blocks = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className={`space-y-3 text-sm text-slate-800 leading-relaxed font-sans ${className}`}>
      {blocks.map((block, blockIdx) => {
        if (block.startsWith("```") && block.endsWith("```")) {
          // Code block
          const lines = block.slice(3, -3).split("\n");
          const language = lines[0].trim() || "plaintext";
          const codeText = lines.slice(1).join("\n").replace(/\n$/, "");

          return (
            <div
              key={blockIdx}
              className="my-3 rounded-lg border border-slate-700/80 bg-slate-900 text-slate-100 overflow-hidden font-mono text-xs shadow-sm"
            >
              <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-800/80 border-b border-slate-700 text-slate-400 select-none">
                <span className="text-[11px] font-medium tracking-wide uppercase">
                  {language}
                </span>
                <button
                  onClick={() => handleCopyCode(codeText, blockIdx)}
                  className="flex items-center gap-1 hover:text-slate-200 transition-colors text-xs"
                >
                  {copiedIndex === blockIdx ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-400 text-[11px]">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span className="text-[11px]">Copy</span>
                    </>
                  )}
                </button>
              </div>
              <div className="p-3.5 overflow-x-auto">
                <pre className="m-0 leading-normal">{codeText}</pre>
              </div>
            </div>
          );
        }

        // Regular markdown text: process lines
        const lines = block.split("\n");
        return (
          <div key={blockIdx} className="space-y-2">
            {lines.map((line, lineIdx) => {
              const trimmed = line.trim();
              if (!trimmed) return null;

              if (trimmed.startsWith("### ")) {
                return (
                  <h4 key={lineIdx} className="text-sm font-bold text-slate-900 mt-3 mb-1">
                    {renderFormattedText(trimmed.slice(4))}
                  </h4>
                );
              }
              if (trimmed.startsWith("## ")) {
                return (
                  <h3 key={lineIdx} className="text-base font-bold text-slate-900 mt-4 mb-1">
                    {renderFormattedText(trimmed.slice(3))}
                  </h3>
                );
              }
              if (trimmed.startsWith("# ")) {
                return (
                  <h2 key={lineIdx} className="text-lg font-bold text-slate-900 mt-4 mb-2">
                    {renderFormattedText(trimmed.slice(2))}
                  </h2>
                );
              }
              if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                return (
                  <div key={lineIdx} className="flex items-start gap-2 pl-2">
                    <span className="text-blue-500 font-bold shrink-0 leading-relaxed">•</span>
                    <div className="flex-1">{renderFormattedText(trimmed.slice(2))}</div>
                  </div>
                );
              }
              if (/^\d+\.\s/.test(trimmed)) {
                const match = trimmed.match(/^(\d+)\.\s(.*)$/);
                if (match) {
                  return (
                    <div key={lineIdx} className="flex items-start gap-2 pl-2">
                      <span className="text-slate-500 font-semibold shrink-0 text-xs mt-0.5">
                        {match[1]}.
                      </span>
                      <div className="flex-1">{renderFormattedText(match[2])}</div>
                    </div>
                  );
                }
              }

              return (
                <p key={lineIdx} className="leading-relaxed">
                  {renderFormattedText(trimmed)}
                </p>
              );
            })}
          </div>
        );
      })}
    </div>
  );
};

