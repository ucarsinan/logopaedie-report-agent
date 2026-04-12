"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatBubbleProps {
  role: string;
  content: string;
}

export function ChatBubble({ role, content }: ChatBubbleProps) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-accent px-4 py-2.5 text-sm text-white leading-relaxed">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 items-start">
      <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent">
        <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 8V4H8" />
          <rect width="16" height="12" x="4" y="8" rx="2" />
          <path d="M2 14h2M20 14h2M15 13v2M9 13v2" />
        </svg>
      </div>
      <div className="min-w-0 flex-1 text-sm leading-relaxed text-foreground">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-base font-bold text-foreground mb-2 mt-3 first:mt-0">{children}</h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-sm font-bold text-foreground mb-1.5 mt-2.5 first:mt-0">{children}</h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-sm font-semibold text-foreground/90 mb-1 mt-2 first:mt-0">{children}</h3>
            ),
            p: ({ children }) => (
              <p className="mb-2.5 last:mb-0 leading-relaxed">{children}</p>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-outside mb-2.5 space-y-1 pl-4">{children}</ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-outside mb-2.5 space-y-1 pl-4">{children}</ol>
            ),
            li: ({ children }) => (
              <li className="text-foreground/90 leading-relaxed">{children}</li>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-foreground">{children}</strong>
            ),
            em: ({ children }) => (
              <em className="italic text-foreground/80">{children}</em>
            ),
            code: ({ children }) => (
              <code className="bg-black/5 dark:bg-white/10 rounded px-1.5 py-0.5 text-xs font-mono">{children}</code>
            ),
            hr: () => <hr className="my-3 border-border/40" />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

/** Animated typing indicator for AI responses */
export function TypingIndicator() {
  return (
    <div className="flex gap-3 items-start">
      <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent">
        <svg className="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 8V4H8" />
          <rect width="16" height="12" x="4" y="8" rx="2" />
          <path d="M2 14h2M20 14h2M15 13v2M9 13v2" />
        </svg>
      </div>
      <div className="flex items-center gap-1 pt-2.5">
        <span className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0ms]" />
        <span className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:150ms]" />
        <span className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}
