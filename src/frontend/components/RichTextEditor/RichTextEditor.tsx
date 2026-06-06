'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import UnderlineExtension from '@tiptap/extension-underline';
import type { Editor } from '@tiptap/core';
import { Bold, Italic, List, ListOrdered, Underline as UnderlineIcon } from 'lucide-react';
import { htmlToMarkdown, markdownToHtml, normalizeMarkdown, sanitizeEditorHtml } from './markdownSerializer';

export interface RichTextEditorProps {
  content: string;
  onChange: (markdown: string) => void;
  readOnly?: boolean;
  ariaLabelledBy?: string;
  placeholder?: string;
  onFocus?: () => void;
  onBlur?: () => void;
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
}: RichTextEditorProps) {
  const onChangeRef = useRef(onChange);
  const editorRef = useRef<Editor | null>(null);
  const applyingExternalContentRef = useRef(false);
  const [isFocused, setIsFocused] = useState(false);
  const [isEmpty, setIsEmpty] = useState(content.trim().length === 0);
  const [toolbarState, setToolbarState] = useState<ToolbarState>(EMPTY_TOOLBAR_STATE);

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

  const focusEditor = () => {
    if (!readOnly) {
      editor?.chain().focus().run();
    }
  };

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
      {!readOnly && (
        <div className="flex items-center gap-1 border-b border-border-default bg-card px-2 py-1.5" role="toolbar" aria-label="Text formatting">
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
