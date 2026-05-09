import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type Props = {
  content: string;
  className?: string;
};

/**
 * Renders assistant/user chat text as GitHub-flavored Markdown (tables, lists, code, etc.).
 */
export default function ChatMarkdown({ content, className = '' }: Props) {
  if (!content.trim()) return null;
  return (
    <div className={`chat-md ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
