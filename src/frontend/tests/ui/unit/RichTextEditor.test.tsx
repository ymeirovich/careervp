import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { RichTextEditor } from '../../../components/RichTextEditor';

function emptyClientRects(): DOMRectList {
  return {
    item: () => null,
    length: 0,
    [Symbol.iterator]: function* iterator() {
      return;
    },
  } as DOMRectList;
}

function emptyBoundingRect(): DOMRect {
  return new DOMRect(0, 0, 0, 0);
}

function renderEditor(
  props: Partial<React.ComponentProps<typeof RichTextEditor>> = {},
) {
  const onChange = props.onChange ?? vi.fn();

  render(
    <RichTextEditor
      content=""
      onChange={onChange}
      placeholder="Your answer..."
      {...props}
    />,
  );

  return { onChange };
}

function pasteHtml(target: HTMLElement, html: string) {
  fireEvent.paste(target, {
    clipboardData: {
      getData: (type: string) => (type === 'text/html' ? html : ''),
    },
  });
}

describe('RichTextEditor', () => {
  beforeAll(() => {
    Object.defineProperty(Element.prototype, 'getClientRects', {
      configurable: true,
      value: emptyClientRects,
    });
    Object.defineProperty(Range.prototype, 'getClientRects', {
      configurable: true,
      value: emptyClientRects,
    });
    Object.defineProperty(Range.prototype, 'getBoundingClientRect', {
      configurable: true,
      value: emptyBoundingRect,
    });
    Object.defineProperty(Text.prototype, 'getClientRects', {
      configurable: true,
      value: emptyClientRects,
    });
    Object.defineProperty(Text.prototype, 'getBoundingClientRect', {
      configurable: true,
      value: emptyBoundingRect,
    });
  });

  it('renders an empty editor with placeholder and toolbar', async () => {
    renderEditor();

    expect(screen.getByText('Your answer...')).toBeInTheDocument();
    expect(screen.getByRole('toolbar', { name: 'Text formatting' })).toBeInTheDocument();
    expect(await screen.findByRole('textbox')).toHaveAttribute('aria-multiline', 'true');
  });

  it('renders Markdown and plain text content without storage artifacts', async () => {
    const { rerender } = render(
      <RichTextEditor content="Hello **world**" onChange={vi.fn()} />,
    );

    expect(await screen.findByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('world').tagName).toBe('STRONG');

    rerender(<RichTextEditor content="Plain text answer" onChange={vi.fn()} />);

    expect(await screen.findByText('Plain text answer')).toBeInTheDocument();
    expect(screen.queryByText('**')).not.toBeInTheDocument();
  });

  it.each([
    ['Bold', 'bold'],
    ['Italic', 'italic'],
    ['Underline', 'underline'],
    ['Bullet list', 'bulletList'],
    ['Numbered list', 'orderedList'],
  ])('toggles the %s toolbar action', async (label, activeKey) => {
    renderEditor();

    const textbox = await screen.findByRole('textbox');
    fireEvent.click(textbox);

    const button = screen.getByRole('button', { name: label });
    fireEvent.click(button);

    await waitFor(() => expect(button).toHaveAttribute('aria-pressed', 'true'));
    expect(screen.getByTestId('rich-text-editor').textContent).not.toContain(activeKey);
  });

  it('serializes edited content to Markdown through onChange', async () => {
    const { onChange } = renderEditor();

    const textbox = await screen.findByRole('textbox');
    pasteHtml(textbox, '<p>Hello <strong>world</strong></p><ul><li>First</li></ul>');

    await waitFor(() => {
      expect(onChange).toHaveBeenLastCalledWith(expect.stringContaining('Hello **world**'));
    });
    expect(onChange).toHaveBeenLastCalledWith(expect.stringContaining('- First'));
  });

  it('sanitizes pasted HTML while preserving allowed formatting and lists', async () => {
    const { onChange } = renderEditor();

    const textbox = await screen.findByRole('textbox');
    pasteHtml(
      textbox,
      '<h1>Heading</h1><p><strong>Bold</strong> <em>Italic</em> <a href="https://example.com">Link</a></p><img src="/x.png" alt="bad"><table><tr><td>Cell</td></tr></table><ol><li>One</li></ol>',
    );

    await waitFor(() => expect(onChange).toHaveBeenCalled());

    const latestMarkdown = vi.mocked(onChange).mock.calls.at(-1)?.[0] ?? '';
    expect(latestMarkdown).toContain('Heading');
    expect(latestMarkdown).toContain('**Bold**');
    expect(latestMarkdown).toContain('*Italic*');
    expect(latestMarkdown).toContain('Link');
    expect(latestMarkdown).toContain('Cell');
    expect(latestMarkdown).toContain('1. One');
    expect(latestMarkdown).not.toContain('<a');
    expect(latestMarkdown).not.toContain('<img');
    expect(latestMarkdown).not.toContain('<table');
  });

  it('supports controlled value updates without emitting a synthetic change', async () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <RichTextEditor content="Initial answer" onChange={onChange} />,
    );

    expect(await screen.findByText('Initial answer')).toBeInTheDocument();

    rerender(<RichTextEditor content="Updated **answer**" onChange={onChange} />);

    expect(await screen.findByText('Updated')).toBeInTheDocument();
    expect(screen.getByText('answer').tagName).toBe('STRONG');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('hides the toolbar and disables editing in read-only mode and transitions back', async () => {
    const { rerender } = render(
      <RichTextEditor content="Saved answer" onChange={vi.fn()} readOnly />,
    );

    const textbox = await screen.findByRole('textbox');
    expect(screen.queryByRole('toolbar')).not.toBeInTheDocument();
    expect(textbox).toHaveAttribute('contenteditable', 'false');

    rerender(<RichTextEditor content="Saved answer" onChange={vi.fn()} readOnly={false} />);

    expect(await screen.findByRole('toolbar')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('textbox')).toHaveAttribute('contenteditable', 'true'));
  });

  it('applies ARIA labels and focus styling', async () => {
    renderEditor({ ariaLabelledBy: 'answer-label' });

    const textbox = await screen.findByRole('textbox');
    expect(textbox).toHaveAttribute('aria-labelledby', 'answer-label');

    for (const label of ['Bold', 'Italic', 'Underline', 'Bullet list', 'Numbered list']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }

    fireEvent.focus(textbox);
    await waitFor(() => expect(screen.getByTestId('rich-text-editor')).toHaveClass('ring-1'));
  });
});
