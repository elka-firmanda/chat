import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MessageComponent from '../../components/chat/Message';
import { useChat } from '../../hooks/useChat';
import { useSessions } from '../../hooks/useSessions';
import { useChatStore } from '../../stores/chatStore';

vi.mock('../../hooks/useChat');
vi.mock('../../hooks/useSessions');
vi.mock('../../stores/chatStore');

describe('MessageComponent', () => {
  const mockMessage = {
    id: 'msg-123',
    role: 'user' as const,
    content: 'Hello, chatbot!',
    created_at: new Date().toISOString(),
  };

  const mockAssistantMessage = {
    id: 'msg-456',
    role: 'assistant' as const,
    content: 'I am a helpful assistant.',
    agent_type: 'master',
    created_at: new Date().toISOString(),
    metadata: {
      thinking_content: 'Processing request...',
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useChat as any).mockReturnValue({
      forkConversation: vi.fn().mockResolvedValue('new-session-id'),
    });
    (useSessions as any).mockReturnValue({
      loadSessions: vi.fn().mockResolvedValue(undefined),
    });
    (useChatStore as any).mockReturnValue({
      setActiveSession: vi.fn(),
      setMessages: vi.fn(),
      activeSessionId: 'current-session',
    });
  });

  it('renders user message correctly', () => {
    render(<MessageComponent message={mockMessage} />);
    expect(screen.getByText('Hello, chatbot!')).toBeInTheDocument();
  });

  it('renders assistant message correctly', () => {
    render(<MessageComponent message={mockAssistantMessage} />);
    expect(screen.getByText('I am a helpful assistant.')).toBeInTheDocument();
  });

  it('displays agent type for assistant messages', () => {
    render(<MessageComponent message={mockAssistantMessage} />);
    expect(screen.getByText('master')).toBeInTheDocument();
  });

  it('shows copy button for assistant messages', () => {
    render(<MessageComponent message={mockAssistantMessage} />);
    const copyButton = screen.getByTitle('Copy message');
    expect(copyButton).toBeInTheDocument();
  });

  it('hides copy button for user messages', () => {
    render(<MessageComponent message={mockMessage} />);
    expect(screen.queryByTitle('Copy message')).not.toBeInTheDocument();
  });

  it('shows timestamp', () => {
    render(<MessageComponent message={mockMessage} />);
    const timestamp = screen.getByText(/\d{2}:\d{2}/);
    expect(timestamp).toBeInTheDocument();
  });

  it('applies correct styling for user messages', () => {
    const { container } = render(<MessageComponent message={mockMessage} />);
    const messageDiv = container.firstChild?.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('bg-primary');
  });

  it('applies correct styling for assistant messages', () => {
    const { container } = render(<MessageComponent message={mockAssistantMessage} />);
    const messageDiv = container.firstChild?.firstChild as HTMLElement;
    expect(messageDiv).toHaveClass('bg-muted');
  });

  it('opens context menu on button click', async () => {
    render(<MessageComponent message={mockAssistantMessage} />);
    const moreButton = screen.getByRole('button', { name: /more options/i });
    fireEvent.click(moreButton);
    expect(screen.getByText('Copy')).toBeInTheDocument();
    expect(screen.getByText('Fork')).toBeInTheDocument();
  });

  it('closes context menu when clicking outside', async () => {
    const { container } = render(<MessageComponent message={mockAssistantMessage} />);
    const moreButton = screen.getByRole('button', { name: /more options/i });
    fireEvent.click(moreButton);
    expect(screen.getByText('Copy')).toBeInTheDocument();
    const outsideDiv = container.firstChild as HTMLElement;
    fireEvent.mouseDown(outsideDiv);
    expect(screen.queryByText('Copy')).not.toBeInTheDocument();
  });
});
