import { marked } from 'marked';
import TurndownService from 'turndown';

const INLINE_TAGS = new Set(['strong', 'b', 'em', 'i', 'u', 'br']);
const LIST_TAGS = new Set(['ul', 'ol', 'li']);
const DROP_WITH_CONTENT_TAGS = new Set(['script', 'style', 'iframe', 'object', 'svg', 'canvas', 'video', 'audio', 'img']);
const BLOCK_TAG_PATTERN = /<\/?(p|ul|ol|li)\b/i;

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function serializeChildren(node: Node): string {
  return Array.from(node.childNodes).map((child) => sanitizeNode(child)).join('');
}

function wrapParagraph(content: string): string {
  const trimmed = content.trim();
  if (!trimmed) return '';
  if (BLOCK_TAG_PATTERN.test(trimmed)) return trimmed;
  return `<p>${trimmed}</p>`;
}

function sanitizeNode(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) {
    return escapeHtml(node.textContent ?? '');
  }

  if (node.nodeType !== Node.ELEMENT_NODE) {
    return '';
  }

  const element = node as Element;
  const tagName = element.tagName.toLowerCase();

  if (DROP_WITH_CONTENT_TAGS.has(tagName)) {
    return '';
  }

  if (tagName === 'br') {
    return '<br>';
  }

  const children = serializeChildren(element);

  if (tagName === 'strong' || tagName === 'b') {
    return `<strong>${children}</strong>`;
  }

  if (tagName === 'em' || tagName === 'i') {
    return `<em>${children}</em>`;
  }

  if (tagName === 'u') {
    return `<u>${children}</u>`;
  }

  if (LIST_TAGS.has(tagName)) {
    return `<${tagName}>${children}</${tagName}>`;
  }

  if (tagName === 'p') {
    return `<p>${children}</p>`;
  }

  if (/^h[1-6]$/.test(tagName)) {
    return wrapParagraph(children);
  }

  if (tagName === 'td' || tagName === 'th') {
    return `${children} `;
  }

  if (tagName === 'tr') {
    return `${children}<br>`;
  }

  if (tagName === 'table' || tagName === 'thead' || tagName === 'tbody' || tagName === 'tfoot') {
    return wrapParagraph(children);
  }

  if (INLINE_TAGS.has(tagName)) {
    return children;
  }

  return children;
}

function createTurndownService(): TurndownService {
  const service = new TurndownService({
    bulletListMarker: '-',
    codeBlockStyle: 'fenced',
    emDelimiter: '*',
    headingStyle: 'atx',
  });

  service.addRule('underline', {
    filter: ['u'],
    replacement(content) {
      return `<u>${content}</u>`;
    },
  });

  return service;
}

export function sanitizeEditorHtml(html: string): string {
  const trimmedHtml = html.trim();
  if (!trimmedHtml) return '';

  if (typeof DOMParser === 'undefined') {
    return trimmedHtml;
  }

  const parser = new DOMParser();
  const parsedDocument = parser.parseFromString(`<div>${trimmedHtml}</div>`, 'text/html');
  const sanitized = serializeChildren(parsedDocument.body);

  return wrapParagraph(sanitized);
}

export function markdownToHtml(markdown: string): string {
  const trimmedMarkdown = markdown.trim();
  if (!trimmedMarkdown) return '';

  const html = marked.parse(trimmedMarkdown, {
    async: false,
    breaks: false,
    gfm: true,
  }) as string;

  return sanitizeEditorHtml(html);
}

export function htmlToMarkdown(html: string): string {
  const sanitizedHtml = sanitizeEditorHtml(html);
  if (!sanitizedHtml) return '';

  const markdown = createTurndownService().turndown(sanitizedHtml);

  return markdown
    .split('\n')
    .map((line) => line.replace(/^(\s*[-*+])\s{2,}/, '$1 ').replace(/^(\s*\d+\.)\s{2,}/, '$1 '))
    .map((line) => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function normalizeMarkdown(markdown: string): string {
  return htmlToMarkdown(markdownToHtml(markdown));
}
