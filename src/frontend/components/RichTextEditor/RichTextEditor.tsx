'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import UnderlineExtension from '@tiptap/extension-underline';
import type { Editor } from '@tiptap/core';
import { Bold, Italic, List, ListOrdered, Sparkles, Underline as UnderlineIcon } from 'lucide-react';
import { htmlToMarkdown, markdownToHtml, normalizeMarkdown, sanitizeEditorHtml } from './markdownSerializer';

export interface RichTextEditorProps {
  content: string;
  onChange: (markdown: string) => void;
  readOnly?: boolean;
  ariaLabelledBy?: string;
  placeholder?: string;
  onFocus?: () => void;
  onBlur?: () => void;
  /** When true, the toolbar is only visible while the editor is focused */
  showToolbarOnFocusOnly?: boolean;
  /** Async function that returns generated markdown to insert into the editor */
  onAiAssist?: () => Promise<string>;
  /** Increment this counter to flash a 2s "Saved ✓" toast in the toolbar */
  saveToastKey?: number;
}

type ToolbarState = {
  bold: boolean;
  italic: boolean;
  underline: boolean;
  bulletList: boolean;
  orderedList: boolean;
};

type ToolbarAction = keyof ToolbarState;

type ToolbarButtonConfig = {
  action: ToolbarAction;
  ariaLabel: string;
  Icon: React.ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
  onClick: (editor: Editor) => void;
};

const DEFAULT_PLACEHOLDER = 'Your answer...';

const EMPTY_TOOLBAR_STATE: ToolbarState = {
  bold: false,
  italic: false,
  underline: false,
  bulletList: false,
  orderedList: false,
};

function editorAttributes(ariaLabelledBy: string | undefined): Record<string, string> {
  const attributes: Record<string, string> = {
    'aria-multiline': 'true',
    class: 'outline-none',
    role: 'textbox',
  };

  if (ariaLabelledBy) {
    attributes['aria-labelledby'] = ariaLabelledBy;
  } else {
    attributes['aria-label'] = 'Rich text editor';
  }

  return attributes;
}

function buildToolbarState(editor: Editor | null): ToolbarState {
  if (!editor) return EMPTY_TOOLBAR_STATE;

  return {
    bold: editor.isActive('bold'),
    italic: editor.isActive('italic'),
    underline: editor.isActive('underline'),
    bulletList: editor.isActive('bulletList'),
    orderedList: editor.isActive('orderedList'),
  };
}

const toolbarButtons: ToolbarButtonConfig[] = [
  {
    action: 'bold',
    ariaLabel: 'Bold',
    Icon: Bold,
    onClick: (editor) => editor.chain().focus().toggleBold().run(),
  },
  {
    action: 'italic',
    ariaLabel: 'Italic',
    Icon: Italic,
    onClick: (editor) => editor.chain().focus().toggleItalic().run(),
  },
  {
    action: 'underline',
    ariaLabel: 'Underline',
    Icon: UnderlineIcon,
    onClick: (editor) => editor.chain().focus().toggleUnderline().run(),
  },
  {
    action: 'bulletList',
    ariaLabel: 'Bullet list',
    Icon: List,
    onClick: (editor) => editor.chain().focus().toggleBulletList().run(),
  },
  {
    action: 'orderedList',
    ariaLabel: 'Numbered list',
    Icon: ListOrdered,
    onClick: (editor) => editor.chain().focus().toggleOrderedList().run(),
  },
];

