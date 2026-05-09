import {
  Children,
  isValidElement,
  type ComponentPropsWithoutRef,
  type ReactElement,
  type ReactNode,
} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ChatChartWidget from './ChatChartWidget';

type Props = {
  content: string;
  className?: string;
};

type CodeLikeProps = { className?: string; children?: ReactNode };

function isChartCodeBlock(child: ReactNode): child is ReactElement<CodeLikeProps> {
  if (!isValidElement<CodeLikeProps>(child)) return false;
  const cls = child.props.className;
  return typeof cls === 'string' && /\blanguage-chart\b/.test(cls);
}

function ChatPre(props: ComponentPropsWithoutRef<'pre'>) {
  const { children, className, ...rest } = props;
  const first = Children.toArray(children)[0];
  if (isChartCodeBlock(first)) {
    const text = String(first.props.children ?? '').replace(/\n$/, '');
    return <ChatChartWidget source={text} />;
  }
  return (
    <pre {...rest} className={['chat-md-pre-block', className].filter(Boolean).join(' ')}>
      {children}
    </pre>
  );
}

/**
 * Renders assistant/user chat text as GitHub-flavored Markdown (tables, lists, code, etc.).
 * Fenced blocks with language `chart` embed an interactive chart widget (line, bar, pie).
 */
export default function ChatMarkdown({ content, className = '' }: Props) {
  if (!content.trim()) return null;
  return (
    <div className={`chat-md ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ pre: ChatPre }}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
