import React, { useState } from 'react';
import { Copy, Check, Printer, Download, RefreshCw, Share2 } from 'lucide-react';
import { ParliamentaryBriefResponse } from '../../types';

interface ResponseActionsProps {
  brief: ParliamentaryBriefResponse;
  onRegenerate: () => void;
  isRegenerating?: boolean;
}

export const ResponseActions: React.FC<ResponseActionsProps> = ({
  brief,
  onRegenerate,
  isRegenerating = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    // Copy the clean markdown brief
    navigator.clipboard.writeText(brief.brief_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    const w = window.open('', '_blank');
    if (!w) return;

    // Convert Markdown tables/headings to clean styled HTML for print
    // To ensure pristine printing, build a clean government document
    w.document.write(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Parliamentary Brief — ${brief.subsidiary} (${brief.period})</title>
  <style>
    @page { margin: 20mm; size: A4 portrait; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      background: #ffffff;
      line-height: 1.6;
      font-size: 11pt;
      margin: 0;
      padding: 20px;
    }
    .header {
      text-align: center;
      border-bottom: 2px solid #881337;
      padding-bottom: 12px;
      margin-bottom: 20px;
    }
    .header h1 {
      font-size: 16pt;
      margin: 0 0 4px 0;
      color: #881337;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .header h2 {
      font-size: 12pt;
      margin: 0 0 4px 0;
      color: #334155;
      font-weight: 600;
    }
    .header h3 {
      font-size: 10pt;
      margin: 0;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .meta-table {
      width: 100%;
      margin-bottom: 20px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 14px;
    }
    .meta-table td {
      padding: 4px 8px;
      font-size: 10pt;
    }
    .meta-label {
      font-weight: bold;
      color: #475569;
      width: 140px;
    }
    h2, h3 {
      color: #0f172a;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
      margin-top: 20px;
      margin-bottom: 10px;
    }
    h3 { font-size: 12pt; color: #881337; }
    p { margin: 8px 0; font-size: 10.5pt; text-align: justify; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;
      font-size: 10pt;
    }
    th {
      background: #f1f5f9;
      color: #1e293b;
      font-weight: 600;
      text-align: left;
      padding: 8px 10px;
      border: 1px solid #cbd5e1;
    }
    td {
      padding: 7px 10px;
      border: 1px solid #cbd5e1;
    }
    ul, ol { margin: 8px 0; padding-left: 20px; }
    li { margin-bottom: 4px; font-size: 10pt; }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      background: #dcfce7;
      color: #166534;
      font-weight: bold;
      font-size: 9pt;
    }
    .footer {
      margin-top: 30px;
      border-top: 1px solid #cbd5e1;
      padding-top: 10px;
      font-size: 8.5pt;
      color: #64748b;
      display: flex;
      justify-content: space-between;
    }
    @media print {
      body { padding: 0; }
      .no-print { display: none; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Government of India</h1>
    <h2>Ministry of Coal</h2>
    <h3>Parliamentary Brief — Lok Sabha / Rajya Sabha</h3>
  </div>

  <table class="meta-table">
    <tr>
      <td class="meta-label">Subject:</td>
      <td><strong>${brief.query}</strong></td>
    </tr>
    <tr>
      <td class="meta-label">Reporting Period:</td>
      <td>${brief.period}</td>
    </tr>
    <tr>
      <td class="meta-label">Subsidiary / Entity:</td>
      <td>${brief.subsidiary}</td>
    </tr>
    <tr>
      <td class="meta-label">Audit Protocol:</td>
      <td><span class="badge">NumberSafe 2.0 Certified — Zero Generative Hallucination</span></td>
    </tr>
  </table>

  <div>
    ${brief.brief_text
      .replace(/^##\s*(.*?)$/gm, '<h2>$1</h2>')
      .replace(/^###\s*(.*?)$/gm, '<h3>$1</h3>')
      .replace(/^####\s*(.*?)$/gm, '<h4>$1</h4>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^\s*\*\s*(.*?)$/gm, '<li>$1</li>')
      .replace(/\|(.+)\|/g, (match) => {
        const cells = match.split('|').filter(c => c.trim().length > 0);
        if (cells.some(c => c.includes('---'))) return '';
        const isHeader = false;
        const tag = isHeader ? 'th' : 'td';
        return '<tr>' + cells.map(c => '<' + tag + '>' + c.trim() + '</' + tag + '>').join('') + '</tr>';
      })
      .replace(/(<tr>.*?<\/tr>)+/gs, '<table>$&</table>')
      .replace(/\n\n/g, '<p></p>')
    }
  </div>

  <div class="footer">
    <span>MineIntel AI Evidence Platform (PS-26023)</span>
    <span>Certified Date: ${new Date().toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
  </div>
</body>
</html>`);
    w.document.close();
    w.focus();
    setTimeout(() => {
      w.print();
    }, 300);
  };

  const handleExport = () => {
    const filename = `parliamentary_brief_${brief.subsidiary}_${brief.period.replace(/\s+/g, '_')}.md`;
    const blob = new Blob([brief.brief_text], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100">
      <button
        onClick={handleCopy}
        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
        title="Copy complete markdown brief"
      >
        {copied ? (
          <>
            <Check className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-emerald-700">Copied!</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5 text-slate-500" />
            <span>Copy Brief</span>
          </>
        )}
      </button>

      <button
        onClick={handlePrint}
        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
        title="Print official Ministry of Coal report"
      >
        <Printer className="w-3.5 h-3.5 text-slate-500" />
        <span>Print Official Brief</span>
      </button>

      <button
        onClick={handleExport}
        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors"
        title="Export as Markdown (.md) file"
      >
        <Download className="w-3.5 h-3.5 text-slate-500" />
        <span>Export Markdown</span>
      </button>

      <button
        onClick={onRegenerate}
        disabled={isRegenerating}
        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors disabled:opacity-50 ml-auto"
        title="Regenerate brief with latest Evidence Ledger facts"
      >
        <RefreshCw className={`w-3.5 h-3.5 text-slate-500 ${isRegenerating ? 'animate-spin' : ''}`} />
        <span>Regenerate</span>
      </button>
    </div>
  );
};