export function RichTextEditor({
  content,
  onChange,
  readOnly = false,
  ariaLabelledBy,
  placeholder = DEFAULT_PLACEHOLDER,
  onFocus,
  onBlur,
  showToolbarOnFocusOnly = false,
  onAiAssist,
  saveToastKey,
}: RichTextEditorProps) {
  const onChangeRef = useRef(onChange);
  const editorRef = useRef<Editor | null>(null);
  const applyingExternalContentRef = useRef(false);
  const [isFocused, setIsFocused] = useState(false);
  const [isEmpty, setIsEmpty] = useState(content.trim().length === 0);
  const [toolbarState, setToolbarState] = useState<ToolbarState>(EMPTY_TOOLBAR_STATE);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [showSaveToast, setShowSaveToast] = useState(false);
  const prevSaveToastKeyRef = useRef<number | undefined>(undefined);

  const refreshState = useCallback((currentEditor: Editor | null) => {
    setToolbarState(buildToolbarState(currentEditor));
    setIsEmpty(currentEditor?.isEmpty ?? true);
  }, []);

  const editor = useEditor({
    content: markdownToHtml(content),
    editable: !readOnly,
    extensions: [
      StarterKit.configure({
        blockquote: false,
        code: false,
        codeBlock: false,
        heading: false,
        horizontalRule: false,
        link: false,
        strike: false,
        underline: false,
      }),
      UnderlineExtension,
    ],
    immediatelyRender: false,
    editorProps: {
      attributes: editorAttributes(ariaLabelledBy),
      handlePaste: (_view, event) => {
        const html = event.clipboardData?.getData('text/html');
        if (!html) return false;

        const currentEditor = editorRef.current;
        if (!currentEditor) return false;

        event.preventDefault();
        currentEditor.chain().focus().insertContent(sanitizeEditorHtml(html)).run();
        return true;
      },
    },
    onBlur: () => { setIsFocused(false); onBlur?.(); },
    onFocus: () => { setIsFocused(true); onFocus?.(); },
    onSelectionUpdate: ({ editor: currentEditor }) => refreshState(currentEditor),
    onUpdate: ({ editor: currentEditor }) => {
      refreshState(currentEditor);
      if (applyingExternalContentRef.current) return;
      onChangeRef.current(htmlToMarkdown(currentEditor.getHTML()));
    },
  });

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    editorRef.current = editor;
    refreshState(editor);
  }, [editor, refreshState]);

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(!readOnly, false);
  }, [editor, readOnly]);

  useEffect(() => {
    if (!editor) return;
    editor.setOptions({
      editorProps: {
        ...editor.options.editorProps,
        attributes: editorAttributes(ariaLabelledBy),
      },
    });
  }, [ariaLabelledBy, editor]);

  useEffect(() => {
    if (!editor) return;

    const currentMarkdown = htmlToMarkdown(editor.getHTML());
    if (normalizeMarkdown(currentMarkdown) === normalizeMarkdown(content)) return;

    applyingExternalContentRef.current = true;
    editor.commands.setContent(markdownToHtml(content), { emitUpdate: false });
    applyingExternalContentRef.current = false;
    refreshState(editor);
  }, [content, editor, refreshState]);

  // Flash "Saved ✓" toast when saveToastKey increments
  useEffect(() => {
    if (saveToastKey === undefined || saveToastKey === 0) {
      prevSaveToastKeyRef.current = saveToastKey;
      return;
    }
    if (prevSaveToastKeyRef.current === saveToastKey) return;
    prevSaveToastKeyRef.current = saveToastKey;
    setShowSaveToast(true);
    const timer = setTimeout(() => setShowSaveToast(false), 2000);
    return () => clearTimeout(timer);
  }, [saveToastKey]);

  const handleAiAssist = async () => {
    if (!onAiAssist || !editor) return;
    setIsAiLoading(true);
    try {
      const generated = await onAiAssist();
      applyingExternalContentRef.current = true;
      editor.commands.setContent(markdownToHtml(generated), { emitUpdate: false });
      applyingExternalContentRef.current = false;
      onChangeRef.current(generated);
      refreshState(editor);
    } finally {
      setIsAiLoading(false);
    }
  };

  const focusEditor = () => {
    if (!readOnly) {
      editor?.chain().focus().run();
    }
  };

  const showToolbar = !readOnly && (!showToolbarOnFocusOnly || isFocused);

  const containerClassName = [
    'overflow-hidden rounded-lg border bg-card transition-colors',
    isFocused ? 'border-primary-action ring-1 ring-primary-action' : 'border-border-default',
    readOnly ? 'bg-surface-subtle' : 'bg-card',
  ].join(' ');

  const contentClassName = [
    'rich-text-editor-content relative min-h-[120px] text-sm text-text-primary',
    '[&_.ProseMirror]:min-h-[120px]',
    '[&_.ProseMirror]:px-3',
    '[&_.ProseMirror]:py-2',
    '[&_.ProseMirror]:outline-none',
    '[&_.ProseMirror_p]:my-0',
    '[&_.ProseMirror_ul]:list-disc',
    '[&_.ProseMirror_ol]:list-decimal',
    '[&_.ProseMirror_ul]:pl-5',
    '[&_.ProseMirror_ol]:pl-5',
    '[&_.ProseMirror_li]:my-1',
    readOnly ? '[&_.ProseMirror]:cursor-default' : '[&_.ProseMirror]:cursor-text',
  ].join(' ');

  return (
    <div className={containerClassName} data-testid="rich-text-editor">
      {showToolbar && (
        <div
          className="flex items-center gap-1 border-b border-border-default bg-card px-2 py-1.5"
          role="toolbar"
          aria-label="Text formatting"
          // Prevent blur when clicking toolbar buttons
          onMouseDown={(e) => e.preventDefault()}
        >
          {toolbarButtons.map(({ action, ariaLabel, Icon, onClick: handleClick }) => {
            const active = toolbarState[action];
            return (
              <button
                key={action}
                type="button"
                aria-label={ariaLabel}
                aria-pressed={active}
                disabled={!editor}
                onClick={() => {
                  if (editor) {
                    handleClick(editor);
                    refreshState(editor);
                  }
                }}
                className={`
                  inline-flex h-8 w-8 items-center justify-center rounded-md border text-sm transition-colors
                  disabled:cursor-not-allowed disabled:opacity-50
                  focus:outline-none focus:ring-2 focus:ring-primary-action focus:ring-offset-1
                  ${active ? 'border-border-strong bg-surface-subtle text-primary-action' : 'border-transparent bg-card text-text-primary hover:bg-surface-subtle'}
                `.trim()}
              >
                <Icon className="h-4 w-4" aria-hidden />
              </button>
            );
          })}

          {onAiAssist && (
            <>
              <div className="mx-1 h-5 w-px bg-border-default" />
              <button
                type="button"
                aria-label="AI Assist"
                disabled={!editor || isAiLoading}
                onClick={() => void handleAiAssist()}
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-transparent bg-card px-2 text-xs font-medium text-primary-action transition-colors hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isAiLoading ? (
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-primary-action border-t-transparent" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" aria-hidden />
                )}
                {isAiLoading ? 'Generating…' : 'AI Assist'}
              </button>
            </>
          )}

          {showSaveToast && (
            <span className="ml-auto text-xs font-medium text-state-active">
              Saved ✓
            </span>
          )}
        </div>
      )}

      <div className={contentClassName} onClick={focusEditor}>
        {isEmpty && !readOnly && (
          <span className="pointer-events-none absolute left-3 top-2 text-sm text-text-muted">
            {placeholder}
          </span>
        )}
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

export default RichTextEditor;
