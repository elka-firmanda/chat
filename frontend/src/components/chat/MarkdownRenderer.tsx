import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import { Copy, Check } from 'lucide-react'

interface MarkdownRendererProps {
  content: string
  className?: string
}

interface CodeProps {
  node?: any
  inline?: boolean
  className?: string
  children?: React.ReactNode
  [key: string]: any
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  const [copiedBlocks, setCopiedBlocks] = useState<Set<number>>(new Set())

  const copyToClipboard = async (text: string, index: number) => {
    await navigator.clipboard.writeText(text)
    setCopiedBlocks(prev => new Set(prev).add(index))
    setTimeout(() => {
      setCopiedBlocks(prev => {
        const next = new Set(prev)
        next.delete(index)
        return next
      })
    }, 2000)
  }

  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ node, inline, className, children, ...props }: CodeProps) {
            const match = /language-(\w+)/.exec(className || '')
            const codeString = String(children).replace(/\n$/, '')
            const index = Math.abs(
              content.slice(0, content.indexOf(codeString)).split('').reduce((a, b) => a + b.charCodeAt(0), 0)
            )

            if (inline) {
              return (
                <code className="px-1.5 py-0.5 bg-muted-foreground/20 rounded text-sm font-mono" {...props}>
                  {children}
                </code>
              )
            }

            return (
              <div className="relative group my-3 rounded-lg overflow-hidden bg-zinc-900 dark:bg-zinc-950 border border-border/50">
                <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-800/50 dark:bg-zinc-900/50 border-b border-border/50">
                  <span className="text-xs text-zinc-400 font-medium uppercase">
                    {match?.[1] || 'text'}
                  </span>
                  <button
                    onClick={() => copyToClipboard(codeString, index)}
                    className="flex items-center gap-1 px-2 py-1 text-xs text-zinc-400 hover:text-foreground hover:bg-zinc-700/50 rounded transition-colors"
                    title="Copy code"
                  >
                    {copiedBlocks.has(index) ? (
                      <>
                        <Check size={14} />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={14} />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 overflow-x-auto">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            )
          },
          pre({ children }) {
            return <>{children}</>
          },
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline break-all"
              >
                {children}
              </a>
            )
          },
          ul({ children }) {
            return <ul className="list-disc list-inside my-2 space-y-1">{children}</ul>
          },
          ol({ children }) {
            return <ol className="list-decimal list-inside my-2 space-y-1">{children}</ol>
          },
          li({ children }) {
            return <li className="text-sm">{children}</li>
          },
          p({ children }) {
            return <p className="my-2 text-sm leading-relaxed">{children}</p>
          },
          h1({ children }) {
            return <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>
          },
          h2({ children }) {
            return <h2 className="text-lg font-bold mt-3 mb-2">{children}</h2>
          },
          h3({ children }) {
            return <h3 className="text-base font-semibold mt-2 mb-1">{children}</h3>
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-primary/30 pl-3 my-2 italic text-muted-foreground">
                {children}
              </blockquote>
            )
          },
          hr() {
            return <hr className="my-4 border-border/50" />
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-3">
                <table className="min-w-full border border-border/50 rounded-lg text-sm">
                  {children}
                </table>
              </div>
            )
          },
          thead({ children }) {
            return <thead className="bg-muted/50">{children}</thead>
          },
          tbody({ children }) {
            return <tbody>{children}</tbody>
          },
          tr({ children }) {
            return <tr className="border-b border-border/50 last:border-0">{children}</tr>
          },
          th({ children }) {
            return <th className="px-3 py-2 text-left font-semibold">{children}</th>
          },
          td({ children }) {
            return <td className="px-3 py-2">{children}</td>
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
